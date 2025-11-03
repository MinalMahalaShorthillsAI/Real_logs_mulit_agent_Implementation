import os
import json
import asyncio
import glob
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from prompts.analyser_prompt import analysis_prompt_template, enhanced_instruction, standalone_instruction, standalone_analysis_prompt
from google.adk.tools.agent_tool import AgentTool
from tools.local_command_tools import close_persistent_terminal, get_terminal_session_info


load_dotenv()

# Configure logging
logger.remove()
logger.add(sink=lambda msg: print(msg, end=""), format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | <level>{message}</level>", level="INFO")

log_filename = f"agent_logs/agent_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
os.makedirs("agent_logs", exist_ok=True)
logger.add(sink=log_filename, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} | {message}", level="DEBUG")
logger.info(f"Logging session to file: {log_filename}")


def stream_logs_by_timestamp(log_file_path):
    """Stream complete log entries grouped by timestamp (handles multi-line logs like stack traces)"""
    import re
    
    try:
        logger.info(f"Starting timestamp-based log streaming from: {log_file_path}")
        
        # Common log timestamp patterns
        # Matches patterns like: "2025-10-09 16:20:41,140" or "2025-10-09 16:20:41.140"
        timestamp_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3}')
        
        with open(log_file_path, 'r') as file:
            current_log_entry = []
            log_entry_count = 0
            line_count = 0
            
            for line in file:
                line_count += 1
                line = line.rstrip()  # Keep leading spaces but remove trailing
                
                # Check if this line starts with a timestamp (new log entry)
                if timestamp_pattern.match(line):
                    # If we have a previous log entry, yield it
                    if current_log_entry:
                        complete_log = '\n'.join(current_log_entry)
                        log_entry_count += 1
                        logger.debug(f"Yielding log entry #{log_entry_count} ({len(current_log_entry)} lines): {current_log_entry[0][:80]}...")
                        yield complete_log
                    
                    # Start new log entry
                    current_log_entry = [line]
                else:
                    # This is a continuation line (stack trace, multi-line message, etc.)
                    if current_log_entry and line:  # Only add non-empty continuation lines
                        current_log_entry.append(line)
                
                if line_count % 1000 == 0:
                    logger.debug(f"Streaming progress: {line_count} lines processed, {log_entry_count} log entries yielded")
            
            # Yield the last log entry if exists
            if current_log_entry:
                complete_log = '\n'.join(current_log_entry)
                log_entry_count += 1
                logger.debug(f"Yielding final log entry #{log_entry_count}: {current_log_entry[0][:80]}...")
                yield complete_log
        
        logger.info(f"Streaming complete: {line_count} lines processed into {log_entry_count} complete log entries")
        
    except FileNotFoundError:
        logger.error(f"File not found: {log_file_path}")
    except Exception as e:
        logger.error(f"Error during streaming: {e}")


def save_agent_interaction(log_index, log_entry, input_prompt, agent_output, session_id=None, 
                          tool_calls=None, execution_metadata=None, output_dir="agent_outputs"):
    """Save agent interaction data with complete execution details"""
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
            "model": "gemini-2.5-flash",
            "tools_available": ["nifi_agent_tool"],
            "sub_agents_available": ["remediation_agent"]
        },
        "execution_trace": {
            "tool_calls": tool_calls or [],
            "total_responses": execution_metadata.get("total_responses", 0) if execution_metadata else 0,
            "total_tool_calls": len(tool_calls) if tool_calls else 0,
            "processing_time_ms": execution_metadata.get("processing_time_ms", 0) if execution_metadata else 0,
            "sub_agent_triggered": execution_metadata.get("sub_agent_triggered", False) if execution_metadata else False
        },
        "log_analysis": {
            "original_log_entry": log_entry,
            "input_prompt_to_agent": input_prompt,
            "agent_analysis_output": agent_output,
            "intermediate_responses": execution_metadata.get("all_responses", []) if execution_metadata else []
        }
    }
    
    filename = f"{output_dir}/complete_log_{log_index:05d}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(interaction_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save interaction for log {log_index}: {e}")


async def process_log_file(log_file_path, status_callback=None):
    """Process ALL logs for analysis - remediation handled by sub-agent automatically"""
    logger.info(f"Starting real-time streaming processing from: {log_file_path}")
    logger.info("📊 ANALYZING: All log types (INFO/WARN/ERROR/DEBUG) will be analyzed")
    logger.info("🔧 REMEDIATION: ERROR logs classified as ANOMALY will trigger remediation sub-agent automatically")
    
    session = await agent_runner.session_service.create_session(
        app_name="log_analysis_agent", 
        user_id="log_analyzer"
    )
    logger.info(f"Created session: {session.id}")
    
    if status_callback:
        status_callback("info", f"Session created: {session.id[:8]}...")
    
    error_log_count = 0
    
    # Choose prompt template based on correlation mode
    prompt_template = analysis_prompt_template if CORRELATION_MODE else standalone_analysis_prompt
    
    try:
        for log_entry in stream_logs_by_timestamp(log_file_path):
            error_log_count += 1
            # Show first line of log entry (timestamp line)
            first_line = log_entry.split('\n')[0]
            logger.info(f"Processing log #{error_log_count}: {first_line[:60]}...")
            
            if status_callback:
                status_callback("log", log_entry)  # Send the actual log content
                status_callback("processing", f"Analyzing log #{error_log_count}")
            
            prompt = prompt_template.format(log_entry=log_entry)
            
            try:
                content = types.Content(
                    parts=[types.Part.from_text(text=prompt)],
                    role="user"
                )
                
                logger.info(f"Calling multi-agent system for log #{error_log_count}")
                
                # Initialize tracking variables
                agent_output = "No response from agent"
                all_responses = []
                tool_calls = []  # Track all tool calls
                start_time = datetime.now()
                
                response_count = 0
                # Capture multiple responses to get full flow:
                # - Agent 1 analysis
                # - Agent 3 delegation (if triggered)
                # - Agent 3 response
                max_responses = 3  # Increased to capture Agent 1's analysis + Agent 3 flow
                
                async for event in agent_runner.run_async(
                    user_id=session.user_id, 
                    session_id=session.id,
                    new_message=content
                ):
                    # Handle different types of events
                    if hasattr(event, 'content') and event.content and event.content.parts:
                        for part in event.content.parts:
                            # Log function calls and track them
                            if hasattr(part, 'function_call') and part.function_call:
                                tool_name = part.function_call.name
                                call_time = datetime.now()
                                
                                # Capture tool call details
                                tool_call_info = {
                                    "tool_name": tool_name,
                                    "timestamp": call_time.isoformat(),
                                    "call_sequence": len(tool_calls) + 1
                                }
                                
                                # Try to capture arguments if available
                                try:
                                    if hasattr(part.function_call, 'args') and part.function_call.args:
                                        tool_call_info["arguments"] = str(part.function_call.args)[:500]  # Limit size
                                except:
                                    pass
                                
                                tool_calls.append(tool_call_info)
                                
                                logger.info(f"🔧 Tool call #{len(tool_calls)}: {tool_name}")
                                if status_callback:
                                    status_callback("tool_call", f"🔧 Tool call: {tool_name}")
                                
                            # Log function responses with details
                            elif hasattr(part, 'function_response') and part.function_response:
                                tool_name = part.function_response.name
                                response_time = datetime.now()
                                
                                # Update the corresponding tool call with response time
                                for tool_call in reversed(tool_calls):
                                    if tool_call["tool_name"] == tool_name and "response_timestamp" not in tool_call:
                                        tool_call["response_timestamp"] = response_time.isoformat()
                                        
                                        # Calculate response time
                                        call_time = datetime.fromisoformat(tool_call["timestamp"])
                                        response_duration = (response_time - call_time).total_seconds() * 1000
                                        tool_call["response_time_ms"] = round(response_duration, 2)
                                        
                                        # Capture response preview
                                        try:
                                            if hasattr(part.function_response, 'response'):
                                                response_preview = str(part.function_response.response)[:300]
                                                tool_call["response_preview"] = response_preview
                                        except:
                                            pass
                                        break
                                
                                logger.info(f"📋 Tool response: {tool_name}")
                                if status_callback:
                                    status_callback("tool_response", f"📋 Tool response: {tool_name}")
                                if tool_name == "nifi_agent_tool":
                                    logger.info(f"📊 NiFi tool response content: {str(part.function_response.response)[:200]}...")
                    
                    if event.is_final_response():
                        response_count += 1
                        logger.info(f"📨 Capturing response #{response_count}")
                        if status_callback:
                            status_callback("response", f"📨 Agent response #{response_count}")
                        
                        # Capture response text
                        current_response = ""
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    current_response = part.text
                                    all_responses.append(current_response)
                                    logger.debug(f"Response #{response_count} preview: {current_response[:100]}...")
                        
                        # Update agent_output only if we got actual text (not just delegation)
                        if current_response:
                            agent_output = current_response
                        
                        # Exit immediately if we've captured expected responses
                        if response_count >= max_responses:
                            logger.info(f"📋 Captured {response_count} responses - exiting")
                            break
                
                # Calculate total processing time
                end_time = datetime.now()
                processing_time_ms = round((end_time - start_time).total_seconds() * 1000, 2)
                
                # Detect if sub-agent was triggered
                sub_agent_triggered = response_count > 1 or any("remediation" in str(resp).lower() for resp in all_responses)
                
                # Combine multiple responses if any - preserve ALL responses
                if len(all_responses) > 1:
                    agent_output = "\n\n--- AGENT FLOW ---\n".join(all_responses)
                    logger.info(f"📋 Combined {len(all_responses)} responses into final output")
                elif len(all_responses) == 1:
                    agent_output = all_responses[0]
                    logger.info(f"📋 Single response captured")
                
                # Prepare execution metadata
                execution_metadata = {
                    "total_responses": response_count,
                    "processing_time_ms": processing_time_ms,
                    "sub_agent_triggered": sub_agent_triggered,
                    "all_responses": all_responses,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
                    
            except Exception as e:
                logger.error(f"Failed to call multi-agent system: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error occurred for log entry: {log_entry[:100]}...")
                agent_output = f"Error calling multi-agent system: {e}"
                tool_calls = []
                execution_metadata = {
                    "total_responses": 0,
                    "processing_time_ms": 0,
                    "sub_agent_triggered": False,
                    "all_responses": [],
                    "error": str(e)
                }
                
    
            save_agent_interaction(
                log_index=error_log_count, 
                log_entry=log_entry, 
                input_prompt=prompt, 
                agent_output=agent_output,
                session_id=session.id,
                tool_calls=tool_calls,
                execution_metadata=execution_metadata
            )
            
            if error_log_count % 10 == 0:
                logger.info(f"Progress: {error_log_count} logs processed")
            
            
    except KeyboardInterrupt:
        logger.warning("Processing stopped by user")
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    
    finally:
        # Check if terminal was used and close it
        terminal_info = get_terminal_session_info()
        if terminal_info["is_active"]:
            logger.info(f"🖥️  Terminal was used during this session")
            logger.info(f"📊 Total commands executed: {terminal_info['commands_executed']}")
            close_persistent_terminal(f"Log file processing complete - {error_log_count} logs analyzed")
    
    logger.info(f"Streaming processing complete - {error_log_count} logs analyzed")
    logger.info("All interactions saved to agent_outputs/")


def create_log_analysis_agent():
    """Create and configure the Log Analysis Agent with automatic NiFi correlation detection"""
    try:
        logger.info("Gemini model configured")
        
        # Try to load Agent 2 and Agent 3
        tools_list = []
        correlation_available = False
        
        # Check if NiFi logs exist and Agent 2 can be loaded
        nifi_log_path = "logs/nifi_app/nifi-app.log"
        if os.path.exists(nifi_log_path):
            try:
                from agent_2 import nifi_agent
                nifi_agent_tool = AgentTool(agent=nifi_agent, skip_summarization=False)
                nifi_agent_tool.name = "nifi_agent_tool"
                nifi_agent_tool.description = "Correlates application errors with NiFi infrastructure logs by timestamp analysis"
                tools_list.append(nifi_agent_tool)
                correlation_available = True
                logger.info("✓ NiFi correlation ENABLED (logs found)")
            except Exception as e:
                logger.warning(f"⚠ Could not load NiFi agent: {e}")
                logger.info("✗ NiFi correlation DISABLED (agent import failed)")
        else:
            logger.info(f"✗ NiFi correlation DISABLED (no logs at {nifi_log_path})")
        
        # Load Agent 3 (Remediation)
        from agent_3 import remediation_agent
        
        # Choose instruction based on correlation availability
        instruction = enhanced_instruction if correlation_available else standalone_instruction
        
        # Create agent with appropriate configuration
        agent = LlmAgent(
            name="log_analysis_agent",
            description="Application log analysis agent that identifies anomalies, correlates with NiFi application logs, and has remediation sub-agent for HITL planning",
            model="gemini-2.5-flash",
            generate_content_config=types.GenerateContentConfig(temperature=0.1),
            instruction=instruction,
            tools=tools_list,  # Empty if no NiFi correlation
            sub_agents=[remediation_agent]  # Remediation is a sub-agent, not a tool
        )
        
        mode = "WITH NiFi correlation" if correlation_available else "STANDALONE (no correlation)"
        logger.info(f"Log Analysis Agent created in {mode} mode")
        
        return agent, InMemoryRunner(agent=agent, app_name="log_analysis_agent"), correlation_available
        
    except Exception as e:
        logger.error(f"Failed to create Log Analysis Agent: {str(e)}")
        raise

# Create the agent and runner
Analyser_agent, agent_runner, CORRELATION_MODE = create_log_analysis_agent()

# Export for ADK Web Interface
root_agent = Analyser_agent


# Main execution for standalone file processing
async def main():
    """Run standalone log file processing"""
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
    # This allows running the script directly for file processing
    # while also being importable for ADK web interface
    asyncio.run(main())
