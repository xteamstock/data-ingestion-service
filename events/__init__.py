"""
Events module for Data Ingestion Service.

This module contains event publishing functionality for microservices communication.
"""

from .event_publisher import EventPublisher

__all__ = ['EventPublisher']