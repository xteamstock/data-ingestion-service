"""
Facebook-specific platform handler.

This module implements the Facebook handler that preserves existing BrightData logic
while fitting into the new platform abstraction.
"""

import re
from typing import Dict, Any, List, Set
from datetime import datetime
from ..base import BasePlatformHandler


class FacebookHandler(BasePlatformHandler):
    """Facebook platform handler using BrightData API."""
    
    # Class constants for better maintainability
    FACEBOOK_DOMAINS = {
        'facebook.com', 'www.facebook.com', 
        'fb.com', 'www.fb.com'
    }
    
    FACEBOOK_URL_PATTERN = re.compile(
        r'https?://(www\.)?(facebook\.com|fb\.com)', 
        re.IGNORECASE
    )
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate Facebook-specific parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid for Facebook, False otherwise
        """
        if not isinstance(params, dict):
            return False
            
        # Check if URL parameter exists
        url = params.get('url', '')
        if not url or not isinstance(url, str):
            return False
            
        # Validate Facebook URLs using regex for better accuracy
        return bool(self.FACEBOOK_URL_PATTERN.match(url.strip()))
    
    def prepare_request_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic parameters to Facebook/BrightData format.
        
        Args:
            params: Generic crawl parameters from user request
            
        Returns:
            Facebook-specific parameters formatted for BrightData API
        """
        if not isinstance(params, dict):
            return {}
            
        # Filter out internal tracking parameters - only send what BrightData expects
        brightdata_params = {}
        
        # BrightData Facebook parameters (based on legacy system)
        expected_params = {
            'url', 'num_of_posts', 'start_date', 'end_date', 
            'include_profile_data', 'dataset_id'
        }
        
        for key, value in params.items():
            if key in expected_params:
                brightdata_params[key] = value
        
        # Convert date formats for BrightData
        date_fields = ['start_date', 'end_date']
        for field in date_fields:
            if field in brightdata_params and brightdata_params[field]:
                brightdata_params[field] = self._convert_date_format(brightdata_params[field])
            
        return brightdata_params
    
    def extract_media_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Facebook media information from attachments field.
        
        Args:
            data: Raw Facebook post data
            
        Returns:
            Standardized media metadata dictionary
        """
        if not isinstance(data, dict):
            return self._create_media_info()
            
        attachments = data.get('attachments', [])
        
        if not attachments or not isinstance(attachments, list):
            return self._create_media_info()
        
        # Extract all media types (preserving duplicates)
        media_types = [
            attachment.get('type', '')
            for attachment in attachments
            if isinstance(attachment, dict) and attachment.get('type')
        ]
        
        return self._create_media_info(
            has_media=True,
            media_count=len(attachments),
            media_types=media_types
        )
    
    def get_storage_path(self, snapshot_id: str, competitor: str, brand: str, category: str, timestamp: datetime) -> str:
        """Generate Facebook hierarchical storage path.
        
        Args:
            snapshot_id: Unique identifier for the crawl snapshot
            competitor: Competitor name for business context
            brand: Brand name for business context
            category: Category for business context
            timestamp: Timestamp when the crawl was performed
            
        Returns:
            Hierarchical GCS storage path with business context partitioning
        """
        if not isinstance(snapshot_id, str) or not isinstance(timestamp, datetime):
            raise ValueError("Invalid snapshot_id or timestamp")
            
        return f"raw_snapshots/platform={self.config.name.lower()}/competitor={competitor}/brand={brand}/category={category}/year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}/snapshot_{snapshot_id}.json"
    
    def get_api_client(self) -> Any:
        """Get BrightData API client for Facebook.
        
        Returns:
            Configured BrightData API client instance
        """
        # API client is managed by the crawl handler
        # This method is not needed for the current architecture
        raise NotImplementedError("API client is managed externally")
    
    def parse_api_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse BrightData response format to standard format.
        
        Args:
            response: Raw response from BrightData API
            
        Returns:
            List of standardized Facebook post dictionaries
        """
        # BrightData returns data as-is for Facebook
        # No additional parsing needed
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return [response]
        else:
            return []
    
    def _convert_date_format(self, date_str: str) -> str:
        """Convert date from YYYY-MM-DD to MM-DD-YYYY format.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Date string in MM-DD-YYYY format
        """
        if not isinstance(date_str, str):
            return str(date_str)
            
        try:
            # Parse YYYY-MM-DD format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Return in MM-DD-YYYY format
            return date_obj.strftime('%m-%d-%Y')
        except ValueError:
            # If parsing fails, return original string
            return date_str
    
    def _create_media_info(self, has_media: bool = False, media_count: int = 0, 
                          media_types: List[str] = None) -> Dict[str, Any]:
        """Create standardized media info dictionary.
        
        Args:
            has_media: Whether the post has media
            media_count: Number of media items
            media_types: List of media types
            
        Returns:
            Standardized media info dictionary
        """
        return {
            "has_media": has_media,
            "media_count": media_count,
            "media_types": media_types or []
        }