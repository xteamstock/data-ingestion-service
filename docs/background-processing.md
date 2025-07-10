# Background Processing Guide - Data Ingestion Service

## 🎯 **Overview**

The Data Ingestion Service implements **background polling and automatic download** to provide immediate user responses while processing crawls asynchronously.

### **User Experience Flow**
```
User → POST /api/v1/crawl/trigger → ✅ Immediate response (2-3 seconds)
Background → Polls BrightData status every 30 seconds
Background → Auto-downloads when ready → Publishes events
Data Processing → Auto-consumes events → Processes data automatically
```

---

## 🏗️ **Architecture**

### **Background Processing Components**

```python
# Background polling workflow
User Request → trigger_crawl() → Immediate Response
             ↓
Background Thread → poll_status() → download_data() → publish_events()
                 ↓
Event-Driven Pipeline → Data Processing → Media Processing
```

### **Core Methods Reused**

The background polling leverages existing crawl handler methods:

| Method | Purpose | Reused In Background |
|--------|---------|---------------------|
| `_get_crawl_metadata()` | Get crawl info from BigQuery | ✅ Status checking |
| `brightdata_client.poll_crawl_status()` | Check BrightData readiness | ✅ Polling loop |
| `download_data()` | Download and store data | ✅ Auto-download |
| `EventPublisher.publish()` | Publish completion events | ✅ Event publishing |

---

## 📋 **Background Polling Logic**

### **Polling Parameters**
- **Poll Interval**: 30 seconds
- **Maximum Polls**: 120 (1 hour total timeout)
- **Concurrent Tasks**: Up to 10 background polling tasks
- **Error Retry**: Automatic retry with exponential backoff

### **Polling States**

```python
# Background polling state machine
POLLING_STATES = {
    'STARTED': 'Background polling initiated',
    'POLLING': 'Checking BrightData status',
    'READY': 'Data ready for download',
    'DOWNLOADING': 'Downloading data from BrightData',
    'COMPLETED': 'Data downloaded and events published',
    'FAILED': 'Polling or download failed',
    'TIMEOUT': 'Maximum polling time exceeded'
}
```

### **Event Publishing**

Background processing publishes events at key stages:

```python
# Events published by background processing
events = {
    'crawl.triggered': {
        'when': 'Immediately after successful crawl trigger',
        'data': ['crawl_id', 'snapshot_id', 'platform', 'competitor']
    },
    'data.ingestion.completed': {
        'when': 'After successful download and storage',
        'data': ['crawl_id', 'gcs_path', 'post_count', 'media_count']
    },
    'crawl.failed': {
        'when': 'On polling timeout, download failure, or errors',
        'data': ['crawl_id', 'error', 'stage']
    }
}
```

---

## 🔧 **Implementation Details**

### **Background Task Management**

```python
# Concurrent task execution
from concurrent.futures import ThreadPoolExecutor
import threading

# Global executor for background tasks
executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="crawl-poller")

# Track active background tasks
active_background_tasks = set()
task_lock = threading.Lock()
```

### **Error Handling Strategy**

```python
# Comprehensive error handling
error_scenarios = {
    'metadata_not_found': 'Crawl metadata missing from BigQuery',
    'brightdata_error': 'BrightData API error or timeout',
    'download_failure': 'Data download from BrightData failed',
    'storage_error': 'GCS upload or BigQuery insert failed',
    'polling_timeout': 'Maximum polling time (1 hour) exceeded',
    'background_exception': 'Unexpected error in background thread'
}

# Each error publishes specific failure event with recovery context
```

### **Timeout and Resource Management**

```python
# Resource management configuration
BACKGROUND_CONFIG = {
    'max_concurrent_polls': 10,
    'poll_interval_seconds': 30,
    'max_poll_attempts': 120,  # 1 hour total
    'timeout_per_download': 300,  # 5 minutes per download
    'retry_failed_polls': 3,
    'cleanup_completed_tasks': True
}
```

---

## 📊 **Monitoring and Observability**

### **Background Task Status**

The `/status` endpoint provides background processing information:

```json
{
  "crawl_id": "uuid",
  "brightdata_status": "processing",
  "ready_for_download": false,
  "background_processing": {
    "polling_active": true,
    "poll_count": 15,
    "estimated_completion": "2025-07-09T15:30:00Z",
    "last_poll_time": "2025-07-09T15:00:00Z",
    "time_elapsed": "7m30s"
  },
  "pipeline_status": "waiting_for_brightdata"
}
```

### **Logging Strategy**

```python
# Structured logging for background tasks
log_levels = {
    'DEBUG': 'Individual poll attempts and status checks',
    'INFO': 'Background task start/completion and state changes',
    'WARNING': 'Retry attempts and recoverable errors',
    'ERROR': 'Task failures and timeout scenarios'
}

# Log format includes crawl_id for easy tracking
logger.info(f"Background polling started for crawl {crawl_id}")
logger.debug(f"Poll {poll_count}/120 for crawl {crawl_id}: not ready")
logger.error(f"Background polling failed for {crawl_id}: {error}")
```

---

## 🚀 **API Usage Examples**

### **Immediate Response Flow**

```bash
# 1. Trigger crawl (immediate response)
curl -X POST "https://data-ingestion-service/api/v1/crawl/trigger" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "gd_lkaxegm826bjpoo9m5",
    "platform": "facebook",
    "competitor": "nutifood",
    "url": "https://www.facebook.com/competitor"
  }'

# Response (immediate - 2-3 seconds):
{
  "status": "success",
  "crawl_id": "uuid-123",
  "snapshot_id": "s_abc123",
  "message": "Crawl triggered successfully",
  "background_processing": "started",
  "timestamp": "2025-07-09T14:00:00Z"
}
```

### **Status Monitoring**

```bash
# 2. Check status (optional - user can poll or wait for events)
curl -X GET "https://data-ingestion-service/api/v1/crawl/uuid-123/status" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# Response shows background processing progress:
{
  "crawl_id": "uuid-123",
  "brightdata_status": "processing", 
  "background_processing": {
    "polling_active": true,
    "poll_count": 8,
    "estimated_completion": "2025-07-09T14:15:00Z"
  }
}
```

### **Event-Driven Integration**

```python
# 3. Downstream services automatically consume events
@subscribe('data.ingestion.completed')
def auto_process_data(event):
    """Automatically triggered when background download completes"""
    crawl_id = event['crawl_id']
    gcs_path = event['gcs_path']
    
    # Process data immediately
    process_crawl_data(crawl_id, gcs_path)
```

---

## ⚠️ **Error Scenarios and Recovery**

### **Common Error Cases**

#### **1. BrightData Processing Timeout**
```json
{
  "event": "crawl.failed",
  "data": {
    "crawl_id": "uuid-123",
    "error": "Polling timeout after 1 hour",
    "stage": "polling_timeout",
    "recovery": "Check BrightData dashboard or retry crawl"
  }
}
```

#### **2. Download Failure**
```json
{
  "event": "crawl.failed", 
  "data": {
    "crawl_id": "uuid-123",
    "error": "Failed to download data: 500 Internal Server Error",
    "stage": "download",
    "recovery": "Use manual download endpoint when BrightData recovers"
  }
}
```

#### **3. Storage Error**
```json
{
  "event": "crawl.failed",
  "data": {
    "crawl_id": "uuid-123", 
    "error": "GCS upload failed: insufficient permissions",
    "stage": "storage",
    "recovery": "Check service account permissions"
  }
}
```

### **Manual Recovery Options**

```bash
# If background processing fails, manual triggers are available:

# 1. Check current status
curl -X GET "/api/v1/crawl/{crawl_id}/status"

# 2. Manual download (if BrightData is ready)
curl -X POST "/api/v1/crawl/{crawl_id}/download"

# 3. Restart background processing (if supported)
curl -X POST "/api/v1/crawl/{crawl_id}/retry-background"
```

---

## 📈 **Performance Characteristics**

### **Response Times**
- **Trigger endpoint**: 2-3 seconds (immediate response)
- **Background polling**: 30 seconds between status checks
- **Download when ready**: 30-60 seconds depending on data size
- **Total pipeline**: 5-15 minutes for typical crawls

### **Resource Usage**
- **Memory**: ~50MB per active background task
- **CPU**: Minimal during polling, higher during download
- **Network**: Periodic API calls to BrightData
- **Concurrency**: Up to 10 simultaneous background crawls

### **Scaling Considerations**
- Background tasks scale with crawl volume
- ThreadPoolExecutor manages resource allocation
- Cloud Run auto-scaling handles traffic spikes
- BigQuery handles metadata queries efficiently

---

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Background processing configuration
BACKGROUND_POLLING_ENABLED=true
BACKGROUND_MAX_WORKERS=10
BACKGROUND_POLL_INTERVAL=30
BACKGROUND_MAX_POLLS=120
BACKGROUND_DOWNLOAD_TIMEOUT=300

# Monitoring and logging
BACKGROUND_LOG_LEVEL=INFO
BACKGROUND_METRICS_ENABLED=true
BACKGROUND_CLEANUP_INTERVAL=3600
```

### **Feature Flags**

```python
# Feature flags for gradual rollout
FEATURE_FLAGS = {
    'background_polling': True,
    'immediate_response': True,
    'background_retry': True,
    'background_metrics': True,
    'background_cleanup': True
}
```

This background processing enhancement provides immediate user responses while maintaining the complete event-driven pipeline for downstream services.