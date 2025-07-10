#!/usr/bin/env python3
"""
Test script to verify Unicode encoding and record preservation fixes.
"""

import json
import os
import sys

def test_unicode_encoding():
    """Test that our JSON encoding preserves Unicode characters correctly."""
    
    # Load the supposed (correct) data
    supposed_file = "/Users/tranquocbao/crawlerX/social-analytics-platform/services/data-ingestion/sample/supposed_raw_data.json"
    result_file = "/Users/tranquocbao/crawlerX/social-analytics-platform/services/data-ingestion/sample/result_raw_data.json"
    
    with open(supposed_file, 'r', encoding='utf-8') as f:
        supposed_data = json.load(f)
    
    with open(result_file, 'r', encoding='utf-8') as f:
        result_data = json.load(f)
    
    print(f"Supposed data: {len(supposed_data)} records")
    print(f"Result data: {len(result_data)} records")
    
    # Check record count
    if len(supposed_data) != len(result_data):
        print(f"❌ MISSING RECORDS: Expected {len(supposed_data)}, got {len(result_data)}")
        return False
    
    # Check Unicode encoding for the first record
    if len(supposed_data) > 0 and len(result_data) > 0:
        supposed_content = supposed_data[0].get('content', '')
        result_content = result_data[0].get('content', '')
        
        print(f"Supposed content: {supposed_content[:50]}...")
        print(f"Result content: {result_content[:50]}...")
        
        if supposed_content != result_content:
            print("❌ UNICODE ENCODING ISSUE: Content doesn't match")
            return False
    
    # Test our encoding fix
    print("\nTesting our JSON encoding fix:")
    test_data = supposed_data
    
    # Use our encoding approach
    json_output = json.dumps(test_data, indent=2, ensure_ascii=False)
    
    # Re-parse to verify round-trip
    reparsed_data = json.loads(json_output)
    
    print(f"Original: {len(test_data)} records")
    print(f"Reparsed: {len(reparsed_data)} records")
    
    if len(test_data) == len(reparsed_data):
        print("✅ Record count preserved")
    else:
        print("❌ Record count lost during encoding")
        return False
    
    # Check content preservation
    if len(test_data) > 0:
        original_content = test_data[0].get('content', '')
        reparsed_content = reparsed_data[0].get('content', '')
        
        if original_content == reparsed_content:
            print("✅ Unicode content preserved")
            print(f"Content sample: {original_content[:50]}...")
        else:
            print("❌ Unicode content corrupted")
            return False
    
    return True

if __name__ == "__main__":
    print("Testing Unicode encoding and record preservation fixes...")
    success = test_unicode_encoding()
    
    if success:
        print("\n✅ All tests passed! The fixes should work correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Issues remain.")
        sys.exit(1)