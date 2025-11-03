# 🤖 Multi-Agent Log Analysis System - Complete Documentation

> **Enterprise-grade AI-powered log analysis with automated remediation and human-in-the-loop decision making**

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [System Operating Modes](#system-operating-modes)
3. [Architecture & Design Patterns](#architecture--design-patterns)
4. [Complete System Flow](#complete-system-flow)
5. [Agent Details](#agent-details)
6. [Tools & Capabilities](#tools--capabilities)
7. [API Reference](#api-reference)
8. [Dashboard Interface](#dashboard-interface)
9. [Setup & Configuration](#setup--configuration)
10. [Usage Examples](#usage-examples)
11. [NiFi-Specific Configuration](#nifi-specific-configuration)
12. [Security & Compliance](#security--compliance)
13. [Summary](#summary)

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
- **Automatic NiFi correlation** for infrastructure errors (when available)
- **Standalone mode** for projects without infrastructure logs
- **Flexible operation modes** for testing and production
- **Human-in-the-loop approval** for safe remediation
- **RESTful API** for integration
- **Streamlit Dashboard** for monitoring and approvals
- **Enterprise security** with command whitelisting and rate limiting
- **Session memory** for context-aware analysis across multiple logs
- **Powered by Google Gemini 2.5** LLM

---

## 🔧 System Operating Modes

The system supports flexible operating modes for different deployment scenarios and testing needs:

### Agent 1 (Analyser) Modes

**1. WITH NiFi Correlation Mode**
- Activated when: `logs/nifi_app/nifi-app.log` exists AND Agent 2 loads successfully
- Behavior: Calls `nifi_agent_tool` to correlate application errors with infrastructure logs
- Use case: Production deployments with NiFi infrastructure
- Output: Analysis includes actual NiFi correlation data

**2. STANDALONE Mode**
- Activated when: NiFi logs unavailable or Agent 2 fails to load
- Behavior: Pure application log analysis without infrastructure correlation
- Use case: Non-NiFi applications or testing without infrastructure logs
- Output: Analysis with `"infrastructure_correlation": "N/A - No correlation source configured"`

**Mode Detection**: Automatic - no configuration needed. Agent 1 detects availability at startup.

### Agent 3 (Remediation) Modes

**1. TEST MODE** (Default)
- Activated when: `AGENT3_TEST_MODE=True` in .env (default)
- Behavior: Quick acknowledgment and immediate exit
- Use case: **Testing Agent 1's delegation logic** without full remediation overhead
- Response: "✓ Remediation agent received delegation for [issue]. Test mode - exiting."
- Tools: None
- Duration: <1 second

**2. PRODUCTION MODE**
- Activated when: `AGENT3_TEST_MODE=False` in .env
- Behavior: Full HITL remediation workflow
- Use case: **Production deployments** requiring actual error resolution
- Response: Complete remediation cycle with human approval
- Tools: Human approval tool + local command execution tools
- Duration: Until issue resolved and tested

**Configuration**: Set `AGENT3_TEST_MODE` environment variable in `.env` file

### Recommended Testing Workflow

**Phase 1: Agent 1 Testing** (AGENT3_TEST_MODE=True)
```bash
# .env configuration
AGENT3_TEST_MODE=True
```
- Validate log parsing and streaming
- Test Agent 1's analysis accuracy
- Verify remediation trigger conditions (ERROR + ANOMALY)
- Confirm Agent 3 delegation occurs correctly
- Fast iteration without waiting for human approvals

**Phase 2: Integration Testing** (AGENT3_TEST_MODE=False)
```bash
# .env configuration
AGENT3_TEST_MODE=False
```
- Test complete HITL workflow
- Validate human approval system
- Test command execution and terminal display
- Verify remediation loops and issue resolution
- Test session memory and context awareness

**Phase 3: Production Deployment** (AGENT3_TEST_MODE=False)
```bash
# .env configuration
AGENT3_TEST_MODE=False
```
- Monitor real application logs
- Handle actual error remediation with human oversight
- Track remediation success rates
- Build knowledge base from successful resolutions

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

**Operating Modes**:
1. **WITH NiFi Correlation**: When `logs/nifi_app/nifi-app.log` exists and Agent 2 loads successfully
2. **STANDALONE Mode**: When NiFi logs are unavailable - pure log analysis without infrastructure correlation

**Automatic Mode Detection**:
```python
# Agent 1 automatically detects NiFi log availability
nifi_log_path = "logs/nifi_app/nifi-app.log"
if os.path.exists(nifi_log_path):
    # Load Agent 2 as tool → CORRELATION MODE
    CORRELATION_MODE = True
else:
    # No NiFi correlation → STANDALONE MODE
    CORRELATION_MODE = False
```

**Key Responsibilities**:
1. Receive and process log entries
2. Call NiFi Agent Tool (CORRELATION MODE only)
3. Perform root cause analysis with session memory
4. Classify logs as NORMAL or ANOMALY
5. Determine severity levels
6. Trigger remediation sub-agent when needed
7. Maintain context awareness across logs in the session

**Tools Available**:
- `nifi_agent_tool` - Correlate with NiFi infrastructure logs (CORRELATION MODE only)
- No tools in STANDALONE MODE

**Sub-Agents**:
- `remediation_agent` - Automatic delegation for ERROR + ANOMALY

**Context Awareness**:
- Session state tracking across multiple log entries
- Historical pattern detection from previous analyses
- Cumulative understanding of system issues
- Reference to earlier anomalies and correlations

**Output Format** (JSON):

*CORRELATION MODE:*
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

*STANDALONE MODE:*
```json
{
  "application": "Application name",
  "classification": "NORMAL | ANOMALY",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "component": "Component that failed",
  "likely_cause": "Root cause based on analysis",
  "infrastructure_correlation": "N/A - No correlation source configured",
  "recommendation": "Action plan based on analysis"
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
- Tracks execution metadata (tool calls, response times, sub-agent triggers)
- Captures multiple responses for complete flow visibility

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

**Operating Modes**:
1. **TEST MODE** (Default): Quick acknowledgment for Agent 1 validation - exits immediately without remediation
2. **PRODUCTION MODE**: Full remediation workflow with human approval and execution

**Mode Configuration**:
```python
# Via environment variable
TEST_MODE = os.getenv("AGENT3_TEST_MODE", "True").lower() == "true"

# TEST_MODE = True  → Quick exit for testing Agent 1
# TEST_MODE = False → Full HITL remediation workflow
```

**TEST MODE Behavior** (For Agent 1 Testing):
- Receives delegation from Agent 1
- Acknowledges error type in 1 sentence
- Exits immediately without tools or remediation
- Response format: "✓ Remediation agent received delegation for [issue type]. Would normally investigate and create remediation plan. Test mode - exiting."
- Purpose: Validate Agent 1's delegation logic without full remediation overhead

**PRODUCTION MODE Responsibilities**:
1. Receive error analysis from Agent 1
2. Check session memory for similar past issues
3. Create remediation plans with confidence scores
4. **MANDATORY**: Get human approval before dangerous commands
5. Execute approved commands locally
6. Analyze execution results based on ACTUAL output only
7. Create follow-up plans if needed
8. Test resolution thoroughly and autonomously
9. Report success to human operator

**Tools Available**:

*TEST MODE:*
- No tools (quick exit)

*PRODUCTION MODE:*
- `human_remediation_approval_tool` - HITL approval system
- `execute_local_command` - Run commands on NiFi server
- `check_local_system` - Test system availability

**Workflow Pattern**:

*TEST MODE:*
```
RECEIVE → ACKNOWLEDGE → EXIT
```

*PRODUCTION MODE:*
```
PLAN → GET APPROVAL → EXECUTE → ANALYZE ACTUAL RESULTS → TEST → REPEAT UNTIL RESOLVED
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

**Session Memory & Context** (PRODUCTION MODE):
- Agent 3 maintains conversation history from current session
- References similar errors fixed earlier in the session
- Learns from previous successful/failed remediation attempts
- Explicitly mentions: "I fixed a similar [error type] [X] logs ago"
- Adapts approach based on historical patterns

**Safety Features**:
- No `sudo` commands allowed (blocked at execution level)
- Rate limiting (0.5s between commands - optimized for responsiveness)
- Safe commands execute without approval overhead
- Dangerous commands require individual human approval
- Terminal window for visual feedback with unique session tracking
- Commands analyzed ONLY on actual output (no assumptions)

**Command Approval Strategy** (PRODUCTION MODE):

*Commands that SKIP approval (safe read-only operations):*
```python
["ls", "pwd", "find", "cat", "ps", "netstat", "lsof", 
 "whoami", "tail", "head", "grep", "df", "systemctl", "java"]
```

*Commands that REQUIRE approval (modify system state):*
- Any `pip install` or package management
- File modifications, deletions
- Service restarts
- Configuration changes
- Any command not in the safe list above

**Critical Execution Rules** (PRODUCTION MODE):
- Agent MUST fully resolve the issue - no partial fixes
- Agent MUST test the resolution autonomously
- Agent analyzes results based ONLY on actual command output
- If command returns empty/no output → Accept that reality, reassess
- Never assume results that weren't actually returned
- Inform human operator ONLY when issue is fully resolved and tested
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
3. `get_terminal_session_info()` - Get current terminal session details
4. `close_persistent_terminal(reason)` - Close terminal session

**Purpose**: Secure local command execution with reliable terminal display

**Security Features**:

1. **Sudo Blocking**:
```python
if command.startswith('sudo'):
    return {"status": "BLOCKED", "error": "Sudo not allowed"}
```

2. **Rate Limiting** (Optimized):
```python
MIN_INTERVAL_BETWEEN_COMMANDS = 0.5  # seconds (reduced from 2s)
# Enforces 0.5-second gap between commands for better responsiveness
```

3. **Concurrent Execution Control**:
```python
_active_executions: Set[str] = set()
# Only one command per server at a time
```

**Terminal Display** (macOS/Linux) - Enhanced Reliability:

*macOS Terminal Targeting Strategy:*
- Creates terminal window with **custom title**: `Agent3-{session_id}`
- Uses custom title for precise window identification
- Prevents cross-contamination with other terminal windows
- Executes commands ONLY in the window matching exact custom title
- Graceful fallback to console-only if terminal targeting fails

*Terminal Features:*
```python
# Session tracking
_terminal_session_id = "abc12345"  # Unique 8-char ID
_terminal_window_id = "Agent3-abc12345"  # Custom title for targeting

# Terminal enabled/disabled flag
_terminal_enabled = True  # Auto-disables if targeting fails

# AppleScript window targeting (macOS)
tell application "Terminal"
    repeat with w in windows
        if custom title of w is "Agent3-abc12345" then
            do script "{command}" in w
        end if
    end repeat
end tell
```

*Linux Terminal Support:*
- Supports `gnome-terminal`, `konsole`, `xterm`
- Uses `xdotool` for window targeting (if available)

**Execution Flow**:
```
1. Validate command (no sudo)
2. Check rate limit (0.5s gap - optimized)
3. Check concurrent execution
4. Open terminal window (if first command) with custom title
5. Target correct window by custom title (reliable)
6. Display command in terminal (if targeting succeeds)
7. Execute via subprocess (always)
8. Capture stdout/stderr
9. Display in console + terminal (dual output)
10. Return structured result
```

**Terminal Session Management**:
```python
# Get session info
terminal_info = get_terminal_session_info()
# Returns: {"session_id": "abc123", "commands_executed": 5, "is_active": True}

# Close terminal when done
close_persistent_terminal("Session complete")
# Closes the specific terminal window by custom title
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

# Agent 3 Operation Mode
AGENT3_TEST_MODE=True   # True: Quick exit for Agent 1 testing
                        # False: Full remediation with HITL workflow
```

**Environment Variable Details**:

- `GOOGLE_API_KEY`: Your Google Gemini API key (required)
- `SERVER_HOST`: FastAPI server bind address (default: 0.0.0.0)
- `SERVER_PORT`: FastAPI server port (default: 8000)
- `PUBLIC_HOST`: Public hostname for API URLs (default: localhost)
- `API_BASE_URL`: Streamlit dashboard API endpoint (default: http://localhost:8000)
- `AGENT3_TEST_MODE`: Controls Agent 3 behavior
  - `True` (default): Agent 3 exits quickly after acknowledgment - useful for testing Agent 1's delegation logic
  - `False`: Full remediation workflow with human approval and command execution

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

### Example 1: Quick Testing (Agent 1 Only - Test Mode)

**Setup**: Ensure `AGENT3_TEST_MODE=True` in `.env` (default)

```bash
# Edit agent_1.py to set your log file path
# Line 398:
log_folder_path = "/path/to/your/logs"

# Run
python agent_1.py
```

**What Happens**:
1. Streams logs one by one from folder
2. Agent 1 analyzes each log
3. NiFi correlation performed automatically (if available)
4. ERROR + ANOMALY triggers Agent 3 delegation
5. Agent 3 **quickly acknowledges and exits** (test mode)
6. Results saved to `agent_outputs/`

**Use Case**: Rapid iteration when testing Agent 1's analysis and delegation logic

**Output Example**:
```
Processing log #5: 2025-10-09 16:20:41 ERROR...
🔧 Tool call: nifi_agent_tool
📨 Agent response #1: [Agent 1 analysis JSON]
📨 Agent response #2: ✓ Remediation agent received delegation for database connection error. Test mode - exiting.
✅ Completed in 2.3s
```

---

### Example 2: Production Remediation (Full HITL Workflow)

**Setup**: Set `AGENT3_TEST_MODE=False` in `.env`

```bash
# .env file
AGENT3_TEST_MODE=False

# Run
python agent_1.py
```

**What Happens**:
1. Streams logs one by one
2. Agent 1 analyzes each log with NiFi correlation
3. ERROR + ANOMALY triggers Agent 3
4. Agent 3 creates remediation plan
5. **Human approval requested** in terminal
6. After approval, commands executed
7. Agent 3 tests resolution autonomously
8. Results saved to `agent_outputs/`

**Approval Process**:
```
🚨 HUMAN APPROVAL REQUIRED
Request ID: req_abc123
================================
UNDERSTANDING: Python module missing
PLAN: pip install requests
RISK: LOW - Safe package installation
CONFIDENCE: 0.95

To approve (in another terminal):
curl -X POST http://localhost:8000/approve/req_abc123
```

---

### Example 3: Analyze via Dashboard (Interactive)

**Setup**: Configure mode in `.env` before starting

1. **Start Services**:
   ```bash
   # Terminal 1 - API Server
   python main.py
   
   # Terminal 2 - Dashboard
   streamlit run unified_dashboard.py
   ```

2. **Open Dashboard**: http://localhost:8501

3. **Configure Mode** (if needed):
   - Stop services
   - Edit `.env`: Set `AGENT3_TEST_MODE=True` or `False`
   - Restart services

4. **Start Analysis**:
   - Tab: "🚀 Trigger Analysis"
   - Select file: `logs/HR_logs (1).log`
   - Click: "🚀 Start Stream Analysis"

5. **Monitor Progress**:
   - Watch "📊 Analysis Status" panel
   - Real-time logs processed count
   - Current log being analyzed
   - Agent activity stream
   - Tool calls and responses

6. **Handle Approvals** (Production Mode Only):
   - Tab: "✅ Approve Plans"
   - Click "🔄 Refresh Now"
   - Review remediation plan with confidence score
   - Click "✅ Approve" or "❌ Reject"
   - Optionally: Provide feedback for plan modification

7. **Check Results**:
   - Files saved in `agent_outputs/`
   - Terminal shows command execution details
   - Session memory preserved across log entries

---

### Example 4: Standalone Mode (No NiFi Correlation)

**Scenario**: Analyzing application logs without NiFi infrastructure

**Setup**:
- Ensure NO file at `logs/nifi_app/nifi-app.log`
- Agent 1 will automatically enter STANDALONE mode

```bash
# Agent 1 detects no NiFi logs and switches to standalone
python agent_1.py
```

**Console Output**:
```
✗ NiFi correlation DISABLED (no logs at logs/nifi_app/nifi-app.log)
Log Analysis Agent created in STANDALONE (no correlation) mode
```

**Analysis Output**:
```json
{
  "application": "MyApp",
  "classification": "ANOMALY",
  "severity": "HIGH",
  "component": "DatabaseService",
  "likely_cause": "Connection pool exhausted",
  "infrastructure_correlation": "N/A - No correlation source configured",
  "recommendation": "Increase pool size or investigate connection leaks"
}
```

**Use Case**: Non-NiFi applications, testing without infrastructure logs, or when NiFi logs unavailable

---

## 🎯 NiFi-Specific Configuration

**For NiFi Deployments**: Agent 3 (in production mode) has pre-configured knowledge of common NiFi installation paths:

**Default NiFi Paths**:
```
/Users/shtlpmac071/Downloads/nifi-2.6.0/                    # NiFi installation root
/Users/shtlpmac071/Downloads/nifi-2.6.0/HR_BOT/             # Application directory
/Users/shtlpmac071/Downloads/nifi-2.6.0/HR_BOT/llm_usage.log # Error log file
/Users/shtlpmac071/Downloads/nifi-2.6.0/conf/nifi.properties # Configuration
```

**Customization**: Update these paths in `prompts/remediation_agent_prompt.py` (line 111) to match your NiFi installation.

**Log Location Discovery**:
Agent 3 knows to look for application error logs at the configured path and will:
1. Read the error log file for detailed stack traces
2. Analyze the complete error context
3. Test resolution by re-running the problematic file/script
4. Verify fixes by checking the log file again

---

## 🔐 Security & Compliance

### Security Features

**1. Command Execution Security**
- **Sudo Blocking**: All `sudo` commands are blocked at execution level
- **Command Whitelisting**: Safe read-only commands execute without approval
- **Approval Required**: Dangerous commands require explicit human approval
- **No Batch Execution**: Each command requires individual approval
- **Rate Limiting**: 0.5s minimum interval between commands

**2. Isolation & Sandboxing**
- **Session Isolation**: Each analysis runs in isolated ADK session
- **Terminal Isolation**: Commands execute in dedicated terminal window with unique ID
- **No Cross-Contamination**: Custom title-based targeting prevents interference

**3. Audit Trail**
- **Complete Logging**: All interactions logged to `agent_logs/`
- **Human Interactions**: Special logging for all HITL decisions
- **Execution Metadata**: Tool calls, response times, command outputs tracked
- **JSON Output**: Complete analysis and remediation saved to `agent_outputs/`

**4. Network Security**
- **Local Execution Only**: Commands run on local system only
- **No Remote SSH**: No SSH connections to remote servers
- **API Authentication**: Can be extended with API keys (not implemented by default)

### Compliance Considerations

**Data Privacy**:
- All log analysis happens locally
- No data sent to external services except Gemini API for LLM inference
- Logs and outputs stored locally in filesystem
- Session data ephemeral (in-memory only during execution)

**Operational Safety**:
- Human approval required for all system-modifying operations
- Clear confidence scoring for remediation plans
- Ability to reject or modify plans before execution
- Test mode available for validation without side effects

**Audit Requirements**:
```
agent_logs/                           # Timestamped session logs
  - agent_session_YYYYMMDD_HHMMSS.txt
  - remediation_agent_session_YYYYMMDD_HHMMSS.txt
  - human_interactions_YYYYMMDD.json

agent_outputs/                        # Complete interaction records
  - complete_log_00001_YYYYMMDD_HHMMSS.json
  - complete_log_00002_YYYYMMDD_HHMMSS.json
```

---

## 📋 Summary

This multi-agent log analysis system provides:

✅ **Intelligent Analysis**: AI-powered log analysis with session memory and pattern detection  
✅ **Infrastructure Correlation**: Automatic NiFi log correlation (when available)  
✅ **Flexible Deployment**: Standalone mode for non-NiFi applications  
✅ **Safe Remediation**: Human-in-the-loop approval for system changes  
✅ **Testing Support**: Test mode for rapid development and validation  
✅ **Enterprise Ready**: Security controls, audit trails, and compliance features  
✅ **Real-time Monitoring**: Dashboard and API for operational visibility  
✅ **Context Awareness**: Session memory for cumulative system understanding  

**Best For**:
- NiFi-based data pipeline monitoring and auto-remediation
- Application log analysis with infrastructure correlation
- Human-supervised automated troubleshooting
- Continuous log monitoring with anomaly detection
- Building operational knowledge bases from successful fixes

**Get Started**:
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` with Gemini API key
3. Set `AGENT3_TEST_MODE=True` for initial testing
4. Run `python agent_1.py` to process logs
5. Switch to `AGENT3_TEST_MODE=False` for production remediation

For questions or contributions, see the project repository.

---

*Documentation last updated: 2025-10-31*