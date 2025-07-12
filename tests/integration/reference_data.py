"""
Reference data structures for Apify integration tests.

Based on actual Apify responses to validate data structure.
"""

import re

# Reference run structure from screenshot: Yp22wgZwvNXUeuLMy
REFERENCE_RUN_STRUCTURE = {
    "run_id": "Yp22wgZwvNXUeuLMy",
    "status": "SUCCEEDED",
    "results": 16,
    "requests_handled": 3,
    "price_usd": 0.086,
    "duration_seconds": 16,
    "actor": "clockworks/tiktok-scraper",
    "origin": {
        "api_version": "ApifyClient/1.12.0",
        "python_version": "3.13.3",
        "is_at_home": False
    },
    "build": "0.0.396",
    "memory_mb": 4096,
    "cpu_usage": {
        "average_percent": 13.05,
        "maximum_percent": 126.31
    },
    "memory_usage": {
        "average_mb": 148.8,
        "maximum_mb": 175.4
    }
}

# Expected TikTok data structure (generalized from actual responses)
TIKTOK_DATA_STRUCTURE = {
    "required_fields": [
        "id",                # String, typically 19 digits
        "text",              # String, caption text
        "createTime",        # Integer, unix timestamp
        "authorMeta",        # Object with author details
        "musicMeta",         # Object with music details
        "covers",            # Object with cover URLs
        "videoUrl",          # String, video URL
        "diggCount",         # Integer, likes
        "shareCount",        # Integer, shares
        "playCount",         # Integer, views
        "commentCount",      # Integer, comments
        "downloaded",        # Boolean
        "mentions",          # Array
        "hashtags",          # Array
    ],
    "author_meta_fields": [
        "id",                # String, author ID
        "secUid",            # String, secure UID
        "name",              # String, username
        "nickName",          # String, display name
        "verified",          # Boolean
        "signature",         # String, bio
        "avatar",            # String, avatar URL
    ],
    "field_types": {
        "id": str,
        "text": str,
        "createTime": int,
        "authorMeta": dict,
        "musicMeta": dict,
        "covers": dict,
        "diggCount": int,
        "shareCount": int,
        "playCount": int,
        "commentCount": int,
        "downloaded": bool,
        "mentions": list,
        "hashtags": list,
    },
    "field_patterns": {
        "id": r'^\d{17,20}$',  # TikTok IDs are typically 19 digits
        "username": r'^[a-zA-Z0-9_.]+$',  # Username pattern
        "secUid": r'^[A-Za-z0-9_-]+$',  # Secure UID pattern
    }
}

# Expected Apify status response structure
APIFY_STATUS_STRUCTURE = {
    "required_fields": [
        "id",
        "actId", 
        "userId",
        "startedAt",
        "finishedAt",
        "status",
        "statusMessage",
        "isStatusMessageTerminal",
        "meta",
        "stats",
        "options",
        "buildId",
        "exitCode",
        "defaultKeyValueStoreId",
        "defaultDatasetId",
        "defaultRequestQueueId",
        "buildNumber",
        "isContainerServerReady",
        "gitBranchName",
        "usage",
        "usageTotalUsd",
        "usageUsd"
    ],
    "status_values": [
        "READY",
        "RUNNING", 
        "SUCCEEDED",
        "FAILED",
        "TIMING-OUT",
        "TIMED-OUT",
        "ABORTING",
        "ABORTED"
    ],
    "stats_fields": [
        "inputBodyLen",
        "restartCount", 
        "resurrectCount",
        "memAvgBytes",
        "memMaxBytes",
        "memCurrentBytes",
        "cpuAvgUsage",
        "cpuMaxUsage", 
        "cpuCurrentUsage",
        "netRxBytes",
        "netTxBytes",
        "durationMillis",
        "runTimeSecs",
        "metamorph",
        "computeUnits"
    ]
}

# Test validation helpers
def validate_tiktok_item(item: dict) -> list:
    """Validate a single TikTok data item and return list of errors."""
    errors = []
    
    # Check required fields
    for field in TIKTOK_DATA_STRUCTURE["required_fields"]:
        if field not in item:
            errors.append(f"Missing required field: {field}")
    
    # Check field types
    for field, expected_type in TIKTOK_DATA_STRUCTURE["field_types"].items():
        if field in item and not isinstance(item[field], expected_type):
            errors.append(f"Field {field} should be {expected_type.__name__}, got {type(item[field]).__name__}")
    
    # Check patterns
    if "id" in item and not re.match(TIKTOK_DATA_STRUCTURE["field_patterns"]["id"], str(item["id"])):
        errors.append(f"Invalid TikTok ID format: {item['id']}")
    
    # Check authorMeta structure
    if "authorMeta" in item and isinstance(item["authorMeta"], dict):
        author = item["authorMeta"]
        for field in TIKTOK_DATA_STRUCTURE["author_meta_fields"]:
            if field not in author:
                errors.append(f"Missing authorMeta.{field}")
        
        if "name" in author:
            if not re.match(TIKTOK_DATA_STRUCTURE["field_patterns"]["username"], author["name"]):
                errors.append(f"Invalid username format: {author['name']}")
    
    return errors


def validate_apify_status(status: dict) -> list:
    """Validate Apify status response and return list of errors."""
    errors = []
    
    # Check status value
    if "status" in status:
        if status["status"] not in APIFY_STATUS_STRUCTURE["status_values"]:
            errors.append(f"Invalid status value: {status['status']}")
    else:
        errors.append("Missing status field")
    
    # Check for stats object
    if "stats" in status and isinstance(status["stats"], dict):
        stats = status["stats"]
        # Just verify it has some expected fields, not all
        expected_stats = ["durationMillis", "computeUnits", "memMaxBytes"]
        for field in expected_stats:
            if field not in stats:
                errors.append(f"Missing stats.{field}")
    
    return errors


# Expected YouTube data structure (based on sample/data/youtube_data_MLwkQMLBIH7R9dZy7.json)
YOUTUBE_DATA_STRUCTURE = {
    "required_fields": [
        "title",                 # String, video title
        "type",                  # String, typically "video"
        "id",                    # String, YouTube video ID (11 chars)
        "url",                   # String, YouTube watch URL
        "thumbnailUrl",          # String, thumbnail image URL
        "viewCount",             # Integer, view count
        "date",                  # String, ISO date format
        "likes",                 # Integer, likes count
        "channelName",           # String, channel name
        "channelUrl",            # String, channel URL
        "channelId",             # String, channel ID (starts with UC)
        "channelUsername",       # String, channel username
        "channelDescription",    # String, channel description
        "duration",              # String, duration in HH:MM:SS format
        "commentsCount",         # Integer, comments count
        "text",                  # String, video description
        "aboutChannelInfo",      # Object, detailed channel info
    ],
    "about_channel_info_fields": [
        "channelDescription",
        "channelJoinedDate",
        "channelDescriptionLinks",
        "channelLocation",
        "channelUsername",
        "channelAvatarUrl",
        "channelBannerUrl",
        "channelTotalVideos",
        "channelTotalViews",
        "numberOfSubscribers",
        "isChannelVerified",
        "channelName",
        "channelUrl",
        "channelId",
    ],
    "field_types": {
        "title": str,
        "type": str,
        "id": str,
        "url": str,
        "thumbnailUrl": str,
        "viewCount": int,
        "date": str,
        "likes": int,
        "channelName": str,
        "channelUrl": str,
        "channelId": str,
        "channelUsername": str,
        "channelDescription": str,
        "duration": str,
        "commentsCount": int,
        "text": str,
        "aboutChannelInfo": dict,
        "descriptionLinks": list,
        "hashtags": list,
    },
    "field_patterns": {
        "id": r'^[A-Za-z0-9_-]{11}$',  # YouTube video IDs are 11 characters
        "channelId": r'^UC[A-Za-z0-9_-]{22}$',  # Channel IDs start with UC + 22 chars
        "url": r'^https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}$',
        "channelUrl": r'^https://www\.youtube\.com/channel/UC[A-Za-z0-9_-]{22}$',
        "thumbnailUrl": r'^https://i\.ytimg\.com/vi/[A-Za-z0-9_-]{11}/.*\.jpg.*$',
        "duration": r'^\d{2}:\d{2}:\d{2}$',  # HH:MM:SS format
        "date": r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$',  # ISO format
    },
    "optional_fields": [
        "location",              # Can be null
        "subtitles",            # Can be null
        "descriptionLinks",     # Can be empty array
        "hashtags",             # Can be empty array
        "formats",              # Can be empty array
        "order",                # Integer, video order
        "commentsTurnedOff",    # Boolean
        "isMonetized",          # Can be null
        "isMembersOnly",        # Boolean
    ]
}

# Reference YouTube run structure based on actual data
REFERENCE_YOUTUBE_RUN = {
    "actor_id": "streamers/youtube-scraper",
    "sample_input": {
        "dateFilter": "month",
        "downloadSubtitles": False,
        "hasSubtitles": True,
        "isHD": True,
        "maxResults": 10,
        "oldestPostDate": "2025-07-01",
        "sortVideosBy": "NEWEST",
        "startUrls": [
            {
                "url": "https://www.youtube.com/@NutiFoodVietNam",
                "method": "GET"
            }
        ],
        "videoType": "video"
    },
    "expected_response_types": [
        "video",     # Regular videos
        "short",     # YouTube Shorts
        "live",      # Live streams
    ]
}

def validate_youtube_item(item: dict) -> list:
    """Validate a single YouTube data item and return list of errors."""
    errors = []
    
    # Check required fields
    for field in YOUTUBE_DATA_STRUCTURE["required_fields"]:
        if field not in item:
            errors.append(f"Missing required field: {field}")
    
    # Check field types
    for field, expected_type in YOUTUBE_DATA_STRUCTURE["field_types"].items():
        if field in item and item[field] is not None:
            if not isinstance(item[field], expected_type):
                errors.append(f"Field {field} should be {expected_type.__name__}, got {type(item[field]).__name__}")
    
    # Check patterns
    for field, pattern in YOUTUBE_DATA_STRUCTURE["field_patterns"].items():
        if field in item and item[field] is not None:
            if not re.match(pattern, str(item[field])):
                errors.append(f"Field {field} doesn't match expected pattern: {item[field]}")
    
    # Check aboutChannelInfo structure
    if "aboutChannelInfo" in item and isinstance(item["aboutChannelInfo"], dict):
        channel_info = item["aboutChannelInfo"]
        for field in YOUTUBE_DATA_STRUCTURE["about_channel_info_fields"]:
            if field not in channel_info:
                errors.append(f"Missing aboutChannelInfo.{field}")
        
        # Validate channel info types
        if "numberOfSubscribers" in channel_info:
            if not isinstance(channel_info["numberOfSubscribers"], int):
                errors.append(f"numberOfSubscribers should be int, got {type(channel_info['numberOfSubscribers']).__name__}")
        
        if "channelTotalVideos" in channel_info:
            if not isinstance(channel_info["channelTotalVideos"], int):
                errors.append(f"channelTotalVideos should be int, got {type(channel_info['channelTotalVideos']).__name__}")
    
    # Validate reasonable ranges
    if "viewCount" in item and isinstance(item["viewCount"], int):
        if item["viewCount"] < 0:
            errors.append("viewCount should be non-negative")
    
    if "likes" in item and isinstance(item["likes"], int):
        if item["likes"] < 0:
            errors.append("likes should be non-negative")
    
    if "commentsCount" in item and isinstance(item["commentsCount"], int):
        if item["commentsCount"] < 0:
            errors.append("commentsCount should be non-negative")
    
    return errors


def validate_youtube_channel_info(channel_info: dict) -> list:
    """Validate YouTube channel info structure."""
    errors = []
    
    required_channel_fields = [
        "channelName", "channelId", "channelUrl", "numberOfSubscribers"
    ]
    
    for field in required_channel_fields:
        if field not in channel_info:
            errors.append(f"Missing channel field: {field}")
    
    # Validate subscriber count format
    if "numberOfSubscribers" in channel_info:
        subscribers = channel_info["numberOfSubscribers"]
        if not isinstance(subscribers, int) or subscribers < 0:
            errors.append(f"Invalid numberOfSubscribers: {subscribers}")
    
    return errors


# Cost tracking thresholds
COST_THRESHOLDS = {
    "warning": 0.10,     # Warn if single test costs more than $0.10
    "error": 0.50,       # Error if single test costs more than $0.50
    "session_limit": 5.00  # Limit for entire test session
}