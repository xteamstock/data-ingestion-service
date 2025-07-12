# 🎯 TDD Implementation Guide for Multi-Platform Support

## 📚 Understanding Test-Driven Development (TDD)

### What is TDD?
TDD is a software development approach where you write tests **BEFORE** writing the actual code. It follows a simple cycle:

1. **🔴 RED**: Write a failing test
2. **🟢 GREEN**: Write minimal code to pass the test
3. **🔵 REFACTOR**: Improve code while keeping tests green

### Why Use TDD?
- **Better Design**: Forces you to think about the interface first
- **Documentation**: Tests serve as living documentation
- **Confidence**: High test coverage from the start
- **Safety**: Refactor without fear of breaking things
- **Focus**: Write only the code you need

## 🚀 Let's Implement Multi-Platform Support with TDD

### Step 1: Set Up Testing Environment

```bash
# Navigate to data-ingestion service
cd /Users/tranquocbao/crawlerX/social-analytics-platform/services/data-ingestion

# Create test directories if they don't exist
mkdir -p tests/unit tests/integration tests/e2e

# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Step 2: Our First TDD Cycle - Platform Base Classes

#### 🔴 RED Phase: Write Failing Test

We've already created `tests/unit/test_platform_base.py`. Let's run it:

```bash
# This will FAIL - that's expected!
python -m pytest tests/unit/test_platform_base.py -v
```

**Expected output:**
```
ImportError: cannot import name 'BasePlatformHandler' from 'platforms.base'
```

**Why this is good:** The test fails because the code doesn't exist yet. This confirms we're testing something that needs to be built.

#### 🟢 GREEN Phase: Make Test Pass

Now let's create the minimal implementation:

```bash
# Create the platforms module
mkdir -p platforms
touch platforms/__init__.py
```

Create `platforms/base.py`:
```python
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

class APIProvider(Enum):
    BRIGHTDATA = "brightdata"
    APIFY = "apify"

@dataclass
class PlatformConfig:
    name: str
    api_provider: APIProvider
    dataset_id: str
    date_format: str
    required_params: List[str]
    optional_params: List[str]
    api_endpoint: str
    media_fields: List[str]

class BasePlatformHandler(ABC):
    def __init__(self, config: PlatformConfig):
        self.config = config
    
    @abstractmethod
    def prepare_request_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def extract_media_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_storage_path(self, snapshot_id: str, timestamp: datetime) -> str:
        pass
    
    @abstractmethod
    def get_api_client(self) -> Any:
        pass
    
    @abstractmethod
    def parse_api_response(self, response: Any) -> List[Dict[str, Any]]:
        pass
```

Run tests again:
```bash
python -m pytest tests/unit/test_platform_base.py -v
```

**Success! Tests should pass now.** ✅

#### 🔵 REFACTOR Phase: Improve Code

Now we can improve the code while keeping tests green:

```python
# Add docstrings, type hints, validation, etc.
# Run tests after each change to ensure they still pass
```

### Step 3: TDD for Facebook Handler

#### 🔴 RED Phase: Write Test First

Create `tests/unit/test_facebook_handler.py`:
```python
import pytest
from datetime import datetime
from platforms.facebook.handler import FacebookHandler
from platforms.base import PlatformConfig, APIProvider

class TestFacebookHandler:
    def test_facebook_handler_validates_facebook_urls(self):
        """Test that Facebook handler only accepts Facebook URLs"""
        # This test will fail initially!
        config = PlatformConfig(
            name="Facebook",
            api_provider=APIProvider.BRIGHTDATA,
            dataset_id="gd_test",
            date_format="MM-DD-YYYY",
            required_params=["url"],
            optional_params=[],
            api_endpoint="https://api.brightdata.com",
            media_fields=["attachments"]
        )
        
        handler = FacebookHandler(config)
        
        # Valid Facebook URLs
        assert handler.validate_params({"url": "https://facebook.com/test"}) == True
        assert handler.validate_params({"url": "https://www.facebook.com/test"}) == True
        assert handler.validate_params({"url": "https://fb.com/test"}) == True
        
        # Invalid URLs
        assert handler.validate_params({"url": "https://twitter.com/test"}) == False
        assert handler.validate_params({"url": "not-a-url"}) == False
        assert handler.validate_params({}) == False
```

#### 🟢 GREEN Phase: Implement Facebook Handler

Create minimal implementation to pass the test:
```python
# platforms/facebook/handler.py
from ..base import BasePlatformHandler

class FacebookHandler(BasePlatformHandler):
    def validate_params(self, params: Dict[str, Any]) -> bool:
        url = params.get('url', '')
        return 'facebook.com' in url or 'fb.com' in url
    
    # Implement other required methods...
```

### Step 4: TDD Best Practices

#### 1. **Test One Thing at a Time**
```python
# Good: Focused test
def test_validates_required_url_parameter():
    assert handler.validate_params({}) == False

# Bad: Testing multiple things
def test_everything():
    # Tests validation, processing, and storage all in one
```

#### 2. **Use Descriptive Test Names**
```python
# Good: Clear what's being tested
def test_facebook_handler_converts_date_format_from_yyyy_mm_dd_to_mm_dd_yyyy():
    pass

# Bad: Unclear
def test_date():
    pass
```

#### 3. **Arrange-Act-Assert Pattern**
```python
def test_prepare_request_params():
    # Arrange: Set up test data
    handler = FacebookHandler(config)
    input_params = {"url": "https://facebook.com/test", "start_date": "2024-01-15"}
    
    # Act: Execute the method
    result = handler.prepare_request_params(input_params)
    
    # Assert: Verify the result
    assert result["start_date"] == "01-15-2024"
```

### Step 5: Integration Testing with TDD

After unit tests, write integration tests:

```python
# tests/integration/test_crawl_handler_multiplatform.py
@pytest.mark.asyncio
async def test_crawl_handler_routes_to_correct_platform():
    """Test that crawl handler selects the right platform handler"""
    # Test will fail until we implement platform routing
    handler = CrawlHandler()
    
    # Facebook request
    fb_result = await handler.handle_crawl_request({
        "platform": "facebook",
        "url": "https://facebook.com/test"
    })
    assert fb_result["platform"] == "facebook"
    
    # TikTok request
    tt_result = await handler.handle_crawl_request({
        "platform": "tiktok",
        "url": "https://tiktok.com/@test"
    })
    assert tt_result["platform"] == "tiktok"
```

## 📋 TDD Workflow Summary

1. **Identify a requirement** (e.g., "Facebook handler should validate URLs")
2. **Write a failing test** that describes the requirement
3. **Run the test** - confirm it fails (RED)
4. **Write minimal code** to make the test pass
5. **Run the test** - confirm it passes (GREEN)
6. **Refactor** the code if needed
7. **Run the test** - ensure it still passes
8. **Repeat** for the next requirement

## 🎯 Benefits You'll Experience

1. **Confidence**: Every line of code is tested
2. **Design**: Better interfaces emerge naturally
3. **Documentation**: Tests show how to use the code
4. **Refactoring**: Safe to change code anytime
5. **Focus**: No over-engineering or unused code

## 🚀 Next Steps

1. Run the educational script:
   ```bash
   python tests/run_tdd_cycle.py
   ```

2. Complete the platform base implementation

3. Move to platform-specific handlers:
   - Facebook handler (preserve existing logic)
   - TikTok handler (new Apify integration)
   - YouTube handler (new Apify integration)

4. Integration tests for the complete system

Remember: **Always write the test first!** If you're writing code without a failing test, you're not doing TDD.