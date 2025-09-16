import os
import json
import asyncio
import glob
import time
import signal
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from prompts.analyser_prompt import analysis_prompt_template, enhanced_instruction
from google.adk.tools.agent_tool import AgentTool
from agent_2 import nifi_agent

load_dotenv()

# Configure logging
logger.remove()
logger.add(sink=lambda msg: print(msg, end=""), format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | <level>{message}</level>", level="INFO")

log_filename = f"agent_logs/agent_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("agent_logs", exist_ok=True)
logger.add(sink=log_filename, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} | {message}", level="DEBUG")
logger.info(f"Logging session to file: {log_filename}")


def cleanup_and_exit():
    """Simple cleanup and exit"""
    logger.info("🧹 Cleanup completed")
    exit(0)

# Only handle Ctrl+C for clean exit
signal.signal(signal.SIGINT, lambda s, f: cleanup_and_exit())

def is_error_log(log_line):
    """Check if a single log line is an error log that needs agent analysis"""
    if not log_line or not log_line.strip():
        return False
    
    error_levels = ['ERROR', 'WARN', 'WARNING', 'CRITICAL', 'FATAL']
    is_error = any(level in log_line.upper() for level in error_levels)
    
    if is_error:
        logger.info(f"🚨 Error log detected: {log_line[:50]}...")
    else:
        logger.info(f"ℹ️  Not an error log: {log_line[:50]}...")
    
    return is_error

def stream_logs_line_by_line(log_file_path):
    """Stream logs line by line and yield only error logs for agent processing"""
    try:
        logger.info(f"🔄 Starting line-by-line streaming from: {log_file_path}")
        
        with open(log_file_path, 'r') as file:
            line_count = 0
            error_count = 0
            
            for line in file:
                line_count += 1
                line = line.strip()
                
                if line and is_error_log(line):
                    error_count += 1
                    logger.debug(f"📨 Yielding error log #{error_count} (line {line_count}) to agent")
                    yield line
                
                # Add delay to see the 0.5 second gap in filtering
                time.sleep(0.5)
                
                if line_count % 1000 == 0:
                    logger.debug(f"📊 Streaming progress: {line_count} lines processed, {error_count} errors found")
        
        logger.info(f"✅ Streaming complete: {line_count} total lines, {error_count} error logs sent to agent")
        
    except FileNotFoundError:
        logger.error(f"❌ File not found: {log_file_path}")
    except Exception as e:
        logger.error(f"❌ Error during streaming: {e}")

def save_agent_interaction(log_index, log_entry, input_prompt, agent_output, session_id=None, output_dir="agent_outputs"):
    """Save agent interaction data"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    interaction_data = {
        "metadata": {
            "timestamp": timestamp,
            "log_index": log_index,
            "session_id": session_id
        },
        "agent_configuration": {
            "name": "log_analysis_agent",
            "model": "gemini-1.5-flash",
            "tools_available": ["nifi_agent_tool"]
        },
        "log_analysis": {
            "original_log_entry": log_entry,
            "input_prompt_to_agent": input_prompt,
            "agent_analysis_output": agent_output
        }
    }
    
    filename = f"{output_dir}/complete_log_{log_index:05d}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(interaction_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save interaction for log {log_index}: {e}")

async def process_log_file(log_file_path):
    """Process logs with real-time streaming - only error logs go to agent"""
    logger.info(f"🚀 Starting real-time streaming processing from: {log_file_path}")
    logger.info("🔄 Only ERROR logs will be sent to agent for analysis")
    
    session = await agent_runner.session_service.create_session(
        app_name="log_analysis_agent", 
        user_id="log_analyzer"
    )
    logger.info(f"✅ Created session: {session.id}")
    
    error_log_count = 0
    
    try:
        for log_entry in stream_logs_line_by_line(log_file_path):
            error_log_count += 1
            logger.info(f"🚨 Processing ERROR log #{error_log_count}: {log_entry[:60]}...")
            
            prompt = analysis_prompt_template.format(log_entry=log_entry)
            
            try:
                content = types.Content(
                    parts=[types.Part.from_text(text=prompt)],
                    role="user"
                )
                
                logger.info(f"📤 Calling Gemini agent for error log #{error_log_count}")
                
                agent_output = "No response from agent"
                
                async for event in agent_runner.run_async(
                    user_id=session.user_id, 
                    session_id=session.id,
                    new_message=content
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    agent_output = part.text
                                    break
                        if agent_output != "No response from agent":
                            break
                
            except Exception as e:
                logger.error(f"❌ Failed to call Gemini agent: {e}")
                agent_output = f"Error calling Gemini agent: {e}"
            
            save_agent_interaction(
                log_index=error_log_count, 
                log_entry=log_entry, 
                input_prompt=prompt, 
                agent_output=agent_output,
                session_id=session.id
            )
            
            if error_log_count % 10 == 0:
                logger.info(f"📊 Progress: {error_log_count} error logs processed")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logger.warning("⚠️  Processing stopped by user")
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
    
    logger.info(f"✅ Streaming processing complete - {error_log_count} error logs analyzed")
    logger.info("💾 All interactions saved to agent_outputs/")

def create_log_analysis_agent():
    """Create and configure the Log Analysis Agent"""
    try:
        model = Gemini(
            model_name="gemini-1.5-pro",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "candidate_count": 1
            }
        )
        logger.info("Gemini model configured")
        
        nifi_agent_tool = AgentTool(agent=nifi_agent)
        nifi_agent_tool.name = "nifi_agent_tool"

        agent = LlmAgent(
            name="log_analysis_agent",
            description="Application log analysis agent that identifies anomalies and can correlate with NiFi pipeline issues",
            model=model,
            instruction=enhanced_instruction,
            tools=[nifi_agent_tool]
        )
        
        logger.info("Log Analysis Agent created with NiFi correlation tool")
        
        return agent, InMemoryRunner(agent=agent, app_name="log_analysis_agent")
        
    except Exception as e:
        logger.error(f"Failed to create Log Analysis Agent: {str(e)}")
        raise

# Create the agent and runner
Analyser_agent, agent_runner = create_log_analysis_agent()

# Main execution
async def main():
    log_folder_path = "/Users/shtlpmac071/Documents/Real_logs_a2a_imple/Real_logs_mulit_agent_Implementation/logs"
    log_files = glob.glob(os.path.join(log_folder_path, "*.log"))
    
    if not log_files:
        logger.error(f"No .log files found in folder: {log_folder_path}")
        return
    
    logger.info(f"Found {len(log_files)} log files to process:")
    for log_file in log_files:
        logger.info(f"  - {os.path.basename(log_file)}")
    
    for i, log_file_path in enumerate(log_files, 1):
        logger.info(f"\nProcessing file {i}/{len(log_files)}: {os.path.basename(log_file_path)}")
        await process_log_file(log_file_path)
        logger.info(f"Completed {os.path.basename(log_file_path)}")
    
    logger.info("All log files processed!")
    
if __name__ == "__main__":
    asyncio.run(main())