"""
FastAPI Web Application for Multi-Agent Log Analysis System
Provides REST API endpoints for the log analysis agents
"""
import os
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from agent_1 import agent_runner, process_log_file, stream_logs_line_by_line
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

@app.post("/analyze/single-log", response_model=LogAnalysisResponse)
async def analyze_single_log(request: LogAnalysisRequest):
    """
    Analyze a single log entry using the exact same multi-agent system as agent_1.py
    Reuses the working process_log_file logic for single log entries
    
    - **log_entry**: The log line to analyze (will trigger full agent pipeline)
    """
    try:
        logger.info(f"🔍 API: Full multi-agent analysis for: {request.log_entry[:100]}...")
        
        # Create a temporary single-line file to reuse existing process_log_file logic
        import tempfile
        import os
        
        # Create a temporary file with the single log entry
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(request.log_entry)
            tmp_file_path = tmp_file.name
        
        logger.info(f"🚀 Using proven process_log_file logic for full multi-agent pipeline")
        
        try:
            # Use the existing working process_log_file function
            await process_log_file(tmp_file_path)
            
            # Find the most recent output file to get results
            import glob
            output_files = glob.glob("agent_outputs/complete_log_*.json")
            
            if output_files:
                # Get the most recent output file
                latest_file = max(output_files, key=os.path.getctime)
                
                # Read the result
                import json
                with open(latest_file, 'r') as f:
                    result_data = json.load(f)
                
                # Extract analysis from the result
                agent_response = result_data.get('agent_output', 'Analysis completed')
                session_id = result_data.get('session_id', 'temp_session')
                
                # Determine classification and triggers
                classification = "ANOMALY" if '"ANOMALY"' in agent_response else "NORMAL"
                nifi_correlation = "nifi" in agent_response.lower()
                remediation_triggered = ("remediation" in agent_response.lower() or 
                                       "human approval" in agent_response.lower() or
                                       (classification == "ANOMALY" and " ERROR " in request.log_entry))
                
                logger.info(f"✅ Full analysis complete - Classification: {classification}, NiFi: {nifi_correlation}, Remediation: {remediation_triggered}")
                
                return LogAnalysisResponse(
                    status="success",
                    analysis=agent_response,
                    session_id=session_id,
                    timestamp=datetime.now().isoformat(),
                    classification=classification,
                    nifi_correlation=nifi_correlation,
                    remediation_triggered=remediation_triggered
                )
            else:
                # Fallback response if no output file found
                return LogAnalysisResponse(
                    status="success",
                    analysis=f"Multi-agent analysis completed for: {request.log_entry}",
                    session_id=f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now().isoformat(),
                    classification="NORMAL",
                    nifi_correlation=False,
                    remediation_triggered=False
                )
                
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
    except Exception as e:
        logger.error(f"❌ API Error in full multi-agent analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Multi-agent analysis failed: {str(e)}")

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
                    yield f"data: {{'status': 'processing', 'log_number': {error_log_count}, 'log_preview': '{log_entry[:60]}...'}}\n\n"
                    
                    # Use same prompt template as agent_1.py
                    prompt = analysis_prompt_template.format(log_entry=log_entry)
                    
                    try:
                        content = types.Content(
                            parts=[types.Part.from_text(text=prompt)],
                            role="user"
                        )
                        
                        yield f"data: {{'status': 'agent_call', 'message': 'Calling multi-agent system for log #{error_log_count}'}}\n\n"
                        
                        agent_output = "No response from agent"
                        all_responses = []
                        
                        response_count = 0
                        max_responses = 5  # Same as agent_1.py
                        
                        # Exact same agent runner call as agent_1.py
                        async for event in agent_runner.run_async(
                            user_id=session.user_id, 
                            session_id=session.id,
                            new_message=content
                        ):
                            # Handle events exactly like agent_1.py
                            if hasattr(event, 'content') and event.content and event.content.parts:
                                for part in event.content.parts:
                                    # Log function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        tool_name = part.function_call.name
                                        yield f"data: {{'status': 'tool_call', 'tool': '{tool_name}'}}\n\n"
                                        
                                    # Log function responses  
                                    elif hasattr(part, 'function_response') and part.function_response:
                                        tool_name = part.function_response.name
                                        yield f"data: {{'status': 'tool_response', 'tool': '{tool_name}'}}\n\n"
                                        if tool_name == "nifi_agent_tool":
                                            yield f"data: {{'status': 'nifi_correlation', 'message': 'NiFi correlation performed'}}\n\n"
                            
                            if event.is_final_response():
                                response_count += 1
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
                            
                    except Exception as e:
                        error_msg = f"Failed to call multi-agent system: {e}"
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

@app.post("/analyze/file", response_model=FileAnalysisResponse)
async def analyze_log_file(request: LogFileRequest, background_tasks: BackgroundTasks):
    """
    Analyze an entire log file using the multi-agent system
    
    - **file_path**: Path to the log file to analyze
    
    Note: This runs as a background task and returns immediately with a session ID.
    Use the session ID to check status or get results.
    """
    try:
        # Validate file exists
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        
        logger.info(f"📁 API: Starting file analysis for: {request.file_path}")
        
        # Add background task for file processing
        session_id = f"file_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        background_tasks.add_task(process_log_file, request.file_path)
        
        # Count total logs for estimation
        try:
            total_logs = sum(1 for _ in stream_logs_line_by_line(request.file_path))
        except:
            total_logs = 0
        
        return FileAnalysisResponse(
            status="started",
            message=f"File analysis started in background. Check agent_outputs/ for results.",
            total_logs_processed=total_logs,
            session_id=session_id,
            start_time=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ API Error starting file analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")

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


# ============================================================
# HUMAN-IN-THE-LOOP APPROVAL ENDPOINTS (Simple file-based)
# ============================================================

@app.post("/approve/{request_id}")
async def approve_request_endpoint(request_id: str):
    """Approve an approval request by updating the file"""
    import json
    approval_file = f"agent_logs/approval_{request_id}.json"
    
    if not os.path.exists(approval_file):
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    try:
        with open(approval_file, 'r') as f:
            data = json.load(f)
        
        data["status"] = "approved"
        
        with open(approval_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {"status": "success", "message": f"Request {request_id} approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reject/{request_id}")
async def reject_request_endpoint(request_id: str):
    """Reject an approval request by updating the file"""
    import json
    approval_file = f"agent_logs/approval_{request_id}.json"
    
    if not os.path.exists(approval_file):
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    try:
        with open(approval_file, 'r') as f:
            data = json.load(f)
        
        data["status"] = "rejected"
        
        with open(approval_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {"status": "success", "message": f"Request {request_id} rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
