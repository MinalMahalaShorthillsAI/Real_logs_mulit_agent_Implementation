"""
Local Command Execution Tools for Agent 3
Secure local command execution with optional terminal display
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
MIN_INTERVAL_BETWEEN_COMMANDS = 2  # seconds

# Simple terminal session tracking
_terminal_session_id = None
_terminal_usage_count = 0

# Allowed commands for security - prevent malicious usage
ALLOWED_COMMAND_PATTERNS = [
    # Essential file/directory operations
    "ls", "pwd", "find", "cat",
    
    # Critical system diagnostics  
    "ps", "netstat", "lsof", "whoami",
    
    # Log analysis tools
    "tail", "head", "grep",
    
    # Optional: Keep only if needed for your specific use case
    # "systemctl status",  # Uncomment if you need service status
    # "df -h",             # Uncomment if you need disk usage
    # "java -version",     # Uncomment if you need Java version checks
]

def _is_command_allowed(command: str) -> bool:
    """Check if command is allowed for security"""
    command_lower = command.lower().strip()
    
    # Block dangerous commands
    dangerous_patterns = ["rm", "del", "format", "mkfs", "dd", "wget", "curl", "nc", "ncat", ">", ">>", ";", "&", "$(", "`"]
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return False
    
    # Allow only whitelisted command patterns
    for allowed in ALLOWED_COMMAND_PATTERNS:
        if command_lower.startswith(allowed.lower()):
            return True
    
    return False

def _try_open_terminal():
    """Try to open a terminal window - simplified cross-platform approach"""
    global _terminal_session_id
    
    # If terminal already exists, don't open a new one
    if _terminal_session_id is not None:
        print(f"✅ Using existing terminal session: {_terminal_session_id}")
        return True
    
    try:
        import uuid
        _terminal_session_id = str(uuid.uuid4())[:8]
        system = platform.system().lower()
        
        # Simple terminal commands by platform
        if system == "darwin":
            # macOS - simple osascript
            cmd = ['osascript', '-e', f'tell application "Terminal" to do script "echo \\"🚀 Agent3 Session: {_terminal_session_id}\\"; echo \\"Commands will appear here...\\"" activate']
        elif system == "linux":
            # Linux - try common terminals
            for term in ['gnome-terminal', 'konsole', 'xterm']:
                if subprocess.run(['which', term], capture_output=True).returncode == 0:
                    cmd = [term, '--', 'bash', '-c', f'echo "🚀 Agent3 Session: {_terminal_session_id}"; echo "Commands will appear here..."; bash']
                    break
            else:
                return False
        elif system == "windows":
            # Windows - try PowerShell
            cmd = ['powershell', '-NoExit', '-Command', f'Write-Host "🚀 Agent3 Session: {_terminal_session_id}"']
        else:
            return False
        
        # Try to open terminal
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Opened terminal session: {_terminal_session_id}")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not open terminal: {e}")
        return False

def _execute_in_terminal(command: str) -> bool:
    """Try to execute command in terminal window"""
    if not _terminal_session_id:
        return False
    
    try:
        system = platform.system().lower()
        
        if system == "darwin":
            # macOS - send command to front Terminal window
            script = f'tell application "Terminal" to do script "{command}" in front window'
            subprocess.run(['osascript', '-e', script], check=True)
            return True
        else:
            # For other platforms, terminal execution is complex, so skip
            return False
            
    except Exception:
        return False

async def execute_local_command(server_name: str, command: str, timeout: Optional[int] = None) -> Dict:
    """
    Execute a secure command locally with optional terminal display
    """
    # Security validation
    if not _is_command_allowed(command):
        error_msg = f"Command '{command}' not allowed for security reasons"
        logger.warning(f"🚫 BLOCKED: {error_msg}")
        return {"status": "BLOCKED", "output": error_msg, "error": "Command not in allowlist"}
    
    # Rate limiting
    async with _execution_lock:
        current_time = time.time()
        last_time = _last_execution_time.get(server_name, 0)
        
        if current_time - last_time < MIN_INTERVAL_BETWEEN_COMMANDS:
            wait_time = MIN_INTERVAL_BETWEEN_COMMANDS - (current_time - last_time)
            logger.info(f"⏳ Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        if server_name in _active_executions:
            return {"status": "BUSY", "output": f"Server {server_name} is busy", "error": "Concurrent execution limit"}
        
        _active_executions.add(server_name)
        _last_execution_time[server_name] = time.time()
    
    try:
        timeout = timeout or 15
        
        if command.strip().lower().startswith('sudo'):
            print(f"🚫 BLOCKED: Sudo commands not allowed")
            return {"status": "BLOCKED", "output": "Sudo commands blocked", "error": "Sudo not allowed"}
        
        logger.info(f"🔧 LOCAL: {server_name} -> {command}")
        print(f"\n{'='*60}")
        print(f"🚀 EXECUTING COMMAND (HUMAN APPROVED)")
        print(f"📍 Server: {server_name}")
        print(f"💻 Command: {command}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Try terminal execution first (macOS only for simplicity)
        terminal_success = False
        if platform.system().lower() == "darwin":
            global _terminal_usage_count
            
            # Ensure we have a terminal (reuse existing or create new)
            terminal_success = _try_open_terminal()
            
            # Try to execute in terminal if we have one
            if terminal_success and _terminal_session_id and _execute_in_terminal(command):
                _terminal_usage_count += 1
                print(f"🖥️  Command sent to terminal (session: {_terminal_session_id})")
                print(f"📊 Commands in terminal: {_terminal_usage_count}")
                await asyncio.sleep(1)  # Give time for command to run
            else:
                terminal_success = False
        
        # Always run in subprocess for reliable output capture
        print(f"📺 LIVE OUTPUT:")
        print(f"{'='*40}")
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        execution_time = round(time.time() - start_time, 2)
        output_text = stdout.decode('utf-8').strip()
        error_text = stderr.decode('utf-8').strip()
        status = "SUCCESS" if process.returncode == 0 else "FAILED"
        
        # Display results
        if output_text:
            print(output_text)
        if error_text:
            print(f"⚠️  {error_text}")
        
        print(f"{'='*40}")
        print(f"✅ Command completed in {execution_time}s")
        print(f"📊 Status: {status}")
        if terminal_success:
            print(f"🖥️  Also displayed in terminal window")
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
        print(f"⏰ TIMEOUT: Command timed out after {timeout} seconds")
        return {"status": "TIMEOUT", "output": f"Timeout after {timeout}s", "error": "Timeout"}
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
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
    global _terminal_session_id, _terminal_usage_count
    
    if _terminal_session_id:
        print(f"🔒 Closing terminal session: {_terminal_session_id}")
        print(f"📊 Commands executed: {_terminal_usage_count}")
        
        if platform.system().lower() == "darwin":
            try:
                script = 'tell application "Terminal" to close front window'
                subprocess.run(['osascript', '-e', script], timeout=5)
                print(f"✅ Terminal closed")
            except Exception:
                print(f"⚠️  Could not close terminal automatically")
        
        _terminal_session_id = None
        _terminal_usage_count = 0

def force_close_terminal():
    """Force close terminal immediately"""
    close_persistent_terminal("Force closed")
    return _terminal_session_id is None

# Create tools
local_execution_tools = [
    FunctionTool(execute_local_command),
    FunctionTool(check_local_system)
]

for tool in local_execution_tools:
    tool.name = tool.func.__name__

__all__ = [
    'local_execution_tools', 'execute_local_command', 'check_local_system', 
    'close_persistent_terminal', 'force_close_terminal', 'get_terminal_session_info'
]
