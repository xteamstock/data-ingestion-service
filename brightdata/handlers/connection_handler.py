"""
Connection handler for BrightData API connectivity testing.

This module provides functionality for testing API connectivity,
validating configuration, and performing health checks on the
BrightData API connection.
"""

import requests
import logging
from typing import Dict, Any
from datetime import datetime

from ..base_client import BaseClient

logger = logging.getLogger(__name__)


class ConnectionHandler(BaseClient):
    """
    Handler for BrightData API connectivity operations.
    
    This class manages API connection testing, configuration validation,
    and network health checks for the BrightData API.
    """
    
    def test_api_connection(self) -> Dict[str, Any]:
        """
        Test BrightData API connection and authentication.
        
        This method performs a comprehensive test of the BrightData API connection
        by making a request to the progress endpoint with a default snapshot ID.
        It validates configuration, tests network connectivity, and verifies API
        authentication credentials.
        
        Returns:
            Dict[str, Any]: Standardized response containing:
                - status: 'success' or 'error'
                - message: Human-readable status message
                - api_response: Raw API response (on success)
                - response_code: HTTP status code
                - timestamp: ISO timestamp of the test
        
        Example:
            handler = ConnectionHandler()
            result = handler.test_api_connection()
            if result['status'] == 'success':
                print("API is accessible")
            else:
                print(f"API test failed: {result['message']}")
        """
        try:
            logger.info("Testing BrightData API connection")
            
            # Step 1: Validate configuration before making any API calls
            is_valid, error_msg = self.validate_config()
            if not is_valid:
                return self._create_error_response(error_msg)
            
            # Step 2: Construct test URL using progress endpoint
            # Using a default snapshot ID for testing
            default_snapshot_id = "test_snapshot_123"
            test_url = f"{self.base_url}/progress/{default_snapshot_id}"
            headers = self.get_headers()
            
            logger.info(f"Calling BrightData API: {test_url}")
            
            # Step 3: Make the test request with timeout protection
            response = requests.get(test_url, headers=headers, timeout=30)
            
            # Step 4: Process successful response
            if response.status_code == 200:
                logger.info("BrightData API connection successful")
                return self._create_success_response(
                    message="BrightData API connection successful",
                    api_response=response.json(),
                    response_code=response.status_code
                )
            else:
                # Step 5: Handle API errors
                return self._handle_api_error(response, "API test")
                
        except requests.exceptions.Timeout:
            return self._create_error_response("Request timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            return self._create_error_response("Connection error - Cannot reach BrightData API")
        except requests.exceptions.RequestException as e:
            return self._create_error_response(f"Request error: {str(e)}")
        except Exception as e:
            return self._create_error_response(f"Unexpected error: {str(e)}")
    
    def _create_success_response(self, message: str, api_response: Dict = None, response_code: int = 200) -> Dict[str, Any]:
        """Create standardized success response."""
        return {
            'status': 'success',
            'message': message,
            'api_response': api_response,
            'response_code': response_code,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _create_error_response(self, error_message: str, response_code: int = 500) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'status': 'error',
            'message': error_message,
            'response_code': response_code,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _handle_api_error(self, response: requests.Response, operation: str) -> Dict[str, Any]:
        """Handle API error responses."""
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'API error during {operation}')
        except:
            error_message = f'API error during {operation} - HTTP {response.status_code}'
        
        logger.error(f"API error: {error_message}")
        return self._create_error_response(error_message, response.status_code)