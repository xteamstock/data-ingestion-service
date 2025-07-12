# Apify Integration Test Guide

## Overview

This guide explains the integration testing strategy for the Apify API client, addressing the challenges of testing against external APIs with dynamic data.

## Key Principles

### 1. **Test Structure, Not Content**
- Focus on validating data schema and field types
- Use pattern matching for IDs and usernames
- Check reasonable ranges (e.g., counts >= 0) instead of exact values
- Validate relationships between fields

### 2. **Control Test Costs**
- Use minimal data requests (resultsPerPage: 1-5)
- Disable expensive features (video/cover downloads)
- Set up cost monitoring and reporting
- Use test-specific API tokens with limited quotas

### 3. **Handle Dynamic Data**
- Use stable test accounts (corporate/brand accounts)
- Skip tests when no data is returned
- Implement retry logic for transient failures
- Use conditional assertions based on data availability

## Test Categories

### **Basic Tests** (Always Run)
- `test_api_connectivity`: Verifies client initialization
- `test_invalid_actor_error_handling`: Tests error handling

### **TikTok Integration Tests** (Require API Token)
- `test_tiktok_scraper_data_structure`: Validates TikTok response structure
- `test_with_retry_logic`: Tests retry mechanism
- `test_list_recent_runs`: Tests TikTok run listing functionality

### **YouTube Integration Tests** (Require API Token)
- `test_youtube_scraper_data_structure`: **CRITICAL** - Validates YouTube response structure against sample data
- `test_youtube_channel_validation`: Tests channel info validation
- `test_youtube_vs_tiktok_comparison`: Compares both platforms
- `test_youtube_actor_list_runs`: Tests YouTube run listing
- `test_youtube_error_handling`: Tests YouTube error scenarios
- `test_youtube_data_completeness`: Tests data completeness

### **Expensive Tests** (Run Selectively)
- `test_cost_tracking`: Monitors API costs
- Full data scraping tests with `@pytest.mark.expensive`

## Running Tests

### Prerequisites
```bash
# Set your Apify token
export APIFY_TOKEN='your-token-here'
# OR use a dedicated test token
export APIFY_TEST_TOKEN='your-test-token-here'
```

### Test Commands

```bash
# Run all non-expensive tests (default)
./tests/run_integration_tests.sh

# Run only quick connectivity tests
./tests/run_integration_tests.sh quick

# Run all tests including expensive ones
./tests/run_integration_tests.sh all

# Run a specific test
./tests/run_integration_tests.sh single test_api_connectivity

# Run with coverage report
./tests/run_integration_tests.sh coverage

# Run only YouTube tests
./tests/run_integration_tests.sh youtube

# Run only TikTok tests
./tests/run_integration_tests.sh tiktok

# Run only data structure validation tests
./tests/run_integration_tests.sh structure
```

### Using Pytest Directly

```bash
# Run all integration tests
pytest -m integration tests/integration/

# Skip expensive tests
pytest -m "integration and not expensive"

# Run only YouTube tests
pytest -m integration -k youtube tests/integration/

# Run only TikTok tests  
pytest -m integration -k tiktok tests/integration/

# Run only data structure tests
pytest -m integration -k "data_structure or structure" tests/integration/

# Run only flaky tests with retries
pytest -m "integration and flaky"

# Run with specific verbosity
pytest -v -m integration tests/integration/
```

## Test Structure Validation

The tests validate the following Apify response structures:

### TikTok Data Item
```python
{
    'id': '7123456789012345678',  # 19-digit string
    'text': 'Caption text',
    'createTime': 1625097600,
    'authorMeta': {
        'id': '123456789',
        'name': 'username',
        'nickName': 'Display Name',
        'verified': True,
        'signature': 'Bio text',
        'avatar': 'https://...'
    },
    'diggCount': 1234,     # >= 0
    'shareCount': 567,     # >= 0
    'playCount': 89012,    # >= 0
    'commentCount': 345    # >= 0
}
```

### YouTube Data Item (Critical Structure Validation)
```python
{
    'title': 'Video Title Here',                    # String, video title
    'type': 'video',                               # String, content type
    'id': 'hw4czb5o5Ys',                          # String, 11-char YouTube ID
    'url': 'https://www.youtube.com/watch?v=hw4czb5o5Ys',  # Video URL
    'thumbnailUrl': 'https://i.ytimg.com/vi/hw4czb5o5Ys/maxresdefault.jpg',
    'viewCount': 11,                               # Integer, view count
    'date': '2025-07-10T11:39:24.000Z',           # ISO date format
    'likes': 0,                                    # Integer, likes count
    'channelName': 'Nutifood - Chuyên Gia Dinh Dưỡng',
    'channelUrl': 'https://www.youtube.com/channel/UCWrg_PFo09xFsW00voXoU-Q',
    'channelId': 'UCWrg_PFo09xFsW00voXoU-Q',       # String, starts with UC + 22 chars
    'channelUsername': 'NutiFoodVietNam',
    'duration': '00:00:33',                        # HH:MM:SS format
    'commentsCount': 0,                            # Integer, comments count
    'text': 'Video description...',                # Video description
    'aboutChannelInfo': {                          # Critical for analytics
        'channelName': 'Nutifood - Chuyên Gia Dinh Dưỡng',
        'channelId': 'UCWrg_PFo09xFsW00voXoU-Q',
        'numberOfSubscribers': 188000,             # Integer
        'channelTotalVideos': 403,                 # Integer
        'channelTotalViews': 307651554,            # Integer
        'isChannelVerified': False,                # Boolean
        'channelDescription': 'Channel description...'
    },
    'descriptionLinks': [                          # Array of links in description
        {
            'url': 'https://youtube.com/hashtag/example',
            'text': '#example'
        }
    ],
    'hashtags': ['#varnacolostrum', '#varna']      # Array of hashtags
}
```

### Apify Status Response
```python
{
    'status': 'SUCCEEDED',  # One of: READY, RUNNING, SUCCEEDED, FAILED, etc.
    'is_ready': True,
    'dataset_id': 'abc123...',
    'started_at': '2025-01-11T15:30:00Z',
    'finished_at': '2025-01-11T15:30:16Z',
    'runtime_secs': 16,
    'items_scraped': 16,
    'compute_units': 0.123,
    'total_cost_usd': 0.086
}
```

## Cost Management

### Monitoring Costs
- Tests track cost per operation
- Session-wide cost reporting at test completion
- Warning threshold: $0.10 per test
- Error threshold: $0.50 per test
- Session limit: $5.00 total

### Cost Report Example
```
======================================
INTEGRATION TEST COST REPORT
======================================
Total Cost: $0.1234
Total Tests: 5
Average Duration: 23.45s
Total Items Scraped: 25
======================================
```

## Handling Common Issues

### Rate Limiting
- Tests implement automatic retry with exponential backoff
- Use `@pytest.mark.flaky` for tests prone to rate limits
- Consider using multiple test tokens

### Empty Results
- Tests skip gracefully when profiles have no content
- Use `pytest.skip()` instead of failing

### Network Issues
- Timeout set to 5 minutes for long-running operations
- Automatic job cancellation on timeout
- Cleanup fixture ensures no orphaned jobs

### API Changes
- Focus on core fields that are unlikely to change
- Use flexible validation (patterns over exact matches)
- Regular review of test assumptions

## Best Practices

1. **Always use cleanup fixtures** to cancel unfinished jobs
2. **Set reasonable timeouts** to avoid hanging tests
3. **Use stable test data** (official accounts, brand pages)
4. **Monitor costs** and set up alerts for unusual spending
5. **Document test failures** with API response details
6. **Version your test data** structures for easy updates

## Debugging Failed Tests

```bash
# Run with full output
pytest -vvs tests/integration/test_apify_integration.py::test_name

# Enable debug logging
PYTEST_CURRENT_TEST=1 pytest -v --log-cli-level=DEBUG

# Run with pdb on failure
pytest --pdb tests/integration/test_apify_integration.py
```

## Reference Data

See `reference_data.py` for:
- Expected data structures
- Validation patterns
- Cost thresholds
- Example responses from actual Apify runs