"""
Base client for BrightData API operations.

This module provides the foundational client class that other handlers
inherit from, containing shared configuration, utilities, and common
HTTP client functionality.
"""

import os
from typing import Dict, Any


class BaseClient:
    """
    Base client class providing shared functionality for BrightData handlers.
    
    This class encapsulates common configuration, HTTP client setup, and
    utility methods that are shared across all BrightData operation handlers.
    
    Attributes:
        api_key (str): BrightData API key from environment
        base_url (str): Base URL for BrightData API endpoints
    """
    
    def __init__(self):
        """
        Initialize base client with configuration.
        
        Sets up the client with necessary configuration including API keys,
        base URLs, and timeout settings from environment variables.
        """
        self.api_key = os.getenv('BRIGHTDATA_API_KEY')
        self.base_url = "https://api.brightdata.com/datasets/v3"
    
    def validate_config(self) -> tuple[bool, str]:
        """
        Validate client configuration before API operations.
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not self.api_key:
            return False, "BRIGHTDATA_API_KEY environment variable is not set"
        
        if not self.base_url:
            return False, "BrightData base URL is not configured"
        
        return True, ""
    
    def get_headers(self) -> Dict[str, str]:
        """Get standard BrightData API headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'social-analytics-platform/1.0'
        }
    
    def get_download_headers(self) -> Dict[str, str]:
        """Get headers for download operations."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'User-Agent': 'social-analytics-platform/1.0'
        }