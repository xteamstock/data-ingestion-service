# Data Ingestion Service

Social media data ingestion microservice using BrightData API.

## 🚀 Auto-Deployment Setup

This service auto-deploys to Cloud Run when you push to the main branch.

### Cloud Run Configuration
- **Service**: data-ingestion-service  
- **Region**: asia-southeast1
- **Project**: competitor-destroyer

### Environment Variables (Auto-configured)
- `GOOGLE_CLOUD_PROJECT=competitor-destroyer`
- `PUBSUB_TOPIC_PREFIX=social-analytics`
- `GCS_BUCKET_RAW_DATA=social-analytics-raw-data`
- `GCS_BUCKET_PROCESSED_DATA=social-analytics-processed-data`
- `BIGQUERY_DATASET=social_analytics`

### Required Secret
- `BRIGHTDATA_API_KEY` (configured in Secret Manager)

## 📋 API Endpoints

- `GET /health` - Health check
- `POST /api/v1/crawl/trigger` - Trigger crawl
- `GET /api/v1/crawl/{id}/status` - Check status

## 🔧 Local Development

```bash
pip install -r requirements.txt
export BRIGHTDATA_API_KEY=your_key
python app.py
```