"""
Event publisher for Data Ingestion Service.

This module handles publishing events to Google Cloud Pub/Sub
for microservices communication.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publisher for sending events to other microservices via Pub/Sub.
    
    This class handles event publishing for the Data Ingestion Service,
    allowing other services to react to ingestion events.
    """
    
    def __init__(self):
        """Initialize the event publisher."""
        self.publisher = pubsub_v1.PublisherClient()
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'competitor-destroyer')
        self.topic_prefix = os.getenv('PUBSUB_TOPIC_PREFIX', 'social-analytics')
    
    def publish(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Publish an event to the appropriate Pub/Sub topic.
        
        Args:
            event_type (str): Type of event (e.g., 'crawl-triggered', 'data-ingestion-completed')
            event_data (Dict[str, Any]): Event payload data
        
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Construct topic name
            topic_name = f"{self.topic_prefix}-{event_type}"
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            # Prepare event message
            message = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'data-ingestion-service',
                'data': event_data
            }
            
            # Convert to JSON bytes
            message_data = json.dumps(message).encode('utf-8')
            
            logger.info(f"Publishing event: {event_type} to {topic_name}")
            
            # Publish the message
            future = self.publisher.publish(topic_path, message_data)
            message_id = future.result()  # Wait for publish to complete
            
            logger.info(f"Event published successfully: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event_type}: {str(e)}")
            return False
    
    def publish_crawl_triggered(self, crawl_id: str, snapshot_id: str, crawl_params: Dict[str, Any]) -> bool:
        """
        Publish a crawl triggered event.
        
        Args:
            crawl_id (str): The crawl ID
            snapshot_id (str): The BrightData snapshot ID
            crawl_params (Dict[str, Any]): Original crawl parameters
        
        Returns:
            bool: True if published successfully
        """
        event_data = {
            'crawl_id': crawl_id,
            'snapshot_id': snapshot_id,
            'platform': crawl_params.get('platform'),
            'competitor': crawl_params.get('competitor'),
            'brand': crawl_params.get('brand'),
            'category': crawl_params.get('category'),
            'status': 'triggered'
        }
        
        return self.publish('crawl-triggered', event_data)
    
    def publish_data_ingestion_completed(self, crawl_id: str, snapshot_id: str, gcs_path: str, 
                                       post_count: int, media_count: int, crawl_metadata: Dict[str, Any] = None) -> bool:
        """
        Publish a data ingestion completed event.
        
        Args:
            crawl_id (str): The crawl ID
            snapshot_id (str): The BrightData snapshot ID
            gcs_path (str): Path to the stored raw data in GCS
            post_count (int): Number of posts processed
            media_count (int): Number of media files found
            crawl_metadata (Dict[str, Any], optional): Original crawl metadata with platform, competitor, etc.
        
        Returns:
            bool: True if published successfully
        """
        event_data = {
            'crawl_id': crawl_id,
            'snapshot_id': snapshot_id,
            'gcs_path': gcs_path,
            'platform': None,
            'competitor': None,
            'brand': None,
            'category': None,
            'crawl_metadata': {
                'dataset_id': None,
                'num_posts': post_count,
                'crawl_date': datetime.utcnow().isoformat()
            }
        }
        
        # Include metadata fields that data-processing service expects
        if crawl_metadata and 'crawl_params' in crawl_metadata:
            params = crawl_metadata['crawl_params']
            event_data.update({
                'platform': params.get('platform'),
                'competitor': params.get('competitor'),
                'brand': params.get('brand'),
                'category': params.get('category')
            })
            
            # Update crawl_metadata with available information
            event_data['crawl_metadata'].update({
                'dataset_id': params.get('dataset_id'),
                'num_posts': post_count,
                'crawl_date': crawl_metadata.get('crawl_date', datetime.utcnow().isoformat())
            })
        
        return self.publish('data-ingestion-completed', event_data)
    
    def publish_crawl_failed(self, crawl_id: str, error_message: str, stage: str = None) -> bool:
        """
        Publish a crawl failed event.
        
        Args:
            crawl_id (str): The crawl ID
            error_message (str): Description of the failure
            stage (str, optional): Stage where failure occurred (e.g., 'polling', 'download')
        
        Returns:
            bool: True if published successfully
        """
        event_data = {
            'crawl_id': crawl_id,
            'error_message': error_message,
            'status': 'failed'
        }
        
        if stage:
            event_data['stage'] = stage
        
        return self.publish('crawl-failed', event_data)