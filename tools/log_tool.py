from google.adk.tools import FunctionTool
from loguru import logger

def search_nifi_logs_by_timestamp(timestamp: str) -> dict:
    """Search NiFi infrastructure logs around a timestamp for correlation.
    
    Args:
        timestamp: Time in HH:MM:SS format (e.g., "10:00:09")
        
    Returns:
        Dictionary with NiFi logs and correlation analysis
    """
    logger.info(f"NIFI TOOL CALLED: search_nifi_logs_by_timestamp({timestamp})")
    logger.info(f"Agent 1 is requesting NiFi correlation for timestamp: {timestamp}")
    
    # Find NiFi log files dynamically
    import os
    import glob
    
    nifi_log_pattern = "logs/nifi_app/nifi-app_*.log"
    nifi_files = glob.glob(nifi_log_pattern)
    
    if not nifi_files:
        logger.warning("No NiFi log files found in logs/nifi_app/")
        return {
            "status": "error", 
            "message": "No NiFi log files available",
            "timestamp_searched": timestamp,
            "nifi_logs_found": 0
        }
    
    # Use the most recent NiFi log file
    nifi_file = max(nifi_files, key=os.path.getctime)
    logger.info(f"Using dynamic NiFi log file: {nifi_file}")
    
    try:
        # Parse the target timestamp to find logs within 2 seconds before
        from datetime import datetime, timedelta
        
        try:
            # Extract date dynamically from the first line of the log file
            log_date = None
            with open(nifi_file, 'r') as f:
                first_line = f.readline().strip()
                if first_line and len(first_line) >= 10:
                    log_date = first_line[:10]  # Extract "YYYY-MM-DD"
            
            if not log_date:
                raise ValueError("Could not extract date from log file")
            
            # Parse target timestamp with extracted date
            target_dt = datetime.strptime(f"{log_date} {timestamp}", "%Y-%m-%d %H:%M:%S")
            logger.info(f"Using extracted log date: {log_date} for timestamp {timestamp}")
            start_time = target_dt - timedelta(seconds=2)  # 2 seconds before
            end_time = target_dt + timedelta(seconds=1)    # Include same second with milliseconds
            
            matching_logs = []
            with open(nifi_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            # Extract timestamp from log line (first 23 characters: "2025-09-14 10:01:09,437")
                            log_timestamp_str = line[:23]
                            log_dt = datetime.strptime(log_timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                            
                            # Check if log is between start_time and end_time
                            if start_time <= log_dt <= end_time:
                                matching_logs.append(line.strip())
                        except (ValueError, IndexError):
                            continue
        except ValueError:
            # Fallback: simple string matching for exact timestamp
            matching_logs = []
            with open(nifi_file, 'r') as f:
                for line in f:
                    if timestamp in line:
                        matching_logs.append(line.strip())
        
        # Return top 10 relevant logs
        result = {
            "status": "success",
            "timestamp_searched": timestamp,
            "nifi_logs_found": len(matching_logs),
            "nifi_infrastructure_logs": matching_logs[:10],
            "search_scope": f"NiFi infrastructure logs around {timestamp}",
            "correlation_ready": True
        }
        
        logger.info(f"📊 Found {len(matching_logs)} NiFi infrastructure logs around {timestamp}")
        logger.info(f"✅ NIFI TOOL COMPLETED: Returning {len(matching_logs)} logs to Agent 1")
        return result
        
    except Exception as e:
        logger.error(f"❌ NiFi search error: {e}")
        logger.error(f"❌ NIFI TOOL FAILED: Error occurred while searching for {timestamp}")
        return {
            "status": "error",
            "timestamp_searched": timestamp,
            "nifi_logs_found": 0,
            "nifi_infrastructure_logs": [],
            "error": str(e)
        }

# Create the tool
search_nifi_logs_tool = FunctionTool(func=search_nifi_logs_by_timestamp)