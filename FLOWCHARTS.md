# 🔄 Multi-Agent System Flowcharts

## 1. Overall System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         START SYSTEM                                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
            ┌────────────▼────────────┐
            │   Choose Entry Point    │
            └────┬──────────┬─────────┘
                 │          │
      ┌──────────▼──┐    ┌──▼──────────────┐    ┌──────────────────┐
      │ CLI Direct  │    │ FastAPI + Web   │    │ Streamlit UI     │
      │ agent_1.py  │    │ main.py         │    │ unified_dashboard│
      └──────┬──────┘    └──┬──────────────┘    └────────┬─────────┘
             │              │                            │
             └──────────────┼────────────────────────────┘
                            │
                ┌───────────▼──────────────┐
                │  Log File Streaming      │
                │  (stream_logs_by_        │
                │   timestamp)             │
                └───────────┬──────────────┘
                            │
                            │ For Each Log Entry
                            │
                ┌───────────▼──────────────┐
                │   AGENT 1 PROCESSING     │
                │   (Analyser Agent)       │
                └───────────┬──────────────┘
                            │
                ┌───────────▼──────────────────┐
                │  Call NiFi Agent Tool        │
                │  (MANDATORY)                 │
                └───────────┬──────────────────┘
                            │
                ┌───────────▼──────────────┐
                │  AGENT 2 PROCESSING      │
                │  (NiFi Correlation)      │
                └───────────┬──────────────┘
                            │
                ┌───────────▼──────────────┐
                │  Return Correlation      │
                │  Data to Agent 1         │
                └───────────┬──────────────┘
                            │
                ┌───────────▼────────────────┐
                │  Generate JSON Analysis    │
                │  Classification + Severity │
                └───────────┬────────────────┘
                            │
                      ┌─────▼─────┐
                      │  Trigger  │
                      │  Check?   │
                      └─┬───────┬─┘
                        │       │
                   NO   │       │  YES
                        │       │
                ┌───────▼─┐   ┌─▼──────────────────┐
                │  Save & │   │  AGENT 3 TRIGGER   │
                │  Done   │   │  (Remediation)     │
                └─────────┘   └──┬─────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │  Create Remediation Plan    │
                    └────────────┬────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │  HITL Approval Request      │
                    │  (human_remediation_tool)   │
                    └────────────┬────────────────┘
                                 │
                           ┌─────▼──────┐
                           │  Wait for  │
                           │  Human     │
                           └─┬────────┬─┘
                             │        │
                      REJECT │        │ APPROVE
                             │        │
                ┌────────────▼─┐    ┌─▼────────────────┐
                │  New Plan    │    │  Execute Command │
                │  Required    │    │  (local_command) │
                └────────┬─────┘    └──┬───────────────┘
                         │              │
                         │          ┌───▼───────────────┐
                         │          │  Analyze Results  │
                         │          └───┬───────────────┘
                         │              │
                         │        ┌─────▼──────┐
                         │        │  Resolved? │
                         │        └─┬────────┬─┘
                         │          │        │
                         │     NO   │        │  YES
                         │          │        │
                         └──────────┘        │
                                    ┌────────▼─────────┐
                                    │  Test Resolution │
                                    │  Report Success  │
                                    └──────────────────┘
```

## 2. Agent 1: Analysis Flow (Detailed)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 1: LOG ANALYSER                        │
│                    Model: gemini-2.5-flash                      │
│                    Temperature: 0.1                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Input: Single Log Entry
                            │
            ┌───────────────▼──────────────────┐
            │  Parse Log Entry                 │
            │  - Extract timestamp             │
            │  - Identify log level            │
            │  - Extract error message         │
            │  - Keep stack traces together    │
            └───────────────┬──────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
            │  MANDATORY STEP 1:                       │
            │  Call nifi_agent_tool                    │
            │  - Pass: log entry + timestamp           │
            │  - Wait for correlation data             │
            └───────────────┬──────────────────────────┘
                            │
                            │ NiFi Agent processes
                            │
            ┌───────────────▼──────────────────────────┐
            │  Receive NiFi Correlation Data           │
            │  {                                       │
            │    "correlation_found": true,            │
            │    "nifi_issue_summary": "...",          │
            │    "nifi_logs_analyzed": [...]           │
            │  }                                       │
            └───────────────┬──────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
            │  STEP 2: Analyze with Context            │
            │  - Application error details             │
            │  - NiFi infrastructure correlation       │
            │  - Historical patterns (session state)   │
            │  - Error severity assessment             │
            └───────────────┬──────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
            │  STEP 3: Classify Log                    │
            │                                          │
            │  Classification Decision Tree:           │
            │  ┌─────────────────────────────┐         │
            │  │ Is error known/expected?    │         │
            │  └─┬─────────────────────────┬─┘         │
            │    │ YES                 NO  │           │
            │  ┌─▼─────────┐      ┌────────▼──┐        │
            │  │  NORMAL    │      │  ANOMALY  │       │
            │  └────────────┘      └───────────┘       │
            │                                          │
            │  Severity Assessment:                    │
            │  - LOW: Minor issues, no impact          │
            │  - MEDIUM: Functionality affected        │
            │  - HIGH: Major functionality down        │
            │  - CRITICAL: System-wide failure         │
            └───────────────┬──────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
            │  STEP 4: Generate JSON Response          │
            │  {                                       │
            │    "application": "HR_BOT",              │
            │    "classification": "ANOMALY",          │
            │    "severity": "HIGH",                   │
            │    "component": "ExecuteStreamCommand",  │
            │    "likely_cause": "Missing module",     │
            │    "nifi_correlation": "[from tool]",    │
            │    "recommendation": "Install module"    │
            │  }                                       │
            └───────────────┬──────────────────────────┘
                            │
            ┌───────────────▼─────────────────────────┐
            │  STEP 5: Check Remediation Trigger      │
            │                                         │
            │  Condition 1: " ERROR " in log_entry?   │
            │  ┌────────────────┐                     │
            │  │  Search for    │                     │
            │  │  exact string  │                     │
            │  │  " ERROR "     │                     │
            │  └────┬───────────┘                     │
            │       │                                 │
            │  Condition 2: classification="ANOMALY"? │
            │  ┌────────────────┐                     │
            │  │  Check JSON    │                     │
            │  │  field value   │                     │
            │  └────┬───────────┘                     │
            │       │                                 │
            │  IF BOTH TRUE:                          │
            │  ┌────────────────────────────┐         │
            │  │ MUST trigger remediation   │         │
            │  │ sub-agent immediately      │         │
            │  │ No exceptions!             │         │
            │  └────┬───────────────────────┘         │
            └───────┼─────────────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────────┐
        │  YES: Delegate to Agent 3   │
        └─────────────────────────────┘
```

## 3. Agent 2: NiFi Correlation Flow

```
┌────────────────────────────────────────────────────────┐
│           AGENT 2: NiFi SPECIALIST                     │
│           (Invoked as Tool by Agent 1)                 │
│           Model: gemini-2.5-flash                      │
└─────────────────────┬──────────────────────────────────┘
                      │
                      │ Input from Agent 1:
                      │ - Application error context
                      │ - Timestamp (HH:MM:SS)
                      │
      ┌───────────────▼───────────────────┐
      │  STEP 1: Extract Timestamp        │
      │  - Format: "16:20:41"             │
      │  - Validate format                │
      └───────────────┬───────────────────┘
                      │
      ┌───────────────▼─────────────────────────┐
      │  STEP 2: Call search_nifi_logs_tool     │
      │  (Direct file access)                   │
      └───────────────┬─────────────────────────┘
                      │
      ┌───────────────▼─────────────────────────┐
      │  Tool: search_nifi_logs_by_timestamp    │
      ├─────────────────────────────────────────┤
      │  1. Open: logs/nifi_app/nifi-app.log    │
      │                                         │
      │  2. Extract date from first line:       │
      │     "2025-10-09 16:20:18,696..."        │
      │     → date = "2025-10-09"               │
      │                                         │
      │  3. Parse target timestamp:             │
      │     target = "2025-10-09 16:20:41"      │
      │                                         │
      │  4. Calculate search window:            │
      │     start = target - 2 seconds          │
      │     end = target + 1 second             │
      │     → [16:20:39, 16:20:42]              │
      │                                         │
      │  5. Scan file line by line:             │
      │     for line in nifi_log:               │
      │       extract line_timestamp            │
      │       if start <= line_time <= end:     │
      │         add to matching_logs            │
      │                                         │
      │  6. Return top 10 matches               │
      └───────────────┬─────────────────────────┘
                      │
      ┌───────────────▼─────────────────────────┐
      │  STEP 3: Analyze Returned Logs          │
      │                                         │
      │  Example NiFi logs found:               │
      │  ┌────────────────────────────────────┐ │
      │  │ 16:20:39 INFO Checkpoint started   │ │
      │  │ 16:20:41 ERROR ExecuteStream...    │ │
      │  │ 16:20:41 ERROR Python script exit 1│ │
      │  └────────────────────────────────────┘ │
      │                                         │
      │  Agent 2 analyzes:                      │
      │  - Is there correlation?                │
      │  - What's the NiFi-level issue?         │
      │  - How did it cause app error?          │
      │  - What's the infrastructure impact?    │
      └───────────────┬─────────────────────────┘
                      │
      ┌───────────────▼─────────────────────────┐
      │  STEP 4: Generate Correlation JSON      │
      │                                         │
      │  {                                      │
      │    "correlation_found": true,           │
      │    "nifi_issue_summary":                │
      │      "NiFi processor ExecuteStream      │
      │       failed to run Python script",     │
      │    "likely_nifi_cause":                 │
      │      "Python environment missing        │
      │       required module 'requests'",      │
      │    "correlation_details":               │
      │      "NiFi tried to execute script      │
      │       but Python threw NameError",      │
      │    "nifi_logs_analyzed": [              │
      │      "16:20:41,140 ERROR ...",          │
      │      "...stack trace..."                │
      │    ],                                   │
      │    "timestamp_searched": "16:20:41",    │
      │    "recommendation":                    │
      │      "Install requests module in        │
      │       NiFi's Python environment"        │
      │  }                                      │
      └───────────────┬─────────────────────────┘
                      │
                      │ Return to Agent 1
                      │
      ┌───────────────▼─────────────────────────┐
      │  Agent 1 receives correlation data      │
      │  and incorporates into analysis         │
      └─────────────────────────────────────────┘
```

## 4. Agent 3: Remediation Flow (HITL)

```
┌────────────────────────────────────────────────────────────────┐
│             AGENT 3: REMEDIATION SPECIALIST                    │
│             (Sub-Agent of Agent 1)                             │
│             Model: gemini-2.5-pro                              │
│             Triggered when: ERROR + ANOMALY                    │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ Input: Complete Analysis from Agent 1
                         │
         ┌───────────────▼──────────────────┐
         │  Receive Analysis Report         │
         │  - Application details           │
         │  - Error classification          │
         │  - Root cause analysis           │
         │  - NiFi correlation findings     │
         │  - Initial recommendations       │
         └───────────────┬──────────────────┘
                         │
         ┌───────────────▼──────────────────┐
         │  STEP 1: Understand the Problem  │
         │  - Parse error details           │
         │  - Identify affected component   │
         │  - Assess impact scope           │
         │  - Consider NiFi correlation     │
         └───────────────┬──────────────────┘
                         │
         ┌───────────────▼────────────────────────┐
         │  STEP 2: Create Remediation Plan       │
         │                                        │
         │  Plan Components:                      │
         │  ┌──────────────────────────────────┐ │
         │  │ UNDERSTANDING:                   │ │
         │  │ "Python script missing 'requests'│ │
         │  │  module causing NiFi processor   │ │
         │  │  ExecuteStreamCommand to fail"   │ │
         │  └──────────────────────────────────┘ │
         │                                        │
         │  ┌──────────────────────────────────┐ │
         │  │ PLAN:                            │ │
         │  │ "Install requests module:        │ │
         │  │  /path/to/venv/bin/pip install   │ │
         │  │  requests"                       │ │
         │  └──────────────────────────────────┘ │
         │                                        │
         │  ┌──────────────────────────────────┐ │
         │  │ RISK:                            │ │
         │  │ "LOW - Safe package installation,│ │
         │  │  no system changes, easily       │ │
         │  │  reversible"                     │ │
         │  └──────────────────────────────────┘ │
         │                                        │
         │  ┌──────────────────────────────────┐ │
         │  │ CONFIDENCE: 0.95                 │ │
         │  │ HIGH - Well-known error pattern, │ │
         │  │ proven solution                  │ │
         │  └──────────────────────────────────┘ │
         └───────────────┬────────────────────────┘
                         │
         ┌───────────────▼──────────────────────────┐
         │  STEP 3: MANDATORY HITL Approval         │
         │  Call: human_remediation_approval_tool   │
         └───────────────┬──────────────────────────┘
                         │
         ┌───────────────▼──────────────────────────┐
         │  HITL Tool: Store & Display              │
         │  ┌────────────────────────────────────┐  │
         │  │ 1. Generate request_id: req_abc123 │  │
         │  │                                    │  │
         │  │ 2. Store in memory:                │  │
         │  │    _approval_requests[req_abc123]  │  │
         │  │                                    │  │
         │  │ 3. Display to terminal/dashboard   │  │
         │  │    ┌─────────────────────────────┐│  │
         │  │    │🚨 APPROVAL REQUIRED         ││  │
         │  │    │Request ID: req_abc123       ││  │
         │  │    │                             ││  │
         │  │    │[Plan details displayed]     ││  │
         │  │    │                             ││  │
         │  │    │Approve: POST /approve/...   ││  │
         │  │    │Reject: POST /reject/...     ││  │
         │  │    └─────────────────────────────┘│  │
         │  │                                    │  │
         │  │ 4. Poll every 5 seconds            │  │
         │  │    while status == "pending"       │  │
         │  │                                    │  │
         │  │ 5. Timeout after 5 minutes         │  │
         │  └────────────────────────────────────┘  │
         └───────────────┬──────────────────────────┘
                         │
                         │ Wait for Human Decision
                         │
            ┌────────────▼────────────┐
            │  Human Response via:     │
            │  - Dashboard buttons     │
            │  - curl commands         │
            │  - API calls             │
            └────┬─────────────┬───────┘
                 │             │
          REJECT │             │ APPROVE
                 │             │
    ┌────────────▼──┐      ┌──▼─────────────────────┐
    │  Feedback?    │      │  STEP 4: Execute Plan  │
    └────┬────────┬─┘      └──┬─────────────────────┘
         │        │            │
    YES  │        │ NO         │
         │        │            │
    ┌────▼───┐  ┌─▼──────┐    │
    │ Modify │  │ Create │    │
    │  Plan  │  │  New   │    │
    │ Based  │  │ Alt.   │    │
    │   on   │  │ Plan   │    │
    │Feedback│  │        │    │
    └────┬───┘  └─┬──────┘    │
         │        │            │
         └────────┴────────────┘
                  │            │
            Back to STEP 3     │
                               │
                  ┌────────────▼────────────────────┐
                  │  Call: execute_local_command    │
                  │  - Server: NiFi-Server-Local    │
                  │  - Command: [approved command]  │
                  │  - Timeout: 15s default         │
                  └────────────┬────────────────────┘
                               │
                  ┌────────────▼────────────────────┐
                  │  Command Execution              │
                  │  1. Validate (no sudo)          │
                  │  2. Rate limit check            │
                  │  3. Open terminal window        │
                  │  4. Execute via subprocess      │
                  │  5. Capture stdout/stderr       │
                  │  6. Return results              │
                  └────────────┬────────────────────┘
                               │
                  ┌────────────▼────────────────────┐
                  │  STEP 5: Analyze Results        │
                  │  - Parse command output         │
                  │  - Check for errors             │
                  │  - Verify expected outcome      │
                  │  - Base on ACTUAL output only   │
                  └────────────┬────────────────────┘
                               │
                         ┌─────▼──────┐
                         │  Resolved? │
                         └─┬────────┬─┘
                           │        │
                      NO   │        │  YES
                           │        │
              ┌────────────▼──┐   ┌─▼────────────────────┐
              │  STEP 6:      │   │  STEP 6: Test        │
              │  New Plan     │   │  Resolution          │
              │  Required     │   │  - Re-run scenario   │
              │               │   │  - Verify fix works  │
              │  Back to      │   │  - Confirm success   │
              │  STEP 2       │   └──┬───────────────────┘
              └───────────────┘      │
                                     │
                        ┌────────────▼────────────────┐
                        │  STEP 7: Report Success     │
                        │  - Inform human operator    │
                        │  - Log resolution details   │
                        │  - Close remediation cycle  │
                        └─────────────────────────────┘
```

## 5. Human-in-the-Loop Approval Flow

```
┌────────────────────────────────────────────────────────────┐
│              HITL APPROVAL SYSTEM                          │
│              (In-Memory, No Files)                         │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           │ Agent 3 creates plan
                           │
           ┌───────────────▼──────────────────┐
           │  Generate Request ID             │
           │  request_id = uuid.uuid4()[:8]   │
           │  → "req_abc123"                  │
           └───────────────┬──────────────────┘
                           │
           ┌───────────────▼──────────────────────────┐
           │  Store in Memory                         │
           │  _approval_requests["req_abc123"] = {    │
           │    "plan": "UNDERSTANDING:\n...",        │
           │    "status": "pending",                  │
           │    "created_at": 1234567890              │
           │  }                                       │
           └───────────────┬──────────────────────────┘
                           │
           ┌───────────────▼──────────────────────────┐
           │  Display to Human                        │
           │  ┌────────────────────────────────────┐  │
           │  │ Terminal Output:                   │  │
           │  │ ================================   │  │
           │  │ 🚨 HUMAN APPROVAL REQUIRED         │  │
           │  │ Request ID: req_abc123             │  │
           │  │ ================================   │  │
           │  │ [Plan details...]                  │  │
           │  │ ================================   │  │
           │  │                                    │  │
           │  │ To approve (in another terminal):  │  │
           │  │ curl -X POST http://localhost:8000/│  │
           │  │      approve/req_abc123            │  │
           │  │                                    │  │
           │  │ To reject:                         │  │
           │  │ curl -X POST http://localhost:8000/│  │
           │  │      reject/req_abc123             │  │
           │  └────────────────────────────────────┘  │
           │                                          │
           │  ┌────────────────────────────────────┐  │
           │  │ Dashboard Display:                 │  │
           │  │ Tab: "✅ Approve Plans"            │  │
           │  │ ┌────────────────────────────────┐ │  │
           │  │ │ Request: req_abc123            │ │  │
           │  │ │ [Plan details in text box]     │ │  │
           │  │ │ [✅ Approve] [❌ Reject]        │ │  │
           │  │ │ [💬 Send Feedback]              │ │  │
           │  │ └────────────────────────────────┘ │  │
           │  └────────────────────────────────────┘  │
           └───────────────┬──────────────────────────┘
                           │
           ┌───────────────▼──────────────────────────┐
           │  Poll for Status (every 5 seconds)       │
           │  while True:                             │
           │    status = _approval_requests[id]       │
           │                 ["status"]               │
           │    if status != "pending":               │
           │      break                               │
           │    sleep(5)                              │
           └───────────────┬──────────────────────────┘
                           │
                           │ Human acts via:
                           │ - Dashboard buttons
                           │ - curl commands
                           │ - Python API calls
                           │
              ┌────────────▼────────────┐
              │  Human Action Options   │
              └──┬──────────┬─────────┬──┘
                 │          │         │
            ┌────▼─┐   ┌────▼──┐  ┌──▼────────┐
            │Approve│  │Reject │  │ Feedback  │
            └────┬──┘  └────┬──┘  └──┬────────┘
                 │          │         │
    ┌────────────▼─┐  ┌─────▼────┐  ┌▼──────────────┐
    │ POST         │  │ POST     │  │ POST          │
    │ /approve/    │  │ /reject/ │  │ /feedback/    │
    │ {request_id} │  │ {req_id} │  │ {req_id}      │
    └────────────┬─┘  └─────┬────┘  │ ?feedback=... │
                 │          │        └─┬─────────────┘
                 │          │          │
    ┌────────────▼──────────▼──────────▼──────────┐
    │  Update Memory                              │
    │  _approval_requests[request_id]["status"]   │
    │    = "approved" | "rejected"                │
    │  _approval_requests[request_id]["feedback"] │
    │    = feedback_text (if provided)            │
    └────────────┬────────────────────────────────┘
                 │
    ┌────────────▼────────────────────────────────┐
    │  Agent 3 Detects Status Change              │
    │  (on next poll cycle)                       │
    └────────────┬────────────────────────────────┘
                 │
                 │ Return status to Agent 3
                 │
    ┌────────────▼────────────────────────────────┐
    │  Return Value:                              │
    │  - "APPROVED" → Execute immediately         │
    │  - "REJECTED" → Create new plan             │
    │  - "REJECTED_WITH_FEEDBACK: {text}"         │
    │    → Modify plan based on feedback          │
    │  - "TIMEOUT" → No response in 5 minutes     │
    └─────────────────────────────────────────────┘
```

## 6. Data Flow Diagram

```
┌─────────────────┐
│  Log File       │
│  (.log)         │
└────────┬────────┘
         │
         │ Read line-by-line
         │ Group multi-line entries
         ▼
┌──────────────────────────────┐
│  stream_logs_by_timestamp()  │
│  - Parse timestamp pattern   │
│  - Keep stack traces intact  │
│  - Yield complete entries    │
└────────┬─────────────────────┘
         │
         │ Single complete log entry
         ▼
┌─────────────────────────────────────────┐
│  Agent 1: Analyser                      │
├─────────────────────────────────────────┤
│  Input: Log entry text                  │
│  Output: Analysis JSON                  │
└────────┬───────────────┬────────────────┘
         │               │
         │ Timestamp     │ Analysis results
         │ + context     │
         ▼               │
┌──────────────────┐     │
│  Agent 2: NiFi   │     │
├──────────────────┤     │
│  Input:          │     │
│  - Timestamp     │     │
│  - App error     │     │
│                  │     │
│  Process:        │     │
│  - Search logs   │     │
│  - Correlate     │     │
│                  │     │
│  Output:         │     │
│  - Correlation   │     │
│    JSON          │     │
└────────┬─────────┘     │
         │               │
         │ NiFi data     │
         │               │
         └───────────────┘
                 │
                 ▼
       ┌─────────────────┐
       │  IF ERROR +     │
       │  ANOMALY        │
       └────┬────────────┘
            │
            │ YES
            ▼
┌──────────────────────────────────┐
│  Agent 3: Remediation            │
├──────────────────────────────────┤
│  Input: Complete analysis        │
│  Process:                        │
│  1. Create plan                  │
│  2. Get approval ──┐             │
│  3. Execute ◄──────┘             │
│  4. Verify                       │
│  Output: Resolution report       │
└──────────────┬───────────────────┘
               │
               │ Approval needed
               ▼
┌──────────────────────────────────┐
│  HITL: In-Memory Storage         │
│  _approval_requests = {          │
│    "req_id": {                   │
│      "plan": "...",              │
│      "status": "pending"         │
│    }                             │
│  }                               │
└────────┬─────────────┬───────────┘
         │             │
         │ Display     │ Poll status
         │             │
         ▼             │
┌─────────────────┐    │
│  Human via:     │    │
│  - Dashboard    │    │
│  - Terminal     │    │
│  - API          │    │
└────────┬────────┘    │
         │             │
         │ Decision    │
         └─────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  Final Output:                      │
│  agent_outputs/complete_log_XXX.json│
│  - Original log                     │
│  - Agent 1 analysis                 │
│  - NiFi correlation                 │
│  - Remediation actions (if any)     │
└─────────────────────────────────────┘
```

---

*These flowcharts visualize the complete multi-agent system architecture and workflows*

