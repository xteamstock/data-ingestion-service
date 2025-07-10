# Deployment Guide - Data Ingestion Service

This document outlines the complete deployment process for the Data Ingestion Service to Google Cloud Run.

## 📋 Prerequisites

- Google Cloud Project with billing enabled
- Docker installed and configured
- gcloud CLI installed and authenticated
- Required APIs enabled

## 🔧 Step 1: Environment Setup

### Enable Required GCP APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
```

### Create Service Account
```bash
# Create service account
gcloud iam service-accounts create data-ingestion-sa \
    --description="Service account for Data Ingestion Service" \
    --display-name="Data Ingestion SA"

# Grant required permissions
gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Create Required Resources

#### Create GCS Buckets
```bash
# Raw data bucket
gsutil mb -p competitor-destroyer -l asia-southeast1 gs://social-analytics-raw-data

# Processed data bucket  
gsutil mb -p competitor-destroyer -l asia-southeast1 gs://social-analytics-processed-data
```

#### Create BigQuery Dataset and Tables
```bash
# Create dataset
bq mk --location=asia-southeast1 social_analytics

# Create crawl metadata table
bq mk --table social_analytics.crawl_metadata \
    crawl_id:STRING,snapshot_id:STRING,platform:STRING,competitor:STRING,brand:STRING,category:STRING,status:STRING,created_at:TIMESTAMP,updated_at:TIMESTAMP

# Create raw data snapshots table
bq mk --table social_analytics.raw_data_crawl_snapshots \
    crawl_id:STRING,snapshot_id:STRING,gcs_path:STRING,file_format:STRING,total_posts:INTEGER,total_media:INTEGER,file_size_bytes:INTEGER,ingestion_timestamp:TIMESTAMP
```

#### Create Pub/Sub Topics
```bash
# Create topics for event-driven communication
gcloud pubsub topics create social-analytics-crawl-triggered
gcloud pubsub topics create social-analytics-data-ingestion-completed
gcloud pubsub topics create social-analytics-crawl-failed
```

#### Create Secrets
```bash
# Store BrightData API key (without newline)
echo -n "your-brightdata-api-key" | gcloud secrets create brightdata-api-key --data-file=-
```

## 🐳 Step 2: Docker Configuration

### Configure Docker for GCR
```bash
gcloud auth configure-docker --quiet
```

### Build Docker Image for AMD64 (Cloud Run)
```bash
cd /path/to/social-analytics-platform/services/data-ingestion

# Build for AMD64 architecture (required for Cloud Run)
docker build --platform linux/amd64 -t gcr.io/competitor-destroyer/data-ingestion:latest .
```

### Push Image to GCR
```bash
docker push gcr.io/competitor-destroyer/data-ingestion:latest
```

## ☁️ Step 3: Cloud Run Deployment

### Grant User Permission to Act as Service Account
```bash
gcloud iam service-accounts add-iam-policy-binding \
    data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com \
    --member="user:your-email@gmail.com" \
    --role="roles/iam.serviceAccountTokenCreator"
```

### Deploy to Cloud Run
```bash
gcloud run deploy data-ingestion-service \
    --image=gcr.io/competitor-destroyer/data-ingestion:latest \
    --service-account=data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com \
    --region=asia-southeast1 \
    --no-allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=540 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=competitor-destroyer,PUBSUB_TOPIC_PREFIX=social-analytics,GCS_BUCKET_RAW_DATA=social-analytics-raw-data,GCS_BUCKET_PROCESSED_DATA=social-analytics-processed-data,BIGQUERY_DATASET=social_analytics" \
    --set-secrets="BRIGHTDATA_API_KEY=brightdata-api-key:latest"
```

### Grant User Permission to Invoke Service
```bash
gcloud run services add-iam-policy-binding data-ingestion-service \
    --region=asia-southeast1 \
    --member="user:your-email@gmail.com" \
    --role="roles/run.invoker"
```

## 🧪 Step 4: Testing Deployment

### Test Health Endpoint
```bash
curl -X GET "https://data-ingestion-service-ud5pi5bwfq-as.a.run.app/health" \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    -H "Content-Type: application/json"
```

### Test Crawl Trigger
```bash
curl -X POST "https://data-ingestion-service-ud5pi5bwfq-as.a.run.app/api/v1/crawl/trigger" \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    -H "Content-Type: application/json" \
    -d '{
        "dataset_id": "gd_lkaxegm826bjpoo9m5",
        "platform": "facebook", 
        "competitor": "nutifood",
        "brand": "growplus-nutifood",
        "category": "sua-bot-tre-em",
        "url": "https://www.facebook.com/GrowPLUScuaNutiFood/?locale=vi_VN",
        "num_of_posts": 3,
        "start_date": "2024-01-01",
        "end_date": "2024-01-01",
        "include_profile_data": true
    }'
```

Expected response:
```json
{
    "crawl_id": "uuid-here",
    "message": "Crawl triggered successfully",
    "snapshot_id": "s_xxxxxxxxxx",
    "status": "success",
    "timestamp": "2025-07-09T03:12:48.123702"
}
```

### Verify Pub/Sub Events
```bash
# Create test subscription
gcloud pubsub subscriptions create test-subscription --topic=social-analytics-crawl-triggered

# Check for events
gcloud pubsub subscriptions pull test-subscription --limit=1 --auto-ack
```

## 🔧 Common Issues and Solutions

### Issue 1: Architecture Mismatch
**Error**: `Container manifest type 'application/vnd.oci.image.index.v1+json' must support amd64/linux`

**Solution**: Rebuild image with `--platform linux/amd64` flag:
```bash
docker build --platform linux/amd64 -t gcr.io/competitor-destroyer/data-ingestion:latest .
```

### Issue 2: Authentication Errors
**Error**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
1. Grant run.invoker permission:
```bash
gcloud run services add-iam-policy-binding data-ingestion-service \
    --region=asia-southeast1 \
    --member="user:your-email@gmail.com" \
    --role="roles/run.invoker"
```

2. Use correct token type:
```bash
# Use identity token for Cloud Run
gcloud auth print-identity-token

# NOT access token
gcloud auth print-access-token
```

### Issue 3: Secret Access Denied
**Error**: `Permission denied on secret: brightdata-api-key`

**Solution**: Grant Secret Manager access:
```bash
gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Issue 4: BrightData API Key Format
**Error**: `Invalid header value b'Bearer key\\n'`

**Solution**: Remove newline when creating secret:
```bash
echo -n "your-api-key" | gcloud secrets versions add brightdata-api-key --data-file=-
```

### Issue 5: BigQuery Permission Denied
**Error**: `Access Denied: Dataset competitor-destroyer:social_analytics`

**Solution**: Grant BigQuery permissions:
```bash
gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"
```

## 📊 Monitoring and Logs

### View Service Logs
```bash
gcloud run services logs read data-ingestion-service --region=asia-southeast1 --limit=20
```

### Check Service Status
```bash
gcloud run services describe data-ingestion-service --region=asia-southeast1
```

### Monitor Pub/Sub Topics
```bash
gcloud pubsub topics list --filter="name:social-analytics"
gcloud pubsub subscriptions list --filter="topic:social-analytics-crawl-triggered"
```

## 🔄 Updating the Service

### Method 1: Simple Update (Zero Downtime)
For quick updates where you want to replace the current version immediately:

```bash
# 1. Build new image with same tag
docker build --platform linux/amd64 -t gcr.io/competitor-destroyer/data-ingestion:latest .

# 2. Push to registry
docker push gcr.io/competitor-destroyer/data-ingestion:latest

# 3. Deploy update (Cloud Run will automatically pull new image)
gcloud run services update data-ingestion-service --region=asia-southeast1
```

### Method 2: Controlled Deployment (Recommended for Production)
For controlled deployments where you want to test before routing traffic:

```bash
# 1. Build new image with version tag
docker build --platform linux/amd64 -t gcr.io/competitor-destroyer/data-ingestion:v1.x .

# 2. Push to registry
docker push gcr.io/competitor-destroyer/data-ingestion:v1.x

# 3. Deploy new revision without traffic
gcloud run deploy data-ingestion-service \
    --image=gcr.io/competitor-destroyer/data-ingestion:v1.x \
    --region=asia-southeast1 \
    --no-traffic

# 4. Test the new revision (it will have 0% traffic initially)
# Check Cloud Run console for the revision-specific URL or use:
gcloud run revisions list --service=data-ingestion-service --region=asia-southeast1

# 5. Test endpoints (health check first, then your new features)
curl -X GET "https://data-ingestion-service-ud5pi5bwfq-as.a.run.app/health" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# 6. Route traffic to new revision when ready
gcloud run services update-traffic data-ingestion-service \
    --to-latest \
    --region=asia-southeast1

# 7. Verify deployment
gcloud run services describe data-ingestion-service --region=asia-southeast1
```

### Rollback if Needed
```bash
# List all revisions to find the previous working one
gcloud run revisions list --service=data-ingestion-service --region=asia-southeast1

# Route traffic back to previous revision
gcloud run services update-traffic data-ingestion-service \
    --to-revisions=data-ingestion-service-00004-gvv=100 \
    --region=asia-southeast1
```

## 🏗️ Service Configuration

### Current Environment Variables
- `GOOGLE_CLOUD_PROJECT`: competitor-destroyer
- `PUBSUB_TOPIC_PREFIX`: social-analytics  
- `GCS_BUCKET_RAW_DATA`: social-analytics-raw-data
- `GCS_BUCKET_PROCESSED_DATA`: social-analytics-processed-data
- `BIGQUERY_DATASET`: social_analytics

### Current Secrets
- `BRIGHTDATA_API_KEY`: BrightData API authentication key

### Service Specifications
- **Memory**: 1GB
- **CPU**: 1 vCPU
- **Scaling**: 0-10 instances
- **Timeout**: 540 seconds (9 minutes)
- **Region**: asia-southeast1
- **Access**: Private (authentication required)

## 🚀 Latest Deployment Status (July 10, 2025)

### ✅ Successfully Deployed - Revision 00010-c9x

**Critical Fixes Implemented:**

1. **BrightData JSON Parsing Issue RESOLVED** ✅
   - **Problem**: BrightData API returned concatenated JSON objects causing `json.JSONDecodeError: Extra data: line 2 column 1`
   - **File Fixed**: `brightdata/handlers/download_handler.py`
   - **Solution**: Implemented robust `_parse_brightdata_response()` method with multiple parsing strategies:
     - Standard JSON parsing
     - Concatenated JSON object parsing using `JSONDecoder.raw_decode()`
     - JSON line-by-line parsing
     - Content filtering to extract valid JSON from mixed content
   - **Result**: Service now successfully processes all BrightData response formats

2. **Unicode Encoding Issue RESOLVED** ✅
   - **Problem**: Vietnamese text stored as escape sequences (`\u0110\u00e2y l\u00e0`) instead of proper UTF-8
   - **File Fixed**: `handlers/crawl_handler.py` in `_store_raw_data_gcs()` method
   - **Solution**: Added `ensure_ascii=False` and proper UTF-8 encoding:
     ```python
     json_data = json.dumps(data, indent=2, ensure_ascii=False)
     blob.upload_from_string(
         json_data.encode('utf-8'),
         content_type='application/json; charset=utf-8'
     )
     ```
   - **Result**: Vietnamese text now properly stored and readable in GCS files

**Deployment Details:**
- **Service**: `data-ingestion-service` 
- **Revision**: `00010-c9x`
- **Status**: ✅ **PRODUCTION READY**
- **Traffic**: 100% routed to latest revision
- **Region**: asia-southeast1
- **Last Deployed**: July 10, 2025 10:56:45 UTC

**Exact Commands Used for Deployment:**
```bash
# 1. Navigate to service directory
cd /Users/tranquocbao/crawlerX/social-analytics-platform/services/data-ingestion

# 2. Deploy with source (from working directory)
export GOOGLE_CLOUD_PROJECT=social-analytics-prod
export REGION=asia-southeast1
gcloud run deploy data-ingestion-service \
  --source . \
  --region=asia-southeast1 \
  --allow-unauthenticated

# 3. Manually route traffic to latest revision (CRITICAL STEP)
gcloud run services update-traffic data-ingestion-service \
  --to-latest \
  --region=asia-southeast1

# 4. Verify deployment status
gcloud run services describe data-ingestion-service --region=asia-southeast1
```

**Verification Tests Passed:**
- ✅ Health endpoint responsive
- ✅ BrightData JSON parsing working for all response formats
- ✅ Unicode encoding properly handled
- ✅ GCS storage working with UTF-8 content
- ✅ Pub/Sub events publishing successfully
- ✅ BigQuery metadata storage functional

## 📈 Next Steps

1. **Complete Data Processing Service deployment** - Currently blocked on build failure
2. **End-to-end pipeline testing** with both services operational
3. **Set up monitoring and alerting** for production use
4. **Implement CI/CD pipeline** for automated deployments

## ❓ Frequently Asked Questions (FAQ)

### Q1: PubSub Events Not Appearing in Console
**What**: PubSub events are being published successfully (confirmed in logs) but not visible in Google Cloud Console.

**Why**: Events published to PubSub topics are immediately consumed by active subscriptions. The Cloud Console only shows topic metrics, not individual messages unless they're pulled from subscriptions.

**When**: This happens when you have active subscribers or when checking the wrong place in the console.

**How to Fix**: 
```bash
# Check if messages are actually being published by pulling from subscription
gcloud pubsub subscriptions pull realtime-test --limit=10 --project=competitor-destroyer

# Create a test subscription if needed
gcloud pubsub subscriptions create debug-subscription --topic=social-analytics-crawl-triggered
```

### Q2: BigQuery Permission Denied for Status Endpoint
**What**: `/api/v1/crawl/<crawl_id>/status` returns "Crawl not found" even though the crawl exists in BigQuery.

**Why**: Service account has `bigquery.dataEditor` permission but missing `bigquery.jobUser` permission required to run queries.

**When**: Occurs when implementing new endpoints that perform BigQuery queries (not just inserts).

**How to Fix**:
```bash
# Grant BigQuery job user permission
gcloud projects add-iam-policy-binding competitor-destroyer \
    --member="serviceAccount:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
```

**Error in Logs**: `403 POST https://bigquery.googleapis.com/bigquery/v2/projects/competitor-destroyer/jobs: Access Denied: User does not have bigquery.jobs.create permission`

### Q3: Docker Architecture Mismatch on Cloud Run
**What**: `Container manifest type 'application/vnd.oci.image.index.v1+json' must support amd64/linux`

**Why**: Docker image was built for ARM64 (Apple Silicon) but Cloud Run requires AMD64 architecture.

**When**: Building Docker images on Apple Silicon Macs without the platform flag.

**How to Fix**:
```bash
# Always build with AMD64 platform for Cloud Run
docker build --platform linux/amd64 -t gcr.io/competitor-destroyer/data-ingestion:latest .
```

### Q4: Service Not Updating After Deployment
**What**: Code changes not reflected after deploying new revision.

**Why**: Traffic is still routed to the old revision, or the new image wasn't properly built/pushed.

**When**: Using `--no-traffic` flag without manually routing traffic afterward.

**How to Fix**:
```bash
# Check which revision is receiving traffic
gcloud run services describe data-ingestion-service --region=asia-southeast1

# Route traffic to latest revision
gcloud run services update-traffic data-ingestion-service \
    --to-latest \
    --region=asia-southeast1
```

### Q5: Authentication Errors (401/403) When Testing Endpoints
**What**: `401 Unauthorized` or `403 Forbidden` when calling Cloud Run endpoints.

**Why**: Using wrong token type or missing run.invoker permission.

**When**: Testing endpoints after deployment.

**How to Fix**:
```bash
# Use identity token (not access token) for Cloud Run
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" ...

# Grant run.invoker permission if needed
gcloud run services add-iam-policy-binding data-ingestion-service \
    --region=asia-southeast1 \
    --member="user:your-email@gmail.com" \
    --role="roles/run.invoker"
```

### Q6: Health Endpoint Works But Feature Endpoints Fail
**What**: `/health` returns 200 but new endpoints return 404 or errors.

**Why**: New code deployed but traffic not routed to new revision, or import/syntax errors in new code.

**When**: After adding new endpoints and deploying.

**How to Debug**:
```bash
# Check Cloud Run logs for errors
gcloud run services logs read data-ingestion-service --region=asia-southeast1 --limit=50

# Verify revision is receiving traffic
gcloud run revisions list --service=data-ingestion-service --region=asia-southeast1

# Test health endpoint to confirm service is running
curl -X GET "https://your-service-url/health" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

### Q7: Data Exists in BigQuery But Query Returns No Results
**What**: Data visible in BigQuery console but application queries return empty results.

**Why**: Query syntax issues, wrong dataset/table names, or missing query permissions.

**When**: Implementing database lookup functionality.

**How to Debug**:
```bash
# Test the exact query manually
bq query --use_legacy_sql=false --project_id=competitor-destroyer \
  "SELECT * FROM \`competitor-destroyer.social_analytics.crawl_metadata\` 
   WHERE crawl_id = 'your-crawl-id' LIMIT 1"

# Check service account permissions
gcloud projects get-iam-policy competitor-destroyer \
  --flatten="bindings[].members" \
  --filter="bindings.members:data-ingestion-sa@competitor-destroyer.iam.gserviceaccount.com"
```

### Q8: PubSub Events Not Retained After Being Consumed
**What**: PubSub events are published successfully but cannot be seen when creating new subscriptions.

**Why**: PubSub messages are **deleted permanently after being consumed** (acknowledged). New subscribers cannot access previously consumed messages.

**When**: Testing PubSub functionality by creating temporary subscriptions after events were published.

**How PubSub Works**:
1. Message published → Stored in topic
2. Subscriber pulls message → Message delivered to subscriber  
3. Subscriber acknowledges → **Message permanently deleted**
4. New subscribers → Cannot access previously consumed messages

**Solution - Create Persistent Monitoring Subscriptions**:
```bash
# Create persistent subscriptions for monitoring (DO THIS ONCE)
gcloud pubsub subscriptions create monitoring-crawl-triggered \
  --topic=social-analytics-crawl-triggered --project=competitor-destroyer

gcloud pubsub subscriptions create monitoring-data-ingestion-completed \
  --topic=social-analytics-data-ingestion-completed --project=competitor-destroyer

gcloud pubsub subscriptions create monitoring-crawl-failed \
  --topic=social-analytics-crawl-failed --project=competitor-destroyer
```

**How to Always Monitor Events**:
```bash
# Check recent events (run these anytime to see events)
gcloud pubsub subscriptions pull monitoring-crawl-triggered --limit=10 --auto-ack
gcloud pubsub subscriptions pull monitoring-data-ingestion-completed --limit=10 --auto-ack  
gcloud pubsub subscriptions pull monitoring-crawl-failed --limit=10 --auto-ack
```

**Alternative - Add Event Logging to BigQuery**:
For permanent event storage, consider adding an event audit table to BigQuery that logs all published events.

### Q9: Why Are GCP Services So Slow?
**What**: Cloud Run cold starts, BrightData API calls, and BigQuery queries sometimes take 20-60 seconds.

**Why**: Multiple factors contribute to latency in distributed cloud systems:

**Cloud Run Cold Starts** (2-10 seconds):
- Container must start from scratch if no warm instances
- Image pulling, dependency loading, service initialization
- Happens with `min-instances=0` setting

**BrightData API Processing** (30-300 seconds):
- Web scraping inherently slow (page loads, rate limiting, data extraction)
- Social media platforms have anti-bot protections
- Large datasets require significant processing time

**BigQuery Query Latency** (1-5 seconds):
- Distributed processing across multiple nodes
- Data locality and caching affects performance
- Complex queries on large datasets take longer

**Network Latency** (100-500ms per request):
- Asia-Southeast1 region to US-based services
- Multiple API calls compound the latency
- TLS handshakes and authentication add overhead

**How to Optimize**:
```bash
# Reduce cold starts
gcloud run services update data-ingestion-service \
  --min-instances=1 \
  --region=asia-southeast1

# Enable background processing for immediate responses
# (Already implemented in current version)

# Use Cloud Run concurrency
gcloud run services update data-ingestion-service \
  --concurrency=100 \
  --region=asia-southeast1
```

**Expected Latencies**:
- Health check: 100-500ms
- Crawl trigger: 2-5 seconds (immediate response with background processing)
- Status check: 1-3 seconds  
- Background processing: 30-300 seconds (depending on data volume)
- Manual download: 10-60 seconds (depends on BrightData response)

## 🛠️ Debugging Checklist

When encountering issues:

1. **Check Cloud Run logs** first: `gcloud run services logs read data-ingestion-service --region=asia-southeast1 --limit=20`
2. **Verify service account permissions** for the specific operation
3. **Test endpoints incrementally**: health → simple → complex features
4. **Check revision traffic distribution**: `gcloud run services describe data-ingestion-service --region=asia-southeast1`
5. **Validate BigQuery queries manually** before debugging application code
6. **Use identity tokens** (not access tokens) for Cloud Run authentication

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Container Registry Documentation](https://cloud.google.com/container-registry/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)