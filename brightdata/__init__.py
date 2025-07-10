"""
BrightData API client library for Data Ingestion Service.

This package provides a clean, modular interface for interacting with the
BrightData API, organized into specialized handlers for different operations.
"""

from .client import BrightDataClient
from .base_client import BaseClient

__all__ = ['BrightDataClient', 'BaseClient']