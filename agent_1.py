import os
import time
import json
import asyncio
import glob
import sys
import argparse
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from prompts.analyser_prompt import analysis_prompt_template, enhanced_instruction
from tools.memory_tool import add_log_tool, get_context_tool

# Load environment variables from .env file
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
from datetime import datetime
log_filename = f"agent_logs/agent_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("agent_logs", exist_ok=True)

logger.add(
    sink=log_filename,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} | {message}",
    level="DEBUG"  # Capture everything in file
)

logger.info(f"Logging session to file: {log_filename}")


def filter_important_logs_with_context(logs):
    """Filter logs to keep ERROR/WARN/CRITICAL logs plus 5 logs before and after each error"""
    important_levels = ['ERROR', 'WARN', 'WARNING', 'CRITICAL', 'FATAL']
    context_window = 2  # logs before and after
    
    # Find indices of error logs
    error_indices = []
    for i, log in enumerate(logs):
        if any(level in log.upper() for level in important_levels):
            error_indices.append(i)
    
    # Collect error logs with context
    selected_indices = set()
    for error_idx in error_indices:
        # Add 5 logs before, the error log, and 5 logs after
        start = max(0, error_idx - context_window)
        end = min(len(logs), error_idx + context_window + 1)
        for i in range(start, end):
            selected_indices.add(i)
    
    # Sort indices and extract logs
    filtered_logs = [logs[i] for i in sorted(selected_indices)]
    
    logger.info(f"Found {len(error_indices)} error logs")
    logger.info(f"Filtered {len(logs)} total logs down to {len(filtered_logs)} logs (with context)")
    logger.info(f"Context window: {context_window} logs before and after each error")
    
    return filtered_logs

def stream_logs_from_file(log_file_path):
    """Simple function to read and stream logs from file"""
    try:
        with open(log_file_path, 'r') as file:
            logs = [line.strip() for line in file.readlines() if line.strip()]
        
        # Filter to important logs with context (5 before and 5 after each error)
        filtered_logs = filter_important_logs_with_context(logs)
        return filtered_logs
        
    except FileNotFoundError:
        logger.error(f"File not found: {log_file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return []

def save_agent_interaction(log_index, log_entry, input_prompt, agent_output, session_id=None, output_dir="agent_outputs"):
    """Save complete agent interaction including tool calls and context"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get current memory state
    from tools.memory_tool import memory_buffer
    current_memory = list(memory_buffer)
    
    # Save complete interaction data
    interaction_data = {
        "metadata": {
            "timestamp": timestamp,
            "log_index": log_index,
            "session_id": session_id,
            "processing_time": timestamp
        },
        "agent_configuration": {
            "name": "log_analysis_agent",
            "model": "gemini-2.5-pro",
            "enhanced_instructions": enhanced_instruction,
            "tools_available": ["add_log_to_memory", "get_memory_context"],
            "memory_buffer_size": f"{len(current_memory)}/100"
        },
        "log_analysis": {
            "original_log_entry": log_entry,
            "input_prompt_to_agent": input_prompt,
            "agent_analysis_output": agent_output
        },
        "tool_interactions": "Check terminal output for real-time tool calls",
        "memory_state": {
            "buffer_size": len(current_memory),
            "recent_logs_in_memory": current_memory[-5:] if current_memory else [],
            "memory_context_available": len(current_memory) > 0
        }
    }
    
    # Save to individual file for this log
    filename = f"{output_dir}/complete_log_{log_index:05d}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(interaction_data, f, indent=2)
        logger.debug(f"Saved complete interaction to: {filename}")
    except Exception as e:
        logger.error(f"Failed to save interaction for log {log_index}: {e}")

async def process_log_file(agent, log_file_path):
    """Process logs from file - let the agent decide what's anomalous"""
    
    logger.info(f"Starting to process logs from: {log_file_path}")
    logger.info("=" * 80)
    
    # Load all logs from file
    all_logs = stream_logs_from_file(log_file_path)
    
    if not all_logs:
        logger.error("No logs found to process")
        return []
    
    logger.info(f"Loaded {len(all_logs)} log entries")
    logger.info("Creating output directory for agent interactions...")
    
    # Create ONE session for ALL logs - this ensures memory persists
    logger.info("Creating persistent session for memory continuity...")
    session = await agent_runner.session_service.create_session(
        app_name="log_analysis_agent", 
        user_id="log_analyzer"
    )
    logger.info(f"Created session: {session.id}")
    
    logger.info("Tool interactions will be visible in terminal output")
    
    results = []
    
    try:
        for i, log_entry in enumerate(all_logs, 1):
            logger.info(f"Processing log {i}/{len(all_logs)}: {log_entry[:100]}...")
            
            # Create prompt for the agent
            prompt = analysis_prompt_template.format(log_entry=log_entry)
            
            # Send log to Gemini agent using the SAME session for memory persistence
            logger.info(f"Sending log to Gemini agent (session: {session.id}): {log_entry[:50]}...")
            
            try:
                # Create content for the agent
                content = types.Content(
                    parts=[types.Part.from_text(text=prompt)],
                    role="user"
                )
                
                logger.info(f"Calling Gemini agent for log {i} (persistent session)...")
                
                # Get real agent analysis using the SAME session
                response_text = ""
                async for event in agent_runner.run_async(
                    user_id=session.user_id, 
                    session_id=session.id,  # Same session = persistent memory
                    new_message=content
                ):
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text
                
                agent_output = response_text if response_text.strip() else "No response from agent"
                logger.info(f"Got real agent analysis: {agent_output[:100]}...")
                
                # Check if agent used tools (function calls in response)
                if "function_call" in str(response_text):
                    logger.success(f"Agent used tools for log {i} - memory is being built!")
                
            except Exception as e:
                logger.error(f"Failed to call Gemini agent: {e}")
                agent_output = f"Error calling Gemini agent: {e}"
            
            # Save complete interaction with full context
            save_agent_interaction(
                log_index=i, 
                log_entry=log_entry, 
                input_prompt=prompt, 
                agent_output=agent_output,
                session_id=session.id
            )
            
            # Store the result
            results.append({
                'index': i,
                'log_entry': log_entry,
                'prompt': prompt,
                'agent_output': agent_output
            })
            
            # Wait 3 seconds between each log analysis
            logger.debug(f"Waiting 3 seconds before next log...")
            
            # Show progress every 10 logs and verify memory
            if i % 10 == 0:
                logger.info(f"Processed {i}/{len(all_logs)} logs, saved to agent_outputs/...")
                logger.info(f"Session {session.id} maintaining memory across logs...")
                
                # Check if our global memory buffer is being updated
                from tools.memory_tool import memory_buffer
                logger.info(f"Global memory buffer size: {len(memory_buffer)}/100")
                if len(memory_buffer) > 0:
                    logger.success("✅ Memory buffer is being populated by agent tools!")
                    logger.info(f"Latest log in memory: {list(memory_buffer)[-1][:80]}...")
                else:
                    logger.warning("⚠️ Global memory buffer is empty - agent might be using internal memory")
            
    except KeyboardInterrupt:
        logger.warning("Processing stopped by user")
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    
    # Final summary
    logger.success("PROCESSING COMPLETE")
    logger.success(f"Total logs processed: {len(results)}")
    logger.success(f"All interactions saved to agent_outputs/ directory")
    logger.success(f"Session {session.id} maintained memory across all logs")
    logger.info("=" * 80)
    
    return results

def create_log_analysis_agent():
    """Create and configure the Log Analysis Agent following ADK LlmAgent patterns"""
    try:
        
        
        # Use Gemini model
        model = Gemini(
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "candidate_count": 1
            }
        )
        logger.info("Gemini model configured")
        

        # Create LlmAgent with tools
        agent = LlmAgent(
            name="log_analysis_agent",
            description="NiFi log analysis agent that identifies anomalies and provides remediation steps",
            model=model,
            instruction=enhanced_instruction,
            tools=[
                add_log_tool,
                get_context_tool
            ]
        )
        
        logger.info("Log Analysis LlmAgent created successfully")
        logger.info(f"Model: gemini-2.5-pro")
        logger.info("Tools: 3 memory management tools")
        
        # Create in-memory runner for agent invocation
        runner = InMemoryRunner(
            agent=agent,
            app_name="log_analysis_agent"
        )
        
        logger.info("InMemoryRunner created for agent invocation")
        
        return agent, runner
        
    except Exception as e:
        logger.error(f"Failed to create Log Analysis Agent: {str(e)}")
        raise

# Create the agent and runner
Analyser_agent, agent_runner = create_log_analysis_agent()

# Main execution
async def main():
    # Give folder path here - it will process all .log files in the folder
    log_folder_path = "/Users/shtlpmac071/Documents/Real_logs_a2a_imple/Real_logs_mulit_agent_Implementation/logs"
    
    # Find all log files in the folder
    import glob
    log_files = glob.glob(os.path.join(log_folder_path, "*.log"))
    
    if not log_files:
        logger.error(f"No .log files found in folder: {log_folder_path}")
        return
    
    logger.info(f"Found {len(log_files)} log files to process:")
    for log_file in log_files:
        logger.info(f"  - {os.path.basename(log_file)}")
    
    all_results = []
    
    # Process each log file
    for i, log_file_path in enumerate(log_files, 1):
        logger.info(f"\nProcessing file {i}/{len(log_files)}: {os.path.basename(log_file_path)}")
        results = await process_log_file(Analyser_agent, log_file_path)
        all_results.extend(results)
        logger.success(f"Completed {os.path.basename(log_file_path)}: {len(results)} logs processed")
    
    logger.success(f"All done! Processed {len(all_results)} logs total from {len(log_files)} files!")
    
if __name__ == "__main__":
    asyncio.run(main())