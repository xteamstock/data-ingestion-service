"""
Crawl handler for BrightData API crawl operations.

This module provides functionality for triggering crawl jobs,
monitoring their progress, and managing the complete crawl lifecycle
on the BrightData platform.
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from ..base_client import BaseClient

logger = logging.getLogger(__name__)


class CrawlHandler(BaseClient):
    """
    Handler for BrightData API crawl operations.
    
    This class manages crawl job triggering, status monitoring, and
    lifecycle management for BrightData crawl operations.
    """
    
    def trigger_crawl(self, dataset_id: str, crawl_params: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Trigger a new crawl job on BrightData platform.
        
        Args:
            dataset_id (str): The BrightData dataset identifier (e.g., "gd_abc123")
            crawl_params (Dict[str, Any]): Parameters for the crawl job including:
                - url: Target URL to crawl
                - num_of_posts: Number of posts to collect
                - start_date: Start date for data collection
                - end_date: End date for data collection
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (snapshot_id, error_message)
        """
        try:
            # Construct trigger endpoint URL
            trigger_url = f"{self.base_url}/trigger"
            headers = self.get_headers()
            
            # Set up request parameters
            params = {
                "dataset_id": dataset_id,
                "include_errors": "true",
            }
            
            # BrightData expects an array of crawl parameter objects
            data = [crawl_params]
            
            logger.info(f"Triggering crawl for dataset {dataset_id}")
            
            # Make POST request to trigger the crawl
            response = requests.post(
                trigger_url, 
                headers=headers, 
                params=params, 
                json=data, 
                timeout=30
            )
            
            # Check for HTTP errors
            if response.status_code != 200:
                error_msg = f"Trigger crawl failed: {response.text}"
                logger.error(error_msg)
                return None, error_msg
            
            # Extract snapshot_id from response
            response_data = response.json()
            snapshot_id = response_data.get('snapshot_id')
            if not snapshot_id:
                error_msg = f"No snapshot_id returned: {response.text}"
                logger.error(error_msg)
                return None, error_msg
            
            logger.info(f"Triggered crawl, snapshot_id: {snapshot_id}")
            return snapshot_id, None
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout while triggering crawl"
            logger.error(error_msg)
            return None, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error while triggering crawl"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while triggering crawl: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def poll_crawl_status(self, snapshot_id: str) -> Tuple[bool, Optional[str]]:
        """
        Poll crawl job status until completion or timeout.
        
        Args:
            snapshot_id (str): The unique identifier for the crawl job to monitor
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            max_attempts = 60  # 30 minutes with 30-second intervals
            attempt = 0
            
            while attempt < max_attempts:
                progress_url = f"{self.base_url}/progress/{snapshot_id}"
                headers = self.get_headers()
                
                logger.info(f"Polling crawl status (attempt {attempt + 1}/{max_attempts})")
                
                response = requests.get(progress_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    progress_data = response.json()
                    status = progress_data.get('status', 'unknown')
                    
                    if status == 'ready':
                        logger.info(f"Crawl completed successfully: {snapshot_id}")
                        return True, None
                    elif status == 'failed':
                        error_msg = f"Crawl failed: {progress_data.get('error', 'Unknown error')}"
                        logger.error(error_msg)
                        return False, error_msg
                    else:
                        # Still in progress
                        logger.info(f"Crawl in progress: {status}")
                        time.sleep(30)  # Wait 30 seconds before next check
                        attempt += 1
                else:
                    error_msg = f"Error checking crawl status: {response.text}"
                    logger.error(error_msg)
                    return False, error_msg
            
            # Timeout reached
            error_msg = f"Crawl status polling timed out after {max_attempts} attempts"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Error polling crawl status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg