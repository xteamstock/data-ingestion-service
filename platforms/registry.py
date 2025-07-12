"""
Platform registry for managing social media platform handlers.

This module provides a centralized registry for platform handlers,
allowing dynamic registration and retrieval of platform-specific
implementations for Facebook, TikTok, YouTube, etc.
"""

import os
import yaml
from typing import Dict, Type, Optional, Any
from .base import BasePlatformHandler, PlatformConfig, APIProvider


class PlatformRegistry:
    """Registry for platform handlers with configuration management.
    
    This singleton-style class manages platform handler registration
    and provides factory methods for creating handler instances.
    """
    
    _handlers: Dict[str, Type[BasePlatformHandler]] = {}
    _configs: Dict[str, PlatformConfig] = {}
    _initialized = False
    
    @classmethod
    def register(cls, platform: str, handler_class: Type[BasePlatformHandler], config: PlatformConfig):
        """Register a platform handler with its configuration.
        
        Args:
            platform: Platform name (e.g., 'facebook', 'tiktok', 'youtube')
            handler_class: Handler class that implements BasePlatformHandler
            config: Platform-specific configuration
        """
        platform = platform.lower()
        cls._handlers[platform] = handler_class
        cls._configs[platform] = config
    
    @classmethod
    def get_handler(cls, platform: str) -> Optional[BasePlatformHandler]:
        """Get handler instance for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Configured handler instance or None if platform not registered
        """
        platform = platform.lower()
        if platform in cls._handlers:
            handler_class = cls._handlers[platform]
            config = cls._configs[platform]
            return handler_class(config)
        return None
    
    @classmethod
    def get_config(cls, platform: str) -> Optional[PlatformConfig]:
        """Get configuration for platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Platform configuration or None if not registered
        """
        platform = platform.lower()
        return cls._configs.get(platform)
    
    @classmethod
    def list_platforms(cls) -> Dict[str, Dict[str, Any]]:
        """List all registered platforms with their basic info.
        
        Returns:
            Dictionary mapping platform names to their basic information
        """
        platforms = {}
        for platform, config in cls._configs.items():
            platforms[platform] = {
                'name': config.name,
                'api_provider': config.api_provider.value,
                'dataset_id': config.dataset_id,
                'required_params': config.required_params,
                'optional_params': config.optional_params
            }
        return platforms
    
    @classmethod
    def is_registered(cls, platform: str) -> bool:
        """Check if platform is registered.
        
        Args:
            platform: Platform name
            
        Returns:
            True if platform is registered, False otherwise
        """
        return platform.lower() in cls._configs
    
    @classmethod
    def load_from_config(cls, config_path: str):
        """Load platform configurations from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config format is invalid
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Platform config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        if 'platforms' not in config_data:
            raise ValueError("Config file must contain 'platforms' section")
        
        for platform, config in config_data['platforms'].items():
            try:
                # Create PlatformConfig from YAML data
                platform_config = PlatformConfig(
                    name=config['name'],
                    api_provider=APIProvider(config['api_provider']),
                    dataset_id=config['dataset_id'],
                    date_format=config['date_format'],
                    required_params=config['required_params'],
                    optional_params=config['optional_params'],
                    api_endpoint=config['api_endpoint'],
                    media_fields=config['media_fields']
                )
                
                # Store config (handler registration will happen if import succeeds)
                cls._configs[platform.lower()] = platform_config
                
                # Try to dynamically import and register handler
                try:
                    # Import platform handler module
                    module_path = f'platforms.{platform}.handler'
                    module = __import__(module_path, fromlist=[f'{platform.capitalize()}Handler'])
                    
                    # Try to get the handler class - look for both naming conventions
                    handler_class = None
                    for class_name in [f'{platform.capitalize()}Handler', 'Handler']:
                        try:
                            handler_class = getattr(module, class_name)
                            break
                        except AttributeError:
                            continue
                    
                    if handler_class:
                        # Register the handler
                        cls._handlers[platform.lower()] = handler_class
                    
                except ImportError:
                    # Platform handler not implemented yet - config is still registered
                    pass
                    
            except (KeyError, ValueError) as e:
                raise ValueError(f"Invalid config for platform '{platform}': {e}")
        
        cls._initialized = True
    
    @classmethod
    def load_default_config(cls):
        """Load default platform configuration.
        
        This method loads the default platforms.yaml file from the config directory.
        """
        # Look for config file in the service config directory
        config_paths = [
            '/app/config/platforms.yaml',  # Docker container path
            'config/platforms.yaml',       # Local development path
            os.path.join(os.path.dirname(__file__), '..', 'config', 'platforms.yaml')
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                cls.load_from_config(config_path)
                return
        
        # If no config file found, register minimal built-in configs
        cls._register_builtin_configs()
    
    @classmethod
    def _register_builtin_configs(cls):
        """Register built-in platform configurations as fallback."""
        # Facebook configuration (BrightData)
        facebook_config = PlatformConfig(
            name="Facebook",
            api_provider=APIProvider.BRIGHTDATA,
            dataset_id="gd_lkaxegm826bjpoo9m5",
            date_format="MM-DD-YYYY",
            required_params=["url"],
            optional_params=["num_of_posts", "start_date", "end_date", "include_profile_data"],
            api_endpoint="https://api.brightdata.com/datasets/v3/trigger",
            media_fields=["attachments"]
        )
        
        # TikTok configuration (Apify)
        tiktok_config = PlatformConfig(
            name="TikTok",
            api_provider=APIProvider.APIFY,
            dataset_id="clockworks/tiktok-scraper",
            date_format="YYYY-MM-DD",
            required_params=["url"],
            optional_params=["country", "start_date", "end_date", "num_of_posts"],
            api_endpoint=None,  # Not needed for Apify - client handles URLs internally
            media_fields=["videoMeta", "webVideoUrl"]
        )
        
        # YouTube configuration (Apify)
        youtube_config = PlatformConfig(
            name="YouTube",
            api_provider=APIProvider.APIFY,
            dataset_id="streamers/youtube-scraper",
            date_format="YYYY-MM-DD",
            required_params=["url"],
            optional_params=["date_filter", "video_type", "quality_filters", "sorting", "start_date", "num_of_posts"],
            api_endpoint=None,  # Not needed for Apify - client handles URLs internally
            media_fields=["thumbnailUrl", "url"]
        )
        
        # Store configs (handlers will be registered when imported)
        cls._configs['facebook'] = facebook_config
        cls._configs['tiktok'] = tiktok_config
        cls._configs['youtube'] = youtube_config
        
        cls._initialized = True
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if registry has been initialized.
        
        Returns:
            True if registry is initialized, False otherwise
        """
        return cls._initialized


# Convenience function for getting handlers
def get_platform_handler(platform: str) -> Optional[BasePlatformHandler]:
    """Get platform handler instance.
    
    Args:
        platform: Platform name (e.g., 'facebook', 'tiktok', 'youtube')
        
    Returns:
        Handler instance or None if platform not supported
    """
    if not PlatformRegistry.is_initialized():
        PlatformRegistry.load_default_config()
    
    return PlatformRegistry.get_handler(platform)


# Auto-initialize on import if not already done
def _auto_initialize():
    """Auto-initialize the registry on module import."""
    if not PlatformRegistry.is_initialized():
        try:
            PlatformRegistry.load_default_config()
        except Exception:
            # Silently fail auto-initialization - can be done manually later
            pass

_auto_initialize()