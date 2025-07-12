"""
Platform abstraction layer for multi-platform social media crawling.

This module provides the base classes and interfaces for implementing
platform-specific handlers for different social media platforms and API providers.
"""

from .base import BasePlatformHandler, PlatformConfig, APIProvider
from .registry import PlatformRegistry, get_platform_handler

# Import platform handlers to register them
try:
    from .facebook.handler import FacebookHandler
    from .tiktok.handler import TikTokHandler
    from .youtube.handler import YouTubeHandler
    
    # Register handlers if not already registered
    if not PlatformRegistry.is_initialized():
        PlatformRegistry.load_default_config()
        
    # Register handler classes if configs exist but handlers are not registered
    if PlatformRegistry.get_config('facebook') and 'facebook' not in PlatformRegistry._handlers:
        PlatformRegistry._handlers['facebook'] = FacebookHandler
    if PlatformRegistry.get_config('tiktok') and 'tiktok' not in PlatformRegistry._handlers:
        PlatformRegistry._handlers['tiktok'] = TikTokHandler
    if PlatformRegistry.get_config('youtube') and 'youtube' not in PlatformRegistry._handlers:
        PlatformRegistry._handlers['youtube'] = YouTubeHandler
        
except ImportError:
    # Platform handlers not available yet
    pass

__all__ = [
    'BasePlatformHandler', 
    'PlatformConfig', 
    'APIProvider',
    'PlatformRegistry',
    'get_platform_handler'
]