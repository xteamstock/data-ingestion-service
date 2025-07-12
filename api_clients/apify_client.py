"""
Apify API client for TikTok and YouTube data scraping.

This module provides an async wrapper around the Apify Python client,
implementing all methods needed for the data-ingestion service endpoints:
/v1/trigger, /v1/status, /v1/download plus bonus functionality.
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from apify_client import ApifyClient

from .base import BaseAPIClient, APIClientError


class ApifyAPIClient(BaseAPIClient):
    """Apify API client for social media data scraping.
    
    Supports TikTok (clockworks/tiktok-scraper) and YouTube (streamers/youtube-scraper)
    actors with comprehensive async interface.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize Apify client.
        
        Args:
            api_token: Apify API token. If None, will try to get from APIFY_API_TOKEN env var
        """
        token = api_token or os.environ.get('APIFY_API_TOKEN')
        if not token:
            raise ValueError("Apify API token is required")
        
        self.client = ApifyClient(token)
    
    # =============================================================================
    # CORE WORKFLOW METHODS (Required for 3 main endpoints)
    # =============================================================================
    
    async def trigger_crawl(self, actor_id: str, params: Dict[str, Any]) -> str:
        """Trigger an actor run for /v1/trigger endpoint.
        
        Args:
            actor_id: Apify actor ID (e.g., "clockworks/tiktok-scraper")
            params: Actor-specific input parameters
            
        Returns:
            Run ID that can be used for status polling and download
            
        Raises:
            APIClientError: If actor start fails
        """
        try:
            # Run in executor since Apify SDK is synchronous
            loop = asyncio.get_event_loop()
            run_info = await loop.run_in_executor(
                None,
                lambda: self.client.actor(actor_id).start(run_input=params)
            )
            
            return run_info['id']
            
        except Exception as e:
            raise APIClientError(f"Failed to trigger crawl: {str(e)}", "apify")
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check actor run status for /v1/status endpoint.
        
        Args:
            job_id: Run ID from trigger_crawl
            
        Returns:
            Standardized status information with Apify-specific details
            
        Raises:
            APIClientError: If status check fails
        """
        try:
            # Run in executor since Apify SDK is synchronous
            loop = asyncio.get_event_loop()
            run_info = await loop.run_in_executor(
                None,
                lambda: self.client.run(job_id).get()
            )
            
            # Extract key information and standardize format
            status_info = {
                'status': run_info['status'],
                'is_ready': run_info['status'] == 'SUCCEEDED',
                'dataset_id': run_info.get('defaultDatasetId'),
                'started_at': run_info.get('startedAt'),
                'finished_at': run_info.get('finishedAt'),
                'runtime_secs': run_info.get('stats', {}).get('runtimeMillis', 0) // 1000,
                'items_scraped': run_info.get('stats', {}).get('items', 0),
                'compute_units': run_info.get('usage', {}).get('COMPUTE_UNITS', 0),
                'total_cost_usd': run_info.get('usageTotalUsd', 0),
                'exit_code': run_info.get('exitCode')
            }
            
            # Add error information for failed runs
            if run_info['status'] in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                status_info['error_message'] = run_info.get('statusMessage', 'Unknown error')
            
            return status_info
            
        except Exception as e:
            raise APIClientError(f"Failed to check status: {str(e)}", "apify")
    
    async def download_data(self, job_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Download actor run results for /v1/download endpoint.
        
        Args:
            job_id: Run ID from trigger_crawl
            limit: Optional limit on number of items to download
            
        Returns:
            List of scraped data items
            
        Raises:
            APIClientError: If download fails or job not ready
        """
        try:
            # First check if job is completed
            run_info = await self._get_run_info(job_id)
            
            if run_info['status'] != 'SUCCEEDED':
                raise APIClientError(
                    f"Job not completed yet. Current status: {run_info['status']}",
                    "apify"
                )
            
            dataset_id = run_info.get('defaultDatasetId')
            if not dataset_id:
                raise APIClientError("No dataset available for this job", "apify")
            
            # Download dataset items
            loop = asyncio.get_event_loop()
            
            # Prepare list_items parameters
            list_params = {}
            if limit:
                list_params['limit'] = limit
            
            dataset_items = await loop.run_in_executor(
                None,
                lambda: self.client.dataset(dataset_id).list_items(**list_params)
            )
            
            return dataset_items.items
            
        except APIClientError:
            # Re-raise our own errors
            raise
        except Exception as e:
            raise APIClientError(f"Failed to download data: {str(e)}", "apify")
    
    # =============================================================================
    # BONUS METHODS (For additional functionality)
    # =============================================================================
    
    async def list_recent_runs(self, actor_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent runs for an actor.
        
        Args:
            actor_id: Apify actor ID
            limit: Maximum number of runs to return
            
        Returns:
            List of recent run information
        """
        try:
            loop = asyncio.get_event_loop()
            runs_response = await loop.run_in_executor(
                None,
                lambda: self.client.actor(actor_id).runs().list(limit=limit)
            )
            
            # Standardize format
            runs = []
            for run in runs_response.items:
                runs.append({
                    'job_id': run['id'],
                    'status': run['status'],
                    'started_at': run.get('startedAt'),
                    'finished_at': run.get('finishedAt'),
                    'items_scraped': run.get('stats', {}).get('items', 0),
                    'cost_usd': run.get('usageTotalUsd', 0)
                })
            
            return runs
            
        except Exception as e:
            raise APIClientError(f"Failed to list runs: {str(e)}", "apify")
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job.
        
        Args:
            job_id: Run ID to cancel
            
        Returns:
            Cancellation status information
        """
        try:
            loop = asyncio.get_event_loop()
            abort_info = await loop.run_in_executor(
                None,
                lambda: self.client.run(job_id).abort()
            )
            
            return {
                'job_id': job_id,
                'status': abort_info['status'],
                'message': abort_info.get('statusMessage', 'Job cancellation requested')
            }
            
        except Exception as e:
            raise APIClientError(f"Failed to cancel job: {str(e)}", "apify")
    
    async def export_dataset(self, dataset_id: str, format_type: str = 'json') -> Dict[str, Any]:
        """Export dataset to different format.
        
        Args:
            dataset_id: Dataset ID to export
            format_type: Export format (json, csv, xml, xlsx)
            
        Returns:
            Export information including download URL
        """
        try:
            loop = asyncio.get_event_loop()
            export_info = await loop.run_in_executor(
                None,
                lambda: self.client.dataset(dataset_id).export_to(format=format_type)
            )
            
            return {
                'format': format_type,
                'download_url': export_info['url'],
                'size_bytes': export_info['size'],
                'item_count': export_info['itemCount'],
                'content_type': export_info['contentType']
            }
            
        except Exception as e:
            raise APIClientError(f"Failed to export dataset: {str(e)}", "apify")
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    async def _get_run_info(self, job_id: str) -> Dict[str, Any]:
        """Get run information (helper method).
        
        Args:
            job_id: Run ID
            
        Returns:
            Raw run information from Apify
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.run(job_id).get()
        )