#!/bin/bash

# Simple run script that uses .env file
echo "🚀 Starting Data Ingestion Service (using .env file)..."

# Just activate venv and run - .env file will be loaded automatically
source venv/bin/activate
python3 app.py