#!/bin/bash

# Test script for Data Ingestion Service
# Supports both local development and Cloud Run deployment

set -e

# Configuration
LOCAL_URL="http://localhost:8080"
CLOUD_RUN_URL="https://data-ingestion-service-ud5pi5bwfq-as.a.run.app"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Function to detect environment and set up authentication
setup_environment() {
    if [ "$1" = "--cloud" ] || [ "$1" = "-c" ]; then
        info "Testing Cloud Run deployment..."
        SERVICE_URL="$CLOUD_RUN_URL"
        
        # Get access token for Cloud Run authentication
        ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)
        if [ -z "$ACCESS_TOKEN" ]; then
            error "Failed to get access token. Please run 'gcloud auth login' first"
            exit 1
        fi
        
        AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
        info "Using Cloud Run URL: $SERVICE_URL"
    else
        info "Testing local development server..."
        SERVICE_URL="$LOCAL_URL"
        AUTH_HEADER=""
        info "Using local URL: $SERVICE_URL"
        
        # Check if local service is running
        if ! curl -s --connect-timeout 2 "$SERVICE_URL/health" > /dev/null 2>&1; then
            warn "Local service doesn't seem to be running at $SERVICE_URL"
            echo "Start it with: python app.py"
            echo "Or test Cloud Run with: $0 --cloud"
            exit 1
        fi
    fi
}

# Function to make authenticated curl request
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local extra_headers="$4"
    
    # Build curl command with proper authentication
    if [ ! -z "$AUTH_HEADER" ]; then
        if [ "$method" = "POST" ] && [ ! -z "$data" ]; then
            curl -s -w "%{http_code}" \
                -X POST \
                -H "$AUTH_HEADER" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$SERVICE_URL$endpoint"
        elif [ "$method" = "POST" ]; then
            curl -s -w "%{http_code}" \
                -X POST \
                -H "$AUTH_HEADER" \
                -H "Content-Type: application/json" \
                "$SERVICE_URL$endpoint"
        else
            curl -s -w "%{http_code}" \
                -H "$AUTH_HEADER" \
                -H "Content-Type: application/json" \
                "$SERVICE_URL$endpoint"
        fi
    else
        # Local development - no auth needed
        if [ "$method" = "POST" ] && [ ! -z "$data" ]; then
            curl -s -w "%{http_code}" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$SERVICE_URL$endpoint"
        elif [ "$method" = "POST" ]; then
            curl -s -w "%{http_code}" \
                -X POST \
                -H "Content-Type: application/json" \
                "$SERVICE_URL$endpoint"
        else
            curl -s -w "%{http_code}" \
                -H "Content-Type: application/json" \
                "$SERVICE_URL$endpoint"
        fi
    fi
}

# Test 1: Health Check
test_health_check() {
    log "Testing health check endpoint..."
    
    response=$(make_request "GET" "/health")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        log "✅ Health check passed"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        error "❌ Health check failed with status $http_code"
        echo "Response: $body"
    fi
    echo ""
}

# Test 2: Trigger Crawl
test_trigger_crawl() {
    log "Testing crawl trigger endpoint..."
    
    local crawl_data='{
        "dataset_id": "gd_lkaxegm826bjpoo9m5",
        "platform": "facebook", 
        "competitor": "nutifood",
        "brand": "growplus-nutifood",
        "category": "sua-bot-tre-em",
        "url": "https://www.facebook.com/GrowPLUScuaNutiFood/?locale=vi_VN",
        "start_date": "2024-12-24",
        "end_date": "2024-12-24",
        "include_profile_data": true
    }'
    
    response=$(make_request "POST" "/api/v1/crawl/trigger" "$crawl_data")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        log "✅ Crawl trigger test passed"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        
        # Extract crawl_id for next test
        CRAWL_ID=$(echo "$body" | grep -o '"crawl_id":"[^"]*"' | cut -d'"' -f4)
        if [ ! -z "$CRAWL_ID" ]; then
            info "Extracted crawl_id: $CRAWL_ID"
        fi
    else
        error "❌ Crawl trigger test failed with status $http_code"
        echo "Response: $body"
    fi
    echo ""
}

# Test 3: Download Data (requires crawl_id from previous test)
test_download_data() {
    if [ -z "$CRAWL_ID" ]; then
        warn "⚠️ Skipping download test - no crawl_id available from trigger test"
        return
    fi
    
    log "Testing download endpoint for crawl_id: $CRAWL_ID"
    warn "Note: This will likely fail until the BrightData crawl is complete (usually 2-3 minutes)"
    
    response=$(make_request "POST" "/api/v1/crawl/$CRAWL_ID/download")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        log "✅ Download test passed"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        warn "⚠️ Download test returned status $http_code (expected if crawl not ready)"
        echo "Response: $body"
    fi
    echo ""
}

# Test 4: Invalid endpoint
test_invalid_endpoint() {
    log "Testing invalid endpoint..."
    
    response=$(make_request "GET" "/invalid-endpoint")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "404" ]; then
        log "✅ Invalid endpoint test passed (correctly returned 404)"
    else
        warn "⚠️ Invalid endpoint returned unexpected status $http_code"
    fi
    echo "Response: $body"
    echo ""
}

# Test 5: Authentication test (for Cloud Run only)
test_authentication() {
    if [ -z "$AUTH_HEADER" ]; then
        info "Skipping authentication test (local development mode)"
        return
    fi
    
    log "Testing unauthenticated request (should fail on Cloud Run)..."
    
    response=$(curl -s -w "%{http_code}" \
        -H "Content-Type: application/json" \
        "$SERVICE_URL/health")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "403" ] || [ "$http_code" = "401" ]; then
        log "✅ Authentication test passed (correctly blocked unauthenticated request)"
    else
        error "❌ Unauthenticated request should have been blocked but got status $http_code"
    fi
    echo "Response: $body"
    echo ""
}

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --cloud, -c    Test Cloud Run deployment (requires gcloud auth)"
    echo "  --local, -l    Test local development server (default)"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Test local server"
    echo "  $0 --local       # Test local server"
    echo "  $0 --cloud       # Test Cloud Run deployment"
}

# Main execution
main() {
    echo "🧪 Testing Data Ingestion Service"
    echo "=================================================="
    
    # Parse command line arguments
    case "${1:-}" in
        --cloud|-c)
            setup_environment "--cloud"
            ;;
        --local|-l)
            setup_environment "--local"
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        "")
            setup_environment "--local"
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    
    # Run all tests
    test_health_check
    test_trigger_crawl
    test_download_data
    test_invalid_endpoint
    test_authentication
    
    log "All tests completed!"
    
    # Provide helpful information
    if [ ! -z "$CRAWL_ID" ]; then
        echo ""
        warn "💡 To test the download endpoint later when the crawl is ready:"
        if [ ! -z "$AUTH_HEADER" ]; then
            echo "curl -H \"Authorization: Bearer \$(gcloud auth print-access-token)\" \\"
        else
            echo "curl \\"
        fi
        echo "     -X POST \\"
        echo "     -H \"Content-Type: application/json\" \\"
        echo "     \"$SERVICE_URL/api/v1/crawl/$CRAWL_ID/download\""
    fi
    
    if [ ! -z "$AUTH_HEADER" ]; then
        echo ""
        info "Cloud Run service is private - authentication is working correctly!"
    fi
}

# Check if gcloud is available for Cloud Run tests
if [ "$1" = "--cloud" ] || [ "$1" = "-c" ]; then
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed or not in PATH"
        error "Install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
fi

# Run the main function
main "$@"