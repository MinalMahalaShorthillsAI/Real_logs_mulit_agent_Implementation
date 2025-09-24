"""
Simple SSH Execution Tools for Agent 3
Just connect, execute, and return output - nothing fancy!
"""

import asyncio
import os
import time
from typing import Dict, Optional
from loguru import logger
from google.adk.tools import FunctionTool

# SSH Configuration - Multiple ways to reference the same node
SSH_CONFIG = {
    "VM-Nifi-dev-Node-03": {
        "host": "104.208.162.61",
        "user": "nifi", 
        "password": "123",
        "sudo_password": "123",  # Add sudo password for privilege escalation
        "port": 22
    }
}

async def execute_ssh_command(node_name: str, command: str, timeout: Optional[int] = None) -> Dict:
    """
    Execute a command on remote NiFi node via SSH
    ⚠️  SAFETY: This tool should only be called AFTER human approval via HITL
    
    Args:
        node_name: Name of the NiFi node (e.g., "VM-Nifi-dev-Node-03")
        command: Command to execute
        timeout: Command timeout in seconds (optional, defaults to 30)
        
    Returns:
        dict: Simple result with output and status
    """
    # Set default timeout if not provided
    if timeout is None or timeout <= 0:
        timeout = 30
    logger.info(f"🔧 SSH: {node_name} -> {command}")
    print(f"\n{'='*60}")
    print(f"🚀 EXECUTING SSH COMMAND (HUMAN APPROVED)")
    print(f"{'='*60}")
    print(f"📍 Node: {node_name}")
    print(f"💻 Command: {command}")
    print(f"⚠️  This command was approved by human operator")
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
    
    # Handle sudo commands by providing password via stdin
    if command.strip().startswith('sudo'):
        # For sudo commands, use -S flag and provide password via stdin
        modified_command = command.replace('sudo', f'echo "{config["sudo_password"]}" | sudo -S', 1)
    else:
        modified_command = command
    
    # Build simple SSH command
    ssh_cmd = [
        "sshpass", "-p", config["password"],
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{config['user']}@{config['host']}",
        modified_command
    ]
    
    print(f"🔌 Connecting to {config['user']}@{config['host']}...")
    
    try:
        # Execute SSH command
        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
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
        error_msg = "sshpass not installed"
        print(f"❌ ERROR: {error_msg}")
        print(f"💡 Install with: brew install hudochenkov/sshpass/sshpass")
        print(f"🔧 Manual command: ssh {config['user']}@{config['host']} '{command}'")
        print(f"{'='*60}\n")
        return {
            "status": "ERROR",
            "output": f"sshpass not installed. Manual: ssh {config['user']}@{config['host']} '{command}'",
            "error": "Missing sshpass - install with: brew install hudochenkov/sshpass/sshpass",
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

async def check_ssh_connectivity(node_name: str) -> Dict:
    """
    Simple connectivity check
    
    Args:
        node_name: Name of the NiFi node
        
    Returns:
        dict: Connectivity status
    """
    logger.info(f"🔍 Checking SSH connectivity to {node_name}")
    print(f"\n🔍 TESTING SSH CONNECTIVITY to {node_name}...")
    
    result = await execute_ssh_command(node_name, "echo 'SSH connection successful'")
    
    connectivity_status = "CONNECTED" if result["status"] == "SUCCESS" else "FAILED"
    print(f"🔗 Connectivity result: {connectivity_status}")
    
    return {
        "node": node_name,
        "connectivity": connectivity_status,
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

__all__ = [
    'ssh_execution_tools',
    'execute_ssh_command', 
    'check_ssh_connectivity',
    'SSH_CONFIG'
]