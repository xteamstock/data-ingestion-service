"""
Main crawl handler for Data Ingestion Service.

This module coordinates BrightData API operations and manages
the complete crawl lifecycle from triggering to data download.
"""

import os
import logging
import json
import uuid
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage
from google.cloud import bigquery

from platforms.registry import PlatformRegistry, get_platform_handler
from api_clients.brightdata_client import BrightDataClient
from api_clients.apify_client import ApifyAPIClient
from platforms.base import APIProvider
from events.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class CrawlHandler:
    """
    Main handler for crawl operations in the Data Ingestion Service.
    
    This class coordinates BrightData API operations and manages
    data storage in GCS and BigQuery.
    """
    
    def __init__(self):
        """Initialize the crawl handler with necessary clients."""
        # Load platform configurations
        if not PlatformRegistry.is_initialized():
            PlatformRegistry.load_default_config()
        
        # Initialize API clients
        self.brightdata_client = BrightDataClient(
            api_key=os.getenv('BRIGHTDATA_API_KEY')
        )
        self.apify_client = ApifyAPIClient(
            api_token=os.getenv('APIFY_API_TOKEN')
        )
        
        # Initialize Google Cloud clients
        self.storage_client = storage.Client()
        self.bigquery_client = bigquery.Client()
        self.event_publisher = EventPublisher()
        
        # Configuration from environment variables
        self.raw_data_bucket = os.getenv('GCS_BUCKET_RAW_DATA', 'social-analytics-raw-data')
        self.bigquery_dataset = os.getenv('BIGQUERY_DATASET', 'social_analytics')
        self.metadata_table = "crawl_metadata"
        self.raw_data_table = "raw_data_crawl_snapshots"
        
        # Background processing configuration
        self.background_polling_enabled = os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
        self.background_max_workers = int(os.getenv('BACKGROUND_MAX_WORKERS', '10'))
        self.background_poll_interval = int(os.getenv('BACKGROUND_POLL_INTERVAL', '30'))
        self.background_max_polls = int(os.getenv('BACKGROUND_MAX_POLLS', '120'))
        
        # In-memory storage for local testing (fallback)
        self.local_metadata_store = {}
        
        # Background processing executor
        self.executor = ThreadPoolExecutor(max_workers=self.background_max_workers)
    
    async def trigger_crawl(self, crawl_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a new crawl job and return the crawl details.
        
        Args:
            crawl_params (Dict[str, Any]): Parameters for the crawl job
        
        Returns:
            Dict[str, Any]: Crawl result with crawl_id and snapshot_id
        """
        try:
            # Generate unique crawl ID
            crawl_id = str(uuid.uuid4())
            
            # Extract platform from request (default to facebook for backward compatibility)
            platform = crawl_params.get('platform', 'facebook').lower()
            
            # Get platform handler
            platform_handler = get_platform_handler(platform)
            if not platform_handler:
                logger.error(f"Unsupported platform: {platform}")
                return {
                    'status': 'error',
                    'message': f'Unsupported platform: {platform}',
                    'crawl_id': crawl_id
                }
            
            # Validate parameters
            if not platform_handler.validate_params(crawl_params):
                logger.error(f"Invalid parameters for platform: {platform}")
                return {
                    'status': 'error',
                    'message': f'Invalid parameters for platform: {platform}',
                    'crawl_id': crawl_id
                }
            
            # Get appropriate API client based on platform
            if platform_handler.config.api_provider == APIProvider.BRIGHTDATA:
                api_client = self.brightdata_client
                params = platform_handler.prepare_request_params(crawl_params)
                # Add dataset_id to params for BrightData client
                params['dataset_id'] = platform_handler.config.dataset_id
                
                logger.info(f"Triggering {platform} crawl {crawl_id} via BrightData with params: {params}")
                
                # Trigger crawl via BrightData API
                snapshot_id = await api_client.trigger_crawl(params)
                error = None
                
            else:  # Apify
                api_client = self.apify_client
                params = platform_handler.prepare_request_params(crawl_params)
                actor_id = platform_handler.config.dataset_id  # Actor ID for Apify
                
                logger.info(f"Triggering {platform} crawl {crawl_id} via Apify with params: {params}")
                
                # Trigger crawl via Apify API
                job_id = await api_client.trigger_crawl(actor_id, params)
                snapshot_id = job_id  # For Apify, job_id serves as snapshot_id
                error = None
            
            if error:
                logger.error(f"Failed to trigger crawl: {error}")
                return {
                    'status': 'error',
                    'message': f'Failed to trigger crawl: {error}',
                    'crawl_id': crawl_id
                }
            
            # Store crawl metadata with platform info
            crawl_params['platform'] = platform
            try:
                self._store_crawl_metadata(crawl_id, snapshot_id, crawl_params)
                logger.info(f"Crawl metadata stored successfully for {crawl_id}")
            except Exception as e:
                logger.error(f"Failed to store crawl metadata: {str(e)}")
                # Continue anyway - this is not a blocking error for trigger
            
            # If background polling is enabled, start polling in background
            if self.background_polling_enabled:
                self.executor.submit(self._background_poll_and_download, crawl_id, snapshot_id, platform_handler, api_client)
                logger.info(f"Started background polling for crawl {crawl_id}")
            
            logger.info(f"Crawl triggered successfully: {crawl_id} -> {snapshot_id}")
            
            return {
                'status': 'success',
                'message': 'Crawl triggered successfully',
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'platform': platform,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error triggering crawl: {str(e)}")
            
            # Update status to failed if crawl_id exists
            if 'crawl_id' in locals():
                self._update_crawl_status(crawl_id, 'failed', str(e))
            
            return {
                'status': 'error',
                'message': f'Error triggering crawl: {str(e)}',
                'crawl_id': crawl_id if 'crawl_id' in locals() else 'unknown'
            }
    
    def _background_poll_and_download(self, crawl_id: str, snapshot_id: str, platform_handler, api_client):
        """Background polling and download task."""
        import time
        
        poll_count = 0
        while poll_count < self.background_max_polls:
            try:
                time.sleep(self.background_poll_interval)
                poll_count += 1
                
                logger.info(f"Polling status for {crawl_id} (attempt {poll_count}/{self.background_max_polls})")
                
                # Check status based on API provider
                if platform_handler.config.api_provider == APIProvider.BRIGHTDATA:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    status_result = loop.run_until_complete(api_client.check_status(snapshot_id))
                    is_ready = status_result.get('is_ready', False)
                else:  # Apify
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    status_result = loop.run_until_complete(api_client.check_status(snapshot_id))
                    is_ready = status_result.get('is_ready', False)
                
                if is_ready:
                    logger.info(f"Crawl {crawl_id} is ready for download")
                    # Trigger download
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._async_download_data(crawl_id))
                    break
                    
            except Exception as e:
                logger.error(f"Error in background polling for {crawl_id}: {str(e)}")
                break
        
        if poll_count >= self.background_max_polls:
            logger.error(f"Max polling attempts reached for {crawl_id}")
            # Publish failure event
            try:
                self.event_publisher.publish_data_ingestion_failed(
                    crawl_id=crawl_id,
                    snapshot_id=snapshot_id,
                    error="Max polling attempts reached"
                )
            except Exception:
                pass
    
    async def download_data(self, crawl_id: str) -> Dict[str, Any]:
        """Async wrapper for download_data."""
        return await self._async_download_data(crawl_id)
    
    async def _async_download_data(self, crawl_id: str) -> Dict[str, Any]:
        """
        Download crawl data and store it in GCS and BigQuery.
        
        Args:
            crawl_id (str): The crawl ID to download data for
        
        Returns:
            Dict[str, Any]: Download result with GCS path and metadata
        """
        try:
            # Get crawl metadata
            crawl_metadata = self._get_crawl_metadata(crawl_id)
            if not crawl_metadata:
                return {
                    'status': 'error',
                    'message': f'Crawl metadata not found for {crawl_id}'
                }
            
            snapshot_id = crawl_metadata['snapshot_id']
            platform = crawl_metadata.get('crawl_params', {}).get('platform', 'facebook')
            
            # Get platform handler
            platform_handler = get_platform_handler(platform)
            if not platform_handler:
                return {
                    'status': 'error',
                    'message': f'Platform handler not found for: {platform}'
                }
            
            logger.info(f"Downloading data for {platform} crawl {crawl_id} (snapshot: {snapshot_id})")
            
            # Update status to downloading
            self._update_crawl_status(crawl_id, 'downloading')
            
            # Get appropriate API client
            if platform_handler.config.api_provider == APIProvider.BRIGHTDATA:
                api_client = self.brightdata_client
                
                # Check status first
                status_result = await api_client.check_status(snapshot_id)
                if not status_result.get('is_ready', False):
                    return {
                        'status': 'error',
                        'message': f'Crawl not ready for download: {status_result.get("status")}'
                    }
                
                # Download data
                data = await api_client.download_data(snapshot_id)
                
            else:  # Apify
                api_client = self.apify_client
                
                # Check status first
                status_result = await api_client.check_status(snapshot_id)
                if not status_result.get('is_ready', False):
                    return {
                        'status': 'error',
                        'message': f'Crawl not ready for download: {status_result.get("status")}'
                    }
                
                # Download data
                data = await api_client.download_data(snapshot_id)
            
            if not data:
                return {
                    'status': 'error',
                    'message': 'No data received from API'
                }
            
            # Parse API response using platform handler
            data = platform_handler.parse_api_response(data)
            
            # Update status to downloaded
            self._update_crawl_status(crawl_id, 'downloaded')
            
            # Store raw data in GCS using hierarchical path
            crawl_params = crawl_metadata.get('crawl_params', {})
            gcs_path = self._store_raw_data_gcs(
                crawl_id=crawl_id,
                snapshot_id=snapshot_id,
                data=data,
                platform_handler=platform_handler,
                competitor=crawl_params.get('competitor', 'unknown'),
                brand=crawl_params.get('brand', 'unknown'),
                category=crawl_params.get('category', 'unknown')
            )
            
            # Update status to uploaded
            self._update_crawl_status(crawl_id, 'uploaded')
            
            # Store metadata in BigQuery
            self._store_crawl_snapshot_bigquery(crawl_id, snapshot_id, data, gcs_path, crawl_metadata)
            
            # Calculate statistics using platform-specific logic
            post_count = len(data) if isinstance(data, list) else 0
            media_count = self._count_media_files_platform_aware(data, platform_handler)
            
            logger.info(f"Data downloaded successfully: {crawl_id} -> {gcs_path}")
            
            # Publish data ingestion completed event (following EVENT_API_DESIGN.md schema)
            try:
                # Include platform metadata in event
                event_metadata = crawl_metadata.copy()
                event_metadata['platform'] = platform
                
                self.event_publisher.publish_data_ingestion_completed(
                    crawl_id=crawl_id,
                    snapshot_id=snapshot_id, 
                    gcs_path=gcs_path,
                    post_count=post_count,
                    media_count=media_count,
                    crawl_metadata=event_metadata
                )
                logger.info(f"Published data.ingestion.completed event for crawl {crawl_id}")
                
                # Update status to completed after successful event publishing
                self._update_crawl_status(crawl_id, 'completed')
            except Exception as e:
                logger.error(f"Failed to publish data.ingestion.completed event: {str(e)}")
                # Don't fail the entire operation for event publishing failure
            
            return {
                'status': 'success',
                'message': 'Data downloaded successfully',
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'gcs_path': gcs_path,
                'post_count': post_count,
                'media_count': media_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error downloading data: {str(e)}")
            
            # Update status to failed with error message
            self._update_crawl_status(crawl_id, 'failed', str(e))
            
            # Also publish failure event
            try:
                self.event_publisher.publish_data_ingestion_failed(
                    crawl_id=crawl_id,
                    snapshot_id=snapshot_id if 'snapshot_id' in locals() else None,
                    error=str(e)
                )
            except Exception:
                pass  # Don't fail on event publishing error
            
            return {
                'status': 'error',
                'message': f'Error downloading data: {str(e)}',
                'crawl_id': crawl_id
            }
    
    def _store_crawl_metadata(self, crawl_id: str, snapshot_id: str, crawl_params: Dict[str, Any]):
        """Store crawl metadata in BigQuery as primary store."""
        try:
            # Prepare metadata for BigQuery
            table_id = f"{self.bigquery_client.project}.{self.bigquery_dataset}.{self.metadata_table}"
            
            rows_to_insert = [{
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'platform': crawl_params.get('platform', 'unknown'),
                'competitor': crawl_params.get('competitor', 'unknown'),
                'brand': crawl_params.get('brand', 'unknown'),
                'category': crawl_params.get('category', 'unknown'),
                'crawl_params': json.dumps(crawl_params),
                'created_at': datetime.utcnow().isoformat(),
                'status': 'triggered',
                'updated_at': datetime.utcnow().isoformat()
            }]
            
            # Insert into BigQuery
            errors = self.bigquery_client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                raise Exception(f"BigQuery insert errors: {errors}")
            
            logger.info(f"Crawl metadata stored in BigQuery: {crawl_id}")
            
        except Exception as e:
            # Fallback to local storage for testing
            logger.warning(f"Failed to store in BigQuery, using local storage: {str(e)}")
            metadata = {
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'crawl_params': crawl_params,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'triggered'
            }
            self.local_metadata_store[crawl_id] = metadata
            logger.info(f"Crawl metadata stored locally: {crawl_id}")
    
    def _get_crawl_metadata(self, crawl_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve crawl metadata from BigQuery or local storage."""
        try:
            # Try to get from BigQuery first
            query = f"""
            SELECT crawl_id, snapshot_id, platform, competitor, brand, category, crawl_params, created_at, status
            FROM `{self.bigquery_client.project}.{self.bigquery_dataset}.{self.metadata_table}`
            WHERE crawl_id = @crawl_id
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("crawl_id", "STRING", crawl_id)
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = list(query_job)
            
            if results:
                row = results[0]
                metadata = {
                    'crawl_id': row.crawl_id,
                    'snapshot_id': row.snapshot_id,
                    'crawl_params': json.loads(row.crawl_params) if row.crawl_params else {},
                    'created_at': row.created_at,
                    'status': row.status
                }
                logger.info(f"Retrieved crawl metadata from BigQuery: {crawl_id}")
                return metadata
            else:
                logger.warning(f"Crawl metadata not found in BigQuery: {crawl_id}")
                
        except Exception as e:
            logger.warning(f"Error retrieving crawl metadata from BigQuery: {str(e)}")
        
        # Fallback to local storage
        if crawl_id in self.local_metadata_store:
            logger.info(f"Retrieved crawl metadata from local storage: {crawl_id}")
            return self.local_metadata_store[crawl_id]
        
        logger.error(f"Crawl metadata not found anywhere: {crawl_id}")
        return None
    
    def _store_raw_data_gcs(self, crawl_id: str, snapshot_id: str, data: List[Dict], 
                           platform_handler, competitor: str, brand: str, category: str) -> str:
        """Store raw data in GCS with hierarchical path structure."""
        import time
        from google.api_core import retry
        from google.cloud.exceptions import GoogleCloudError
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                bucket = self.storage_client.bucket(self.raw_data_bucket)
                
                # Generate hierarchical storage path using platform handler
                timestamp = datetime.utcnow()
                blob_name = platform_handler.get_storage_path(
                    snapshot_id=snapshot_id,
                    competitor=competitor,
                    brand=brand,
                    category=category,
                    timestamp=timestamp
                )
                blob = bucket.blob(blob_name)
                
                # Store raw data exactly as received from BrightData
                # No processing, no grouping - just preserve the original data
                record_count = len(data) if isinstance(data, list) else 'unknown'
                logger.info(f"Storing raw snapshot {snapshot_id} with {record_count} records")
                
                # Use ensure_ascii=False to preserve Unicode characters exactly as received
                json_data = json.dumps(data, indent=2, ensure_ascii=False)
                
                # Store with proper UTF-8 encoding
                blob.upload_from_string(
                    json_data,
                    content_type='application/json; charset=utf-8',
                    retry=retry.Retry(
                        predicate=retry.if_exception_type(GoogleCloudError),
                        deadline=300.0  # 5 minutes
                    )
                )
                
                gcs_path = f"gs://{self.raw_data_bucket}/{blob_name}"
                logger.info(f"Raw snapshot stored: {gcs_path} ({record_count} records)")
                
                return gcs_path
                
            except Exception as e:
                logger.warning(f"GCS upload attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"All GCS upload attempts failed: {str(e)}")
                    raise
    
    def _store_crawl_snapshot_bigquery(self, crawl_id: str, snapshot_id: str, data: List[Dict], gcs_path: str, metadata: Dict[str, Any]):
        """Store crawl snapshot record in BigQuery raw_data_crawl_snapshots table."""
        try:
            table_id = f"{self.bigquery_client.project}.{self.bigquery_dataset}.{self.raw_data_table}"
            
            rows_to_insert = [{
                'snapshot_id': snapshot_id,
                'crawl_id': crawl_id,
                'platform': metadata['crawl_params'].get('platform', 'unknown'),
                'competitor': metadata['crawl_params'].get('competitor', 'unknown'),
                'brand': metadata['crawl_params'].get('brand', 'unknown'),
                'category': metadata['crawl_params'].get('category', 'unknown'),
                'raw_data': json.dumps(data) if len(json.dumps(data)) < 1000000 else '{}',  # Limit size
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'file_path': gcs_path,
                'status': 'completed'
            }]
            
            errors = self.bigquery_client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.info(f"Crawl snapshot stored in BigQuery: {snapshot_id}")
                
        except Exception as e:
            logger.error(f"Error storing crawl snapshot in BigQuery: {str(e)}")
    
    def _update_crawl_status(self, crawl_id: str, status: str, error_message: str = None):
        """
        Record crawl status by inserting new record to crawl_metadata table.
        
        Since BigQuery streaming buffer doesn't allow UPDATE operations,
        we insert a new row for each status change and query for the latest status.
        
        Args:
            crawl_id: The crawl ID to update
            status: New status (triggered, downloading, downloaded, uploading, uploaded, completed, failed)
            error_message: Optional error message for failed status
        """
        try:
            # Insert new status record into crawl_metadata table
            table_id = f"{self.bigquery_client.project}.{self.bigquery_dataset}.{self.metadata_table}"
            
            # Get original crawl params if they exist
            crawl_params = {}
            snapshot_id = f"status_update_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            if crawl_id in self.local_metadata_store:
                original = self.local_metadata_store[crawl_id]
                crawl_params = original.get('crawl_params', {})
                snapshot_id = original.get('snapshot_id', snapshot_id)
            
            rows_to_insert = [{
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'platform': crawl_params.get('platform', 'unknown'),
                'competitor': crawl_params.get('competitor', 'unknown'),
                'brand': crawl_params.get('brand', 'unknown'),
                'category': crawl_params.get('category', 'unknown'),
                'crawl_params': json.dumps(crawl_params),
                'created_at': datetime.utcnow().isoformat(),
                'status': status,
                'updated_at': datetime.utcnow().isoformat(),
                'error_message': error_message
            }]
            
            # Insert status record
            errors = self.bigquery_client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                logger.warning(f"BigQuery status insert errors: {errors}")
            else:
                logger.info(f"Recorded status '{status}' for {crawl_id}")
            
            # Also update local store
            if crawl_id not in self.local_metadata_store:
                self.local_metadata_store[crawl_id] = {}
                
            self.local_metadata_store[crawl_id]['status'] = status
            self.local_metadata_store[crawl_id]['updated_at'] = datetime.utcnow().isoformat()
            if error_message:
                self.local_metadata_store[crawl_id]['error_message'] = error_message
                    
        except Exception as e:
            logger.error(f"Failed to record crawl status: {str(e)}")
            
            # Fallback: Always update local store
            if crawl_id not in self.local_metadata_store:
                self.local_metadata_store[crawl_id] = {}
            
            self.local_metadata_store[crawl_id]['status'] = status
            self.local_metadata_store[crawl_id]['updated_at'] = datetime.utcnow().isoformat()
            if error_message:
                self.local_metadata_store[crawl_id]['error_message'] = error_message
            
            logger.info(f"Status '{status}' recorded in local store for {crawl_id}")
    
    def _count_media_files(self, data: List[Dict]) -> int:
        """Count media files in the crawl data (legacy method for backward compatibility)."""
        media_count = 0
        try:
            for item in data:
                if isinstance(item, dict) and 'attachments' in item:
                    attachments = item['attachments']
                    if isinstance(attachments, list):
                        media_count += len(attachments)
        except Exception as e:
            logger.error(f"Error counting media files: {str(e)}")
        
        return media_count
    
    def _count_media_files_platform_aware(self, data: List[Dict], platform_handler) -> int:
        """Count media files using platform-specific logic."""
        media_count = 0
        try:
            for item in data:
                if isinstance(item, dict):
                    media_info = platform_handler.extract_media_info(item)
                    media_count += media_info.get('media_count', 0)
        except Exception as e:
            logger.error(f"Error counting media files: {str(e)}")
        
        return media_count
    
    def _convert_date_format(self, date_str: str) -> str:
        """
        Convert date from YYYY-MM-DD format to MM-DD-YYYY format for BrightData API.
        
        Args:
            date_str (str): Date in YYYY-MM-DD format
            
        Returns:
            str: Date in MM-DD-YYYY format
        """
        try:
            if not date_str:
                return None
            
            # Parse YYYY-MM-DD format
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Convert to MM-DD-YYYY format
            return date_obj.strftime('%m-%d-%Y')
        except Exception as e:
            logger.error(f"Error converting date format: {str(e)}")
            return date_str  # Return original if conversion fails