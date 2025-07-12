"""
Base API client interface for social media data providers.

This module defines the abstract base class that all API clients must implement,
ensuring consistent behavior across different providers (BrightData, Apify).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAPIClient(ABC):
    """Abstract base class for API clients.
    
    All API provider clients (BrightData, Apify) must inherit from this class
    and implement all abstract methods to ensure consistent interface.
    """
    
    @abstractmethod
    async def trigger_crawl(self, actor_or_dataset_id: str, params: Dict[str, Any]) -> str:
        """Trigger a crawl job and return job ID.
        
        Args:
            actor_or_dataset_id: Actor ID for Apify or dataset ID for BrightData
            params: Provider-specific parameters for the crawl
            
        Returns:
            Unique job identifier that can be used to check status and download results
            
        Raises:
            APIClientError: If the crawl trigger request fails
        """
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a crawl job.
        
        Args:
            job_id: Job identifier returned by trigger_crawl
            
        Returns:
            Dictionary containing:
                - status: Current job status (running, completed, failed, etc.)
                - is_ready: Boolean indicating if data is ready for download
                - additional provider-specific metadata
                
        Raises:
            APIClientError: If the status check request fails
        """
        pass
    
    @abstractmethod
    async def download_data(self, job_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Download crawl results.
        
        Args:
            job_id: Job identifier returned by trigger_crawl
            limit: Optional limit on number of items to download
            
        Returns:
            List of raw data items from the crawl
            
        Raises:
            APIClientError: If the download request fails or data is not ready
        """
        pass


class APIClientError(Exception):
    """Exception raised by API clients for provider-specific errors."""
    
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        """Initialize API client error.
        
        Args:
            message: Error description
            provider: Name of the API provider (brightdata, apify)
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code