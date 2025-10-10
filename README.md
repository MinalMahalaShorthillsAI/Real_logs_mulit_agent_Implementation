# 🤖 Multi-Agent Log Analysis System

> **Enterprise-grade AI-powered log analysis with automated remediation and human-in-the-loop decision making**

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-orange.svg)](https://ai.google.dev/adk)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5-green.svg)](https://ai.google.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)](https://streamlit.io/)

---

## 📖 What is This?

An **intelligent multi-agent system** that analyzes application logs, correlates them with infrastructure (NiFi) logs, detects anomalies, and automatically creates remediation plans with human approval. Built using **Google's Gemini 2.5** AI models and **Agent Development Kit (ADK)**.

### ✨ Key Features

- 🤖 **Three Specialized AI Agents** working collaboratively
- 📊 **Real-time log streaming** and analysis
- 🔗 **Automatic NiFi correlation** for infrastructure issues
- 👤 **Human-in-the-loop (HITL)** approval for safe remediation
- 🌐 **RESTful API** with FastAPI for integration
- 📱 **Streamlit Dashboard** for monitoring and approvals
- 🔒 **Enterprise security** with command validation and rate limiting
- ⚡ **Powered by Gemini 2.5** for accurate analysis

---

## 🎯 Problem It Solves

### Before:
- ❌ Manual log analysis takes hours
- ❌ Hard to correlate app errors with infrastructure issues
- ❌ Error patterns missed without deep expertise
- ❌ Remediation requires manual investigation
- ❌ Risk of executing wrong fixes

### After:
- ✅ **Automated analysis** in seconds per log
- ✅ **Automatic correlation** with NiFi infrastructure
- ✅ **AI-powered anomaly detection** with confidence scores
- ✅ **Intelligent remediation plans** with risk assessment
- ✅ **Human approval required** before execution (safe!)

---

## 🏗️ Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────┐
│                    USER INTERFACES                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   CLI    │  │  Streamlit   │  │   REST API       │  │
│  │ Terminal │  │  Dashboard   │  │   /docs          │  │
│  └──────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │
         ┌───────────────▼────────────────────┐
         │    FastAPI Application Layer        │
         │    Orchestration & API Endpoints    │
         └───────────────┬────────────────────┘
                         │
         ┌───────────────▼────────────────────┐
         │     MULTI-AGENT SYSTEM (ADK)       │
         ├────────────────────────────────────┤
         │                                    │
         │  ┌──────────────────────────────┐ │
         │  │  AGENT 1: Analyser Agent     │ │
         │  │  Main log analysis           │ │
         │  │  gemini-2.5-flash            │ │
         │  └───────┬──────────┬───────────┘ │
         │          │          │             │
         │      Tool│          │Sub-Agent    │
         │          ▼          ▼             │
         │  ┌──────────┐  ┌─────────────┐   │
         │  │ AGENT 2  │  │  AGENT 3    │   │
         │  │ NiFi     │  │ Remediation │   │
         │  │ Analyst  │  │ (HITL)      │   │
         │  └──────────┘  └─────────────┘   │
         │                                    │
         └────────────────────────────────────┘
```

### Three Intelligent Agents

#### 🔍 Agent 1: Analyser Agent
- **Role**: Main log analysis and orchestration
- **Model**: `gemini-2.5-flash` (Fast, efficient)
- **Responsibilities**:
  - Analyze log entries
  - Call NiFi Agent for correlation
  - Classify as NORMAL or ANOMALY
  - Determine severity levels
  - Trigger remediation when needed

#### 🔗 Agent 2: NiFi Correlation Agent
- **Role**: Infrastructure log specialist (used as a tool)
- **Model**: `gemini-2.5-flash`
- **Responsibilities**:
  - Search NiFi logs by timestamp
  - Find correlations within ±2 seconds
  - Analyze infrastructure issues
  - Return detailed correlation data

#### 🛠️ Agent 3: Remediation Agent
- **Role**: Automated remediation with human approval
- **Model**: `gemini-2.5-pro` (Most capable)
- **Responsibilities**:
  - Create remediation plans
  - Request human approval (HITL)
  - Execute approved commands
  - Verify resolution
  - Report success

---

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.13+
macOS or Linux
Google Gemini API Key
```

### Installation (5 minutes)

```bash
# 1. Navigate to project
cd Real_logs_mulit_agent_Implementation

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your_gemini_api_key_here
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
PUBLIC_HOST=localhost
API_BASE_URL=http://localhost:8000
EOF
```

**Get API Key**: https://makersuite.google.com/app/apikey

### Launch System

**Option 1: Full System (Recommended)**

```bash
# Terminal 1: Start API server
python main.py

# Terminal 2: Start dashboard
streamlit run unified_dashboard.py
```

**Option 2: CLI Only**

```bash
python agent_1.py
```

### Access

- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000

---

## 📊 Usage Examples

### Example 1: Analyze Logs via Dashboard

1. Open http://localhost:8501
2. Tab: "🚀 Trigger Analysis"
3. Select: `logs/HR_logs (1).log`
4. Click: "🚀 Start Stream Analysis"
5. Monitor real-time progress

### Example 2: Handle Remediation Approval

1. Tab: "✅ Approve Plans"
2. Review remediation plan
3. Click "✅ Approve" or "❌ Reject"
4. Watch execution in terminal

### Example 3: API Integration

```python
import requests

# Start analysis
response = requests.post(
    "http://localhost:8000/start-analysis",
    json={"file_path": "logs/app.log"}
)

# Monitor progress
status = requests.get("http://localhost:8000/analysis-status")
print(status.json())

# Approve a plan
requests.post("http://localhost:8000/approve/{request_id}")
```

---

## 📁 Project Structure

```
Real_logs_mulit_agent_Implementation/
│
├── 📄 README.md                        # This file
├── 📄 COMPREHENSIVE_DOCUMENTATION.md   # Complete docs
├── 📄 FLOWCHARTS.md                    # Visual flowcharts
├── 📄 QUICK_START_GUIDE.md            # Quick start
│
├── 🤖 agent_1.py                       # Main Analyser Agent
├── 🤖 agent_2.py                       # NiFi Correlation Agent
├── 🤖 agent_3.py                       # Remediation Agent
│
├── 🌐 main.py                          # FastAPI Application
├── 📱 unified_dashboard.py             # Streamlit Dashboard
│
├── 📝 prompts/
│   ├── analyser_prompt.py              # Agent 1 instructions
│   ├── nifi_agent_prompt.py            # Agent 2 instructions
│   └── remediation_agent_prompt.py     # Agent 3 instructions
│
├── 🛠️ tools/
│   ├── log_tool.py                     # NiFi log search
│   ├── remediation_hitl_tool.py        # Human approval tool
│   └── local_command_tools.py          # Command execution
│
├── 📊 logs/                            # Sample log files
│   ├── HR_logs (1).log                # Application logs
│   └── nifi_app/nifi-app.log          # NiFi logs
│
├── 📋 agent_logs/                      # Agent session logs
├── 📋 agent_outputs/                   # Analysis results
│
├── 📦 requirements.txt                 # Python dependencies
└── ⚙️ .env                             # Environment variables
```

---

## 🔄 System Flow

```
┌─────────────┐
│  Log Entry  │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│   Agent 1:       │
│   Analyser       │
│   ┌──────────┐   │
│   │ Analyze  │   │
│   └────┬─────┘   │
│        │         │
│   ┌────▼──────┐  │
│   │Call Agent2│  │ ──────► Agent 2: NiFi Correlation
│   └────┬──────┘  │           ├─ Search logs
│        │         │           ├─ Find patterns
│        ▼         │           └─ Return data
│   ┌──────────┐   │
│   │ Classify │   │ ◄────────
│   └────┬─────┘   │
│        │         │
│   ┌────▼──────┐  │
│   │ERROR +    │  │
│   │ANOMALY?   │  │
│   └────┬──────┘  │
│        │ YES     │
└────────┼─────────┘
         │
         ▼
┌─────────────────────┐
│   Agent 3:          │
│   Remediation       │
│   ┌─────────────┐   │
│   │Create Plan  │   │
│   └──────┬──────┘   │
│          │          │
│   ┌──────▼──────┐   │
│   │Get Human    │   │ ──────► Human via Dashboard/API
│   │Approval     │   │           ├─ Review plan
│   └──────┬──────┘   │           ├─ Approve/Reject
│          │          │           └─ Send feedback
│   ┌──────▼──────┐   │
│   │Execute      │   │ ◄────────
│   │Commands     │   │
│   └──────┬──────┘   │
│          │          │
│   ┌──────▼──────┐   │
│   │Verify Fix   │   │
│   └──────┬──────┘   │
│          │          │
│   ┌──────▼──────┐   │
│   │Report       │   │
│   │Success      │   │
│   └─────────────┘   │
└─────────────────────┘
```

---

## 🎓 Key Concepts

### Agent-as-a-Tool Pattern

Agent 2 (NiFi Specialist) is wrapped as a tool for Agent 1:

```python
nifi_agent = LlmAgent(...)  # Specialist agent
nifi_tool = AgentTool(agent=nifi_agent)  # Wrap as tool
main_agent = LlmAgent(tools=[nifi_tool])  # Use as tool
```

**Benefits**:
- Reusable specialist agents
- Clean separation of concerns
- Session isolation
- Concurrent access support

### Sub-Agent Delegation

Agent 3 (Remediation) automatically activates when:
- Log contains `" ERROR "`
- Classification is `"ANOMALY"`

```python
main_agent = LlmAgent(
    sub_agents=[remediation_agent]  # Auto-delegation
)
```

### Human-in-the-Loop (HITL)

Critical commands require human approval:

```python
# Agent creates plan
plan = create_remediation_plan()

# Request approval
approval = await human_remediation_approval_tool(plan)

# Execute only if approved
if approval == "APPROVED":
    execute_command()
```

---

## 🔒 Security Features

### Enterprise-Grade Security

✅ **No Sudo Commands** - Automatically blocked
✅ **Rate Limiting** - 2-second minimum between commands
✅ **Timeout Protection** - 15-second default timeout
✅ **Command Validation** - Whitelist for safe operations
✅ **Human Approval** - Required for critical operations
✅ **Audit Trail** - All actions logged
✅ **Environment Variables** - No hardcoded credentials

### Command Whitelisting

**Safe commands** (skip approval):
```
ls, pwd, find, cat, ps, netstat, lsof, whoami,
tail, head, grep, df, systemctl, java
```

**Dangerous commands** (require approval):
```
rm, kill, systemctl restart, package installs,
config changes, service modifications
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - overview and quick start |
| [COMPREHENSIVE_DOCUMENTATION.md](COMPREHENSIVE_DOCUMENTATION.md) | Complete system documentation |
| [FLOWCHARTS.md](FLOWCHARTS.md) | Visual flowcharts and diagrams |
| [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) | 5-minute quick start guide |

---

## 📊 Sample Output

### Analysis Output (JSON)

```json
{
  "application": "HR_BOT",
  "classification": "ANOMALY",
  "severity": "HIGH",
  "component": "ExecuteStreamCommand",
  "likely_cause": "Missing Python module 'requests'",
  "nifi_correlation": "NiFi processor failed due to Python NameError",
  "recommendation": "Install requests module in Python environment"
}
```

### Remediation Plan

```
UNDERSTANDING: Python script executed by NiFi is missing the 'requests' 
               module, causing NameError and processor failure.

PLAN: Install the requests module:
      /path/to/venv/bin/pip install requests

RISK: LOW - Safe package installation, no system changes, 
           easily reversible

CONFIDENCE: 0.95 (HIGH) - Well-known error pattern with proven solution
```

---

## 🛠️ API Endpoints

### Analysis

- `POST /start-analysis` - Start log analysis (non-blocking)
- `GET /analysis-status` - Get real-time status
- `POST /stream/analyze-file` - Streaming analysis (SSE)

### Approvals

- `GET /approvals/pending` - List pending approvals
- `POST /approve/{request_id}` - Approve a plan
- `POST /reject/{request_id}` - Reject a plan
- `POST /feedback/{request_id}` - Send feedback

### System

- `GET /health` - Health check
- `GET /sessions` - List active sessions
- `GET /active-streams` - List active streams

**Full API Docs**: http://localhost:8000/docs

---

## 🎯 Use Cases

### 1. Application Log Analysis
Analyze application logs to find errors, warnings, and anomalies automatically.

### 2. Infrastructure Troubleshooting
Correlate application errors with NiFi infrastructure issues for root cause analysis.

### 3. Automated Remediation
Let AI create and execute remediation plans with your approval.

### 4. DevOps Automation
Integrate with CI/CD pipelines for automated log monitoring and alerting.

### 5. Incident Response
Quickly diagnose and respond to production incidents with AI assistance.

---

## 💡 Advanced Features

### Session State & Context Awareness

All agents maintain **session context**:
- Remember previous analyses
- Build cumulative understanding
- Reference historical correlations
- Provide context-aware recommendations

### Multi-Line Log Handling

Automatically groups stack traces:
```python
# Single log entry with multi-line stack trace
log_entry = """
2025-10-09 16:20:41 ERROR ...
Traceback (most recent call last):
  File "/path/to/script.py", line 34
    response = requests.post(...)
    ^^^^^^^^
NameError: name 'requests' is not defined
"""
```

### Confidence Scoring

Agent 3 provides confidence scores (0.0-1.0):
- **0.9-1.0**: HIGH - Known error, proven solution
- **0.7-0.8**: MEDIUM-HIGH - Standard approach
- **0.5-0.6**: MEDIUM - Experimental solution
- **0.3-0.4**: LOW - Uncertain approach

---

## 🚨 Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not found"**
```bash
echo "GOOGLE_API_KEY=your_key" > .env
```

**"Port 8000 already in use"**
```bash
lsof -ti:8000 | xargs kill -9
```

**"No logs found for correlation"**
```bash
ls logs/nifi_app/nifi-app.log  # Verify exists
```

**"Terminal not opening"**
- macOS: Grant Terminal automation permissions
- Linux: Install `xdotool`

More troubleshooting: See [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)

---

## 📈 Performance

- **Analysis Speed**: ~2-5 seconds per log entry
- **Throughput**: Depends on LLM API rate limits
- **Scalability**: Can process multiple files sequentially
- **Memory**: Minimal (streaming processing)

**Bottlenecks**:
- LLM API latency (~1-2s)
- NiFi log search (~0.5s)
- Rate limiting (2s between commands)

---

## 🔮 Roadmap

### Planned Features

- [ ] Multi-file concurrent processing
- [ ] Database storage (PostgreSQL/MongoDB)
- [ ] Email/Slack alerting
- [ ] Multiple log source correlation
- [ ] Auto-remediation for low-risk fixes
- [ ] Machine learning for pattern recognition
- [ ] Kubernetes deployment support
- [ ] Advanced metrics and analytics

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

[Specify your license]

---

## 🙏 Acknowledgments

- **Google Gemini & ADK** - Powerful AI capabilities
- **Apache NiFi** - Infrastructure log source
- **FastAPI** - Excellent API framework
- **Streamlit** - Beautiful dashboard UI

---

## 📞 Support

**Documentation**:
- [Comprehensive Docs](COMPREHENSIVE_DOCUMENTATION.md)
- [Flowcharts](FLOWCHARTS.md)
- [Quick Start](QUICK_START_GUIDE.md)

**Logs**:
- `agent_logs/` - Agent session logs
- `agent_outputs/` - Analysis results

**API Docs**: http://localhost:8000/docs

---

## 🎉 Get Started Now!

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
echo "GOOGLE_API_KEY=your_key" > .env

# 3. Run
python main.py  # Terminal 1
streamlit run unified_dashboard.py  # Terminal 2

# 4. Open browser
open http://localhost:8501
```

**Start analyzing your logs with AI! 🚀**

---

<div align="center">

**Multi-Agent Log Analysis System v1.0**

Built with ❤️ using Google Gemini, ADK, FastAPI, and Streamlit

*Intelligent log analysis for the modern DevOps era*

</div>

