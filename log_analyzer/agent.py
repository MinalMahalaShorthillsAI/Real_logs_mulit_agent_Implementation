"""
Log Analyzer Agent - ADK Entry Point
Uses the properly configured multi-agent system with Agent-as-a-Tool pattern
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import from the main project
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import the properly configured agent from agent_1
# It now has both nifi_agent_tool and remediation_agent_tool using Agent-as-a-Tool pattern
from agent_1 import root_agent

# Export for ADK
app = root_agent
