#!/usr/bin/env python3
"""
Create the crawl_status_events table for tracking status changes.
"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery

def create_crawl_status_events_table():
    """Create the crawl_status_events table."""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize BigQuery client
    client = bigquery.Client()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'competitor-destroyer')
    dataset_id = os.getenv('BIGQUERY_DATASET', 'social_analytics')
    table_id = f"{project_id}.{dataset_id}.crawl_status_events"
    
    print("🔧 Creating crawl_status_events Table")
    print("=" * 60)
    
    try:
        # Check if table already exists
        try:
            table = client.get_table(table_id)
            print(f"✅ Table already exists: {table_id}")
            return
        except Exception:
            pass  # Table doesn't exist, create it
        
        # Define schema for status events
        schema = [
            bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("crawl_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        # Create table
        table = bigquery.Table(table_id, schema=schema)
        table.description = "Status events for crawl operations tracking"
        
        # Set partitioning on timestamp for better performance
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp"
        )
        
        # Set clustering on crawl_id for better query performance
        table.clustering_fields = ["crawl_id", "status"]
        
        table = client.create_table(table)
        
        print(f"✅ Created table: {table_id}")
        print(f"📋 Schema fields: {', '.join([field.name for field in schema])}")
        print(f"🗓️  Partitioned by: timestamp (daily)")
        print(f"🔗 Clustered by: crawl_id, status")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")


if __name__ == "__main__":
    create_crawl_status_events_table()