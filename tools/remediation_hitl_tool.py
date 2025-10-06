"""
Human-in-the-Loop Tool using polling pattern (like ADK HITL example)
Polls a simple file for approval status - no new files needed!
"""

from google.adk.tools import FunctionTool
from loguru import logger
import asyncio
import time
import uuid
import json
import os

# In-memory storage for approvals (simple dict)
_approvals = {}

async def human_remediation_approval_tool(plan_text: str) -> str:
    """
    Present remediation plan and WAIT for human approval by polling a file.
    Uses the ADK HITL pattern: create request, poll until approved/rejected.
    
    The user approves by editing the approval file or via web endpoint.
    
    Args:
        plan_text: The complete remediation plan
        
    Returns:
        str: "APPROVED" or "REJECTED" based on human decision
    """
    logger.info("🤖➡️👤 HITL Tool activated - Creating approval request")
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Store approval request
    _approvals[request_id] = {
        "plan": plan_text,
        "status": "pending",
        "created_at": time.time()
    }
    
    # Save to file for web interface access
    approval_file = f"agent_logs/approval_{request_id}.json"
    os.makedirs("agent_logs", exist_ok=True)
    with open(approval_file, 'w') as f:
        json.dump(_approvals[request_id], f, indent=2)
    
    # Format message for user
    approval_message = f"""
============================================================
🚨 HUMAN APPROVAL REQUIRED - Request ID: {request_id}
============================================================

{plan_text}

============================================================
⏸️  WAITING FOR YOUR APPROVAL
============================================================

To approve, edit the file: {approval_file}
Change "status": "pending" to "status": "approved" or "rejected"

OR use curl:
  curl -X POST http://localhost:8000/approve/{request_id}
  curl -X POST http://localhost:8000/reject/{request_id}

Polling every 5 seconds for your decision...
"""
    
    logger.info(f"📋 Approval request: {request_id}")
    logger.info(f"📁 Approval file: {approval_file}")
    print(approval_message)
    
    # Poll for approval
    start_time = time.time()
    timeout = 300  # 5 minutes
    poll_interval = 5  # 5 seconds
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            logger.warning(f"⏱️  Request {request_id} TIMED OUT")
            return "TIMEOUT: No response received"
        
        # Check file for status change
        try:
            if os.path.exists(approval_file):
                with open(approval_file, 'r') as f:
                    data = json.load(f)
                    status = data.get("status", "pending")
                    
                    if status == "approved":
                        logger.info(f"✅ Request {request_id} was APPROVED")
                        return "APPROVED"
                    elif status == "rejected":
                        logger.info(f"❌ Request {request_id} was REJECTED")
                        return "REJECTED"
        except Exception as e:
            logger.debug(f"Error reading approval file: {e}")
        
        # Wait before next poll
        elapsed = int(time.time() - start_time)
        logger.info(f"⏳ Still waiting for approval... ({elapsed}s elapsed)")
        await asyncio.sleep(poll_interval)

# Create the HITL tool
human_remediation_tool = FunctionTool(func=human_remediation_approval_tool)
human_remediation_tool.name = "human_remediation_approval_tool"

__all__ = ['human_remediation_tool', 'human_remediation_approval_tool']
