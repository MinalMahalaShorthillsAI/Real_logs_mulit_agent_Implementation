"""
Unified Dashboard for Multi-Agent Log Analysis
Combines: Trigger Analysis + Approval Dashboard
"""

import streamlit as st
import requests
import os
from dotenv import load_dotenv
import time
from datetime import datetime

load_dotenv()
API_BASE = os.getenv("API_BASE_URL")

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Log Analysis Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
    
    .plan-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API Base URL", value=API_BASE)
    
    st.divider()
    
    st.header("📊 System Status")
    try:
        health_response = requests.get(f"{api_url}/health", timeout=2)
        if health_response.status_code == 200:
            st.success("✅ API Connected")
            data = health_response.json()
            st.caption(f"Agents: {', '.join(data.get('agents', []))}")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")
    
    st.divider()
    
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()

# Main Title
st.title("🤖 Multi-Agent Log Analysis Dashboard")
st.markdown("**Complete control center for log analysis and remediation approval**")
st.divider()

# Create tabs
tab1, tab2 = st.tabs(["🚀 Trigger Analysis", "✅ Approve Plans"])

# ============================================================
# TAB 1: TRIGGER ANALYSIS
# ============================================================
with tab1:
    st.header("🚀 Trigger Log Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📁 Select Log File")
        
        # Option 1: Select from available files
        log_dir = "logs"
        if os.path.exists(log_dir):
            log_files = []
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.log'):
                        log_files.append(os.path.join(root, file))
            
            if log_files:
                selected_file = st.selectbox("Available log files:", log_files)
            else:
                st.warning("No .log files found in logs/ directory")
                selected_file = None
        else:
            st.warning("logs/ directory not found")
            selected_file = None
        
        # Option 2: Manual path entry
        st.markdown("**Or enter path manually:**")
        manual_path = st.text_input("Log file path:", value=selected_file if selected_file else "")
    
    with col2:
        st.subheader("📊 File Info")
        if manual_path and os.path.exists(manual_path):
            file_size = os.path.getsize(manual_path) / 1024  # KB
            try:
                with open(manual_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                st.metric("File Size", f"{file_size:.1f} KB")
                st.metric("Total Lines", line_count)
            except:
                st.info("Could not read file")
        else:
            st.info("Select a file to see info")
    
    st.divider()
    
    # Single trigger button
    trigger_btn = st.button("🚀 Start Stream Analysis", type="primary", use_container_width=True)
    
    # Execute stream analysis
    if trigger_btn:
        if not manual_path:
            st.error("❌ Please select or enter a log file path")
        else:
            with st.spinner("🔄 Starting analysis..."):
                try:
                    endpoint = f"{api_url}/start-analysis"
                    payload = {"file_path": manual_path}
                    
                    # Use the background endpoint - returns immediately
                    response = requests.post(endpoint, json=payload, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success("✅ Analysis started successfully!")
                        st.json(data)
                    else:
                        st.error(f"❌ Failed to start analysis: {response.status_code}")
                        st.code(response.text)
                        
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out - Server might be busy")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to API - Is the FastAPI server running?")
                    st.code(f"python main.py", language="bash")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Show status section ALWAYS (outside the if block)
    st.divider()
    st.subheader("📊 Analysis Status")
    
    # Get current status
    try:
        status_response = requests.get(f"{api_url}/analysis-status", timeout=2)
        if status_response.status_code == 200:
            status_data = status_response.json()
            
            # Debug expander to see raw data
            with st.expander("🔍 Debug - Raw Status Data"):
                st.json(status_data)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if status_data["is_running"]:
                    st.success("🔴 Status: LIVE - Running")
                else:
                    st.info("⚪ Status: Idle")
            with col2:
                st.metric("Logs Processed", status_data.get("logs_processed", 0))
            with col3:
                st.metric("🕐 Last Update", datetime.now().strftime("%H:%M:%S"))
            
            # Show current log being processed
            if status_data.get("current_log"):
                st.markdown("### 📋 Current Log Being Analyzed")
                st.code(status_data["current_log"], language="text")
            
            # Show important events only (without emojis)
            if status_data.get("agent_events"):
                st.markdown("### 📜 Recent Activity (Live Stream)")
                # Create a scrollable container
                activity_container = st.container()
                with activity_container:
                    for event in reversed(status_data["agent_events"][-20:]):
                        st.text(f"[{event['time']}] {event['message']}")
            else:
                st.info("💡 No activity yet. Start analysis to see live updates here.")
            
            # Check for pending approvals and show notification
            try:
                approval_response = requests.get(f"{api_url}/approvals/pending", timeout=1)
                if approval_response.status_code == 200:
                    approval_data = approval_response.json()
                    pending_approvals = approval_data.get("pending_approvals", {})
                    if pending_approvals:
                        st.warning(f"🔔 **{len(pending_approvals)} Approval Request(s) Pending!** Switch to 'Approve Plans' tab →")
            except:
                pass  # Silently ignore if can't check approvals
            
            # Real-time auto-refresh - updates every 1 second when running
            # DISABLED to prevent blur in other tabs
            # if status_data["is_running"]:
            #     time.sleep(1)  # 1 second for real-time feel
            #     st.rerun()
    
    except Exception as e:
        st.warning(f"⚠️ Could not fetch status: {e}")
    
    st.divider()
    st.info("💡 **Tip:** Switch to 'Approve Plans' tab to handle approval requests when they appear")

# ============================================================
# TAB 2: APPROVAL DASHBOARD
# ============================================================
with tab2:
    st.header("✅ Remediation Plan Approvals")
    
    # Manual refresh button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    with col2:
        st.caption("💡 Click refresh to check for new approval requests")
    
    st.divider()
    
    # Fetch pending approvals
    def get_pending_approvals():
        try:
            response = requests.get(f"{api_url}/approvals/pending", timeout=5)
            st.write(f"DEBUG: API Response Status: {response.status_code}")  # DEBUG
            if response.status_code == 200:
                data = response.json()
                st.write(f"DEBUG: Raw data: {data}")  # DEBUG
                approvals = data.get("pending_approvals", {})
                st.write(f"DEBUG: Approvals extracted: {len(approvals)} items")  # DEBUG
                return approvals
            return {}
        except Exception as e:
            st.error(f"❌ Error fetching approvals: {e}")
            import traceback
            st.code(traceback.format_exc())
            return {}
    
    def approve_request(request_id):
        try:
            response = requests.post(f"{api_url}/approve/{request_id}", timeout=5)
            if response.status_code == 200:
                st.success(f"✅ Request {request_id} approved!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Failed to approve: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    def reject_request(request_id):
        try:
            response = requests.post(f"{api_url}/reject/{request_id}", timeout=5)
            if response.status_code == 200:
                st.warning(f"❌ Request {request_id} rejected!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Failed to reject: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    def send_feedback(request_id, feedback):
        try:
            response = requests.post(
                f"{api_url}/feedback/{request_id}",
                params={"feedback": feedback},
                timeout=5
            )
            if response.status_code == 200:
                st.success(f"💬 Feedback sent for request {request_id}!")
                st.info("Agent will modify the plan based on your suggestions...")
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ Failed to send feedback: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    approvals = get_pending_approvals()
    pending_count = len(approvals)
    
    # Debug: Show raw data
    with st.expander("🔍 Debug Info"):
        st.json({
            "pending_count": pending_count, 
            "approval_ids": list(approvals.keys()) if approvals else [],
            "full_data": approvals
        })
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏳ Pending Approvals", pending_count)
    with col2:
        st.metric("✅ Status", "Active" if pending_count > 0 else "Idle")
    with col3:
        st.metric("🕐 Last Check", datetime.now().strftime("%H:%M:%S"))
    
    st.divider()
    
    # Display approvals
    if pending_count == 0:
        st.info("✅ **No pending approvals** - All remediation plans have been reviewed!")
        
        # Show execution logs from terminal
        st.markdown("---")
        st.subheader("📜 Execution Logs")
        st.info("💡 **Tip:** After approving a plan, check your **FastAPI terminal** to see real-time execution progress and command outputs.")
        
        with st.expander("🔍 Where to see execution details"):
            st.markdown("""
            **After you approve a plan:**
            1. ✅ The approval is sent to the agent
            2. 🔧 The agent executes the command in the terminal
            3. 📊 Results appear in the **FastAPI server terminal** (where you ran `python main.py`)
            4. 🤖 The agent may present a new plan based on the results
            
            **To see execution progress:**
            - Look at the terminal where `python main.py` is running
            - You'll see command outputs and agent responses there
            - New approval requests will appear here automatically
            """)
    else:
        st.success(f"📋 **{pending_count} Approval Request{'s' if pending_count > 1 else ''} Found!**")
        
        for request_id, approval in approvals.items():
            with st.container():
                # Card header
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### 🔖 Request ID: `{request_id}`")
                with col2:
                    created_time = datetime.fromtimestamp(approval.get("created_at", 0))
                    st.caption(f"⏰ {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Plan details - handle both old and new format
                plan_content = approval.get("plan", "") or approval.get("plan_text", "")
                
                # Try to parse the structured format
                if "UNDERSTANDING:" in plan_content:
                    # New format: all in one string
                    st.markdown("**📋 Remediation Plan:**")
                    st.text_area("Plan Details", plan_content, height=300, disabled=True, key=f"plan_display_{request_id}", label_visibility="collapsed")
                else:
                    # Old format: separate fields
                    st.markdown("**🧠 Understanding:**")
                    st.info(approval.get("understanding", "N/A"))
                    
                    st.markdown("**📋 Plan:**")
                    st.code(plan_content or "No plan details", language="text")
                    
                # Action buttons
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Approve", key=f"approve_{request_id}", type="primary", use_container_width=True):
                        approve_request(request_id)
                        st.success("✅ Approved! Check the FastAPI terminal for execution progress.")
                with col2:
                    if st.button("❌ Reject", key=f"reject_{request_id}", use_container_width=True):
                        reject_request(request_id)
                
                # Feedback/Suggestion section
                with st.expander("💬 Provide Feedback / Suggestions"):
                    feedback = st.text_area(
                        "Your suggestions for modifying the plan:",
                        key=f"feedback_{request_id}",
                        placeholder="e.g., 'Use df -h instead of df', 'Check /var/log first', 'Add error handling'...",
                        height=100
                    )
                    if st.button("📝 Send Feedback", key=f"feedback_btn_{request_id}", use_container_width=True):
                        if feedback.strip():
                            send_feedback(request_id, feedback)
                        else:
                            st.warning("Please enter your feedback first!")
                
                st.divider()

# Footer
st.markdown("---")
st.caption("🤖 Multi-Agent Log Analysis System | Powered by ADK, Gemini & Streamlit")
