from flask import Flask, request, jsonify
from handlers.crawl_handler import CrawlHandler
from platforms.registry import get_platform_handler
from platforms.base import APIProvider
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (for local development only)
# In Cloud Run, environment variables are set via cloudrun.yaml
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
crawl_handler = CrawlHandler()

# Background processing configuration
BACKGROUND_CONFIG = {
    'max_workers': int(os.getenv('BACKGROUND_MAX_WORKERS', '10')),
    'poll_interval': int(os.getenv('BACKGROUND_POLL_INTERVAL', '30')),
    'max_polls': int(os.getenv('BACKGROUND_MAX_POLLS', '120')),  # 1 hour
    'download_timeout': int(os.getenv('BACKGROUND_DOWNLOAD_TIMEOUT', '300')),
    'enabled': os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
}

# Note: Background processing is now handled entirely by CrawlHandler
# This eliminates duplicate polling and race conditions


@app.route('/health', methods=['GET'])
def health_check():
    """Health check with background task status"""
    try:
        crawl_handler_polling_enabled = os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
        
        # Test that we can access environment variables
        env_check = {
            'GOOGLE_CLOUD_PROJECT': bool(os.getenv('GOOGLE_CLOUD_PROJECT')),
            'GCS_BUCKET_RAW_DATA': bool(os.getenv('GCS_BUCKET_RAW_DATA')),
            'BRIGHTDATA_API_KEY': bool(os.getenv('BRIGHTDATA_API_KEY')),
            'APIFY_API_TOKEN': bool(os.getenv('APIFY_API_TOKEN'))
        }
        
        return jsonify({
            'status': 'healthy', 
            'service': 'data-ingestion',
            'environment_check': env_check,
            'background_processing': {
                'enabled': crawl_handler_polling_enabled,
                'handler': 'CrawlHandler',
                'poll_interval_seconds': int(os.getenv('BACKGROUND_POLL_INTERVAL', '30')),
                'max_workers': int(os.getenv('BACKGROUND_MAX_WORKERS', '10'))
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/v1/crawl/trigger', methods=['POST'])
def trigger_crawl():
    """Trigger new crawl with background polling - returns immediately"""
    try:
        crawl_params = request.json
        logger.info(f"Triggering crawl with params: {crawl_params}")
        
        # Trigger crawl (handle async method)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(crawl_handler.trigger_crawl(crawl_params))
        
        if result['status'] == 'success':
            # Publish crawl triggered event
            crawl_handler.event_publisher.publish_crawl_triggered(
                result['crawl_id'],
                result['snapshot_id'],
                crawl_params
            )
            
            # Background polling is handled by CrawlHandler
            # Check if CrawlHandler background polling is enabled
            crawl_handler_polling_enabled = os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
            
            if crawl_handler_polling_enabled:
                result['background_processing'] = {
                    'enabled': True,
                    'status': 'started',
                    'poll_interval_seconds': int(os.getenv('BACKGROUND_POLL_INTERVAL', '30')),
                    'max_polling_time_minutes': (int(os.getenv('BACKGROUND_MAX_POLLS', '120')) * int(os.getenv('BACKGROUND_POLL_INTERVAL', '30'))) // 60,
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
        
        # Handle async download method
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(crawl_handler.download_data(crawl_id))
        
        if result['status'] == 'success':
            # Publish ingestion completed event
            crawl_handler.event_publisher.publish_data_ingestion_completed(
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
        
        # Get platform to use correct API client
        platform = crawl_metadata.get('crawl_params', {}).get('platform', 'facebook')
        platform_handler = get_platform_handler(platform)
        
        # Check status with appropriate API client
        if platform_handler and platform_handler.config.api_provider == APIProvider.BRIGHTDATA:
            # Handle async check_status
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status_result = loop.run_until_complete(crawl_handler.brightdata_client.check_status(snapshot_id))
            is_ready = status_result.get('is_ready', False)
            error = status_result.get('error')
        elif platform_handler:  # Apify
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status_result = loop.run_until_complete(crawl_handler.apify_client.check_status(snapshot_id))
            is_ready = status_result.get('is_ready', False)
            error = status_result.get('error')
        else:
            is_ready = False
            error = f"Unknown platform: {platform}"
        
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
        crawl_handler_polling_enabled = os.getenv('BACKGROUND_POLLING_ENABLED', 'true').lower() == 'true'
        
        response['background_processing'] = {
            'enabled': crawl_handler_polling_enabled,
            'handler': 'CrawlHandler',
            'status': 'handled_by_crawl_handler',
            'poll_interval_seconds': int(os.getenv('BACKGROUND_POLL_INTERVAL', '30')),
            'max_polling_time_minutes': (int(os.getenv('BACKGROUND_MAX_POLLS', '120')) * int(os.getenv('BACKGROUND_POLL_INTERVAL', '30'))) // 60
        }
        
        # Estimate completion time if still processing
        if crawl_handler_polling_enabled and status == 'processing':
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