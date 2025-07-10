from flask import Flask, request, jsonify
from handlers.crawl_handler import CrawlHandler
from events.event_publisher import EventPublisher
import os
import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
crawl_handler = CrawlHandler()
event_publisher = EventPublisher()

# Background processing configuration
BACKGROUND_CONFIG = {
    'max_workers': int(os.getenv('BACKGROUND_MAX_WORKERS', '10')),
    'poll_interval': int(os.getenv('BACKGROUND_POLL_INTERVAL', '30')),
    'max_polls': int(os.getenv('BACKGROUND_MAX_POLLS', '120')),  # 1 hour
    'download_timeout': int(os.getenv('BACKGROUND_DOWNLOAD_TIMEOUT', '300')),
    'enabled': os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
}

# Background task management
executor = ThreadPoolExecutor(
    max_workers=BACKGROUND_CONFIG['max_workers'], 
    thread_name_prefix="crawl-poller"
)
active_background_tasks = set()
task_lock = threading.Lock()

def background_poll_and_download(crawl_id: str):
    """
    Background task: Poll BrightData status and auto-download when ready.
    
    This function reuses existing crawl handler methods to:
    1. Poll BrightData status every 30 seconds
    2. Download data when ready
    3. Publish completion events
    4. Handle errors and timeouts
    """
    logger.info(f"Starting background polling for crawl {crawl_id}")
    
    # Track this task
    with task_lock:
        active_background_tasks.add(crawl_id)
    
    try:
        poll_count = 0
        max_polls = BACKGROUND_CONFIG['max_polls']
        poll_interval = BACKGROUND_CONFIG['poll_interval']
        
        while poll_count < max_polls:
            poll_count += 1
            
            try:
                # Reuse existing status checking logic
                crawl_metadata = crawl_handler._get_crawl_metadata(crawl_id)
                if not crawl_metadata:
                    logger.error(f"Crawl metadata not found for {crawl_id}")
                    event_publisher.publish_crawl_failed(
                        crawl_id, 
                        "Crawl metadata not found", 
                        "metadata_lookup"
                    )
                    break
                
                snapshot_id = crawl_metadata['snapshot_id']
                
                # Check BrightData status (reusing existing method)
                is_ready, error = crawl_handler.brightdata_client.poll_crawl_status(snapshot_id)
                
                if error:
                    logger.error(f"BrightData error for {crawl_id}: {error}")
                    # Don't fail immediately - might be temporary
                    if poll_count >= max_polls - 5:  # Only fail on last few attempts
                        event_publisher.publish_crawl_failed(
                            crawl_id,
                            f"BrightData polling error: {error}",
                            "brightdata_error"
                        )
                        break
                    # Continue polling on temporary errors
                    
                elif is_ready:
                    logger.info(f"Crawl {crawl_id} is ready for download (poll {poll_count}/{max_polls})")
                    
                    # Reuse existing download logic
                    download_result = crawl_handler.download_data(crawl_id)
                    
                    if download_result['status'] == 'success':
                        # Reuse existing event publishing logic
                        event_publisher.publish_data_ingestion_completed(
                            download_result['crawl_id'],
                            download_result['snapshot_id'],
                            download_result['gcs_path'],
                            download_result['post_count'],
                            download_result['media_count']
                        )
                        logger.info(f"Successfully completed background processing for {crawl_id}")
                    else:
                        logger.error(f"Download failed for {crawl_id}: {download_result.get('message')}")
                        event_publisher.publish_crawl_failed(
                            crawl_id,
                            download_result.get('message', 'Download failed'),
                            "download_failure"
                        )
                    break
                    
                else:
                    # Still processing - continue polling
                    logger.debug(f"Crawl {crawl_id} not ready yet, poll {poll_count}/{max_polls}")
                
            except Exception as poll_error:
                logger.error(f"Poll attempt {poll_count} failed for {crawl_id}: {str(poll_error)}")
                if poll_count >= max_polls - 3:  # Fail if last few attempts error
                    event_publisher.publish_crawl_failed(
                        crawl_id,
                        f"Polling error: {str(poll_error)}",
                        "polling_exception"
                    )
                    break
            
            # Wait before next poll (unless this was the last attempt)
            if poll_count < max_polls:
                time.sleep(poll_interval)
        
        # Handle timeout scenario
        if poll_count >= max_polls:
            timeout_minutes = (max_polls * poll_interval) // 60
            logger.warning(f"Polling timeout for crawl {crawl_id} after {timeout_minutes} minutes")
            event_publisher.publish_crawl_failed(
                crawl_id,
                f"Polling timeout after {timeout_minutes} minutes",
                "polling_timeout"
            )
            
    except Exception as e:
        logger.error(f"Background polling failed for {crawl_id}: {str(e)}")
        event_publisher.publish_crawl_failed(
            crawl_id,
            f"Background processing error: {str(e)}",
            "background_exception"
        )
        
    finally:
        # Remove from active tasks
        with task_lock:
            active_background_tasks.discard(crawl_id)
        logger.info(f"Background polling completed for {crawl_id}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check with background task status"""
    with task_lock:
        active_count = len(active_background_tasks)
    
    return jsonify({
        'status': 'healthy', 
        'service': 'data-ingestion',
        'background_tasks': {
            'active_count': active_count,
            'max_workers': BACKGROUND_CONFIG['max_workers'],
            'enabled': BACKGROUND_CONFIG['enabled']
        }
    })

@app.route('/api/v1/crawl/trigger', methods=['POST'])
def trigger_crawl():
    """Trigger new crawl with background polling - returns immediately"""
    try:
        crawl_params = request.json
        logger.info(f"Triggering crawl with params: {crawl_params}")
        
        # Trigger BrightData crawl
        result = crawl_handler.trigger_crawl(crawl_params)
        
        if result['status'] == 'success':
            # Publish crawl triggered event
            event_publisher.publish_crawl_triggered(
                result['crawl_id'],
                result['snapshot_id'],
                crawl_params
            )
            
            # Start background polling if enabled
            if BACKGROUND_CONFIG['enabled']:
                logger.info(f"Starting background polling for crawl {result['crawl_id']}")
                executor.submit(background_poll_and_download, result['crawl_id'])
                
                # Enhance response with background processing info
                result['background_processing'] = {
                    'enabled': True,
                    'status': 'started',
                    'poll_interval_seconds': BACKGROUND_CONFIG['poll_interval'],
                    'max_polling_time_minutes': (BACKGROUND_CONFIG['max_polls'] * BACKGROUND_CONFIG['poll_interval']) // 60,
                    'message': 'Background polling started - crawl will auto-download when ready'
                }
            else:
                result['background_processing'] = {
                    'enabled': False,
                    'message': 'Background polling disabled - use /download endpoint manually'
                }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error triggering crawl: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/crawl/<crawl_id>/download', methods=['POST'])
def download_crawl_data(crawl_id):
    """Download and store raw data"""
    try:
        logger.info(f"Downloading data for crawl_id: {crawl_id}")
        
        result = crawl_handler.download_data(crawl_id)
        
        if result['status'] == 'success':
            # Publish ingestion completed event
            event_publisher.publish_data_ingestion_completed(
                result['crawl_id'],
                result['snapshot_id'],
                result['gcs_path'],
                result['post_count'],
                result['media_count']
            )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error downloading crawl data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/crawl/<crawl_id>/status', methods=['GET'])
def get_crawl_status(crawl_id):
    """Get crawl status - READ ONLY, no events published"""
    try:
        logger.info(f"Checking status for crawl_id: {crawl_id}")
        
        # Get crawl metadata to find snapshot_id
        crawl_metadata = crawl_handler._get_crawl_metadata(crawl_id)
        if not crawl_metadata:
            logger.warning(f"Crawl metadata not found for: {crawl_id}")
            return jsonify({
                'error': 'Crawl not found',
                'crawl_id': crawl_id
            }), 404
            
        snapshot_id = crawl_metadata['snapshot_id']
        logger.info(f"Found snapshot_id: {snapshot_id} for crawl_id: {crawl_id}")
        
        # Check status with BrightData (read-only operation)
        is_ready, error = crawl_handler.brightdata_client.poll_crawl_status(snapshot_id)
        
        # Determine status based on BrightData response
        if error:
            status = 'error'
            ready_for_download = False
        elif is_ready:
            status = 'ready'
            ready_for_download = True
        else:
            status = 'processing'
            ready_for_download = False
        
        response = {
            'crawl_id': crawl_id,
            'snapshot_id': snapshot_id,
            'status': status,
            'ready_for_download': ready_for_download,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Include error message if there's an error
        if error:
            response['error_message'] = error
            
        # Include metadata for context
        response['metadata'] = {
            'platform': crawl_metadata.get('crawl_params', {}).get('platform'),
            'competitor': crawl_metadata.get('crawl_params', {}).get('competitor'),
            'created_at': crawl_metadata.get('created_at')
        }
        
        # Include background processing status
        with task_lock:
            is_background_active = crawl_id in active_background_tasks
        
        response['background_processing'] = {
            'enabled': BACKGROUND_CONFIG['enabled'],
            'active': is_background_active,
            'status': 'polling' if is_background_active else ('completed' if status == 'ready' else 'not_started'),
            'poll_interval_seconds': BACKGROUND_CONFIG['poll_interval'],
            'max_polling_time_minutes': (BACKGROUND_CONFIG['max_polls'] * BACKGROUND_CONFIG['poll_interval']) // 60
        }
        
        # Estimate completion time if still processing
        if is_background_active and status == 'processing':
            import datetime as dt
            created_at = crawl_metadata.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_time = dt.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_time = created_at
                    
                elapsed_minutes = (datetime.utcnow() - created_time.replace(tzinfo=None)).total_seconds() / 60
                estimated_total_minutes = 10  # Average BrightData processing time
                remaining_minutes = max(0, estimated_total_minutes - elapsed_minutes)
                
                response['background_processing']['estimated_completion'] = (
                    datetime.utcnow() + dt.timedelta(minutes=remaining_minutes)
                ).isoformat()
                response['background_processing']['elapsed_minutes'] = int(elapsed_minutes)
        
        logger.info(f"Status check result for {crawl_id}: {status}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting crawl status for {crawl_id}: {str(e)}")
        return jsonify({
            'error': f'Error checking crawl status: {str(e)}',
            'crawl_id': crawl_id
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)