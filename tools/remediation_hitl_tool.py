"""
Super Simple Human-in-the-Loop Tool for Agent 3
Just shows Agent 3's plan and gets human approval - nothing else!
"""

from google.adk.tools import FunctionTool
from loguru import logger

async def human_remediation_approval_tool(plan_text: str) -> str:
    """
    Ultra-simple human approval tool.
    Agent 3 provides the plan, human approves/rejects, that's it!
    
    Args:
        plan_text: The complete remediation plan from Agent 3
        
    Returns:
        str: Human decision (APPROVED/REJECTED)
    """
    logger.info("🤖➡️👤 Simple HITL Tool activated - Human approval required")
    
    # Display Agent 3's plan exactly as provided
    print("\n" + "="*60)
    print("🚨 HUMAN APPROVAL REQUIRED")
    print("="*60)
    print(plan_text)
    print("="*60)
    
    # Get simple human decision
    decision = input("👤 Your decision (approve/reject): ").strip().lower()
    
    if decision.startswith('a'):
        result = "APPROVED"
    elif decision.startswith('r'):
        result = "REJECTED"
    else:
        result = f"DECISION: {decision}"
    
    logger.info(f"👤 Human decision: {result}")
    return result

# Create the simple HITL tool for Agent 3
human_remediation_tool = FunctionTool(func=human_remediation_approval_tool)
human_remediation_tool.name = "human_remediation_approval_tool"

__all__ = ['human_remediation_tool', 'human_remediation_approval_tool']
