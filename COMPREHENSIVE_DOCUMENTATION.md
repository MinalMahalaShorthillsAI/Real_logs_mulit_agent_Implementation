# 🤖 Multi-Agent Log Analysis System - Complete Documentation

> **Enterprise-grade AI-powered log analysis with automated remediation and human-in-the-loop decision making**

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Design Patterns](#architecture--design-patterns)
3. [Complete System Flow](#complete-system-flow)
4. [Agent Details](#agent-details)
5. [Tools & Capabilities](#tools--capabilities)
6. [API Reference](#api-reference)
7. [Dashboard Interface](#dashboard-interface)
8. [Setup & Configuration](#setup--configuration)
9. [Usage Examples](#usage-examples)
10. [Security & Compliance](#security--compliance)

---

## 🎯 System Overview

### What Does This System Do?

This is an **AI-powered multi-agent log analysis system** that:
- **Analyzes** application logs in real-time
- **Correlates** errors with infrastructure (NiFi) logs
- **Detects** anomalies automatically
- **Plans** remediation actions with AI
- **Executes** fixes with human approval (HITL - Human-in-the-Loop)

### Key Features

- **Three Specialized AI Agents** working together
- **Real-time log streaming** and analysis
- **Automatic NiFi correlation** for infrastructure errors
- **Human-in-the-loop approval** for safe remediation
- **RESTful API** for integration
- **Streamlit Dashboard** for monitoring and approvals
- **Enterprise security** with command whitelisting and rate limiting
- **Powered by Google Gemini 2.5** LLM

---

## 🏗️ Architecture & Design Patterns

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
├─────────────────┬───────────────────────────────────────────┤
│  CLI Interface  │  Streamlit Dashboard  │  REST API         │
└────────┬────────┴───────────┬───────────┴───────┬───────────┘
         │                    │                   │
         └────────────────────┼───────────────────┘
                              │
         ┌────────────────────▼─────────────────────┐
         │       FastAPI Application Layer          │
         │        (main.py - Orchestration)         │
         └────────────────────┬─────────────────────┘
                              │
         ┌────────────────────▼─────────────────────┐
         │      MULTI-AGENT SYSTEM (ADK)            │
         ├──────────────────────────────────────────┤
         │                                          │
         │  ┌─────────────────────────────────────┐ │
         │  │   AGENT 1: Analyser Agent           │ │
         │  │   (Main Log Analysis)               │ │
         │  │   Model: gemini-2.5-flash           │ │
         │  └───────┬──────────────────┬──────────┘ │
         │          │                  │            │
         │          │ (Tool)           │ (Sub-Agent)│
         │          ▼                  ▼            │
         │  ┌──────────────┐   ┌─────────────────┐  │
         │  │   AGENT 2:   │   │   AGENT 3:      │  │
         │  │  NiFi Agent  │   │ Remediation     │  │
         │  │  (As Tool)   │   │ Agent (HITL)    │  │
         │  │              │   │                 │  │
         │  │ gemini-2.5   │   │ gemini-2.5-pro  │  │
         │  │  -flash      │   │                 │  │
         │  └──────┬───────┘   └────────┬────────┘  │
         │         │                    │           │
         └─────────┼────────────────────┼───────────┘
                   │                    │
         ┌─────────▼────────┐  ┌────────▼─────────┐
         │   NiFi Logs      │  │  Local System    │
         │  (log_tool.py)   │  │  Execution       │
         └──────────────────┘  │ (SSH/Commands)   │
                               └──────────────────┘
```

### Design Patterns Used

#### 1. **Agent-as-a-Tool Pattern** 🔧
- **NiFi Agent (Agent 2)** serves as a callable tool for the main analyzer
- Enables specialist agents to be reused across multiple parent agents
- Provides session isolation

```python
# Implementation
nifi_agent = LlmAgent(...)  # Create specialist agent
nifi_tool = AgentTool(agent=nifi_agent)  # Wrap as tool
main_agent = LlmAgent(tools=[nifi_tool])  # Register with main agent
```

#### 2. **Sub-Agent Delegation Pattern** 🔀
- **Remediation Agent (Agent 3)** automatically activates for anomalies
- Triggered when: `ERROR` log + `ANOMALY` classification
- Maintains context and session state

```python
main_agent = LlmAgent(
    sub_agents=[remediation_agent]  # Automatic delegation
)
```

#### 3. **Human-in-the-Loop (HITL) Pattern** 👤
- Critical commands require human approval
- In-memory request/response system
- Feedback loop for plan modifications

---

## 🔄 Complete System Flow

### Main Processing Flow

```
START: Log File Processing
│
├─> [1] Log File Streaming
│   │
│   ├─> Read logs line-by-line from a log file (stream_logs_by_timestamp)
│   └─> Group multi-line logs (stack traces) together
│
├─> [2] Agent 1: Analysis
│   │
│   ├─> Receive single log entry
│   │
│   ├─> [2.1] Call NiFi Agent Tool
│   │   │
│   │   ├─> Extract timestamp from log (HH:MM:SS)
│   │   ├─> Agent 2 searches NiFi logs
│   │   ├─> Returns correlation data
│   │   └─> Agent 1 receives NiFi context
│   │
│   ├─> [2.2] Generate Analysis (JSON)
│   │   │
│   │   └─> {
│   │         "classification": "NORMAL" | "ANOMALY",
│   │         "severity": "LOW|MEDIUM|HIGH|CRITICAL",
│   │         "likely_cause": "...",
│   │         "nifi_correlation": "...",
│   │         "recommendation": "..."
│   │       }
│   │
│   └─> [2.3] Check Remediation Trigger
│       │
│       ├─> Condition 1: Log contains " ERROR "?
│       ├─> Condition 2: Classification = "ANOMALY"?
│       │
│       └─> IF BOTH TRUE ──> [3] Trigger Remediation Sub-Agent
│
├─> [3] Agent 3: Remediation (HITL)
│   │
│   ├─> [3.1] Receive Analysis Report
│   │
│   ├─> [3.2] Create Remediation Plan
│   │   │
│   │   └─> PLAN FORMAT:
│   │       ├─> UNDERSTANDING: Issue summary
│   │       ├─> PLAN: Specific command/approach
│   │       ├─> RISK: Risk assessment
│   │       └─> CONFIDENCE: Score (0.0-1.0)
│   │
│   ├─> [3.3] MANDATORY: Call HITL Approval Tool
│   │   │
│   │   ├─> Store plan in memory (_approval_requests)
│   │   ├─> Display to terminal/dashboard
│   │   ├─> Poll every 5s for approval
│   │   │
│   │   └─> Wait for Human Decision:
│   │       ├─> APPROVED ──> [3.4]
│   │       ├─> REJECTED ──> Create Alternative Plan ──> [3.3]
│   │       └─> FEEDBACK ──> Modify Plan ──> [3.3]
│   │
│   ├─> [3.4] Execute Command
│   │   │
│   │   ├─> Call execute_local_command tool
│   │   ├─> Run command on NiFi server
│   │   ├─> Capture output/errors
│   │   └─> Display in terminal window
│   │
│   ├─> [3.5] Analyze Results
│   │   │
│   │   ├─> Parse command output
│   │   ├─> Determine if issue resolved
│   │   │
│   │   └─> Decision:
│   │       ├─> RESOLVED ──> [3.6] Verify & Test
│   │       └─> NOT RESOLVED ──> [3.2] New Plan
│   │
│   ├─> [3.6] Test Resolution
│   │   │
│   │   ├─> Re-test the original error scenario
│   │   └─> Confirm fix is working
│   │
│   └─> [3.7] Report to Human
│       │
│       └─> "Issue fully resolved and tested successfully"
│
├─> [4] Save Interaction
│   │
│   └─> agent_outputs/complete_log_XXXXX.json
│       ├─> Original log entry
│       ├─> Analysis from Agent 1
│       ├─> NiFi correlation data
│       └─> Remediation actions (if any)
│
└─> [5] Next Log Entry
    │
    └─> LOOP back to [2] until all logs processed
```

### Detailed Agent Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOG ENTRY ARRIVES                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │      AGENT 1: ANALYSER            │
        │   (Main Orchestrator)             │
        └───────────┬───────────────────────┘
                    │
                    │ Step 1: Extract timestamp
                    │ Step 2: Call NiFi Tool
                    │
                    ▼
        ┌─────────────────────────────────────┐
        │   TOOL CALL: nifi_agent_tool        │
        │   (Agent 2 wrapped as tool)         │
        └───────────┬─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────────────────┐
        │      AGENT 2: NiFi SPECIALIST       │
        │   (Correlation Analysis)            │
        ├─────────────────────────────────────┤
        │ 1. Receives: app error + timestamp  │
        │ 2. Calls: search_nifi_logs_tool     │
        │ 3. Searches: NiFi logs   │
        │ 4. Analyzes: Correlation patterns   │
        │ 5. Returns: JSON correlation data   │
        └───────────┬─────────────────────────┘
                    │
                    │ NiFi Correlation Data
                    │
                    ▼
        ┌─────────────────────────────────────┐
        │      AGENT 1: ANALYSER              │
        │   (Receives NiFi data)              │
        ├─────────────────────────────────────┤
        │ 1. Combines: App error + NiFi data  │
        │ 2. Classifies: NORMAL or ANOMALY    │
        │ 3. Determines: Severity level       │
        │ 4. Generates: JSON analysis         │
        └───────────┬─────────────────────────┘
                    │
                    │ Check Trigger Conditions
                    │
                    ▼
        ┌─────────────────────────────────────┐
        │   CONDITION CHECK:                  │
        │   ✓ Contains " ERROR "?             │
        │   ✓ Classification = "ANOMALY"?     │
        └───────┬─────────────┬───────────────┘
                │             │
         NO ────┘             └──── YES
         │                          │
         ▼                          ▼
    ┌────────┐          ┌────────────────────────┐
    │ Done   │          │  SUB-AGENT DELEGATION  │
    │ Save   │          │  AGENT 3: REMEDIATION  │
    └────────┘          └──────────┬─────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   AGENT 3: REMEDIATION       │
                    │   (Human-Interactive)        │
                    ├──────────────────────────────┤
                    │ 1. Analyze error report      │
                    │ 2. Create remediation plan   │
                    │ 3. HITL: Request approval    │
                    │ 4. Execute when approved     │
                    │ 5. Analyze results           │
                    │ 6. Loop until resolved       │
                    │ 7. Test resolution           │
                    │ 8. Report success            │
                    └──────────────────────────────┘
```

---

## 🤖 Agent Details

### Agent 1: Analyser Agent (Main Orchestrator)

**File**: `agent_1.py`

**Role**: Main log analysis agent that orchestrates the entire workflow

**Model**: `gemini-2.5-flash` (Fast, efficient for log analysis)

**Temperature**: `0.1` (Deterministic with slight creativity)

**Key Responsibilities**:
1. Receive and process log entries
2. Call NiFi Agent Tool
3. Perform root cause analysis
4. Classify logs as NORMAL or ANOMALY
5. Determine severity levels
6. Trigger remediation sub-agent when needed

**Tools Available**:
- `nifi_agent_tool` - Correlate with NiFi infrastructure logs

**Sub-Agents**:
- `remediation_agent` - Automatic delegation for ERROR + ANOMALY

**Output Format** (JSON):
```json
{
  "application": "Application name",
  "classification": "NORMAL | ANOMALY",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "component": "Component that failed",
  "likely_cause": "Root cause analysis",
  "nifi_correlation": "Actual data from NiFi Agent",
  "recommendation": "Action plan"
}
```

**Triggering Logic**:
```python
if " ERROR " in log_entry and classification == "ANOMALY":
    # MANDATORY: Engage remediation sub-agent
    delegate_to_remediation_agent()
```

**Session Management**:
- Creates InMemoryRunner session for context

---

### Agent 2: NiFi Agent (Specialist Tool)

**File**: `agent_2.py`

**Role**: NiFi infrastructure log correlation specialist (used as a tool)

**Model**: `gemini-2.5-flash` (Fast correlation analysis)

**Temperature**: `0.1` (Consistent correlations)

**Key Responsibilities**:
1. Search NiFi logs by timestamp
2. Find logs of application error
3. Analyze infrastructure-level issues
4. Correlate NiFi problems with application errors
5. Return structured correlation data

**Tools Available**:
- `search_nifi_logs_tool` - Direct access to NiFi app log file

**How It's Used**:
```python
# Agent 1 calls Agent 2 as a tool
nifi_agent_tool = AgentTool(agent=nifi_agent, skip_summarization=False)
main_agent = LlmAgent(tools=[nifi_agent_tool])
```

**Output Format** (JSON):
```json
{
  "correlation_found": true/false,
  "nifi_issue_summary": "Description of NiFi issue",
  "likely_nifi_cause": "Root cause in NiFi",
  "correlation_details": "How NiFi issue caused app error",
  "nifi_logs_analyzed": ["actual log entries"],
  "timestamp_searched": "HH:MM:SS",
  "recommendation": "Steps to fix NiFi issue"
}
```

**Search Algorithm**:
1. Parse timestamp from application error
2. Extract date from first line of NiFi log
3. Search logs
4. Return top 10 relevant entries
5. Analyze correlation patterns

---

### Agent 3: Remediation Agent (HITL Specialist)

**File**: `agent_3.py`

**Role**: Human-interactive remediation planning and execution

**Model**: `gemini-2.5-pro` (Most capable for complex troubleshooting)

**Temperature**: `0.1` (Consistent remediation plans)

**Key Responsibilities**:
1. Receive error analysis from Agent 1
2. Create remediation plans with confidence scores
3. **MANDATORY**: Get human approval before execution
4. Execute approved commands locally
5. Analyze execution results
6. Create follow-up plans if needed
7. Test resolution thoroughly
8. Report success to human

**Tools Available**:
- `human_remediation_approval_tool` - HITL approval system
- `execute_local_command` - Run commands on NiFi server
- `check_local_system` - Test system availability

**Workflow Pattern**:
```
PLAN → GET APPROVAL → EXECUTE → ANALYZE → REPEAT
```

**Confidence Scoring**:
- `0.9-1.0`: HIGH - Well-known error, proven solution
- `0.7-0.8`: MEDIUM-HIGH - Standard approach
- `0.5-0.6`: MEDIUM - Experimental solution
- `0.3-0.4`: LOW - Uncertain approach
- `0.0-0.2`: VERY LOW - Last resort

**Approval Responses**:
- `APPROVED` → Execute immediately
- `REJECTED` → Create **completely different** alternative
- `REJECTED_WITH_FEEDBACK` → Modify plan based on human input

**Safety Features**:
- No `sudo` commands allowed
- Rate limiting (2s between commands)
- Command whitelisting for safe operations
- Each command requires separate approval
- Terminal window for visual feedback

**Allowed Commands** (Skip approval):
```python
["ls", "pwd", "find", "cat", "ps", "netstat", "lsof", 
 "whoami", "tail", "head", "grep", "df", "systemctl", "java"]
```
---

## 🛠️ Tools & Capabilities

### 1. NiFi Log Search Tool

**File**: `tools/log_tool.py`

**Function**: `search_nifi_logs_by_timestamp(timestamp: str)`

**Purpose**: Search NiFi infrastructure logs for correlation

**How It Works**:
```python
# 1. Find NiFi log file
nifi_file = "logs/nifi_app/nifi-app.log"

# 2. Parse target timestamp
target_dt = datetime.strptime(f"{date} {timestamp}", "%Y-%m-%d %H:%M:%S")
```

**Returns**:
```json
{
  "status": "success",
  "timestamp_searched": "16:20:41",
  "nifi_logs_found": 5,
  "nifi_infrastructure_logs": ["Correlation analysis"],
  "correlation_ready": true
}
```

---

### 2. Human Remediation Approval Tool (HITL)

**File**: `tools/remediation_hitl_tool.py`

**Function**: `human_remediation_approval_tool(plan_text: str)`

**Purpose**: Get human approval for remediation plans

**Architecture**: In-memory request/response system

**Flow**:
```
1. Agent creates plan
2. Tool generates unique request_id
3. Store in _approval_requests{} dictionary
4. Display to terminal/dashboard
5. Poll every 5 seconds for status
6. Timeout after 5 minutes
7. Return approval status to agent
```

**In-Memory Storage**:
```python
_approval_requests = {
    "abc123": {
        "plan": "Remediation plan text",
        "status": "pending",  # or "approved" or "rejected"
        "created_at": 1234567890,
        "feedback": "Optional human feedback"
    }
}
```

**API Integration**:
- `POST /approve/{request_id}` - Approve a plan
- `POST /reject/{request_id}` - Reject a plan
- `POST /feedback/{request_id}` - Send feedback
- `GET /approvals/pending` - List pending approvals

**Return Values**:
- `"APPROVED"` - Human approved, execute now
- `"REJECTED"` - Human rejected, create alternative
- `"REJECTED_WITH_FEEDBACK: {feedback}"` - Human wants modifications

---

### 3. Local Command Execution Tools

**File**: `tools/local_command_tools.py`

**Functions**:
1. `execute_local_command(server_name, command, timeout)`
2. `check_local_system(server_name)`

**Purpose**: Secure local command execution with terminal display

**Security Features**:

1. **Sudo Blocking**:
```python
if command.startswith('sudo'):
    return {"status": "BLOCKED", "error": "Sudo not allowed"}
```

2. **Rate Limiting**:
```python
MIN_INTERVAL_BETWEEN_COMMANDS = 2  # seconds
# Enforces 2-second gap between commands
```

3. **Concurrent Execution Control**:
```python
_active_executions: Set[str] = set()
# Only one command per server at a time
```

**Terminal Display** (macOS/Linux):
- Opens a dedicated terminal window
- All commands executed visibly
- Tracks session with unique ID
- Auto-closes when done

**Execution Flow**:
```
1. Validate command (no sudo)
2. Check rate limit (2s gap)
3. Check concurrent execution
4. Open terminal window (if first command)
5. Display command in terminal
6. Execute via subprocess
7. Capture stdout/stderr
8. Return structured result
```

**Return Format**:
```json
{
  "status": "SUCCESS | FAILED | TIMEOUT | ERROR",
  "output": "stdout text",
  "error": "stderr text",
  "command": "executed command",
  "server": "server_name"
}
```

---

## 🌐 API Reference

### FastAPI Application

**File**: `main.py`

**Base URL**: `http://localhost:8000` (configurable via .env)

---

### Endpoints

#### 1. Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "agents": ["analyser_agent", "nifi_agent", "remediation_agent"],
  "timestamp": "2025-10-09T16:20:41.123456"
}
```

---

#### 2. Start Background Analysis

```http
POST /start-analysis
Content-Type: application/json

{
  "file_path": "/path/to/log/file.log"
}
```

**Purpose**: Start log analysis in background (non-blocking)

**Response**:
```json
{
  "status": "started",
  "message": "Analysis started for /path/to/log/file.log",
  "file_path": "/path/to/log/file.log",
  "note": "Check FastAPI terminal for progress. Approval requests will appear in the dashboard."
}
```

---

#### 3. Get Analysis Status

```http
GET /analysis-status
```

**Purpose**: Real-time status updates for dashboard

**Response**:
```json
{
  "is_running": true,
  "logs_processed": 42,
  "current_activity": "Analyzing log entry",
  "current_log": "2025-10-09 16:20:41 ERROR ...",
  "agent_events": [
    {
      "type": "processing",
      "message": "Analyzing log #42",
      "time": "16:20:45"
    },
    {
      "type": "tool_call",
      "message": "🔧 Tool call: nifi_agent_tool",
      "time": "16:20:46"
    }
  ]
}
```

**Updates**: 
- Logs processed count
- Current log being analyzed
- Recent agent events (last 30)
- Current activity status

---

#### 4. Stream File Analysis

```http
POST /stream/analyze-file
Content-Type: application/json

{
  "file_path": "/path/to/log/file.log"
}
```

**Purpose**: Real-time streaming analysis (SSE - Server-Sent Events)

**Response**: Stream of JSON events

```
data: {"status": "starting", "message": "Starting processing..."}

data: {"status": "processing", "log_number": 1, "log_preview": "..."}

data: {"status": "tool_call", "tool": "nifi_agent_tool"}

data: {"status": "response", "response_number": 1}

data: {"status": "completed", "total_logs": 100}
```

**Event Types**:
- `starting` - Analysis initiated
- `session_created` - Session ID generated
- `processing` - Processing log entry
- `agent_call` - Calling multi-agent system
- `tool_call` - Tool being called
- `tool_response` - Tool response received
- `response` - Agent response received
- `error` - Error occurred
- `completed` - Analysis finished

---

#### 5. Stop Stream

```http
POST /stop-stream/{stream_id}
```

**Purpose**: Gracefully stop active streaming session

**Response**:
```json
{
  "status": "stopping",
  "stream_id": "stream_abc123",
  "message": "Stream stop signal sent"
}
```

---

#### 6. List Pending Approvals

```http
GET /approvals/pending
```

**Purpose**: Get all pending HITL approval requests

**Response**:
```json
{
  "pending_approvals": {
    "req_abc123": {
      "plan": "UNDERSTANDING: ...\nPLAN: ...\nRISK: ...\nCONFIDENCE: 0.85",
      "status": "pending",
      "created_at": 1234567890
    }
  },
  "count": 1,
  "timestamp": "2025-10-09T16:20:41.123456"
}
```

---

#### 7. Approve Remediation Plan

```http
POST /approve/{request_id}
```

**Purpose**: Approve a pending remediation plan

**Response**:
```json
{
  "status": "success",
  "message": "Request req_abc123 approved",
  "timestamp": "2025-10-09T16:20:41.123456"
}
```

**Effect**: Agent 3 receives "APPROVED" and executes the plan

---

#### 8. Reject Remediation Plan

```http
POST /reject/{request_id}
```

**Purpose**: Reject a pending remediation plan

**Response**:
```json
{
  "status": "success",
  "message": "Request req_abc123 rejected",
  "timestamp": "2025-10-09T16:20:41.123456"
}
```

**Effect**: Agent 3 creates a completely different alternative plan

---

#### 9. Send Feedback

```http
POST /feedback/{request_id}?feedback=Use+df+-h+instead
```

**Purpose**: Send modification suggestions to agent

**Response**:
```json
{
  "status": "success",
  "message": "Feedback sent for request req_abc123",
  "feedback": "Use df -h instead",
  "action": "Agent will modify the plan based on your feedback",
  "timestamp": "2025-10-09T16:20:41.123456"
}
```

**Effect**: Agent 3 receives feedback and modifies the plan

---

## 📊 Dashboard Interface

### Unified Streamlit Dashboard

**File**: `unified_dashboard.py`

**Launch**: 
```bash
streamlit run unified_dashboard.py
```

**URL**: `http://localhost:8501`

---

## 🚀 Setup & Configuration

### Prerequisites

```bash
Python 3.13+
macOS / Linux (for terminal display feature)
NiFi 2.6.0 (optional, for actual NiFi integration)
```

### Installation Steps

#### 1. Clone Repository
```bash
cd Real_logs_mulit_agent_Implementation
```

#### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Required Packages**:
```
google-adk>=0.1.0           # Google Agent Development Kit
google-generativeai>=0.8.0  # Gemini API
python-dotenv>=1.0.0        # Environment variables
loguru>=0.7.0               # Logging
fastapi>=0.104.0            # REST API
uvicorn[standard]>=0.24.0   # ASGI server
streamlit>=1.28.0           # Dashboard
requests>=2.31.0            # HTTP client
```

---

### Environment Configuration

#### Create `.env` file:

```bash
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key_here

# FastAPI Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
PUBLIC_HOST=localhost  # or your server IP/hostname

# Streamlit Configuration
API_BASE_URL=http://localhost:8000
```

#### Get Gemini API Key:
1. Go to: https://makersuite.google.com/app/apikey
2. Create new API key
3. Copy to `.env` file

---

### Project Structure

```
Real_logs_mulit_agent_Implementation/
│
├── agent_1.py              # Main Analyser Agent
├── agent_2.py              # NiFi Correlation Agent
├── agent_3.py              # Remediation Agent (HITL)
├── main.py                 # FastAPI Application
├── unified_dashboard.py    # Streamlit Dashboard
│
├── prompts/
│   ├── analyser_prompt.py          # Agent 1 instructions
│   ├── nifi_agent_prompt.py        # Agent 2 instructions
│   └── remediation_agent_prompt.py # Agent 3 instructions
│
├── tools/
│   ├── log_tool.py                 # NiFi log search
│   ├── remediation_hitl_tool.py    # HITL approval
│   └── local_command_tools.py      # Command execution
│
├── log_analyzer/
│   └── agent.py            # ADK entry point
│
├── logs/
│   ├── HR_logs (1).log     # Sample application logs
│   └── nifi_app/
│       └── nifi-app.log    # Sample NiFi logs
│
├── agent_logs/             # Agent session logs (auto-generated)
├── agent_outputs/          # Analysis outputs (auto-generated)
│
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (create this)
```

---

## 📖 Usage Examples

### Example 1: Analyze Single Log File (CLI)

```bash
# Edit agent_1.py to set your log file path
# Line 282-283:
log_folder_path = "/path/to/your/logs"

# Run
python agent_1.py
```

**Process**:
1. Streams logs one by one
2. Each log analyzed by Agent 1
3. NiFi correlation performed automatically
4. ERROR + ANOMALY triggers remediation
5. Approvals appear in terminal
6. Results saved to `agent_outputs/`

---

### Example 2: Analyze via Dashboard

1. **Start Services**:
   ```bash
   # Terminal 1
   python main.py
   
   # Terminal 2
   streamlit run unified_dashboard.py
   ```

2. **Open Dashboard**: http://localhost:8501

3. **Start Analysis**:
   - Tab: "🚀 Trigger Analysis"
   - Select file: `logs/HR_logs (1).log`
   - Click: "🚀 Start Stream Analysis"

4. **Monitor Progress**:
   - Watch "📊 Analysis Status" panel
   - Real-time logs processed count
   - Current log being analyzed
   - Agent activity stream

5. **Handle Approvals**:
   - Tab: "✅ Approve Plans"
   - Click "🔄 Refresh Now"
   - Review remediation plan
   - Click "✅ Approve" or "❌ Reject"

6. **Check Results**:
   - Files saved in `agent_outputs/`
   - Terminal shows execution details