#!/usr/bin/env python3
"""
Basic test script for Data Ingestion Service.

This script tests the basic functionality of the service without
requiring actual BrightData API calls.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the service directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_health_check():
    """Test the health check endpoint."""
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed:", data)
            return True
        else:
            print("❌ Health check failed:", response.status_code, response.text)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Make sure it's running on port 8080")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_crawl_trigger():
    """Test the crawl trigger endpoint (mock)."""
    try:
        test_params = {
            'url': 'https://facebook.com/test',
            'num_of_posts': 10,
            'platform': 'facebook',
            'competitor': 'test-competitor',
            'brand': 'test-brand',
            'category': 'test-category',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        response = requests.post(
            'http://localhost:8080/api/v1/crawl/trigger',
            json=test_params,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Crawl trigger response:", data)
            return True, data.get('crawl_id')
        else:
            print("❌ Crawl trigger failed:", response.status_code, response.text)
            return False, None
    except Exception as e:
        print(f"❌ Crawl trigger error: {e}")
        return False, None

def test_crawl_status(crawl_id):
    """Test the crawl status endpoint."""
    try:
        response = requests.get(
            f'http://localhost:8080/api/v1/crawl/{crawl_id}/status',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Crawl status response:", data)
            return True
        else:
            print("❌ Crawl status failed:", response.status_code, response.text)
            return False
    except Exception as e:
        print(f"❌ Crawl status error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Data Ingestion Service")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    if not test_health_check():
        print("❌ Health check failed. Please start the service first.")
        sys.exit(1)
    
    # Test 2: Crawl trigger
    print("\n2. Testing crawl trigger...")
    success, crawl_id = test_crawl_trigger()
    if not success:
        print("❌ Crawl trigger test failed")
        sys.exit(1)
    
    # Test 3: Crawl status
    if crawl_id:
        print(f"\n3. Testing crawl status for ID: {crawl_id}")
        test_crawl_status(crawl_id)
    
    print("\n✅ Basic tests completed successfully!")
    print("🎉 Data Ingestion Service is working!")

if __name__ == '__main__':
    main()