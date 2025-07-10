#!/bin/bash

# Start Data Ingestion Service
echo "🚀 Starting Data Ingestion Service..."

# Set environment variables
export GOOGLE_CLOUD_PROJECT=competitor-destroyer
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
export BRIGHTDATA_API_KEY=f81f4318e2131a01162a4c671761ded8eaeb0316d2dd52ae264a664574f08bab
export PUBSUB_TOPIC_PREFIX=social-analytics
export GCS_BUCKET_RAW_DATA=social-analytics-raw-data
export BIGQUERY_DATASET=social_analytics
export PORT=8080
export PYTHONPATH=.

# Activate virtual environment
source venv/bin/activate

# Start the service
echo "Starting Flask app on port $PORT..."
python app.py