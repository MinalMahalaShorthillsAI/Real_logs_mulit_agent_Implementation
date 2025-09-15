from collections import deque
from typing import Dict, Any, Optional
from google.adk.tools import FunctionTool
from loguru import logger

# Global memory buffer - keeps only last 100 logs to save space
memory_buffer = deque(maxlen=50)


def add_log_to_memory(log_entry: str) -> Dict[str, Any]:
    """Add a log entry to the memory buffer.
    
    Args:
        log_entry: The log entry to add to memory
        
    Returns:
        Status of the operation with buffer size
    """
    global memory_buffer
    
    # Log the tool call
    logger.info(f"TOOL CALLED: add_log_to_memory")
    logger.debug(f"INPUT: {log_entry[:100]}...")
    
    memory_buffer.append(log_entry)
    
    result = {
        "status": "success", 
        "message": f"Added log to memory. Buffer size: {len(memory_buffer)}/100",
        "buffer_size": len(memory_buffer)
    }
    
    # Log the tool response
    logger.info(f"OUTPUT: {result}")
    logger.debug(f"Memory buffer now contains {len(memory_buffer)} logs")
    logger.debug("-" * 60)
    
    return result

def get_memory_context() -> Dict[str, Any]:
    """Get recent logs context for analysis.
    
    Returns:
        Recent logs formatted for context analysis
    """
    global memory_buffer
    
    # Log the tool call
    logger.info(f"TOOL CALLED: get_memory_context")
    logger.debug(f"INPUT: Request for recent logs context")
    
    if not memory_buffer:
        result = {"status": "empty", "context": "No previous logs in memory."}
        logger.info(f"OUTPUT: {result}")
        logger.debug("-" * 60)
        return result
    
    logs = list(memory_buffer)
    context = "Recent logs context (last 10):\n"
    for i, log in enumerate(logs[-10:], 1):
        context += f"{i}. {log}\n"
    
    result = {
        "status": "success",
        "context": context,
        "total_logs": len(logs),
        "context_logs": min(10, len(logs))
    }
    
    # Log the tool response
    logger.info(f"OUTPUT: Providing context of {min(10, len(logs))} recent logs from buffer of {len(logs)}")
    logger.debug(f"Context preview: {context[:200]}...")
    logger.debug("-" * 60)
    
    return result

# Create FunctionTool instances
add_log_tool = FunctionTool(func=add_log_to_memory)
get_context_tool = FunctionTool(func=get_memory_context)