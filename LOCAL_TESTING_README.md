# Local Testing Guide for Data Ingestion Service

This guide shows you how to test the multi-platform data-ingestion service locally in isolation, without needing real GCP services or API keys.

## 🚀 Quick Start

### Option 1: Local Development Server (Recommended)
Run the service locally with all dependencies mocked:

```bash
# Start the local development server
python local_dev_server.py

# The server will start on http://localhost:8080
# All external dependencies (GCS, BigQuery, PubSub, APIs) are mocked
```

### Option 2: Test Suite
Run comprehensive tests without starting a server:

```bash
# Run the full test suite
python tests/local_testing_guide.py

# Run only endpoint tests (requires running server)
python tests/local_testing_guide.py --endpoints-only

# Create manual testing scripts
python tests/local_testing_guide.py --create-scripts
```

## 🧪 Testing Features

### 1. **Multi-Platform Support**
Test all three platforms with mocked API responses:

```bash
# Facebook crawl
curl -X POST http://localhost:8080/api/v1/crawl/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "facebook",
    "url": "https://facebook.com/GrowPLUScuaNutiFood",
    "num_of_posts": 5,
    "competitor": "nutifood",
    "brand": "growplus-nutifood", 
    "category": "sua-bot-tre-em"
  }'

# TikTok crawl
curl -X POST http://localhost:8080/api/v1/crawl/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "tiktok",
    "url": "https://tiktok.com/@nutifoodvietnam",
    "num_of_posts": 5,
    "country": "VN",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }'

# YouTube crawl  
curl -X POST http://localhost:8080/api/v1/crawl/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "youtube",
    "url": "https://youtube.com/@NutiFoodVietNam",
    "num_of_posts": 5,
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }'
```

### 2. **Platform Registry**
Check supported platforms:

```bash
curl http://localhost:8080/api/v1/platforms
```

### 3. **Event Monitoring**
View captured PubSub events (normally sent to data-processing service):

```bash
curl http://localhost:8080/api/v1/events
```

### 4. **Storage Verification** 
Check mock GCS uploads:

```bash
curl http://localhost:8080/api/v1/uploads
```

### 5. **BigQuery Verification**
Check mock BigQuery inserts:

```bash
curl http://localhost:8080/api/v1/bigquery
```

## 📊 What Gets Tested

### ✅ **Architecture Components**
- ✅ **Platform Registry**: Facebook, TikTok, YouTube handlers
- ✅ **API Client Integration**: BrightData (Facebook) & Apify (TikTok/YouTube)  
- ✅ **Hierarchical Storage**: GCS paths with business context partitioning
- ✅ **Event Publishing**: PubSub events for data-processing service
- ✅ **Parameter Validation**: Platform-specific URL and parameter checks
- ✅ **Error Handling**: Invalid platforms, missing parameters

### ✅ **Multi-Platform Features**
- ✅ **Facebook**: BrightData integration with date format conversion
- ✅ **TikTok**: Apify integration with profile URL handling
- ✅ **YouTube**: Apify integration with channel URL support
- ✅ **Unified API**: Same endpoint supports all platforms via `platform` parameter

### ✅ **Data Flow**
```
HTTP Request → Platform Handler → API Client (Mocked) → Storage (Mocked) → Event (Logged)
```

## 🔧 Local Development Features

### **Mocked Dependencies**
- **✅ Google Cloud Storage**: Logs upload operations, tracks file paths
- **✅ BigQuery**: Logs insert operations, tracks metadata
- **✅ PubSub**: Logs events, available via `/api/v1/events`
- **✅ BrightData API**: Returns mock snapshot IDs and data
- **✅ Apify API**: Returns mock run IDs and data

### **Enhanced Logging**
The local server provides detailed logging for:
- 🚀 Crawl trigger operations
- 📡 PubSub event publishing
- 💾 GCS file uploads  
- 📊 BigQuery row inserts
- 🔍 API client interactions

### **Development Endpoints**
Additional endpoints for testing:
- `GET /api/v1/platforms` - List supported platforms
- `GET /api/v1/events` - View captured events
- `GET /api/v1/uploads` - View mock GCS uploads
- `GET /api/v1/bigquery` - View mock BigQuery inserts

## 🎯 Testing Scenarios

### **Scenario 1: Multi-Platform Crawl**
Test that all platforms work with their respective API providers:

```bash
python local_dev_server.py &
SERVER_PID=$!

# Test all platforms
for platform in facebook tiktok youtube; do
  echo "Testing $platform..."
  curl -s -X POST http://localhost:8080/api/v1/crawl/trigger \
    -H "Content-Type: application/json" \
    -d "{\"platform\":\"$platform\",\"url\":\"https://$platform.com/test\",\"competitor\":\"test\"}" \
    | jq '.status'
done

kill $SERVER_PID
```

### **Scenario 2: Event Flow Verification**
Verify events are published correctly:

```bash
# Trigger a crawl
curl -X POST http://localhost:8080/api/v1/crawl/trigger -H "Content-Type: application/json" -d '{"platform":"facebook","url":"https://facebook.com/test","competitor":"nutifood"}'

# Check events were published
curl http://localhost:8080/api/v1/events | jq '.events[] | {event_type: .event_type, platform: .data.platform}'
```

### **Scenario 3: Storage Path Verification**
Check hierarchical storage paths:

```bash
# Trigger a crawl
curl -X POST http://localhost:8080/api/v1/crawl/trigger -H "Content-Type: application/json" -d '{"platform":"tiktok","url":"https://tiktok.com/@test","competitor":"nutifood","brand":"growplus","category":"sua-bot"}'

# Check storage paths
curl http://localhost:8080/api/v1/uploads | jq 'keys[]' | grep "platform=tiktok/competitor=nutifood"
```

## 🔄 Integration with Data Processing Service

### **Event Schema**
The service publishes events in the format expected by data-processing:

```json
{
  "event_type": "data.ingestion.completed",
  "timestamp": "2024-01-01T10:00:00.000Z",
  "data": {
    "crawl_id": "uuid",
    "snapshot_id": "provider_id", 
    "gcs_path": "gs://bucket/platform=facebook/competitor=nutifood/...",
    "post_count": 10,
    "media_count": 5,
    "platform": "facebook",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em"
  }
}
```

### **Testing with Real Data Processing Service**
To test integration with the real data-processing service:

1. **Start both services locally**:
   ```bash
   # Terminal 1: Data Ingestion (mocked)
   python local_dev_server.py
   
   # Terminal 2: Data Processing (you'll need to set this up)
   cd ../data-processing
   python app.py
   ```

2. **Use real PubSub** (optional):
   ```bash
   # Set real GCP project and enable PubSub
   export GOOGLE_CLOUD_PROJECT=your-project
   python local_dev_server.py --no-mock-pubsub
   ```

## 📝 Next Steps

After local testing is successful:

1. **Deploy to Cloud Run**: Use the deployment scripts in `docs/deployment-results.md`
2. **Configure real API keys**: Set `BRIGHTDATA_API_KEY` and `APIFY_API_TOKEN`
3. **Set up PubSub topics**: Create topics for event communication
4. **Configure data-processing service**: Ensure it subscribes to ingestion events
5. **Test end-to-end**: Trigger real crawls and verify data flows to BigQuery

## 🐛 Troubleshooting

### **Import Errors**
```bash
# Make sure you're in the service directory
cd /path/to/social-analytics-platform/services/data-ingestion

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Platform Handler Not Found**
```bash
# Check platform registry
python -c "from platforms.registry import PlatformRegistry; PlatformRegistry.load_default_config(); print(PlatformRegistry.list_platforms())"
```

### **API Client Errors**
The local server mocks all API clients, so you shouldn't see real API errors. If you do, check:
- Environment variables are set correctly
- Mock patches are working properly

This local testing setup allows you to verify the entire multi-platform integration without external dependencies! 🎉