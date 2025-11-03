"""
Local Command Execution Tools for Agent 3
Secure local command execution with optional terminal display

Terminal Display Strategy (macOS):
- Creates a dedicated Terminal window with a unique custom title (e.g., "Agent3-a1b2c3d4")
- Commands are executed ONLY in the window matching that exact custom title
- This prevents cross-contamination with other terminal windows (e.g., Elasticsearch)
- If terminal targeting fails, commands still execute with output in the console
"""

import asyncio
import time
import subprocess
import platform
from typing import Dict, Optional, Set
from loguru import logger
from google.adk.tools import FunctionTool

# Rate limiting to prevent high CPU usage
_active_executions: Set[str] = set()
_execution_lock = asyncio.Lock()
_last_execution_time = {}
MIN_INTERVAL_BETWEEN_COMMANDS = 0.5  # seconds

# Simple terminal session tracking
_terminal_session_id = None
_terminal_usage_count = 0
_terminal_window_id = None  # Track specific terminal window
_terminal_enabled = True  # Can be disabled if terminal targeting fails

def _try_open_terminal():
    """Try to open a terminal window for macOS and Linux"""
    global _terminal_session_id, _terminal_window_id, _terminal_enabled
    
    if not _terminal_enabled:
        return False
    
    if _terminal_session_id is not None:
        return True
    
    try:
        import uuid
        _terminal_session_id = str(uuid.uuid4())[:8]
        system = platform.system().lower()
        
        if system == "darwin":
            # Create a new Terminal window with a unique title we can target
            # Use custom title to identify the correct window
            window_title = f"Agent3-{_terminal_session_id}"
            
            script = f'''
            tell application "Terminal"
                set newWindow to do script "printf '\\\\033]0;{window_title}\\\\007'; clear; echo '🚀 Agent3 Command Terminal'; echo 'Session ID: {_terminal_session_id}'; echo ''; echo 'Commands will appear below:'; echo '═══════════════════════════════════════'; echo ''"
                activate
                set custom title of newWindow to "{window_title}"
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode == 0:
                _terminal_window_id = window_title  # Store the title instead of ID
                print(f"✅ Opened terminal session: {_terminal_session_id}")
                print(f"   Terminal title: {window_title}")
                return True
            else:
                print(f"⚠️  Failed to create terminal: {result.stderr}")
                _terminal_enabled = False
                return False
            
        elif system == "linux":
            for term in ['gnome-terminal', 'konsole', 'xterm']:
                if subprocess.run(['which', term], capture_output=True).returncode == 0:
                    cmd = [term, '--', 'bash', '-c', f'echo "🚀 Agent3 Session: {_terminal_session_id}"; echo "Commands will appear here..."; bash']
                    break
            else:
                return False
            
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ Opened terminal session: {_terminal_session_id}")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"⚠️  Could not open terminal: {e}")
        _terminal_window_id = None
        _terminal_enabled = False
        return False

def _execute_in_terminal(command: str) -> bool:
    """Execute command in terminal window (macOS/Linux)"""
    if not _terminal_session_id or not _terminal_window_id:
        return False
    
    try:
        system = platform.system().lower()
        
        if system == "darwin":
            # Find the window by our custom title and execute command there
            # Escape quotes properly for AppleScript
            escaped_command = command.replace('\\', '\\\\').replace('"', '\\"')
            window_title = _terminal_window_id  # This is the title string now
            
            script = f'''
            tell application "Terminal"
                repeat with w in windows
                    if custom title of w is "{window_title}" then
                        do script "{escaped_command}" in w
                        return true
                    end if
                end repeat
                return false
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
            return "true" in result.stdout.lower()
        
        elif system == "linux":
            try:
                result = subprocess.run(
                    ['xdotool', 'search', '--name', f'Agent3 Session: {_terminal_session_id}'],
                    capture_output=True, text=True, timeout=2
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    window_id = result.stdout.strip().split('\n')[0]
                    subprocess.run(['xdotool', 'windowactivate', window_id], timeout=2)
                    subprocess.run(['xdotool', 'type', '--clearmodifiers', command], timeout=2)
                    subprocess.run(['xdotool', 'key', 'Return'], timeout=2)
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False
        
        return False
    except Exception:
        return False

async def execute_local_command(server_name: str, command: str, timeout: Optional[int] = None) -> Dict:
    """Execute a secure command locally with optional terminal display"""
    

    if command.strip().lower().startswith('sudo'):
        return {"status": "BLOCKED", "output": "Sudo commands blocked", "error": "Sudo not allowed"}
    
    # Rate limiting
    async with _execution_lock:
        current_time = time.time()
        last_time = _last_execution_time.get(server_name, 0)
        
        if current_time - last_time < MIN_INTERVAL_BETWEEN_COMMANDS:
            wait_time = MIN_INTERVAL_BETWEEN_COMMANDS - (current_time - last_time)
            await asyncio.sleep(wait_time)
        
        if server_name in _active_executions:
            return {"status": "BUSY", "output": f"Server {server_name} is busy", "error": "Concurrent execution"}
        
        _active_executions.add(server_name)
        _last_execution_time[server_name] = time.time()
    
    try:
        timeout = timeout or 15
        logger.info(f"🔧 LOCAL: {server_name} -> {command}")
        print(f"\n{'='*60}\n🚀 EXECUTING: {command}\n📍 Server: {server_name}\n{'='*60}")
        
        start_time = time.time()
        
        # Try terminal display (macOS/Linux) - Now using title-based targeting for reliability
        terminal_success = False
        if platform.system().lower() in ["darwin", "linux"] and _terminal_enabled:
            global _terminal_usage_count
            if _try_open_terminal() and _execute_in_terminal(command):
                _terminal_usage_count += 1
                terminal_success = True
                print(f"🖥️  Sent to terminal (session: {_terminal_session_id})")
                await asyncio.sleep(0.5)
            elif not _terminal_enabled:
                print(f"⚠️  Terminal display failed - commands will show in console only")
        
        # Execute in subprocess
        print(f"📺 OUTPUT:\n{'='*40}")
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        execution_time = round(time.time() - start_time, 2)
        output_text = stdout.decode('utf-8').strip()
        error_text = stderr.decode('utf-8').strip()
        status = "SUCCESS" if process.returncode == 0 else "FAILED"
        
        if output_text:
            print(output_text)
        if error_text:
            print(f"⚠️  {error_text}")
        
        print(f"{'='*40}\n✅ Completed in {execution_time}s | Status: {status}")
        if terminal_success:
            print(f"🖥️  Also in terminal")
        print(f"{'='*60}\n")
        
        return {
            "status": status,
            "output": output_text,
            "error": error_text,
            "execution_time": execution_time,
            "command": command,
            "server": server_name
        }
        
    except asyncio.TimeoutError:
        return {"status": "TIMEOUT", "output": f"Timeout after {timeout}s", "error": "Timeout"}
    except Exception as e:
        return {"status": "ERROR", "output": "", "error": str(e)}
    finally:
        async with _execution_lock:
            _active_executions.discard(server_name)

async def check_local_system(server_name: str) -> Dict:
    """Check local system status"""
    result = await execute_local_command(server_name, "echo 'System check successful'")
    return {
        "server": server_name,
        "system_status": "AVAILABLE" if result["status"] == "SUCCESS" else "UNAVAILABLE",
        "details": result
    }

def get_terminal_session_info():
    """Get terminal session information"""
    return {
        "session_id": _terminal_session_id,
        "commands_executed": _terminal_usage_count,
        "is_active": _terminal_session_id is not None
    }

def close_persistent_terminal(reason="Session complete"):
    """Close terminal session"""
    global _terminal_session_id, _terminal_usage_count, _terminal_window_id
    
    if _terminal_session_id:
        print(f"🔒 Closing terminal: {_terminal_session_id} ({_terminal_usage_count} commands)")
        
        if platform.system().lower() == "darwin" and _terminal_window_id:
            try:
                # Close the specific window by custom title
                window_title = _terminal_window_id  # This is the title string
                script = f'''
                tell application "Terminal"
                    repeat with w in windows
                        if custom title of w is "{window_title}" then
                            close w
                            return true
                        end if
                    end repeat
                    return false
                end tell
                '''
                subprocess.run(['osascript', '-e', script], timeout=5, check=False)
            except Exception as e:
                print(f"⚠️  Could not close terminal window: {e}")
        
        _terminal_session_id = None
        _terminal_usage_count = 0
        _terminal_window_id = None

# Create tools
local_execution_tools = [
    FunctionTool(execute_local_command),
    FunctionTool(check_local_system)
]

for tool in local_execution_tools:
    tool.name = tool.func.__name__

__all__ = [
    'local_execution_tools', 'execute_local_command', 'check_local_system', 
    'close_persistent_terminal', 'get_terminal_session_info'
]
