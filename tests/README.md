# Data Ingestion Service Tests

## 🧪 Test Crawl Endpoint

The `test_crawl_endpoint.py` script tests the crawl trigger endpoint for Facebook, TikTok, and YouTube platforms.

### Usage

#### Test Cloud Run Endpoint (Default)
```bash
# Test with default Cloud Run endpoint
python3 tests/test_crawl_endpoint.py --platform facebook --num-posts 50 --start-date 2025-01-01 --end-date 2025-01-01

# Test all platforms
python3 tests/test_crawl_endpoint.py --platform all --num-posts 10
```

#### Test Local Endpoint
```bash
# Use --local flag to test against localhost:8080
python3 tests/test_crawl_endpoint.py --local --platform facebook --num-posts 50
```

### Options
- `--platform`: Choose platform to test (facebook, tiktok, youtube, all). Default: all
- `--num-posts`: Number of posts to crawl. Default: 100
- `--start-date`: Start date in YYYY-MM-DD format. Default: 2025-01-01
- `--end-date`: End date in YYYY-MM-DD format. Default: 2025-01-01
- `--local`: Use local endpoint (http://localhost:8080) instead of Cloud Run
- `--base-url`: Override the base URL completely (optional)

### Examples

```bash
# Test Facebook on Cloud Run with specific date range
python3 tests/test_crawl_endpoint.py --platform facebook --num-posts 50 --start-date 2025-01-01 --end-date 2025-01-15

# Test all platforms locally
python3 tests/test_crawl_endpoint.py --local --platform all --num-posts 5

# Test with custom base URL
python3 tests/test_crawl_endpoint.py --base-url https://custom-url.run.app --platform tiktok
```

### Platform Differences
- **Facebook**: Uses BrightData API with standard date parameters
- **TikTok**: Uses Apify API with different date parameter names
- **YouTube**: Uses Apify API with startUrls format