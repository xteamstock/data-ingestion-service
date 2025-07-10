"""
Main BrightData API client for Data Ingestion Service.

This module provides the main facade client that coordinates all BrightData
API operations by delegating to specialized handler classes.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from .handlers import ConnectionHandler, CrawlHandler, DownloadHandler

logger = logging.getLogger(__name__)


class BrightDataClient:
    """
    Main facade client for interacting with BrightData API.
    
    This class coordinates all BrightData API operations by delegating to
    specialized handler classes. It maintains backwards compatibility while
    providing a clean, modular architecture for API operations.
    
    The client uses a handler pattern with:
    - ConnectionHandler: API connectivity and health checks
    - CrawlHandler: Crawl job triggering and monitoring
    - DownloadHandler: Data download operations
    
    Example:
        from brightdata import BrightDataClient
        
        client = BrightDataClient()
        result = client.test_api_connection()
        if result['status'] == 'success':
            snapshot_id, error = client.trigger_crawl(dataset_id, params)
    """
    
    def __init__(self):
        """
        Initialize BrightData client with handler instances.
        
        Sets up the client with specialized handlers for different
        categories of BrightData API operations.
        """
        self.connection_handler = ConnectionHandler()
        self.crawl_handler = CrawlHandler()
        self.download_handler = DownloadHandler()
    
    def test_api_connection(self) -> Dict[str, Any]:
        """
        Test BrightData API connection and authentication.
        
        Delegates to ConnectionHandler for API connectivity testing.
        
        Returns:
            Dict[str, Any]: Standardized response with connection test results
        """
        return self.connection_handler.test_api_connection()
    
    def download_snapshot(self, snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Download snapshot data from BrightData API.
        
        Delegates to DownloadHandler for snapshot download operations.
        
        Args:
            snapshot_id (Optional[str]): The snapshot ID to download
        
        Returns:
            Dict[str, Any]: Standardized response with download results
        """
        return self.download_handler.download_snapshot(snapshot_id)
    
    def trigger_crawl(self, dataset_id: str, crawl_params: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Trigger a new crawl job on BrightData platform.
        
        Delegates to CrawlHandler for crawl job triggering.
        
        Args:
            dataset_id (str): The BrightData dataset identifier
            crawl_params (Dict[str, Any]): Parameters for the crawl job
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (snapshot_id, error_message)
        """
        return self.crawl_handler.trigger_crawl(dataset_id, crawl_params)
    
    def poll_crawl_status(self, snapshot_id: str) -> Tuple[bool, Optional[str]]:
        """
        Poll crawl job status until completion or timeout.
        
        Delegates to CrawlHandler for status polling operations.
        
        Args:
            snapshot_id (str): The unique identifier for the crawl job to monitor
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        return self.crawl_handler.poll_crawl_status(snapshot_id)
    
    def download_crawl_data(self, snapshot_id: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Download collected data from a completed crawl job.
        
        Delegates to DownloadHandler for crawl data download operations.
        
        Args:
            snapshot_id (str): The unique identifier for the completed crawl job
        
        Returns:
            Tuple[Optional[List[Dict]], Optional[str]]: (data, error_message)
        """
        return self.download_handler.download_crawl_data(snapshot_id)