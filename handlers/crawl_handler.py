"""
Main crawl handler for Data Ingestion Service.

This module coordinates BrightData API operations and manages
the complete crawl lifecycle from triggering to data download.
"""

import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.cloud import storage
from google.cloud import bigquery

from brightdata.client import BrightDataClient
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
        self.brightdata_client = BrightDataClient()
        self.storage_client = storage.Client()
        self.bigquery_client = bigquery.Client()
        self.event_publisher = EventPublisher()
        
        # Configuration from environment variables
        self.raw_data_bucket = os.getenv('GCS_BUCKET_RAW_DATA', 'social-analytics-raw-data')
        self.bigquery_dataset = os.getenv('BIGQUERY_DATASET', 'social_analytics')
        self.metadata_table = "crawl_metadata"
        self.raw_data_table = "raw_data_crawl_snapshots"
        
        # In-memory storage for local testing (fallback)
        self.local_metadata_store = {}
    
    def trigger_crawl(self, crawl_params: Dict[str, Any]) -> Dict[str, Any]:
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
            
            # Extract dataset ID from params or use default
            dataset_id = crawl_params.get('dataset_id', 'gd_default')
            
            # Prepare crawl parameters in BrightData format
            brightdata_params = {
                'url': crawl_params.get('url'),
                'num_of_posts': crawl_params.get('num_of_posts', 10),
                'start_date': self._convert_date_format(crawl_params.get('start_date')),
                'end_date': self._convert_date_format(crawl_params.get('end_date')),
                'include_profile_data': crawl_params.get('include_profile_data', True)
            }
            
            logger.info(f"Triggering crawl {crawl_id} with params: {brightdata_params}")
            
            # Trigger crawl via BrightData API
            snapshot_id, error = self.brightdata_client.trigger_crawl(dataset_id, brightdata_params)
            
            if error:
                logger.error(f"Failed to trigger crawl: {error}")
                return {
                    'status': 'error',
                    'message': f'Failed to trigger crawl: {error}',
                    'crawl_id': crawl_id
                }
            
            # Store crawl metadata
            try:
                self._store_crawl_metadata(crawl_id, snapshot_id, crawl_params)
                logger.info(f"Crawl metadata stored successfully for {crawl_id}")
            except Exception as e:
                logger.error(f"Failed to store crawl metadata: {str(e)}")
                # Continue anyway - this is not a blocking error for trigger
            
            logger.info(f"Crawl triggered successfully: {crawl_id} -> {snapshot_id}")
            
            return {
                'status': 'success',
                'message': 'Crawl triggered successfully',
                'crawl_id': crawl_id,
                'snapshot_id': snapshot_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error triggering crawl: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error triggering crawl: {str(e)}',
                'crawl_id': crawl_id if 'crawl_id' in locals() else 'unknown'
            }
    
    def download_data(self, crawl_id: str) -> Dict[str, Any]:
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
            
            logger.info(f"Downloading data for crawl {crawl_id} (snapshot: {snapshot_id})")
            
            # Poll crawl status first
            success, error = self.brightdata_client.poll_crawl_status(snapshot_id)
            if not success:
                return {
                    'status': 'error',
                    'message': f'Crawl not ready for download: {error}'
                }
            
            # Download data from BrightData
            data, error = self.brightdata_client.download_crawl_data(snapshot_id)
            if error:
                return {
                    'status': 'error',
                    'message': f'Failed to download data: {error}'
                }
            
            # Store raw data in GCS
            gcs_path = self._store_raw_data_gcs(crawl_id, snapshot_id, data)
            
            # Store metadata in BigQuery
            self._store_crawl_snapshot_bigquery(crawl_id, snapshot_id, data, gcs_path, crawl_metadata)
            
            # Calculate statistics
            post_count = len(data) if isinstance(data, list) else 0
            media_count = self._count_media_files(data)
            
            logger.info(f"Data downloaded successfully: {crawl_id} -> {gcs_path}")
            
            # Publish data ingestion completed event (following EVENT_API_DESIGN.md schema)
            try:
                self.event_publisher.publish_data_ingestion_completed(
                    crawl_id=crawl_id,
                    snapshot_id=snapshot_id, 
                    gcs_path=gcs_path,
                    post_count=post_count,
                    media_count=media_count,
                    crawl_metadata=crawl_metadata
                )
                logger.info(f"Published data.ingestion.completed event for crawl {crawl_id}")
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
    
    def _store_raw_data_gcs(self, crawl_id: str, snapshot_id: str, data: List[Dict]) -> str:
        """Store raw BrightData snapshot as-is in GCS with proper UTF-8 encoding."""
        import time
        from google.api_core import retry
        from google.cloud.exceptions import GoogleCloudError
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                bucket = self.storage_client.bucket(self.raw_data_bucket)
                
                # Simple timestamp-based path for raw snapshots
                timestamp = datetime.utcnow()
                blob_name = f"raw_snapshots/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/snapshot_{snapshot_id}.json"
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
    
    def _count_media_files(self, data: List[Dict]) -> int:
        """Count media files in the crawl data."""
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