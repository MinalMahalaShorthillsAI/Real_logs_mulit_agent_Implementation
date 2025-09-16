import os
import time
from datetime import datetime
from collections import deque
from loguru import logger
from google.adk.tools import FunctionTool

class NiFiLogBuffer:
    """Simple 200-line rolling buffer for NiFi logs"""
    
    def __init__(self):
        self.buffer = deque()  # [(timestamp, log_line), ...]
        self.max_buffer_size = 200  # Keep only last 200 log lines
        self.loaded = False
        
    def load_logs_if_needed(self, log_file_path="logs/nifi_app/nifi-app_2025-09-14_10.0.log"):
        """Load logs from file into buffer if not already loaded"""
        if self.loaded:
            return
            
        if not os.path.exists(log_file_path):
            logger.warning(f"NiFi log file not found: {log_file_path}")
            return
            
        try:
            logger.info(f"Loading NiFi logs with FIFO buffer (max {self.max_buffer_size}) from: {log_file_path}")
            line_count = 0
            with open(log_file_path, 'r') as file:
                for line in file:
                    self._add_log_line(line)  # FIFO will automatically maintain size
                    line_count += 1
                    if line_count % 5000 == 0:
                        logger.info(f"Processed {line_count} lines, buffer maintains {len(self.buffer)} logs")
                    
            self.loaded = True
            logger.info(f"Successfully loaded {len(self.buffer)} NiFi logs via FIFO from {line_count} total lines")
            
        except Exception as e:
            logger.error(f"Error loading NiFi logs: {e}")
        
    def _add_log_line(self, log_line):
        """Add log line to buffer with FIFO behavior"""
        if not log_line.strip():
            return
            
        log_timestamp = self._parse_timestamp(log_line)
        self.buffer.append((log_timestamp, log_line.strip()))
        self._cleanup_old_logs()  # Maintain FIFO: remove oldest if over limit
        
    def _cleanup_old_logs(self):
        """Maintain FIFO: Remove oldest logs when buffer exceeds max size"""
        while len(self.buffer) > self.max_buffer_size:
            self.buffer.popleft()  # Remove oldest (first) log
        
    def _parse_timestamp(self, log_line):
        """Extract timestamp from NiFi log line"""
        try:
            # Format: "2025-09-14 13:00:09,885 ERROR ..."
            timestamp_part = log_line.split(' ')[0] + ' ' + log_line.split(' ')[1].split(',')[0]
            dt = datetime.strptime(timestamp_part, '%Y-%m-%d %H:%M:%S')
            return dt.timestamp()
        except:
            return time.time()
            
 
    def search_around_timestamp(self, target_time_str):
        """Search buffer for logs within ±2 seconds of target time"""
        self.load_logs_if_needed()  # Auto-load if needed
        
        try:
            # Handle various timestamp formats
            if 'T' in target_time_str or 'Z' in target_time_str:
                # Handle ISO format like "2024-08-02T12:00:00Z" - extract just time part
                if 'T' in target_time_str:
                    time_part = target_time_str.split('T')[1].split('Z')[0]
                    if ':' in time_part:
                        target_time_str = time_part.split('.')[0]  # Remove microseconds if any
            
            # If no date, add the log file date (2025-09-14)
            if ' ' not in target_time_str and len(target_time_str.split(':')) >= 2:
                log_date = "2025-09-14"  # Match the log file date
                target_time_str = f"{log_date} {target_time_str}"
                
            target_dt = datetime.strptime(target_time_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
            target_timestamp = target_dt.timestamp()
            
            # Find logs within ±2 seconds
            matching_logs = []
            for log_timestamp, log_line in self.buffer:
                if abs(log_timestamp - target_timestamp) <= 2:
                    matching_logs.append(log_line)
                    
            return matching_logs
            
        except Exception as e:
            logger.error(f"Error searching timestamp: {e}")
            return []

# Global buffer instance for Agent_2
nifi_buffer = NiFiLogBuffer()

# Pre-load buffer on module import to avoid lazy loading delays
def initialize_buffer_on_startup():
    """Initialize buffer immediately when module is imported"""
    logger.info("Pre-loading NiFi buffer...")
    nifi_buffer.load_logs_if_needed()
    logger.info(f"NiFi buffer ready: {len(nifi_buffer.buffer)} logs")

# Auto-initialize when module is imported
initialize_buffer_on_startup()

def search_nifi_logs_by_timestamp(timestamp: str) -> dict:
    """Tool for Agent_2 to search NiFi logs around a timestamp"""
    matching_logs = nifi_buffer.search_around_timestamp(timestamp)
    
    return {
        "timestamp_searched": timestamp,
        "logs_found": len(matching_logs),
        "matching_logs": matching_logs
    }

def get_nifi_buffer_status() -> dict:
    """Tool for Agent_2 to check buffer status"""
    return {
        "buffer_loaded": nifi_buffer.loaded,
        "total_logs": len(nifi_buffer.buffer),
        "max_buffer_size": nifi_buffer.max_buffer_size
    }

# Create FunctionTools for Agent_2
search_nifi_logs_tool = FunctionTool(func=search_nifi_logs_by_timestamp)
nifi_buffer_status_tool = FunctionTool(func=get_nifi_buffer_status)
