#!/bin/bash
# Setup GCP permissions and resources for data-ingestion service

PROJECT_ID="competitor-destroyer"
SERVICE_ACCOUNT="social-media-cf-sa@competitor-destroyer.iam.gserviceaccount.com"

echo "🚀 Setting up GCP permissions and resources for data-ingestion service"
echo "=" * 70
echo "Project: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# Grant IAM roles
echo "🔐 Granting IAM roles..."
echo "--------------------------------"

echo "📦 Storage permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.objectAdmin"

echo "📊 BigQuery permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.dataEditor"

echo "📡 PubSub permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/pubsub.admin"

# Create GCS buckets
echo ""
echo "🪣 Creating GCS buckets..."
echo "--------------------------------"

echo "Creating social-analytics-raw-data..."
gsutil mb -p $PROJECT_ID gs://social-analytics-raw-data 2>/dev/null || echo "Bucket already exists or creation failed"

echo "Creating social-analytics-processed-data..."
gsutil mb -p $PROJECT_ID gs://social-analytics-processed-data 2>/dev/null || echo "Bucket already exists or creation failed"

# Create BigQuery dataset
echo ""
echo "📊 Creating BigQuery dataset..."
echo "--------------------------------"

echo "Creating social_analytics dataset..."
bq mk --project_id=$PROJECT_ID social_analytics 2>/dev/null || echo "Dataset already exists or creation failed"

# Create PubSub topics
echo ""
echo "📡 Creating PubSub topics..."
echo "--------------------------------"

echo "Creating crawl-triggered topic..."
gcloud pubsub topics create social-analytics-crawl-triggered --project=$PROJECT_ID 2>/dev/null || echo "Topic already exists or creation failed"

echo "Creating data-ingestion-completed topic..."
gcloud pubsub topics create social-analytics-data-ingestion-completed --project=$PROJECT_ID 2>/dev/null || echo "Topic already exists or creation failed"

echo "Creating crawl-failed topic..."
gcloud pubsub topics create social-analytics-crawl-failed --project=$PROJECT_ID 2>/dev/null || echo "Topic already exists or creation failed"

# Verify setup
echo ""
echo "🔍 Verifying setup..."
echo "--------------------------------"

echo "Checking GCS buckets:"
gsutil ls gs://social-analytics-raw-data
gsutil ls gs://social-analytics-processed-data

echo ""
echo "Checking BigQuery dataset:"
bq ls -d $PROJECT_ID:social_analytics

echo ""
echo "Checking PubSub topics:"
gcloud pubsub topics list --project=$PROJECT_ID --filter="name~social-analytics"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary of what was created/configured:"
echo "• Service account permissions: Storage Object Admin, BigQuery Data Editor, PubSub Publisher/Admin"
echo "• GCS buckets: social-analytics-raw-data, social-analytics-processed-data" 
echo "• BigQuery dataset: social_analytics"
echo "• PubSub topics: social-analytics-crawl-triggered, social-analytics-data-ingestion-completed, social-analytics-crawl-failed"
echo ""
echo "🧪 Next steps:"
echo "   python setup_test_environment.py  # Verify access"
echo "   python run_test.py test_event_publisher.py  # Test PubSub events"