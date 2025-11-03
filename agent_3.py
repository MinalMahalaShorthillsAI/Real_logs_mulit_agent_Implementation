import os
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from prompts.remediation_agent_prompt import hitl_remediation_instruction, test_mode_instruction
from tools.remediation_hitl_tool import human_remediation_tool
from tools.local_command_tools import local_execution_tools
from google.genai import types

# Load environment variables
load_dotenv()

# ============================================================
# CONFIGURATION: TEST MODE vs PRODUCTION MODE
# ============================================================
# TEST_MODE = True:  Agent 3 exits quickly for Agent 1 testing
# TEST_MODE = False: Full remediation flow with human approval
TEST_MODE = os.getenv("AGENT3_TEST_MODE", "True").lower() == "true"  # Default: Test mode
# ============================================================

# Configure loguru with both console and file output
logger.remove()  # Remove default handler

# Console output
logger.add(
    sink=lambda msg: print(msg, end=""),  # Print to console
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | <level>{message}</level>",
    level="INFO"
)

# File output - save all logs to file
log_filename = f"agent_logs/remediation_agent_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("agent_logs", exist_ok=True)

logger.add(
    sink=log_filename,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} | {message}",
    level="DEBUG",
    rotation="10 MB"
)

logger.info(f"Remediation Agent logging to: {log_filename}")

def create_remediation_agent_with_hitl():
    """Create Agent 3 designed for human-in-the-loop remediation planning"""
    try:
        mode = "TEST MODE" if TEST_MODE else "PRODUCTION MODE"
        logger.info(f"Creating Remediation Agent in {mode}...")
        
        logger.info("Gemini Pro model configured for human-interactive remediation")
        
        # Choose instruction based on mode
        instruction = test_mode_instruction if TEST_MODE else hitl_remediation_instruction
        
        # In test mode, no tools needed (quick exit)
        # In production mode, full tools available
        all_tools = [] if TEST_MODE else ([human_remediation_tool] + local_execution_tools)
        
        remediation_agent = LlmAgent(
            name="remediation_agent",
            description="Human-interactive remediation specialist with Human in the loop and local command execution",
            model="gemini-2.5-pro",
            generate_content_config=types.GenerateContentConfig(temperature=0.1),
            instruction=instruction,
            tools=all_tools
        )
        
        logger.info("Remediation Agent created successfully")
        logger.info(f"Model: gemini-2.5-pro")
        logger.info(f"Mode: {mode}")
        if TEST_MODE:
            logger.info("Test Mode: Quick acknowledgment and exit (for Agent 1 testing)")
            logger.info("Tools: 0 (test mode)")
        else:
            logger.info("Production Mode: Full remediation with human approval")
            logger.info(f"Tools: {len(all_tools)} tools (HITL + {len(local_execution_tools)} local execution tools)")
        return remediation_agent
        
    except Exception as e:
        logger.error(f"Failed to create Remediation Agent: {str(e)}")
        raise

# Create agent and runner for sub-agent pattern
logger.info("Initializing Human-Interactive Remediation Agent system...")
remediation_agent = create_remediation_agent_with_hitl()
remediation_runner = InMemoryRunner(
    agent=remediation_agent, 
    app_name="remediation_planning_hitl"
)
logger.info("Remediation Agent system ready - can receive control transfer from Agent 1")

# Human interaction state tracking
APPROVAL_STATES = {
    "PLAN_PRESENTED": "Initial plan shown, awaiting feedback",
    "UNDER_DISCUSSION": "Human asking questions/requesting changes", 
    "PLAN_APPROVED": "Human explicitly approved the plan",
    "PLAN_REJECTED": "Human rejected, need alternatives",
    "PLAN_MODIFIED": "Human requested changes, revising",
    "EXECUTION_READY": "Final approval given, ready for execution"
}

def log_human_interaction(interaction_type, content, session_id=None):
    """Log human-agent interactions for audit trail"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    interaction_log = {
        "timestamp": timestamp,
        "session_id": session_id,
        "interaction_type": interaction_type,
        "content": content,
        "agent": "remediation_agent_hitl"
    }
    
    logger.info(f"👤🤖 HUMAN INTERACTION: {interaction_type}")
    logger.debug(f"Content: {content[:100]}...")
    
    # Save detailed interaction log
    interaction_filename = f"agent_logs/human_interactions_{datetime.now().strftime('%Y%m%d')}.json"
    
    try:
        import json
        with open(interaction_filename, 'a') as f:
            json.dump(interaction_log, f, indent=2)
            f.write('\n')
    except Exception as e:
        logger.error(f"Failed to save human interaction log: {e}")

# Export for use by Agent 1
__all__ = ['remediation_agent', 'remediation_runner', 'log_human_interaction', 'APPROVAL_STATES']
