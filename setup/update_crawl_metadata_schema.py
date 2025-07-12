#!/usr/bin/env python3
"""
Update the crawl_metadata table schema to add the error_message column.
"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery

def update_crawl_metadata_table():
    """Add error_message column to crawl_metadata table if it doesn't exist."""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize BigQuery client
    client = bigquery.Client()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'competitor-destroyer')
    dataset_id = os.getenv('BIGQUERY_DATASET', 'social_analytics')
    table_id = f"{project_id}.{dataset_id}.crawl_metadata"
    
    print("🔧 Updating crawl_metadata Table Schema")
    print("=" * 60)
    
    try:
        # Get current table schema
        table = client.get_table(table_id)
        current_fields = [field.name for field in table.schema]
        
        print(f"✅ Found table: {table_id}")
        print(f"📋 Current fields: {', '.join(current_fields)}")
        
        # Check if error_message column exists
        if 'error_message' in current_fields:
            print("✅ error_message column already exists")
            return
        
        # Add error_message column
        print("\n🔨 Adding error_message column...")
        
        # Create new schema with error_message field
        new_schema = list(table.schema)
        new_schema.append(bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"))
        
        # Update table schema
        table.schema = new_schema
        table = client.update_table(table, ["schema"])
        
        print("✅ Successfully added error_message column")
        
        # Verify the update
        updated_table = client.get_table(table_id)
        updated_fields = [field.name for field in updated_table.schema]
        print(f"\n📋 Updated fields: {', '.join(updated_fields)}")
        
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"❌ Table {table_id} not found. Creating it...")
            create_crawl_metadata_table(client, project_id, dataset_id)
        else:
            print(f"❌ Error updating table: {e}")


def create_crawl_metadata_table(client, project_id, dataset_id):
    """Create the crawl_metadata table with proper schema."""
    
    table_id = f"{project_id}.{dataset_id}.crawl_metadata"
    
    # Define schema
    schema = [
        bigquery.SchemaField("crawl_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("snapshot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("platform", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("competitor", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("brand", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("category", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("crawl_params", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
    ]
    
    # Create table
    table = bigquery.Table(table_id, schema=schema)
    table = client.create_table(table)
    
    print(f"✅ Created table {table_id}")
    print(f"📋 Fields: {', '.join([field.name for field in schema])}")


if __name__ == "__main__":
    update_crawl_metadata_table()