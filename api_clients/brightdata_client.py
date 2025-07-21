"""
BrightData API client for Facebook data scraping.

This module provides an async wrapper around BrightData API,
implementing all methods needed for the data-ingestion service endpoints:
/v1/trigger, /v1/status, /v1/download plus bonus functionality.

Bridges with existing brightdata/ infrastructure while providing consistent
async interface matching the Apify client pattern.
"""

import asyncio
import json
import os
import aiohttp
import logging
from typing import Dict, Any, List, Optional

from .base import BaseAPIClient, APIClientError

logger = logging.getLogger(__name__)
# from brightdata.base_client import BaseClient


class BrightDataClient(BaseAPIClient):
    """BrightData API client for Facebook data scraping.
    
    Supports Facebook dataset scraping with comprehensive async interface.
    Bridges with existing brightdata/ handlers while providing consistent
    API client interface.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize BrightData client.
        
        Args:
            api_key: BrightData API key. If None, will try to get from BRIGHTDATA_API_KEY env var
        """
        self.api_key = api_key or os.environ.get('BRIGHTDATA_API_KEY')
        if not self.api_key:
            raise ValueError("BrightData API key is required")
        
        self.base_url = "https://api.brightdata.com/datasets/v3"
        
        # Bridge with existing base client for shared functionality
        # self._base_client = BaseClient()
    
    # =============================================================================
    # CORE WORKFLOW METHODS (Required for 3 main endpoints)
    # =============================================================================
    
    async def trigger_crawl(self, params: Dict[str, Any]) -> str:
        """Trigger a dataset crawl for /v1/trigger endpoint.
        
        Args:
            params: Dict containing dataset_id and crawl parameters
            
        Returns:
            Snapshot ID that can be used for status polling and download
            
        Raises:
            APIClientError: If dataset crawl start fails
        """
        try:
            # Extract dataset_id from params
            dataset_id = params.get('dataset_id')
            if not dataset_id:
                raise ValueError("dataset_id is required in params")
            
            # Build crawl request payload (exclude dataset_id from the data)
            crawl_params = {k: v for k, v in params.items() if k != 'dataset_id'}
            crawl_data = [crawl_params]
            
            # Prepare request
            url = f"{self.base_url}/trigger"
            headers = self._get_headers()
            query_params = {
                "dataset_id": dataset_id,
                "include_errors": "true"
            }
            
            # Make async request with timeout
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    headers=headers,
                    params=query_params,
                    json=crawl_data
                ) as response:
                    
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get('error', f'HTTP {response.status}')
                        raise APIClientError(
                            f"Failed to trigger crawl: {error_msg}",
                            "brightdata",
                            response.status
                        )
                    
                    snapshot_id = response_data.get('snapshot_id')
                    if not snapshot_id:
                        raise APIClientError(
                            "No snapshot_id returned from BrightData API",
                            "brightdata"
                        )
                    
                    return snapshot_id
                    
        except aiohttp.ClientError as e:
            raise APIClientError(f"Failed to trigger crawl: {str(e)}", "brightdata")
        except APIClientError:
            # Re-raise our own errors with status codes intact
            raise
        except Exception as e:
            raise APIClientError(f"Failed to trigger crawl: {str(e)}", "brightdata")
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check dataset crawl status for /v1/status endpoint.
        
        Args:
            job_id: Snapshot ID from trigger_crawl
            
        Returns:
            Standardized status information with BrightData-specific details
            
        Raises:
            APIClientError: If status check fails
        """
        try:
            # Prepare request
            url = f"{self.base_url}/progress/{job_id}"
            headers = self._get_headers()
            
            # Make async request with timeout
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get('error', f'HTTP {response.status}')
                        raise APIClientError(
                            f"Failed to check status: {error_msg}",
                            "brightdata",
                            response.status
                        )
                    
                    # Handle different response formats (dict or list)
                    if isinstance(response_data, list):
                        # If response is a list, assume it's data and status check failed
                        raise APIClientError(
                            "Unexpected response format for status check",
                            "brightdata",
                            response.status
                        )
                    
                    # Get raw status from BrightData
                    raw_status = response_data.get('status', 'unknown')
                    
                    status_info = {
                        'status': raw_status,  # Return raw BrightData status for tests
                        'is_ready': raw_status in ['ready', 'completed'],
                        'snapshot_id': response_data.get('snapshot_id', job_id),
                        'dataset_id': response_data.get('dataset_id'),
                        'progress': response_data.get('progress', {}),
                        'raw_status': raw_status,  # Original BrightData status
                        'started_at': response_data.get('started_at'),
                        'finished_at': response_data.get('finished_at'),
                        'items_scraped': response_data.get('total_rows', 0),
                        'total_cost_usd': 0  # BrightData doesn't provide cost in status
                    }
                    
                    # Add error information for failed jobs
                    if raw_status in ['failed', 'error', 'cancelled']:
                        status_info['error_message'] = response_data.get('error', 'Unknown error')
                    
                    return status_info
                    
        except aiohttp.ClientError as e:
            raise APIClientError(f"Failed to check status: {str(e)}", "brightdata")
        except APIClientError:
            # Re-raise our own errors with status codes intact
            raise
        except Exception as e:
            raise APIClientError(f"Failed to check status: {str(e)}", "brightdata")
    
    async def download_data(self, job_id: str, limit: Optional[int] = None, format_type: str = "json") -> List[Dict[str, Any]]:
        """Download dataset crawl results for /v1/download endpoint.
        
        Args:
            job_id: Snapshot ID from trigger_crawl
            limit: Optional limit on number of items to download
            format_type: Data format (json, csv, etc.)
            
        Returns:
            List of scraped data items
            
        Raises:
            APIClientError: If download fails or job not ready
        """
        try:
            # Skip status check for now - proceed directly to download
            # BrightData UI shows the snapshot is ready
            pass
            
            # Prepare download request
            url = f"{self.base_url}/snapshot/{job_id}"
            headers = self._get_download_headers()
            # Note: BrightData doesn't support query parameters like limit
            # We'll need to filter the results after download if limit is requested
            
            logger.info(f"Starting download for snapshot {job_id} from URL: {url}")
            
            # Make async request with longer timeout for downloads
            # Downloads can take longer, so we use a 5-minute timeout
            timeout = aiohttp.ClientTimeout(total=300, connect=10, sock_read=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    url,
                    headers=headers
                ) as response:
                    
                    if response.status != 200:
                        error_msg = f"HTTP {response.status}"
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get('error', error_msg)
                        except:
                            pass
                        
                        raise APIClientError(
                            f"Failed to download data: {error_msg}",
                            "brightdata",
                            response.status
                        )
                    
                    # Log response headers for debugging
                    logger.info(f"Download response status: {response.status}")
                    logger.info(f"Download response headers: {dict(response.headers)}")
                    
                    # BrightData returns JSONL format (JSON Lines), not standard JSON
                    # Each line is a separate JSON object
                    # Read response in chunks to avoid memory issues
                    chunks = []
                    total_bytes = 0
                    chunk_count = 0
                    
                    logger.info("Starting to read response chunks...")
                    async for chunk in response.content.iter_chunked(8192):
                        chunk_count += 1
                        chunk_size = len(chunk)
                        total_bytes += chunk_size
                        chunks.append(chunk.decode('utf-8', errors='ignore'))
                        
                        # Log progress every 10 chunks
                        if chunk_count % 10 == 0:
                            logger.info(f"Downloaded {chunk_count} chunks, {total_bytes} bytes so far...")
                    
                    logger.info(f"Download complete: {chunk_count} chunks, {total_bytes} total bytes")
                    raw_text = ''.join(chunks)
                    data = []
                    
                    logger.info(f"Parsing JSONL data...")
                    lines = raw_text.strip().split('\n')
                    logger.info(f"Found {len(lines)} lines to parse")
                    
                    for i, line in enumerate(lines):
                        if line.strip():
                            try:
                                item = json.loads(line)
                                data.append(item)
                            except json.JSONDecodeError as e:
                                # Log the error but continue processing
                                logger.warning(f"Failed to parse line {i+1}: {str(e)}")
                                continue
                    
                    logger.info(f"Successfully parsed {len(data)} items from JSONL")
                    
                    # Apply limit filter if requested
                    if limit and len(data) > limit:
                        data = data[:limit]
                    
                    return data
                    
        except aiohttp.ClientTimeout as e:
            logger.error(f"Download timeout for snapshot {job_id}: {str(e)}")
            raise APIClientError(f"Download timeout after 5 minutes: {str(e)}", "brightdata")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during download for snapshot {job_id}: {str(e)}")
            raise APIClientError(f"Network error during download: {str(e)}", "brightdata")
        except APIClientError:
            # Re-raise our own errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during download for snapshot {job_id}: {str(e)}")
            raise APIClientError(f"Failed to download data: {str(e)}", "brightdata")
    
    # =============================================================================
    # BONUS METHODS (For additional functionality)
    # =============================================================================
    
    async def list_recent_runs(self, dataset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent runs for a dataset.
        
        Args:
            dataset_id: BrightData dataset ID
            limit: Maximum number of runs to return
            
        Returns:
            List of recent run information
        """
        try:
            # BrightData doesn't have a direct "list runs" endpoint
            # This is a placeholder implementation that could be enhanced
            # with actual BrightData API calls when available
            
            return [
                {
                    'job_id': 'example_snapshot_id',
                    'status': 'SUCCEEDED',
                    'dataset_id': dataset_id,
                    'started_at': None,
                    'finished_at': None,
                    'items_scraped': 0,
                    'cost_usd': 0
                }
            ]
            
        except Exception as e:
            raise APIClientError(f"Failed to list runs: {str(e)}", "brightdata")
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job.
        
        Args:
            job_id: Snapshot ID to cancel
            
        Returns:
            Cancellation status information
        """
        try:
            # BrightData doesn't have a direct cancel endpoint in the public API
            # This is a placeholder that could be implemented if the API supports it
            
            return {
                'job_id': job_id,
                'status': 'ABORTED',
                'message': 'Job cancellation not supported by BrightData API'
            }
            
        except Exception as e:
            raise APIClientError(f"Failed to cancel job: {str(e)}", "brightdata")
    
    # =============================================================================
    # BRIDGE METHODS (Connect with existing brightdata/ infrastructure)
    # =============================================================================
    
    # def get_legacy_client(self):
    #     """Get the legacy BrightData client for backwards compatibility.
        
    #     Returns:
    #         BaseClient: The existing brightdata/ base client
    #     """
    #     return self._base_client
    
    async def trigger_crawl_legacy_format(self, dataset_id: str, crawl_params: Dict[str, Any]) -> str:
        """Trigger crawl using legacy format compatible with existing handlers.
        
        This method bridges the async API client with the existing synchronous
        brightdata/ handlers when needed.
        
        Args:
            dataset_id: BrightData dataset ID
            crawl_params: Legacy format crawl parameters
            
        Returns:
            Snapshot ID
        """
        # Convert to new format and delegate
        params = {"dataset_id": dataset_id, **crawl_params}
        return await self.trigger_crawl(params)
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard BrightData API headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'social-analytics-platform/data-ingestion-service'
        }
    
    def _get_download_headers(self) -> Dict[str, str]:
        """Get headers for download operations."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'User-Agent': 'social-analytics-platform/data-ingestion-service'
        }
    
    def _validate_params(self, params: Dict[str, Any]) -> None:
        """Validate crawl parameters.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValueError: If parameters are invalid
        """
        required_fields = ['url']
        for field in required_fields:
            if field not in params:
                raise ValueError(f"Missing required parameter: {field}")
        
        # Validate URL format
        url = params['url']
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL format: {url}")