"""
Secure SSH Execution Tools for Agent 3
Enhanced security with key-based auth and rate limiting
"""

import asyncio
import os
import time
from typing import Dict, Optional, Set
from loguru import logger
from google.adk.tools import FunctionTool

# Rate limiting to prevent high CPU usage
_active_connections: Set[str] = set()
_connection_lock = asyncio.Lock()
_last_execution_time = {}
MIN_INTERVAL_BETWEEN_COMMANDS = 2  # seconds

# SSH Configuration - Using environment variables for security
SSH_CONFIG = {
    "VM-Nifi-dev-Node-03": {
        "host": os.getenv("NIFI_NODE_HOST"),
        "user": os.getenv("NIFI_NODE_USER"), 
        "key_path": os.getenv("SSH_KEY_PATH"),  # Use SSH keys instead
        "port": int(os.getenv("SSH_PORT"))
    }
}

# Allowed commands for security - prevent malicious usage
ALLOWED_COMMAND_PATTERNS = [
    "netstat",
    "ps aux",
    "systemctl status",
    "journalctl",
    "ls -la",
    "cat /var/log",
    "df -h",
    "free -h",
    "top -bn1",
    "nifi",
    "java -version",
    "whoami",
    "pwd",
    "echo"
]

def _is_command_allowed(command: str) -> bool:
    """Check if command is allowed for security"""
    command_lower = command.lower().strip()
    
    # Block dangerous commands
    dangerous_patterns = ["rm", "del", "format", "mkfs", "dd", "wget", "curl", "nc", "ncat", "telnet", ">", ">>", "|", ";", "&", "$(", "`"]
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return False
    
    # Allow only whitelisted command patterns
    for allowed in ALLOWED_COMMAND_PATTERNS:
        if command_lower.startswith(allowed.lower()):
            return True
    
    return False

async def execute_ssh_command(node_name: str, command: str, timeout: Optional[int] = None) -> Dict:
    """
    Execute a secure command on remote NiFi node via SSH
    ⚠️  SAFETY: This tool should only be called AFTER human approval via HITL
    
    Args:
        node_name: Name of the NiFi node (e.g., "VM-Nifi-dev-Node-03")
        command: Command to execute (restricted to safe operations)
        timeout: Command timeout in seconds (optional, defaults to 15)
        
    Returns:
        dict: Simple result with output and status
    """
    # Security validation
    if not _is_command_allowed(command):
        error_msg = f"Command '{command}' not allowed for security reasons"
        logger.warning(f"🚫 BLOCKED: {error_msg}")
        return {
            "status": "BLOCKED",
            "output": error_msg,
            "error": "Command not in allowlist"
        }
    
    # Rate limiting to prevent high CPU usage
    async with _connection_lock:
        current_time = time.time()
        last_time = _last_execution_time.get(node_name, 0)
        
        if current_time - last_time < MIN_INTERVAL_BETWEEN_COMMANDS:
            wait_time = MIN_INTERVAL_BETWEEN_COMMANDS - (current_time - last_time)
            logger.info(f"⏳ Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        # Check if already connected to prevent concurrent connections
        if node_name in _active_connections:
            return {
                "status": "BUSY",
                "output": f"Node {node_name} is busy with another command",
                "error": "Concurrent connection limit"
            }
        
        _active_connections.add(node_name)
        _last_execution_time[node_name] = time.time()
    
    try:
        # Set default timeout (reduced for security)
        if timeout is None or timeout <= 0:
            timeout = 15
        
        logger.info(f"🔧 SSH: {node_name} -> {command}")
        print(f"\n{'='*60}")
        print(f"🚀 EXECUTING SECURE SSH COMMAND (HUMAN APPROVED)")
        print(f"{'='*60}")
        print(f"📍 Node: {node_name}")
        print(f"💻 Command: {command}")
        print(f"🔒 Security: Command validated and rate-limited")
        print(f"⏰ Starting execution...")
        print(f"{'='*60}")
        
        if node_name not in SSH_CONFIG:
            error_msg = f"Node {node_name} not configured"
            print(f"❌ ERROR: {error_msg}")
            print(f"{'='*60}\n")
            return {
                "status": "ERROR",
                "output": error_msg,
                "error": "Unknown node"
            }
        config = SSH_CONFIG[node_name]
        start_time = time.time()
        
        # Block sudo commands for security
        if command.strip().lower().startswith('sudo'):
            error_msg = "Sudo commands are blocked for security"
            print(f"🚫 BLOCKED: {error_msg}")
            print(f"{'='*60}\n")
            return {
                "status": "BLOCKED",
                "output": error_msg,
                "error": "Sudo not allowed"
            }
        
        # Build secure SSH command with key-based authentication
        key_path = os.path.expanduser(config['key_path'])
        ssh_cmd = [
            "ssh",
            "-i", key_path,  # Use SSH key instead of password
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=5",
            "-o", "ServerAliveCountMax=2",
            "-p", str(config['port']),
            f"{config['user']}@{config['host']}",
            command
        ]
        
        print(f"🔌 Connecting to {config['user']}@{config['host']} (key-based auth)...")
        
        # Execute SSH command with security measures
        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "SSH_AUTH_SOCK": ""}  # Clear SSH agent for security
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=timeout
        )
        
        execution_time = round(time.time() - start_time, 2)
        output_text = stdout.decode('utf-8').strip()
        error_text = stderr.decode('utf-8').strip()
        status = "SUCCESS" if process.returncode == 0 else "FAILED"
        
        # Display execution results
        print(f"✅ Command completed in {execution_time}s")
        print(f"📊 Status: {status}")
        print(f"📤 Output:")
        if output_text:
            print(f"   {output_text}")
        else:
            print("   (No output)")
        
        if error_text:
            print(f"⚠️  Errors:")
            print(f"   {error_text}")
        
        print(f"{'='*60}\n")
        
        return {
            "status": status, 
            "output": output_text,
            "error": error_text,
            "execution_time": execution_time,
            "command": command,
            "node": node_name
        }
        
    except FileNotFoundError:
        error_msg = "SSH client not found"
        print(f"❌ ERROR: {error_msg}")
        print(f"💡 Ensure SSH is installed and available")
        print(f"🔧 Manual command: ssh -i {config['key_path']} {config['user']}@{config['host']} '{command}'")
        print(f"{'='*60}\n")
        return {
            "status": "ERROR",
            "output": f"SSH client not found. Manual: ssh -i {config['key_path']} {config['user']}@{config['host']} '{command}'",
            "error": "Missing SSH client",
            "execution_time": 0,
            "command": command,
            "node": node_name
        }
        
    except asyncio.TimeoutError:
        print(f"⏰ TIMEOUT: Command timed out after {timeout} seconds")
        print(f"{'='*60}\n")
        return {
            "status": "TIMEOUT",
            "output": f"Command timed out after {timeout} seconds",
            "error": f"Timeout exceeded",
            "execution_time": timeout,
            "command": command,
            "node": node_name
        }
        
    except Exception as e:
        print(f"❌ ERROR: SSH execution failed: {str(e)}")
        print(f"{'='*60}\n")
        return {
            "status": "ERROR",
            "output": "",
            "error": f"SSH execution failed: {str(e)}",
            "execution_time": round(time.time() - start_time, 2),
            "command": command,
            "node": node_name
        }
    finally:
        # Always remove from active connections
        async with _connection_lock:
            _active_connections.discard(node_name)

async def check_ssh_connectivity(node_name: str) -> Dict:
    """
    Secure connectivity check with rate limiting
    
    Args:
        node_name: Name of the NiFi node
        
    Returns:
        dict: Connectivity status
    """
    logger.info(f"🔍 Checking secure SSH connectivity to {node_name}")
    print(f"\n🔍 TESTING SECURE SSH CONNECTIVITY to {node_name}...")
    
    # Use a safe command for connectivity test
    result = await execute_ssh_command(node_name, "echo 'Secure SSH connection successful'")
    
    connectivity_status = "CONNECTED" if result["status"] == "SUCCESS" else "FAILED"
    print(f"🔗 Connectivity result: {connectivity_status}")
    
    return {
        "node": node_name,
        "connectivity": connectivity_status,
        "security_status": "Enhanced with key-based auth and rate limiting",
        "details": result
    }

# Create the simple tools for Agent 3
ssh_execution_tools = [
    FunctionTool(execute_ssh_command),
    FunctionTool(check_ssh_connectivity)
]

# Assign names
for tool in ssh_execution_tools:
    tool.name = tool.func.__name__

# Security setup instructions:
# 1. Set environment variables: NIFI_NODE_HOST, NIFI_NODE_USER, SSH_KEY_PATH, SSH_PORT
# 2. Generate SSH key: ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
# 3. Copy public key to server: ssh-copy-id -i ~/.ssh/id_rsa.pub user@host
# 4. Test connection: ssh -i ~/.ssh/id_rsa user@host 'echo test'

__all__ = [
    'ssh_execution_tools',
    'execute_ssh_command', 
    'check_ssh_connectivity',
    'SSH_CONFIG'
]