"""
Pytest configuration for data-ingestion service tests.

This file configures pytest markers and provides shared fixtures.
"""

import pytest
import asyncio
from typing import Dict, Any


# Configure pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests requiring real API calls")
    config.addinivalue_line("markers", "expensive: marks tests that cost money to run")
    config.addinivalue_line("markers", "slow: marks tests as slow running (>30s)")
    config.addinivalue_line("markers", "flaky: marks tests as potentially flaky due to external dependencies")
    config.addinivalue_line("markers", "unit: marks tests as unit tests (no external dependencies)")


# Configure asyncio for all tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Shared test configuration
@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Shared test configuration."""
    return {
        "timeout": 30,
        "retry_count": 2,
        "retry_delay": 5,
    }