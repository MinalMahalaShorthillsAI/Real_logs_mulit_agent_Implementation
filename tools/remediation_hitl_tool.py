"""
Human-in-the-Loop Tool with In-Memory approval (no files!)
Uses shared memory to store and poll approval requests
"""

from google.adk.tools import FunctionTool
from loguru import logger
import asyncio
import time
import uuid

# In-memory storage for approval requests (shared across the application)
_approval_requests = {}

async def human_remediation_approval_tool(plan_text: str) -> str:
    """
    Present remediation plan and wait for human approval via API.
    Uses in-memory storage - no files created!
    
    Args:
        plan_text: The complete remediation plan from Agent 3
        
    Returns:
        str: "APPROVED" or "REJECTED" based on human decision via API
    """
    logger.info("🤖➡️👤 HITL Tool activated - Creating approval request")
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Store in memory
    _approval_requests[request_id] = {
        "plan": plan_text,
        "status": "pending",
        "created_at": time.time()
    }
    
    # Display message with curl commands
    print("\n" + "="*70)
    print(f"🚨 HUMAN APPROVAL REQUIRED - Request ID: {request_id}")
    print("="*70)
    print(plan_text)
    print("="*70)
    print("\n📡 To approve via curl (in another terminal):")
    print(f"   curl -X POST http://localhost:8000/approve/{request_id}")
    print("\n📡 To reject via curl:")
    print(f"   curl -X POST http://localhost:8000/reject/{request_id}")
    print("\n⏳ Polling every 5 seconds for your decision...")
    print("="*70 + "\n")
    
    logger.info(f"📋 Approval request created: {request_id}")
    
    # Poll for approval
    start_time = time.time()
    timeout = 300  # 5 minutes
    poll_interval = 5  # 5 seconds
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            logger.warning(f"⏱️  Request {request_id} TIMED OUT")
            _approval_requests.pop(request_id, None)  # Clean up
            return "TIMEOUT: No response received within 5 minutes"
        
        # Check in-memory status
        request = _approval_requests.get(request_id)
        if request:
            status = request.get("status", "pending")
            
            if status == "approved":
                logger.info(f"✅ Request {request_id} was APPROVED via API")
                print(f"\n✅ APPROVED - Proceeding with execution...\n")
                _approval_requests.pop(request_id, None)  # Clean up
                return "APPROVED"
            elif status == "rejected":
                # Check if there's feedback
                feedback = request.get("feedback", None)
                if feedback:
                    logger.info(f"💬 Request {request_id} was REJECTED with feedback: {feedback}")
                    print(f"\n💬 REJECTED WITH FEEDBACK - Modifying plan...\n")
                    print(f"Human feedback: {feedback}\n")
                    _approval_requests.pop(request_id, None)  # Clean up
                    return f"REJECTED_WITH_FEEDBACK: {feedback}"
                else:
                    logger.info(f"❌ Request {request_id} was REJECTED via API")
                    print(f"\n❌ REJECTED - Will create alternative plan...\n")
                    _approval_requests.pop(request_id, None)  # Clean up
                    return "REJECTED"
        
        # Wait before next poll
        elapsed = int(time.time() - start_time)
        if elapsed % 10 == 0:  # Log every 10 seconds
            logger.debug(f"⏳ Still waiting for approval... ({elapsed}s elapsed)")
        await asyncio.sleep(poll_interval)

def get_all_approval_requests():
    """Get all approval requests (for API endpoint)"""
    return _approval_requests

def update_approval_status(request_id: str, status: str, feedback: str = None):
    """Update approval status (called by API endpoint)"""
    if request_id in _approval_requests:
        _approval_requests[request_id]["status"] = status
        if feedback:
            _approval_requests[request_id]["feedback"] = feedback
        return True
    return False

def get_approval_feedback(request_id: str):
    """Get feedback for a specific request"""
    if request_id in _approval_requests:
        return _approval_requests[request_id].get("feedback", None)
    return None

# Create the HITL tool
human_remediation_tool = FunctionTool(func=human_remediation_approval_tool)
human_remediation_tool.name = "human_remediation_approval_tool"
human_remediation_tool.description = "Get human approval for remediation plan via FastAPI endpoints (in-memory, no files)."

__all__ = [
    'human_remediation_tool', 
    'human_remediation_approval_tool',
    'get_all_approval_requests',
    'update_approval_status'
]