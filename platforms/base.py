"""
Base classes for platform-specific handlers.

This module defines the abstract base class and configuration that all
platform handlers must implement, along with the API provider enumeration.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime


class APIProvider(Enum):
    """Enumeration of supported API providers."""
    BRIGHTDATA = "brightdata"
    APIFY = "apify"


@dataclass
class PlatformConfig:
    """Configuration for a social media platform.
    
    This dataclass holds all the configuration needed for a platform handler,
    including API provider details, required parameters, and platform-specific settings.
    """
    name: str
    api_provider: APIProvider
    dataset_id: str  # BrightData dataset ID or Apify actor ID
    date_format: str
    required_params: List[str]
    optional_params: List[str]
    api_endpoint: Optional[str]  # Required for BrightData, optional for Apify
    media_fields: List[str]


class BasePlatformHandler(ABC):
    """Abstract base class for platform-specific handlers.
    
    All platform handlers (Facebook, TikTok, YouTube, etc.) must inherit from this
    class and implement all abstract methods. This ensures a consistent interface
    across different platforms and API providers.
    """
    
    def __init__(self, config: PlatformConfig):
        """Initialize the platform handler with configuration.
        
        Args:
            config: Platform-specific configuration
        """
        self.config = config
    
    @abstractmethod
    def prepare_request_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic parameters to platform-specific format.
        
        Args:
            params: Generic crawl parameters from user request
            
        Returns:
            Platform-specific parameters formatted for the API provider
        """
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate platform-specific parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid for this platform, False otherwise
        """
        pass
    
    @abstractmethod
    def extract_media_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract platform-specific media information.
        
        Args:
            data: Raw post/video data from the platform
            
        Returns:
            Standardized media metadata dictionary
        """
        pass
    
    @abstractmethod
    def get_storage_path(self, snapshot_id: str, competitor: str, brand: str, category: str, timestamp: datetime) -> str:
        """Generate platform-specific hierarchical storage path.
        
        Args:
            snapshot_id: Unique identifier for the crawl snapshot
            competitor: Competitor name for business context
            brand: Brand name for business context
            category: Category for business context
            timestamp: Timestamp when the crawl was performed
            
        Returns:
            Hierarchical GCS storage path with business context partitioning
        """
        pass
    
    @abstractmethod
    def get_api_client(self) -> Any:
        """Get appropriate API client (BrightData or Apify).
        
        Returns:
            Configured API client instance for this platform
        """
        pass
    
    @abstractmethod
    def parse_api_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse API-specific response format to standard format.
        
        Args:
            response: Raw response from the API provider
            
        Returns:
            List of standardized post/video dictionaries
        """
        pass