import os
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from tools.log_tool import search_nifi_logs_tool
from prompts.nifi_agent_prompt import nifi_agent_instruction

# Load environment variables
load_dotenv()

# Configure loguru with both console and file output
logger.remove()  # Remove default handler

# Console output
logger.add(
    sink=lambda msg: print(msg, end=""),  # Print to console
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | <level>{message}</level>",
    level="INFO"
)

# File output - save all logs to file
log_filename = f"agent_logs/nifi_agent_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("agent_logs", exist_ok=True)

logger.add(
    sink=log_filename,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} | {message}",
    level="DEBUG",
    rotation="10 MB"
)

# Using buffer and functions from tools/nifi_tool.py

def create_nifi_agent():
    """Create simple NiFi agent with only memory tools"""
    try:
        logger.info("Creating NiFi Agent...")
        
        model = Gemini(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 4096,
                "candidate_count": 1
            }
        )
        logger.info("Gemini model configured for NiFi agent")
        
        # Simple NiFi analysis agent with minimal tools
        nifi_agent = LlmAgent(
            name="nifi_app_log_analyzer",
            description="Simple NiFi log analyzer focused on timestamp correlation",
            model=model,
            instruction=nifi_agent_instruction,
            tools=[
                search_nifi_logs_tool     # Core tool: Search NiFi logs by timestamp
            ]
        )
        
        logger.info("NiFi Agent created successfully")
        logger.info(f"Model: gemini-1.5-flash")
        logger.info("Tools: 1 tool (NiFi buffer search only)")
        return nifi_agent
        
    except Exception as e:
        logger.error(f"Failed to create NiFi Agent: {str(e)}")
        raise

# Create agent and runner
logger.info("Initializing NiFi Agent system...")
nifi_agent = create_nifi_agent()
nifi_runner = InMemoryRunner(agent=nifi_agent, app_name="nifi_app_log_analyzer")
logger.info("NiFi Agent system ready - can be called via AgentTool")
