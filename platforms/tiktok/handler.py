"""
TikTok platform handler implementation.

This module implements the TikTok-specific logic for data crawling using the Apify API.
It handles TikTok URL validation, parameter transformation, and data extraction.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BasePlatformHandler


class TikTokHandler(BasePlatformHandler):
    """TikTok-specific platform handler using Apify API."""
    
    def prepare_request_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare TikTok-specific parameters for Apify API.
        
        Transforms generic parameters to Apify TikTok scraper format.
        Filter out internal tracking parameters and only send what Apify expects.
        
        Args:
            params: Generic parameters from user request
            
        Returns:
            Apify-compatible parameters for TikTok scraping
        """
        if not isinstance(params, dict):
            return {}
        
        # Build TikTok-specific parameters from the input
        tiktok_params = {}
        
        # Map URL/profiles
        if 'url' in params:
            tiktok_params['profiles'] = [params['url']]
        elif 'profiles' in params:
            tiktok_params['profiles'] = params['profiles']
        
        # Map date parameters
        if 'newestPostDate' in params:
            tiktok_params['newestPostDate'] = params['newestPostDate']
        if 'oldestPostDateUnified' in params:
            tiktok_params['oldestPostDateUnified'] = params['oldestPostDateUnified']
        
        # Map other Apify-specific parameters (only if they exist in input)
        apify_params = [
            'excludePinnedPosts', 'profileScrapeSections', 'profileSorting',
            'proxyCountryCode', 'resultsPerPage', 'scrapeRelatedVideos',
            'shouldDownloadAvatars', 'shouldDownloadCovers', 'shouldDownloadMusicCovers',
            'shouldDownloadSlideshowImages', 'shouldDownloadSubtitles', 'shouldDownloadVideos'
        ]
        
        for param in apify_params:
            if param in params:
                tiktok_params[param] = params[param]
        
        # Set defaults if not provided
        if 'excludePinnedPosts' not in tiktok_params:
            tiktok_params['excludePinnedPosts'] = True
        if 'profileScrapeSections' not in tiktok_params:
            tiktok_params['profileScrapeSections'] = ['videos']
        if 'profileSorting' not in tiktok_params:
            tiktok_params['profileSorting'] = 'latest'
        if 'proxyCountryCode' not in tiktok_params:
            tiktok_params['proxyCountryCode'] = 'None'
        if 'resultsPerPage' not in tiktok_params:
            tiktok_params['resultsPerPage'] = 10
        
        return tiktok_params
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate TikTok parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if parameters are valid for TikTok, False otherwise
        """
        # Check required fields
        for field in self.config.required_params:
            if field not in params or not params[field]:
                return False
        
        # Validate URL format for TikTok
        url = params.get('url', '')
        if not url:
            return False
            
        # Only accept TikTok URLs - must contain 'tiktok.com'
        # or be a standalone @username (not from other platforms)
        if 'tiktok.com' in url:
            return True
        elif url.startswith('@') and 'tiktok.com' not in url and 'instagram.com' not in url and 'facebook.com' not in url and 'youtube.com' not in url:
            # Only accept standalone @username format (not URLs from other platforms)
            return True
            
        return False
    
    def extract_media_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract TikTok media information from post data.
        
        Args:
            data: Raw TikTok post data
            
        Returns:
            Standardized media metadata dictionary
        """
        # Extract video metadata if available
        video_meta = data.get('videoMeta', {})
        has_video = bool(video_meta)
        
        return {
            'has_media': has_video,
            'media_count': 1 if has_video else 0,
            'media_types': ['video'] if has_video else [],
            'duration': video_meta.get('duration', 0),
            'play_count': data.get('playCount', 0),
            'is_ad': data.get('isAd', False),
            'video_url': data.get('webVideoUrl'),
            'cover_image': video_meta.get('coverUrl'),
            'height': video_meta.get('height'),
            'width': video_meta.get('width')
        }
    
    def get_storage_path(self, snapshot_id: str, competitor: str, brand: str, category: str, timestamp: datetime) -> str:
        """Generate TikTok hierarchical storage path.
        
        Args:
            snapshot_id: Unique identifier for the crawl snapshot
            competitor: Competitor name for business context
            brand: Brand name for business context
            category: Category for business context
            timestamp: Timestamp when the crawl was performed
            
        Returns:
            Hierarchical GCS storage path with business context partitioning
        """
        return f"raw_snapshots/platform={self.config.name.lower()}/competitor={competitor}/brand={brand}/category={category}/year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}/snapshot_{snapshot_id}.json"
    
    def get_api_client(self) -> Any:
        """Get Apify client for TikTok.
        
        Returns:
            Configured Apify client instance
        """
        # API client is managed by the crawl handler
        # This method is not needed for the current architecture
        raise NotImplementedError("API client is managed externally")
    
    def parse_api_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse Apify response to standard format.
        
        Args:
            response: Raw response from Apify API
            
        Returns:
            List of standardized TikTok post dictionaries
        """
        # Apify returns data directly in the dataset format
        if isinstance(response, list):
            # Filter out non-video entries if any
            videos = []
            for item in response:
                if isinstance(item, dict) and item.get('webVideoUrl'):
                    videos.append(item)
            return videos
        elif isinstance(response, dict) and response.get('webVideoUrl'):
            return [response]
        else:
            return []
    
    def extract_hashtags(self, data: Dict[str, Any]) -> List[str]:
        """Extract hashtags from TikTok post data.
        
        Args:
            data: Raw TikTok post data
            
        Returns:
            List of hashtag names (without # symbol)
        """
        hashtags = data.get('hashtags', [])
        if isinstance(hashtags, list):
            return [tag.get('name', '') for tag in hashtags if isinstance(tag, dict) and 'name' in tag]
        return []
    
    def transform_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform TikTok-specific metrics to standardized format.
        
        Args:
            data: Raw TikTok post data
            
        Returns:
            Standardized metrics dictionary
        """
        author_meta = data.get('authorMeta', {})
        
        return {
            'likes': data.get('diggCount', 0),  # TikTok uses 'diggCount' for likes
            'shares': data.get('shareCount', 0),
            'views': data.get('playCount', 0),  # TikTok uses 'playCount' for views
            'comments': data.get('commentCount', 0),
            'author': author_meta.get('name', ''),
            'created_at': data.get('createTimeISO', ''),
            'is_verified': author_meta.get('verified', False),
            'author_nickname': author_meta.get('nickName', '')
        }