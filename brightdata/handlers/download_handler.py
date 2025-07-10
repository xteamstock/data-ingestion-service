"""
Download handler for BrightData API download operations.

This module provides functionality for downloading collected data
from completed crawl jobs and managing snapshot downloads.
"""

import requests
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from ..base_client import BaseClient

logger = logging.getLogger(__name__)


class DownloadHandler(BaseClient):
    """
    Handler for BrightData API download operations.
    
    This class manages downloading of collected data from completed
    crawl jobs and snapshot management.
    """
    
    def download_snapshot(self, snapshot_id: Optional[str] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Download snapshot data from BrightData API with retry logic.
        
        Args:
            snapshot_id (Optional[str]): The snapshot ID to download
            max_retries (int): Maximum number of retry attempts for JSON parsing failures
        
        Returns:
            Dict[str, Any]: Standardized response with download results
        """
        try:
            if not snapshot_id:
                return self._create_error_response("No snapshot_id provided")
            
            download_url = f"{self.base_url}/snapshot/{snapshot_id}"
            headers = self.get_download_headers()
            
            logger.info(f"Downloading snapshot: {snapshot_id}")
            
            response = requests.get(download_url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # Store raw response for debugging if parsing fails
                raw_response = response.text
                logger.debug(f"Raw response length for {snapshot_id}: {len(raw_response)} characters")
                
                # Use robust JSON parsing to handle concatenated/malformed responses
                data = self._parse_brightdata_response(raw_response, snapshot_id)
                if data is None:
                    # Store raw response for manual debugging
                    self._store_failed_response_for_debug(snapshot_id, raw_response)
                    return self._create_error_response("Failed to parse BrightData response as JSON")
                    
                logger.info(f"Snapshot downloaded successfully: {snapshot_id} ({len(data)} records)")
                return self._create_success_response(
                    message="Snapshot downloaded successfully",
                    data=data,
                    snapshot_id=snapshot_id
                )
            else:
                error_msg = f"Download failed: {response.text}"
                logger.error(error_msg)
                return self._create_error_response(error_msg, response.status_code)
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout while downloading snapshot"
            logger.error(error_msg)
            return self._create_error_response(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error while downloading snapshot"
            logger.error(error_msg)
            return self._create_error_response(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while downloading snapshot: {str(e)}"
            logger.error(error_msg)
            return self._create_error_response(error_msg)
    
    def download_crawl_data(self, snapshot_id: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Download collected data from a completed crawl job.
        
        Args:
            snapshot_id (str): The unique identifier for the completed crawl job
        
        Returns:
            Tuple[Optional[List[Dict]], Optional[str]]: (data, error_message)
        """
        try:
            download_result = self.download_snapshot(snapshot_id)
            
            if download_result['status'] == 'success':
                data = download_result.get('data', [])
                return data, None
            else:
                error_msg = download_result.get('message', 'Unknown download error')
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Error downloading crawl data: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def _parse_brightdata_response(self, response_text: str, snapshot_id: str) -> Optional[List[Dict]]:
        """
        Robust JSON parsing to handle various BrightData response formats.
        
        BrightData may return:
        1. Standard JSON array: [{"data": "value"}, {"data": "value2"}]
        2. Concatenated JSON objects: {"data": "value"}{"data": "value2"}
        3. JSON with metadata: {"data": [...]}{"metadata": {...}}
        4. Mixed content with headers/footers
        
        Args:
            response_text (str): Raw response text from BrightData API
            snapshot_id (str): Snapshot ID for logging context
            
        Returns:
            Optional[List[Dict]]: Parsed data objects or None if parsing fails
        """
        try:
            # First attempt: Try parsing as standard JSON
            try:
                data = json.loads(response_text)
                logger.info(f"Successfully parsed response as standard JSON for {snapshot_id}")
                # Always return as list, preserve all data structure as-is
                if isinstance(data, list):
                    return data
                else:
                    return [data]
            except json.JSONDecodeError as e:
                logger.warning(f"Standard JSON parsing failed for {snapshot_id}: {str(e)}")
                logger.debug(f"Response preview: {response_text[:200]}...")
                
            # Second attempt: Handle concatenated JSON objects
            parsed_objects = []
            decoder = json.JSONDecoder()
            idx = 0
            response_length = len(response_text)
            
            logger.info(f"Attempting to parse concatenated JSON for {snapshot_id} (response length: {response_length})")
            
            while idx < response_length:
                # Skip whitespace and newlines
                while idx < response_length and response_text[idx].isspace():
                    idx += 1
                
                if idx >= response_length:
                    break
                    
                try:
                    # Try to decode JSON object starting at current position
                    obj, end_idx = decoder.raw_decode(response_text, idx)
                    parsed_objects.append(obj)
                    idx += end_idx
                    logger.debug(f"Parsed JSON object {len(parsed_objects)} for {snapshot_id}")
                except json.JSONDecodeError as e:
                    # If we can't parse from current position, try to find next '{'
                    next_brace = response_text.find('{', idx + 1)
                    if next_brace == -1:
                        logger.warning(f"No more JSON objects found starting at position {idx} for {snapshot_id}")
                        break
                    logger.warning(f"Skipping invalid JSON from position {idx} to {next_brace} for {snapshot_id}")
                    idx = next_brace
            
            if parsed_objects:
                # Filter out non-dictionary objects (leftover text fragments)
                valid_objects = [obj for obj in parsed_objects if isinstance(obj, dict)]
                if valid_objects:
                    logger.info(f"Successfully parsed {len(valid_objects)} valid JSON objects for {snapshot_id} (filtered {len(parsed_objects) - len(valid_objects)} invalid fragments)")
                    return valid_objects
                else:
                    logger.warning(f"No valid dictionary objects found in {len(parsed_objects)} parsed fragments for {snapshot_id}")
                
            # Third attempt: Extract only valid JSON lines
            json_lines = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('{') or line.startswith('[')):
                    try:
                        obj = json.loads(line)
                        json_lines.append(obj)
                    except json.JSONDecodeError:
                        continue
            
            if json_lines:
                # Filter out non-dictionary objects from JSON lines too
                valid_lines = [obj for obj in json_lines if isinstance(obj, dict)]
                if valid_lines:
                    logger.info(f"Successfully parsed {len(valid_lines)} valid JSON lines for {snapshot_id} (filtered {len(json_lines) - len(valid_lines)} invalid items)")
                    return valid_lines
                
            # Final attempt: Look for JSON data within response
            # Sometimes responses have headers/metadata we need to skip
            start_marker = response_text.find('[')
            if start_marker == -1:
                start_marker = response_text.find('{')
            
            if start_marker != -1:
                try:
                    # Try parsing from first JSON marker to end
                    json_part = response_text[start_marker:]
                    data = json.loads(json_part)
                    logger.info(f"Successfully parsed JSON starting from position {start_marker} for {snapshot_id}")
                    return data if isinstance(data, list) else [data]
                except json.JSONDecodeError:
                    pass
            
            # Log debugging information for manual inspection
            logger.error(f"All JSON parsing attempts failed for {snapshot_id}")
            logger.error(f"Response preview (first 500 chars): {response_text[:500]}")
            logger.error(f"Response preview (last 500 chars): {response_text[-500:]}")
            
            # Check for common issues
            if '}{' in response_text:
                logger.error(f"Detected concatenated JSON objects without proper separation in {snapshot_id}")
            if response_text.count('{') != response_text.count('}'):
                logger.error(f"Unbalanced JSON braces detected in {snapshot_id}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error in robust JSON parsing for {snapshot_id}: {str(e)}")
            return None
    
    def _store_failed_response_for_debug(self, snapshot_id: str, raw_response: str) -> None:
        """
        Store failed response for manual debugging.
        
        Args:
            snapshot_id (str): Snapshot ID for file naming
            raw_response (str): Raw response text that failed to parse
        """
        try:
            import os
            from datetime import datetime
            
            # Create debug directory if it doesn't exist
            debug_dir = "/tmp/brightdata_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Create timestamped debug file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            debug_file = f"{debug_dir}/failed_response_{snapshot_id}_{timestamp}.txt"
            
            # Store raw response with metadata
            debug_content = f"""
BrightData Response Debug Information
=====================================
Snapshot ID: {snapshot_id}
Timestamp: {datetime.utcnow().isoformat()}
Response Length: {len(raw_response)} characters
Response Content Type: Unknown (from requests.get)

Raw Response:
{raw_response}

Analysis:
- Contains '}}{{': {'Yes' if '}{' in raw_response else 'No'}
- Balanced braces: {'Yes' if raw_response.count('{') == raw_response.count('}') else 'No'}
- First character: {raw_response[0] if raw_response else 'Empty'}
- Last character: {raw_response[-1] if raw_response else 'Empty'}
"""
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(debug_content)
                
            logger.error(f"Failed response stored for debugging: {debug_file}")
            
        except Exception as e:
            logger.error(f"Failed to store debug information: {str(e)}")
    
    def _create_success_response(self, message: str, data: Any = None, snapshot_id: str = None) -> Dict[str, Any]:
        """Create standardized success response."""
        response = {
            'status': 'success',
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if snapshot_id:
            response['snapshot_id'] = snapshot_id
            
        return response
    
    def _create_error_response(self, error_message: str, response_code: int = 500) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'status': 'error',
            'message': error_message,
            'response_code': response_code,
            'timestamp': datetime.utcnow().isoformat()
        }