#!/usr/bin/env python3
"""
Create Pub/Sub subscriptions for testing event publishing.
This script creates subscriptions to verify events are actually being published.
"""

import os
from google.cloud import pubsub_v1

def create_subscriptions():
    """Create Pub/Sub subscriptions for all event topics."""
    
    # Initialize Pub/Sub client
    subscriber_client = pubsub_v1.SubscriberClient()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'social-competitor-prod')
    
    # Define topic-subscription mappings
    topic_subscriptions = {
        'crawl-triggered': 'crawl-triggered-test-sub',
        'data-ingestion-completed': 'data-ingestion-completed-test-sub', 
        'crawl-failed': 'crawl-failed-test-sub',
        'data-processing-completed': 'data-processing-completed-test-sub',
        'media-processing-requested': 'media-processing-requested-test-sub',
        'workflow-completed': 'workflow-completed-test-sub'
    }
    
    print("🚀 Creating Pub/Sub Subscriptions for Event Testing")
    print("=" * 60)
    
    created_count = 0
    existing_count = 0
    
    for topic_name, subscription_name in topic_subscriptions.items():
        topic_path = subscriber_client.topic_path(project_id, topic_name)
        subscription_path = subscriber_client.subscription_path(project_id, subscription_name)
        
        try:
            # Try to create the subscription
            subscription = subscriber_client.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 300,  # 5 minutes to process messages
                }
            )
            print(f"✅ Created subscription: {subscription_name}")
            print(f"   Topic: {topic_name}")
            print(f"   Path: {subscription_path}")
            created_count += 1
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Subscription already exists: {subscription_name}")
                existing_count += 1
            else:
                print(f"❌ Failed to create subscription {subscription_name}: {e}")
        
        print()
    
    print("📊 Subscription Creation Summary")
    print("=" * 40)
    print(f"✅ Created: {created_count}")
    print(f"ℹ️  Already existed: {existing_count}")
    print(f"📝 Total subscriptions: {len(topic_subscriptions)}")
    
    print("\n🔍 Next Steps:")
    print("1. Run test_event_publisher.py to publish events")
    print("2. Run test_subscription_receiver.py to verify events are received")
    print("3. Check GCP Console > Pub/Sub > Subscriptions for message counts")

if __name__ == "__main__":
    create_subscriptions()