# Data Ingestion Service - Comprehensive Functionality Guide

## 📋 Table of Contents
1. [Service Overview](#service-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [API Endpoints](#api-endpoints)
5. [Event System](#event-system)
6. [Data Flow](#data-flow)
7. [Background Processing](#background-processing)
8. [Error Handling](#error-handling)
9. [Storage Systems](#storage-systems)
10. [Configuration](#configuration)
11. [Monitoring & Observability](#monitoring--observability)
12. [Integration Points](#integration-points)

## 🎯 Service Overview

The Data Ingestion Service is the entry point for social media data collection in the social analytics platform. It orchestrates crawl operations via BrightData API, manages data downloads, and triggers downstream processing through event-driven architecture.

### Key Responsibilities
- **Crawl Management**: Trigger and monitor BrightData crawl jobs
- **Data Collection**: Download raw social media data when ready
- **Storage**: Store raw data in GCS with proper structure
- **Event Publishing**: Notify downstream services of data availability
- **Background Processing**: Automated polling and download without blocking user requests

### Service Characteristics
- **Asynchronous**: Returns immediately to users while processing continues
- **Event-Driven**: Publishes events to trigger downstream processing
- **Resilient**: Handles failures gracefully with comprehensive error handling
- **Scalable**: Cloud Run auto-scaling with concurrent background tasks

## 🏗️ Architecture

### Component Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Service                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Flask     │    │   Handlers   │    │  BrightData  │  │
│  │   App       │───▶│              │───▶│   Client     │  │
│  │  (app.py)   │    │ CrawlHandler │    │              │  │
│  └─────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                     │          │
│         │                   ▼                     ▼          │
│         │           ┌──────────────┐    ┌──────────────┐    │
│         │           │   Storage    │    │  Background  │    │
│         └──────────▶│              │    │   Polling    │    │
│                     │  GCS Client  │    │   Tasks      │    │
│                     └──────────────┘    └──────────────┘    │
│                             │                     │          │
│                             ▼                     ▼          │
│                     ┌──────────────┐    ┌──────────────┐    │
│                     │   BigQuery   │    │    Event     │    │
│                     │   Metadata   │    │  Publisher   │    │
│                     └──────────────┘    └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack
- **Runtime**: Python 3.11 on Cloud Run
- **Framework**: Flask for HTTP endpoints
- **BrightData Integration**: Custom client with connection/crawl/download handlers
- **Storage**: Google Cloud Storage (GCS) for raw data
- **Database**: BigQuery for metadata and tracking
- **Messaging**: Google Cloud Pub/Sub for events
- **Concurrency**: ThreadPoolExecutor for background tasks

## 🔧 Core Components

### 1. Flask Application (`app.py`)
The main application entry point providing HTTP endpoints and coordinating all components.

**Key Features**:
- RESTful API endpoints for crawl operations
- Background task management with ThreadPoolExecutor
- Health check with detailed status information
- Immediate response pattern for better UX

### 2. Crawl Handler (`handlers/crawl_handler.py`)
Manages the complete crawl lifecycle from triggering to data storage.

**Responsibilities**:
- Generate unique crawl IDs
- Format parameters for BrightData API
- Store crawl metadata in BigQuery
- Download and store raw data in GCS
- Count posts and media files

**Key Methods**:
- `trigger_crawl()`: Initiates new crawl job
- `download_data()`: Downloads completed crawl data
- `_store_crawl_metadata()`: Persists metadata to BigQuery
- `_store_raw_data_gcs()`: Uploads raw data to GCS with UTF-8 encoding

### 3. BrightData Client (`brightdata/client.py`)
Facade client coordinating all BrightData API operations.

**Architecture Pattern**: Handler-based delegation
- **ConnectionHandler**: API connectivity and health checks
- **CrawlHandler**: Crawl job triggering and monitoring
- **DownloadHandler**: Data download operations

**Key Methods**:
- `test_api_connection()`: Verify API connectivity
- `trigger_crawl()`: Start new crawl job
- `poll_crawl_status()`: Check crawl readiness
- `download_crawl_data()`: Retrieve completed data

### 4. Event Publisher (`events/event_publisher.py`)
Publishes events to Pub/Sub for downstream services.

**Event Types**:
- `crawl-triggered`: New crawl initiated
- `data-ingestion-completed`: Data downloaded and stored
- `crawl-failed`: Crawl or download failure

**Event Schema**:
```json
{
  "event_type": "data-ingestion-completed",
  "timestamp": "2025-07-11T10:00:00Z",
  "source": "data-ingestion-service",
  "data": {
    "crawl_id": "uuid",
    "snapshot_id": "s_123",
    "gcs_path": "gs://bucket/path",
    "post_count": 100,
    "media_count": 50,
    "platform": "facebook",
    "competitor": "brand_name"
  }
}
```

### 5. Background Processing System
Automated polling and download system for non-blocking operations.

**Components**:
- **ThreadPoolExecutor**: Manages concurrent background tasks
- **Polling Loop**: Checks BrightData status every 30 seconds
- **Auto-Download**: Downloads data when ready
- **Event Publishing**: Notifies downstream services

**Configuration**:
- Max Workers: 10 concurrent tasks
- Poll Interval: 30 seconds
- Max Polls: 120 (1 hour timeout)
- Download Timeout: 300 seconds

## 📡 API Endpoints

### 1. Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "data-ingestion",
  "background_tasks": {
    "active_count": 3,
    "max_workers": 10,
    "enabled": true
  }
}
```

### 2. Trigger Crawl
```http
POST /api/v1/crawl/trigger
```

**Request Body**:
```json
{
  "dataset_id": "gd_lkaxegm826bjpoo9m5",
  "platform": "facebook",
  "competitor": "nutifood",
  "brand": "growplus-nutifood",
  "category": "sua-bot-tre-em",
  "url": "https://www.facebook.com/GrowPLUScuaNutiFood/",
  "start_date": "2024-12-24",
  "end_date": "2024-12-24",
  "include_profile_data": true,
  "num_of_posts": 10
}
```

**Response** (Immediate - 2-3 seconds):
```json
{
  "status": "success",
  "message": "Crawl triggered successfully",
  "crawl_id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot_id": "s_abc123def456",
  "timestamp": "2025-07-11T10:00:00Z",
  "background_processing": {
    "enabled": true,
    "status": "started",
    "poll_interval_seconds": 30,
    "max_polling_time_minutes": 60,
    "message": "Background polling started - crawl will auto-download when ready"
  }
}
```

### 3. Download Crawl Data (Manual)
```http
POST /api/v1/crawl/{crawl_id}/download
```

**Response**:
```json
{
  "status": "success",
  "message": "Data downloaded successfully",
  "crawl_id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot_id": "s_abc123def456",
  "gcs_path": "gs://social-analytics-raw-data/raw_snapshots/2025/07/11/snapshot_s_abc123def456.json",
  "post_count": 150,
  "media_count": 75,
  "timestamp": "2025-07-11T10:05:00Z"
}
```

### 4. Check Crawl Status
```http
GET /api/v1/crawl/{crawl_id}/status
```

**Response**:
```json
{
  "crawl_id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot_id": "s_abc123def456",
  "status": "processing",
  "ready_for_download": false,
  "timestamp": "2025-07-11T10:02:00Z",
  "metadata": {
    "platform": "facebook",
    "competitor": "nutifood",
    "created_at": "2025-07-11T10:00:00Z"
  },
  "background_processing": {
    "enabled": true,
    "active": true,
    "status": "polling",
    "poll_interval_seconds": 30,
    "max_polling_time_minutes": 60,
    "estimated_completion": "2025-07-11T10:10:00Z",
    "elapsed_minutes": 2
  }
}
```

## 🔄 Event System

### Published Events

#### 1. Crawl Triggered Event
Published immediately after successful crawl initiation.

```json
{
  "event_type": "crawl-triggered",
  "timestamp": "2025-07-11T10:00:00Z",
  "source": "data-ingestion-service",
  "data": {
    "crawl_id": "uuid",
    "snapshot_id": "s_123",
    "platform": "facebook",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em",
    "status": "triggered"
  }
}
```

#### 2. Data Ingestion Completed Event
Published after successful data download and storage.

```json
{
  "event_type": "data-ingestion-completed",
  "timestamp": "2025-07-11T10:05:00Z",
  "source": "data-ingestion-service",
  "data": {
    "crawl_id": "uuid",
    "snapshot_id": "s_123",
    "gcs_path": "gs://social-analytics-raw-data/raw_snapshots/...",
    "post_count": 150,
    "media_count": 75,
    "platform": "facebook",
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em",
    "status": "completed"
  }
}
```

#### 3. Crawl Failed Event
Published on any failure during crawl or download process.

```json
{
  "event_type": "crawl-failed",
  "timestamp": "2025-07-11T10:30:00Z",
  "source": "data-ingestion-service",
  "data": {
    "crawl_id": "uuid",
    "error_message": "Polling timeout after 60 minutes",
    "stage": "polling_timeout",
    "status": "failed"
  }
}
```

### Event Topics
- `social-analytics-crawl-triggered`
- `social-analytics-data-ingestion-completed`
- `social-analytics-crawl-failed`

## 📊 Data Flow

### 1. Crawl Trigger Flow
```
User Request → API Endpoint → Generate Crawl ID → BrightData API
                                     ↓
                            Store Metadata (BigQuery)
                                     ↓
                            Publish crawl-triggered Event
                                     ↓
                            Start Background Polling (if enabled)
                                     ↓
                            Return Immediate Response
```

### 2. Background Processing Flow
```
Background Thread → Poll BrightData Status (every 30s)
                            ↓
                    Status Ready? → Download Data
                            ↓
                    Store in GCS (UTF-8 encoded JSON)
                            ↓
                    Update BigQuery Metadata
                            ↓
                    Publish data-ingestion-completed Event
```

### 3. Data Storage Structure
```
GCS Raw Data:
gs://social-analytics-raw-data/
└── raw_snapshots/
    └── {year}/
        └── {month}/
            └── {day}/
                └── snapshot_{snapshot_id}.json

BigQuery Tables:
social_analytics.crawl_metadata
social_analytics.raw_data_crawl_snapshots
```

## 🔄 Background Processing

### Polling State Machine
```
STARTED → POLLING → READY → DOWNLOADING → COMPLETED
            ↓         ↓          ↓            ↓
         TIMEOUT   ERROR      ERROR        FAILED
```

### Polling Logic
```python
# Simplified background polling flow
while poll_count < max_polls:
    status = check_brightdata_status(snapshot_id)
    
    if status == "ready":
        data = download_data()
        store_in_gcs(data)
        publish_event("data-ingestion-completed")
        break
    
    elif status == "error":
        publish_event("crawl-failed")
        break
    
    sleep(30)  # Poll interval
    poll_count += 1

if poll_count >= max_polls:
    publish_event("crawl-failed", reason="timeout")
```

### Resource Management
- **Concurrent Tasks**: Up to 10 simultaneous background polls
- **Memory Usage**: ~50MB per active task
- **CPU Usage**: Minimal during polling, higher during download
- **Network**: Periodic API calls to BrightData

## ⚠️ Error Handling

### Error Categories

#### 1. BrightData API Errors
- **Connection Errors**: Retry with exponential backoff
- **Authentication Errors**: Log and fail immediately
- **Rate Limiting**: Respect retry-after headers
- **Server Errors**: Retry up to 3 times

#### 2. Storage Errors
- **GCS Upload Failures**: Retry with exponential backoff
- **BigQuery Insert Errors**: Log and continue (non-blocking)
- **Permission Errors**: Fail immediately with clear message

#### 3. Processing Errors
- **Invalid Data Format**: Log warning and skip
- **Timeout Errors**: Publish failure event
- **Memory Errors**: Fail task and alert

### Error Response Format
```json
{
  "status": "error",
  "message": "Detailed error description",
  "crawl_id": "uuid",
  "error_code": "BRIGHTDATA_TIMEOUT",
  "recovery_suggestion": "Retry crawl or check BrightData dashboard"
}
```

## 💾 Storage Systems

### 1. Google Cloud Storage (GCS)
**Purpose**: Store raw crawl data as source of truth

**Features**:
- UTF-8 encoded JSON storage
- Timestamp-based directory structure
- Retry logic with exponential backoff
- Content-type: `application/json; charset=utf-8`

**Storage Pattern**:
```
raw_snapshots/{year}/{month}/{day}/snapshot_{snapshot_id}.json
```

### 2. BigQuery
**Purpose**: Store metadata and tracking information

**Tables**:
1. **crawl_metadata**: Crawl job tracking
   - crawl_id, snapshot_id, platform, competitor
   - crawl_params (JSON), status, timestamps
   
2. **raw_data_crawl_snapshots**: Snapshot records
   - snapshot_id, crawl_id, file_path
   - platform, competitor, brand, category
   - ingestion_timestamp, status

### 3. Local Fallback Storage
**Purpose**: Testing and development fallback

**Implementation**: In-memory dictionary for metadata when BigQuery unavailable

## ⚙️ Configuration

### Environment Variables
```bash
# Required
BRIGHTDATA_API_KEY=your_api_key

# Optional with defaults
GOOGLE_CLOUD_PROJECT=social-analytics-prod
GCS_BUCKET_RAW_DATA=social-analytics-raw-data
BIGQUERY_DATASET=social_analytics
PUBSUB_TOPIC_PREFIX=social-analytics

# Background processing
BACKGROUND_POLLING_ENABLED=true
BACKGROUND_MAX_WORKERS=10
BACKGROUND_POLL_INTERVAL=30
BACKGROUND_MAX_POLLS=120
BACKGROUND_DOWNLOAD_TIMEOUT=300

# Server configuration
PORT=8080
```

### Feature Flags
- **Background Polling**: Enable/disable automatic polling
- **Event Publishing**: Control event emission
- **Retry Logic**: Configure retry attempts

## 📈 Monitoring & Observability

### Logging Strategy
```python
# Log levels and their usage
DEBUG: Individual poll attempts, detailed API responses
INFO: Task start/completion, state changes
WARNING: Retry attempts, validation failures
ERROR: Task failures, API errors
```

### Key Metrics
1. **Crawl Metrics**
   - Total crawls triggered
   - Success/failure rates
   - Average processing time
   - Data volume processed

2. **Background Task Metrics**
   - Active task count
   - Task completion rate
   - Average polling duration
   - Timeout occurrences

3. **API Metrics**
   - Request latency
   - Error rates by endpoint
   - BrightData API response times

### Health Indicators
- Service uptime
- Background task health
- Storage connectivity
- API authentication status

## 🔗 Integration Points

### 1. BrightData API
- **Authentication**: API key-based
- **Endpoints**: Trigger, status, download
- **Rate Limits**: Respect API quotas

### 2. Data Processing Service
- **Communication**: Via Pub/Sub events
- **Trigger**: data-ingestion-completed event
- **Data Transfer**: GCS path in event payload

### 3. Monitoring Service
- **Events**: All crawl lifecycle events
- **Metrics**: Processing statistics
- **Alerts**: Failure notifications

### 4. Excel Add-in / UI
- **Real-time Updates**: Via WebSocket (if implemented)
- **Status Polling**: REST API endpoints
- **Progress Tracking**: Background task status

## 🚀 Performance Characteristics

### Response Times
- **Trigger Endpoint**: 2-3 seconds (immediate response)
- **Status Check**: < 1 second
- **Manual Download**: 30-60 seconds (data size dependent)

### Throughput
- **Concurrent Crawls**: Up to 10 simultaneous
- **Processing Rate**: ~1000 posts/second download
- **Event Publishing**: < 100ms per event

### Scalability
- **Horizontal**: Cloud Run auto-scaling
- **Vertical**: Configurable worker pool size
- **Storage**: Unlimited GCS capacity
- **Database**: BigQuery handles large volumes

## 🔐 Security Considerations

### Authentication
- **Service-to-Service**: IAM-based authentication
- **External APIs**: Secure key storage in Secret Manager
- **Endpoints**: Can be configured for authentication

### Data Security
- **Encryption at Rest**: GCS and BigQuery encryption
- **Encryption in Transit**: HTTPS for all communications
- **Access Control**: Service account permissions

### Compliance
- **Data Retention**: Configurable per requirements
- **Audit Logging**: All operations logged
- **PII Handling**: No processing, just storage

## 🎯 Best Practices

### 1. Error Handling
- Always publish failure events for observability
- Include recovery suggestions in error messages
- Log sufficient context for debugging

### 2. Performance
- Use background processing for long operations
- Implement proper retry logic with backoff
- Monitor resource usage and scale accordingly

### 3. Reliability
- Validate data before storage
- Use idempotent operations where possible
- Implement circuit breakers for external APIs

### 4. Maintainability
- Keep handler logic separated by concern
- Use configuration over hardcoded values
- Document all event schemas

## 📚 Related Documentation
- [Background Processing Guide](./background-processing.md)
- [Deployment Results](./deployment-results.md)
- [BrightData Client Documentation](../brightdata/README.md)
- [Event API Design](../../../../EVENT_API_DESIGN.md)