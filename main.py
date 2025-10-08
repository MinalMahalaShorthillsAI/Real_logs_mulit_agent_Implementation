"""
FastAPI Web Application for Multi-Agent Log Analysis System
Provides REST API endpoints for the log analysis agents
"""
import os
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server configuration from .env file
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")  # Bind to all interfaces
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
# For URLs in responses - use actual server hostname/IP from .env
PUBLIC_HOST = os.getenv("PUBLIC_HOST", None)  # Will auto-detect if not set in .env

# Import your agents
from agent_1 import agent_runner
from google.genai import types

def get_server_url():
    """Get the public server URL for API responses"""
    if PUBLIC_HOST:
        return f"http://{PUBLIC_HOST}:{SERVER_PORT}"
    
    # Auto-detect server hostname/IP
    import socket
    try:
        # Try to get the hostname
        hostname = socket.gethostname()
        # Try to get the IP address
        local_ip = socket.gethostbyname(hostname)
        
        # For cloud/server environments, prefer hostname over local IP
        if hostname != "localhost" and not hostname.startswith("127."):
            return f"http://{hostname}:{SERVER_PORT}"
        else:
            return f"http://{local_ip}:{SERVER_PORT}"
    except:
        # Fallback to localhost
        return f"http://localhost:{SERVER_PORT}"

# FastAPI App Configuration
app = FastAPI(
    title="Multi-Agent Log Analysis API",
    description="AI-powered log analysis with NiFi correlation and remediation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models for API
class LogAnalysisRequest(BaseModel):
    log_entry: str
    session_id: Optional[str] = None

class LogFileRequest(BaseModel):
    file_path: str
    
class LogAnalysisResponse(BaseModel):
    status: str
    analysis: str
    session_id: str
    timestamp: str
    classification: Optional[str] = None
    nifi_correlation: Optional[bool] = False
    remediation_triggered: Optional[bool] = False

class FileAnalysisResponse(BaseModel):
    status: str
    message: str
    total_logs_processed: int
    session_id: str
    start_time: str

class HealthResponse(BaseModel):
    status: str
    agents: List[str]
    timestamp: str

# Global variables for session management
active_sessions = {}
active_streams = {}  # Track active streaming sessions

# API Endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    server_url = get_server_url()
    return {
        "message": "Multi-Agent Log Analysis API",
        "version": "1.0.0",
        "server_url": server_url,
        "agents": ["Analyser Agent", "NiFi Agent", "Remediation Agent"],
        "endpoints": {
            "health": f"{server_url}/health",
            "single_log_analysis": f"{server_url}/analyze/single-log",
            "streaming_analysis": f"{server_url}/stream/analyze-file",
            "file_analysis": f"{server_url}/analyze/file",
            "stop_stream": f"{server_url}/stop-stream/{{stream_id}}",
            "active_streams": f"{server_url}/active-streams",
            "documentation": f"{server_url}/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        agents=["analyser_agent", "nifi_agent", "remediation_agent"],
        timestamp=datetime.now().isoformat()
    )

@app.post("/stream/analyze-file")
async def stream_analyze_log_file(request: LogFileRequest):
    """
    Stream log file analysis exactly like agent_1.py - processes logs line by line
    Returns real-time streaming updates as each log is processed
    
    - **file_path**: Path to the log file to stream and analyze
    
    This endpoint replicates the exact behavior of running agent_1.py directly:
    1. Streams logs line-by-line from file
    2. For each log: calls full multi-agent system (Analyser → NiFi → Remediation)  
    3. Agent decides automatically what to do with each log
    4. Continues until file ends (or client disconnects)
    5. Saves all interactions to agent_outputs/
    """
    
    async def log_stream_generator():
        try:
            # Import exactly what agent_1.py uses
            from agent_1 import agent_runner, stream_logs_line_by_line, save_agent_interaction
            from prompts.analyser_prompt import analysis_prompt_template
            import time
            
            logger.info(f"🔍 Using agent_runner from agent_1 module")
            
            # Validate file exists
            if not os.path.exists(request.file_path):
                yield f"data: {{'error': 'File not found: {request.file_path}'}}\n\n"
                return
            
            yield f"data: {{'status': 'starting', 'message': 'Starting real-time streaming processing from: {request.file_path}'}}\n\n"
            yield f"data: {{'status': 'info', 'message': '📊 ANALYZING: All log types (INFO/WARN/ERROR/DEBUG) will be analyzed'}}\n\n"
            yield f"data: {{'status': 'info', 'message': '🔧 REMEDIATION: ERROR logs classified as ANOMALY will trigger remediation sub-agent automatically'}}\n\n"
            
            # Create session exactly like agent_1.py
            session = await agent_runner.session_service.create_session(
                app_name="log_analysis_agent", 
                user_id="log_analyzer"
            )
            yield f"data: {{'status': 'session_created', 'session_id': '{session.id}'}}\n\n"
            
            error_log_count = 0
            stream_id = f"stream_{session.id}"
            active_streams[stream_id] = True  # Mark stream as active
            
            server_url = get_server_url()
            yield f"data: {{'status': 'stream_started', 'stream_id': '{stream_id}', 'message': 'Stream started - use {server_url}/stop-stream/{stream_id} to stop'}}\n\n"
            
            try:
                # Stream logs exactly like agent_1.py does
                for log_entry in stream_logs_line_by_line(request.file_path):
                    # Check if stream should stop
                    if not active_streams.get(stream_id, False):
                        yield f"data: {{'status': 'stopped', 'message': 'Stream stopped by user request'}}\n\n"
                        break
                    error_log_count += 1
                    logger.info(f"📋 Processing log #{error_log_count}: {log_entry[:80]}...")
                    yield f"data: {{'status': 'processing', 'log_number': {error_log_count}, 'log_preview': '{log_entry[:60]}...'}}\n\n"
                    
                    # Use same prompt template as agent_1.py
                    prompt = analysis_prompt_template.format(log_entry=log_entry)
                    
                    try:
                        content = types.Content(
                            parts=[types.Part.from_text(text=prompt)],
                            role="user"
                        )
                        
                        logger.info(f"🤖 Calling agent for log #{error_log_count}")
                        yield f"data: {{'status': 'agent_call', 'message': 'Calling multi-agent system for log #{error_log_count}'}}\n\n"
                        
                        agent_output = "No response from agent"
                        all_responses = []
                        
                        response_count = 0
                        max_responses = 5  # Same as agent_1.py
                        
                        # Exact same agent runner call as agent_1.py
                        logger.info(f"⏳ Waiting for agent response...")
                        logger.info(f"🔍 Session: {session.id}, User: {session.user_id}")
                        
                        import asyncio
                        event_count = 0
                        
                        async for event in agent_runner.run_async(
                            user_id=session.user_id, 
                            session_id=session.id,
                            new_message=content
                        ):
                            event_count += 1
                            if event_count == 1:
                                logger.info(f"✅ First event received from agent!")
                            logger.debug(f"📨 Received event: {type(event).__name__}")
                            # Handle events exactly like agent_1.py
                            if hasattr(event, 'content') and event.content and event.content.parts:
                                for part in event.content.parts:
                                    # Log function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        tool_name = part.function_call.name
                                        logger.info(f"🔧 Agent calling tool: {tool_name}")
                                        yield f"data: {{'status': 'tool_call', 'tool': '{tool_name}'}}\n\n"
                                        
                                    # Log function responses  
                                    elif hasattr(part, 'function_response') and part.function_response:
                                        tool_name = part.function_response.name
                                        logger.info(f"✅ Tool response from: {tool_name}")
                                        yield f"data: {{'status': 'tool_response', 'tool': '{tool_name}'}}\n\n"
                                        if tool_name == "nifi_agent_tool":
                                            yield f"data: {{'status': 'nifi_correlation', 'message': 'NiFi correlation performed'}}\n\n"
                            
                            if event.is_final_response():
                                response_count += 1
                                logger.info(f"💬 Agent response #{response_count} received")
                                yield f"data: {{'status': 'response', 'response_number': {response_count}}}\n\n"
                                
                                if event.content and event.content.parts:
                                    for part in event.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            response_text = part.text
                                            all_responses.append(response_text)
                                            agent_output = response_text
                                            
                                # Stop if reached max responses (same as agent_1.py)
                                if response_count >= max_responses:
                                    yield f"data: {{'status': 'max_responses', 'message': 'Reached maximum responses ({max_responses}) - stopping capture'}}\n\n"
                                    break
                        
                        # Combine responses exactly like agent_1.py
                        if len(all_responses) > 1:
                            agent_output = "\\n\\n--- AGENT FLOW ---\\n".join(all_responses)
                        
                        logger.info(f"✅ Agent processing complete for log #{error_log_count}")
                            
                    except Exception as e:
                        error_msg = f"Failed to call multi-agent system: {e}"
                        logger.error(f"❌ Agent error: {e}")
                        yield f"data: {{'status': 'error', 'message': '{error_msg}'}}\n\n"
                        agent_output = f"Error calling multi-agent system: {e}"
                        time.sleep(2)
                    
                    # Save interaction exactly like agent_1.py
                    save_agent_interaction(
                        log_index=error_log_count, 
                        log_entry=log_entry, 
                        input_prompt=prompt, 
                        agent_output=agent_output,
                        session_id=session.id
                    )
                    
                    # Progress updates like agent_1.py
                    if error_log_count % 10 == 0:
                        yield f"data: {{'status': 'progress', 'logs_processed': {error_log_count}}}\n\n"
                    
                    # Same delay as agent_1.py
                    time.sleep(0.5)
                    
            except Exception as e:
                yield f"data: {{'status': 'error', 'message': 'Error during processing: {e}'}}\n\n"
            
            yield f"data: {{'status': 'completed', 'total_logs': {error_log_count}, 'message': 'Streaming processing complete - {error_log_count} logs analyzed'}}\n\n"
            yield f"data: {{'status': 'completed', 'message': 'All interactions saved to agent_outputs/'}}\n\n"
            
        except Exception as e:
            yield f"data: {{'status': 'fatal_error', 'message': 'Stream failed: {str(e)}'}}\n\n"
        finally:
            # Clean up stream tracking
            if 'stream_id' in locals():
                active_streams.pop(stream_id, None)
    
    return StreamingResponse(
        log_stream_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.post("/start-analysis")
async def start_analysis_background(request: LogFileRequest):
    """
    Start log analysis in the background - returns immediately
    Use this from Streamlit to avoid timeout issues
    """
    import asyncio
    from agent_1 import process_log_file
    
    def add_event(event_type, message):
        """Add important event to status"""
        # Special handling for log content
        if event_type == "log":
            analysis_status["current_log"] = message
            return
        
        # Update logs processed counter
        if event_type == "processing":
            analysis_status["logs_processed"] += 1
        
        # Log approval requests specially
        if "approval" in message.lower() or "remediation" in message.lower():
            logger.info(f"🔔 APPROVAL EVENT: {message}")
        
        analysis_status["agent_events"].append({
            "type": event_type,
            "message": message,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        # Keep only last 30 events
        if len(analysis_status["agent_events"]) > 30:
            analysis_status["agent_events"].pop(0)
    
    async def run_analysis():
        """Run the analysis in background"""
        global analysis_status
        try:
            analysis_status["is_running"] = True
            analysis_status["logs_processed"] = 0
            analysis_status["agent_events"] = []
            analysis_status["current_activity"] = "🚀 Starting analysis..."
            
            add_event("start", f"Analysis started: {request.file_path}")
            logger.info(f"🚀 Starting background analysis of: {request.file_path}")
            
            # Use the same process_log_file from agent_1.py with callback
            from agent_1 import process_log_file
            await process_log_file(request.file_path, status_callback=add_event)
            
            analysis_status["current_activity"] = "✅ Analysis complete!"
            add_event("complete", "Analysis finished successfully")
            logger.info(f"✅ Background analysis complete: {request.file_path}")
            
        except Exception as e:
            analysis_status["current_activity"] = f"❌ Error: {str(e)}"
            add_event("error", f"Analysis failed: {str(e)}")
            logger.error(f"❌ Background analysis failed: {e}")
        finally:
            analysis_status["is_running"] = False
    
    # Create task in current event loop - it will run after response is sent
    asyncio.create_task(run_analysis())
    
    return {
        "status": "started",
        "message": f"Analysis started for {request.file_path}",
        "file_path": request.file_path,
        "note": "Check FastAPI terminal for progress. Approval requests will appear in the dashboard."
    }


# Store analysis status in memory
analysis_status = {
    "is_running": False,
    "logs_processed": 0,
    "current_activity": "Idle",
    "current_log": None,
    "agent_events": []  # Keep important agent events only
}

@app.get("/analysis-status")
async def get_analysis_status():
    """Get current analysis status for real-time updates"""
    return analysis_status


@app.get("/analyze/file/results/{session_id}")
async def get_file_analysis_results(session_id: str):
    """Get results from a file analysis session"""
    try:
        # Look for output files with session pattern
        output_dir = "agent_outputs"
        if not os.path.exists(output_dir):
            raise HTTPException(status_code=404, detail="No analysis results found")
        
        # Find the most recent output file (simplified)
        import glob
        output_files = glob.glob(f"{output_dir}/complete_log_*.json")
        
        if not output_files:
            return {"status": "processing", "message": "Analysis still in progress"}
        
        # Return the most recent file info
        latest_file = max(output_files, key=os.path.getctime)
        file_size = os.path.getsize(latest_file)
        
        return {
            "status": "completed",
            "results_file": latest_file,
            "file_size_bytes": file_size,
            "message": f"Analysis complete. Results saved to {latest_file}"
        }
        
    except Exception as e:
        logger.error(f"❌ API Error getting results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@app.get("/sessions")
async def list_active_sessions():
    """List all active analysis sessions"""
    return {
        "active_sessions": list(active_sessions.keys()),
        "total_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.post("/stop-stream/{stream_id}")
async def stop_stream(stream_id: str):
    """
    Stop an active streaming session
    
    - **stream_id**: The stream ID returned when starting the stream
    
    This gracefully stops the log streaming process, similar to Ctrl+C in agent_1.py
    """
    if stream_id in active_streams:
        active_streams[stream_id] = False  # Signal stream to stop
        return {
            "status": "stopping", 
            "stream_id": stream_id,
            "message": "Stream stop signal sent - processing will halt after current log"
        }
    else:
        raise HTTPException(status_code=404, detail="Stream not found or already stopped")

@app.get("/active-streams")
async def list_active_streams():
    """List all currently active streaming sessions"""
    return {
        "active_streams": list(active_streams.keys()),
        "total_active": len(active_streams),
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# HUMAN-IN-THE-LOOP APPROVAL ENDPOINTS & DASHBOARD
# ============================================================

@app.get("/approvals/dashboard", response_class=HTMLResponse)
async def approval_dashboard():
    """Serve the approval dashboard HTML page"""
    return """
    <html>
        <body>
            <h1>Approval Dashboard</h1>
            <p>Please use Streamlit dashboard instead:</p>
            <code>streamlit run approval_dashboard.py</code>
        </body>
    </html>
    """

@app.get("/approvals/pending")
async def list_pending_approvals():
    """List all pending approval requests"""
    from tools.remediation_hitl_tool import get_all_approval_requests
    
    all_requests = get_all_approval_requests()
    pending = {k: v for k, v in all_requests.items() if v.get("status") == "pending"}
    
    # DEBUG: Log what we're returning
    logger.info(f"🔍 /approvals/pending called - Total requests: {len(all_requests)}, Pending: {len(pending)}")
    if pending:
        logger.info(f"🔍 Pending request IDs: {list(pending.keys())}")
    
    return {
        "pending_approvals": pending,
        "count": len(pending),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/approve/{request_id}")
async def approve_request_endpoint(request_id: str):
    """Approve an approval request (in-memory, no files)"""
    from tools.remediation_hitl_tool import update_approval_status
    
    success = update_approval_status(request_id, "approved")
    
    if success:
        logger.info(f"✅ API: Request {request_id} approved")
        return {
            "status": "success",
            "message": f"Request {request_id} approved",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

@app.post("/reject/{request_id}")
async def reject_request_endpoint(request_id: str, feedback: Optional[str] = None):
    """Reject an approval request (in-memory, no files)"""
    from tools.remediation_hitl_tool import update_approval_status
    
    success = update_approval_status(request_id, "rejected", feedback)
    
    if success:
        if feedback:
            logger.info(f"❌ API: Request {request_id} rejected with feedback: {feedback}")
        else:
            logger.info(f"❌ API: Request {request_id} rejected")
        return {
            "status": "success",
            "message": f"Request {request_id} rejected",
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

@app.post("/feedback/{request_id}")
async def send_feedback_endpoint(request_id: str, feedback: str):
    """Send feedback for a request (rejects with feedback for agent to modify plan)"""
    from tools.remediation_hitl_tool import update_approval_status
    
    if not feedback or not feedback.strip():
        raise HTTPException(status_code=400, detail="Feedback cannot be empty")
    
    success = update_approval_status(request_id, "rejected", feedback.strip())
    
    if success:
        logger.info(f"💬 API: Request {request_id} received feedback: {feedback}")
        return {
            "status": "success",
            "message": f"Feedback sent for request {request_id}",
            "feedback": feedback,
            "action": "Agent will modify the plan based on your feedback",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

# Configuration and startup
if __name__ == "__main__":
   
    logger.info("🚀 Starting Multi-Agent Log Analysis API")
    

    os.makedirs("agent_outputs", exist_ok=True)
    
    # Start the server with configurable host and port
    logger.info(f"🌍 Server will be accessible at: {get_server_url()}")
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info"
    )
