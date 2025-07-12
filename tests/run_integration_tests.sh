#!/bin/bash
# Run integration tests for Apify API client

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${1}${2}${NC}"
}

print_status "$YELLOW" "======================================"
print_status "$YELLOW" "Social Analytics Integration Tests Runner"
print_status "$YELLOW" "======================================"

# Check for required environment variables
MISSING_VARS=""

# Check Apify token
if [ -z "$APIFY_TOKEN" ] && [ -z "$APIFY_TEST_TOKEN" ]; then
    MISSING_VARS="$MISSING_VARS APIFY_TOKEN/APIFY_TEST_TOKEN"
fi

# Check BrightData token  
if [ -z "$BRIGHTDATA_API_KEY" ] && [ -z "$BRIGHTDATA_TEST_API_KEY" ]; then
    MISSING_VARS="$MISSING_VARS BRIGHTDATA_API_KEY/BRIGHTDATA_TEST_API_KEY"
fi

# Warn about missing variables but allow partial testing
if [ -n "$MISSING_VARS" ]; then
    print_status "$YELLOW" "⚠️  WARNING: Missing environment variables:$MISSING_VARS"
    echo "Some tests will be skipped. To run all tests, set:"
    if [[ "$MISSING_VARS" == *"APIFY"* ]]; then
        echo "  export APIFY_TOKEN='your-apify-token-here'"
    fi
    if [[ "$MISSING_VARS" == *"BRIGHTDATA"* ]]; then
        echo "  export BRIGHTDATA_API_KEY='your-brightdata-key-here'"
    fi
    echo ""
fi

# Navigate to the service directory
cd "$(dirname "$0")/.." || exit 1

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    print_status "$GREEN" "✓ Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if needed
if ! python3 -m pytest --version > /dev/null 2>&1; then
    print_status "$YELLOW" "Installing pytest and dependencies..."
    pip install pytest pytest-asyncio pytest-cov pytest-flaky
fi

# Default test command - run both Apify and BrightData tests
TEST_CMD="python3 -m pytest tests/integration/ -v"

# Parse command line arguments
case "$1" in
    "all")
        print_status "$GREEN" "Running ALL integration tests (including expensive ones)..."
        TEST_CMD="$TEST_CMD -m integration"
        ;;
    "cheap")
        print_status "$GREEN" "Running only non-expensive integration tests..."
        TEST_CMD="$TEST_CMD -m 'integration and not expensive'"
        ;;
    "quick")
        print_status "$GREEN" "Running quick connectivity tests only..."
        TEST_CMD="$TEST_CMD -m 'integration and not expensive and not slow' -k 'connectivity or error_handling'"
        ;;
    "single")
        if [ -z "$2" ]; then
            print_status "$RED" "❌ ERROR: Please specify test name"
            echo "Usage: $0 single <test_name>"
            exit 1
        fi
        print_status "$GREEN" "Running single test: $2"
        TEST_CMD="$TEST_CMD -k '$2'"
        ;;
    "coverage")
        print_status "$GREEN" "Running tests with coverage report..."
        TEST_CMD="$TEST_CMD -m integration --cov=api_clients --cov-report=html --cov-report=term"
        ;;
    "youtube")
        print_status "$GREEN" "Running YouTube-specific integration tests..."
        TEST_CMD="$TEST_CMD -m integration -k youtube"
        ;;
    "tiktok")
        print_status "$GREEN" "Running TikTok-specific integration tests..."
        TEST_CMD="$TEST_CMD -m integration -k tiktok"
        ;;
    "facebook")
        print_status "$GREEN" "Running Facebook-specific integration tests..."
        TEST_CMD="$TEST_CMD -m integration -k facebook"
        ;;
    "brightdata")
        print_status "$GREEN" "Running BrightData integration tests..."
        TEST_CMD="$TEST_CMD tests/integration/test_brightdata_integration.py -m integration"
        ;;
    "apify")
        print_status "$GREEN" "Running Apify integration tests..."
        TEST_CMD="$TEST_CMD tests/integration/test_apify_integration.py -m integration"
        ;;
    "structure")
        print_status "$GREEN" "Running data structure validation tests..."
        TEST_CMD="$TEST_CMD -m integration -k 'data_structure or structure'"
        ;;
    "")
        print_status "$GREEN" "Running default integration tests (non-expensive)..."
        TEST_CMD="$TEST_CMD -m 'integration and not expensive'"
        ;;
    *)
        print_status "$YELLOW" "Usage: $0 [all|cheap|quick|single <test_name>|coverage|youtube|tiktok|facebook|brightdata|apify|structure]"
        echo ""
        echo "Options:"
        echo "  all       - Run all integration tests (including expensive ones)"
        echo "  cheap     - Run only non-expensive tests (default)"
        echo "  quick     - Run only quick connectivity tests"
        echo "  single    - Run a single test by name"
        echo "  coverage  - Run with coverage report"
        echo "  youtube   - Run only YouTube-specific tests"
        echo "  tiktok    - Run only TikTok-specific tests" 
        echo "  facebook  - Run only Facebook-specific tests"
        echo "  brightdata- Run only BrightData integration tests"
        echo "  apify     - Run only Apify integration tests"
        echo "  structure - Run only data structure validation tests"
        exit 0
        ;;
esac

# Show token status (masked)
if [ -n "$APIFY_TEST_TOKEN" ]; then
    MASKED_TOKEN="${APIFY_TEST_TOKEN:0:8}...${APIFY_TEST_TOKEN: -4}"
    print_status "$GREEN" "✓ Using APIFY_TEST_TOKEN: $MASKED_TOKEN"
elif [ -n "$APIFY_TOKEN" ]; then
    MASKED_TOKEN="${APIFY_TOKEN:0:8}...${APIFY_TOKEN: -4}"
    print_status "$GREEN" "✓ Using APIFY_TOKEN: $MASKED_TOKEN"
fi

if [ -n "$BRIGHTDATA_TEST_API_KEY" ]; then
    MASKED_KEY="${BRIGHTDATA_TEST_API_KEY:0:8}...${BRIGHTDATA_TEST_API_KEY: -4}"
    print_status "$GREEN" "✓ Using BRIGHTDATA_TEST_API_KEY: $MASKED_KEY"
elif [ -n "$BRIGHTDATA_API_KEY" ]; then
    MASKED_KEY="${BRIGHTDATA_API_KEY:0:8}...${BRIGHTDATA_API_KEY: -4}"
    print_status "$GREEN" "✓ Using BRIGHTDATA_API_KEY: $MASKED_KEY"
fi

print_status "$YELLOW" "======================================"
print_status "$YELLOW" "Starting tests..."
print_status "$YELLOW" "======================================"

# Run the tests
$TEST_CMD

# Capture exit code
EXIT_CODE=$?

# Print summary
print_status "$YELLOW" "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    print_status "$GREEN" "✅ Tests completed successfully!"
else
    print_status "$RED" "❌ Tests failed with exit code: $EXIT_CODE"
fi
print_status "$YELLOW" "======================================"

# Show coverage report location if coverage was run
if [[ "$1" == "coverage" ]] && [ $EXIT_CODE -eq 0 ]; then
    print_status "$GREEN" "📊 Coverage report generated:"
    echo "   HTML report: htmlcov/index.html"
    echo "   Open with: open htmlcov/index.html"
fi

exit $EXIT_CODE