#!/usr/bin/env python3
"""
Local Testing Guide for Data Ingestion Service

This script provides multiple ways to test the data-ingestion service locally
in isolation, including mocking external dependencies like PubSub and GCS.
"""

import os
import sys
import json
import asyncio
import requests
import time
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.crawl_handler import CrawlHandler
from platforms.registry import PlatformRegistry


class LocalTester:
    """Local testing utility for the data-ingestion service."""
    
    def __init__(self, mock_external_services=True):
        """Initialize local tester.
        
        Args:
            mock_external_services: If True, mock GCS, BigQuery, and PubSub
        """
        self.mock_external_services = mock_external_services
        self.base_url = "http://localhost:8080"
        
    def setup_environment(self):
        """Set up environment variables for local testing."""
        os.environ.update({
            'BRIGHTDATA_API_KEY': 'test_brightdata_key_12345',
            'APIFY_API_TOKEN': 'test_apify_token_67890',
            'GCS_BUCKET_RAW_DATA': 'test-social-analytics-raw-data',
            'GCS_BUCKET_PROCESSED_DATA': 'test-social-analytics-processed-data',
            'BIGQUERY_DATASET': 'test_social_analytics',
            'GOOGLE_CLOUD_PROJECT': 'test-project-local',
            'BACKGROUND_POLLING_ENABLED': 'false',  # Disable for local testing
            'BACKGROUND_MAX_WORKERS': '2',
            'BACKGROUND_POLL_INTERVAL': '5',
            'BACKGROUND_MAX_POLLS': '10',
        })
        print("✅ Environment variables set for local testing")
    
    def test_platform_registry(self):
        """Test platform registry initialization."""
        print("\n🧪 Testing Platform Registry...")
        
        # Ensure registry is initialized
        if not PlatformRegistry.is_initialized():
            PlatformRegistry.load_default_config()
        
        # Test platform retrieval
        platforms = ['facebook', 'tiktok', 'youtube']
        for platform in platforms:
            handler = PlatformRegistry.get_handler(platform)
            if handler:
                print(f"✅ {platform.title()} handler: {handler.__class__.__name__}")
                print(f"   API Provider: {handler.config.api_provider.value}")
                print(f"   Dataset ID: {handler.config.dataset_id}")
            else:
                print(f"❌ {platform.title()} handler not found")
        
        return True
    
    def test_crawl_handler_initialization(self):
        """Test crawl handler initialization with mocked dependencies."""
        print("\n🧪 Testing Crawl Handler Initialization...")
        
        if self.mock_external_services:
            with patch('handlers.crawl_handler.storage.Client'), \
                 patch('handlers.crawl_handler.bigquery.Client'), \
                 patch('handlers.crawl_handler.EventPublisher'):
                
                try:
                    crawl_handler = CrawlHandler()
                    print("✅ CrawlHandler initialized successfully with mocked services")
                    
                    # Test API clients
                    assert hasattr(crawl_handler, 'brightdata_client')
                    assert hasattr(crawl_handler, 'apify_client')
                    print("✅ API clients initialized")
                    
                    return crawl_handler
                except Exception as e:
                    print(f"❌ CrawlHandler initialization failed: {e}")
                    return None
        else:
            try:
                crawl_handler = CrawlHandler()
                print("✅ CrawlHandler initialized with real services")
                return crawl_handler
            except Exception as e:
                print(f"❌ CrawlHandler initialization failed: {e}")
                print("   Tip: Run with mock_external_services=True for local testing")
                return None
    
    async def test_platform_crawl_trigger(self, platform: str, crawl_handler: CrawlHandler):
        """Test triggering a crawl for a specific platform."""
        print(f"\n🧪 Testing {platform.title()} Crawl Trigger...")
        
        # Platform-specific test parameters
        test_params = {
            'facebook': {
                'platform': 'facebook',
                'url': 'https://facebook.com/GrowPLUScuaNutiFood',
                'num_of_posts': 5,
                'start_date': '2024-01-01',
                'end_date': '2024-01-02',
                'competitor': 'nutifood',
                'brand': 'growplus-nutifood',
                'category': 'sua-bot-tre-em'
            },
            'tiktok': {
                'platform': 'tiktok',
                'url': 'https://tiktok.com/@nutifoodvietnam',
                'num_of_posts': 5,
                'start_date': '2024-01-01',
                'end_date': '2024-01-02',
                'country': 'VN',
                'competitor': 'nutifood',
                'brand': 'growplus-nutifood',
                'category': 'sua-bot-tre-em'
            },
            'youtube': {
                'platform': 'youtube',
                'url': 'https://youtube.com/@NutiFoodVietNam',
                'num_of_posts': 5,
                'start_date': '2024-01-01',
                'competitor': 'nutifood',
                'brand': 'growplus-nutifood',
                'category': 'sua-bot-tre-em'
            }
        }
        
        params = test_params.get(platform)
        if not params:
            print(f"❌ No test parameters for platform: {platform}")
            return False
        
        try:
            # Mock API responses based on platform
            if platform == 'facebook':
                with patch.object(crawl_handler.brightdata_client, 'trigger_crawl', new_callable=AsyncMock) as mock_trigger:
                    mock_trigger.return_value = f"test_snapshot_{platform}_123"
                    
                    with patch.object(crawl_handler, '_store_crawl_metadata'):
                        result = await crawl_handler.trigger_crawl(params)
                        
                        if result['status'] == 'success':
                            print(f"✅ {platform.title()} crawl triggered successfully")
                            print(f"   Crawl ID: {result['crawl_id']}")
                            print(f"   Snapshot ID: {result['snapshot_id']}")
                            print(f"   Platform: {result['platform']}")
                            return result
                        else:
                            print(f"❌ {platform.title()} crawl failed: {result.get('message')}")
                            return False
            
            else:  # TikTok or YouTube (Apify)
                with patch.object(crawl_handler.apify_client, 'trigger_crawl', new_callable=AsyncMock) as mock_trigger:
                    mock_trigger.return_value = f"apify_run_{platform}_456"
                    
                    with patch.object(crawl_handler, '_store_crawl_metadata'):
                        result = await crawl_handler.trigger_crawl(params)
                        
                        if result['status'] == 'success':
                            print(f"✅ {platform.title()} crawl triggered successfully")
                            print(f"   Crawl ID: {result['crawl_id']}")
                            print(f"   Snapshot ID: {result['snapshot_id']}")
                            print(f"   Platform: {result['platform']}")
                            return result
                        else:
                            print(f"❌ {platform.title()} crawl failed: {result.get('message')}")
                            return False
                            
        except Exception as e:
            print(f"❌ Error testing {platform} crawl: {e}")
            return False
    
    def test_service_endpoints(self):
        """Test service endpoints via HTTP requests (requires running service)."""
        print("\n🧪 Testing Service Endpoints...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Health endpoint working")
                print(f"   Status: {health_data.get('status')}")
                print(f"   Service: {health_data.get('service')}")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ Health endpoint unreachable: {e}")
            print("   Tip: Make sure the service is running with 'python app.py'")
            return False
        
        # Test platform crawl endpoints
        platforms = ['facebook', 'tiktok', 'youtube']
        for platform in platforms:
            print(f"\n   Testing {platform.title()} crawl endpoint...")
            
            test_payload = {
                'platform': platform,
                'url': f'https://{platform}.com/test',
                'num_of_posts': 3,
                'competitor': 'test_competitor',
                'brand': 'test_brand',
                'category': 'test_category'
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/v1/crawl/trigger",
                    json=test_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ {platform.title()} endpoint working")
                    print(f"      Crawl ID: {result.get('crawl_id')}")
                    print(f"      Status: {result.get('status')}")
                elif response.status_code == 500:
                    print(f"   ⚠️  {platform.title()} endpoint reachable but errored (expected without real API keys)")
                else:
                    print(f"   ❌ {platform.title()} endpoint failed: {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"   ❌ {platform.title()} endpoint error: {e}")
        
        return True
    
    def test_storage_paths(self):
        """Test hierarchical storage path generation."""
        print("\n🧪 Testing Storage Path Generation...")
        
        timestamp = datetime(2024, 1, 15, 12, 30, 45)
        snapshot_id = "test_snapshot_123"
        competitor = "nutifood"
        brand = "growplus"
        category = "sua-bot"
        
        platforms = ['facebook', 'tiktok', 'youtube']
        for platform in platforms:
            handler = PlatformRegistry.get_handler(platform)
            if handler:
                path = handler.get_storage_path(
                    snapshot_id, competitor, brand, category, timestamp
                )
                expected_pattern = f"raw_snapshots/platform={platform}/competitor={competitor}/brand={brand}/category={category}/year=2024/month=01/day=15/"
                
                if expected_pattern in path:
                    print(f"✅ {platform.title()} storage path correct")
                    print(f"   Path: {path}")
                else:
                    print(f"❌ {platform.title()} storage path incorrect")
                    print(f"   Expected pattern: {expected_pattern}")
                    print(f"   Actual path: {path}")
            else:
                print(f"❌ {platform.title()} handler not found")
    
    def run_full_test_suite(self):
        """Run the complete test suite."""
        print("🚀 Starting Local Data Ingestion Service Test Suite")
        print("=" * 60)
        
        # Setup
        self.setup_environment()
        
        # Basic tests
        self.test_platform_registry()
        crawl_handler = self.test_crawl_handler_initialization()
        
        if not crawl_handler:
            print("\n❌ Cannot continue - CrawlHandler initialization failed")
            return False
        
        # Platform-specific tests
        async def run_async_tests():
            platforms = ['facebook', 'tiktok', 'youtube']
            for platform in platforms:
                await self.test_platform_crawl_trigger(platform, crawl_handler)
        
        asyncio.run(run_async_tests())
        
        # Storage tests
        self.test_storage_paths()
        
        # Service endpoint tests (optional - requires running service)
        print("\n" + "=" * 60)
        print("🌐 Optional: Testing Live Service Endpoints")
        print("   (Start the service with 'python app.py' in another terminal)")
        time.sleep(2)  # Give user time to read
        self.test_service_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ Local Test Suite Complete!")
        print("\n📋 Next Steps:")
        print("   1. Start the service: python app.py")
        print("   2. Test real API calls with valid API keys")
        print("   3. Check PubSub events in GCP console")
        print("   4. Verify data in GCS and BigQuery")
        
        return True


def create_test_requests_script():
    """Create a script with sample curl commands for manual testing."""
    script_content = '''#!/bin/bash
# Manual Testing Script for Data Ingestion Service
# Make sure the service is running on localhost:8080

echo "🧪 Testing Data Ingestion Service Endpoints"
echo "==========================================="

BASE_URL="http://localhost:8080"

echo "📋 1. Health Check"
curl -s -X GET "$BASE_URL/health" | jq '.'

echo -e "\n📋 2. Facebook Crawl Trigger"
curl -s -X POST "$BASE_URL/api/v1/crawl/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "facebook",
    "url": "https://facebook.com/GrowPLUScuaNutiFood",
    "num_of_posts": 5,
    "start_date": "2024-01-01", 
    "end_date": "2024-01-02",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }' | jq '.'

echo -e "\n📋 3. TikTok Crawl Trigger"
curl -s -X POST "$BASE_URL/api/v1/crawl/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "tiktok",
    "url": "https://tiktok.com/@nutifoodvietnam",
    "num_of_posts": 5,
    "start_date": "2024-01-01",
    "end_date": "2024-01-02", 
    "country": "VN",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }' | jq '.'

echo -e "\n📋 4. YouTube Crawl Trigger"
curl -s -X POST "$BASE_URL/api/v1/crawl/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "youtube",
    "url": "https://youtube.com/@NutiFoodVietNam", 
    "num_of_posts": 5,
    "start_date": "2024-01-01",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }' | jq '.'

echo -e "\n📋 5. Platform Registry Info"
curl -s -X GET "$BASE_URL/api/v1/platforms" | jq '.' 2>/dev/null || echo "Platform info endpoint not implemented"

echo -e "\n✅ Manual testing complete!"
echo "   Check the service logs for detailed information"
'''
    
    with open('manual_test_requests.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('manual_test_requests.sh', 0o755)
    print("✅ Created manual_test_requests.sh script")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Local Data Ingestion Service Tester')
    parser.add_argument('--no-mock', action='store_true', 
                       help='Test with real external services (requires proper GCP setup)')
    parser.add_argument('--endpoints-only', action='store_true',
                       help='Only test HTTP endpoints (requires running service)')
    parser.add_argument('--create-scripts', action='store_true',
                       help='Create manual testing scripts')
    
    args = parser.parse_args()
    
    if args.create_scripts:
        create_test_requests_script()
        print("\n📝 Manual testing script created: manual_test_requests.sh")
        print("   Usage: ./manual_test_requests.sh (requires service to be running)")
        exit(0)
    
    tester = LocalTester(mock_external_services=not args.no_mock)
    
    if args.endpoints_only:
        tester.setup_environment()
        tester.test_service_endpoints()
    else:
        tester.run_full_test_suite()