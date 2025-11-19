from datetime import datetime
import streamlit as st
import asyncio
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.devops import DevOpsAgent
from agents.qa import QAAgent
from agents.requirements import RequirementsAgent
from core.config import Config
from core.state import create_initial_state, WorkflowState, TaskStatus
from core.tools import Tools
from orchestrator.graph import WorkflowGraph
from orchestrator.central import CentralOrchestrator

# Load environment variables
load_dotenv()
Config.reload()

st.set_page_config(
    page_title="AI-SOL: AI Software Lifecycle",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Loading ---
def load_css():
    css_file = Path("static/css/main.css")
    if css_file.exists():
        try:
            css_text = css_file.read_text(encoding='utf-8')
            st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)
        except Exception:
            pass

load_css()

# --- Session State Initialization ---
if 'project_id' not in st.session_state:
    st.session_state.project_id = f"proj-{uuid.uuid4().hex[:8]}"
if 'project_name' not in st.session_state:
    st.session_state.project_name = "MyAIProject"
if 'requirements' not in st.session_state:
    st.session_state.requirements = ""
if 'workflow_running' not in st.session_state:
    st.session_state.workflow_running = False
if 'current_state' not in st.session_state:
    st.session_state.current_state = None
if 'output_log' not in st.session_state:
    st.session_state.output_log = []
if 'workflow_stage' not in st.session_state:
    st.session_state.workflow_stage = "idle"
if 'tools' not in st.session_state:
    st.session_state.tools = None

# --- Helper Functions ---
def log_message(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    st.session_state.output_log.append(entry)

def render_log():
    st.subheader("System Log")
    log_html = '<div class="log-container">'
    for entry in reversed(st.session_state.output_log): # Show newest first
        color_class = f"log-{entry['level']}"
        log_html += f'<div class="log-entry {color_class}">[{entry["timestamp"]}] {entry["message"]}</div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)

def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

def init_tools_if_needed():
    workspace_path = Path(Config.WORKSPACE_DIR) / st.session_state.project_name
    # Re-init if path changed or not set
    if not st.session_state.tools or st.session_state.tools.workspace_path != str(workspace_path):
        workspace_path.mkdir(parents=True, exist_ok=True)
        st.session_state.tools = Tools(workspace_path=str(workspace_path))
        Config.WORKSPACE_DIR = str(workspace_path)

# --- Sidebar ---
with st.sidebar:
    st.title("⚡ AI-SOL")
    st.markdown("### Configuration")
    
    st.text_input("Project Name", key="project_name_input", 
                  value=st.session_state.project_name,
                  disabled=st.session_state.workflow_running)
    
    st.text_area("Requirements", key="requirements_input", height=200,
                 value=st.session_state.requirements,
                 placeholder="Describe your application in detail...",
                 disabled=st.session_state.workflow_running)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start", type="primary", disabled=st.session_state.workflow_running):
            if st.session_state.requirements_input:
                st.session_state.project_name = st.session_state.project_name_input.strip().replace(" ", "_")
                st.session_state.requirements = st.session_state.requirements_input
                st.session_state.workflow_running = True
                st.session_state.workflow_stage = "start"
                st.session_state.output_log = [] # Clear log on new run
                
                # Init State
                workspace_path = Path(Config.WORKSPACE_DIR) / st.session_state.project_name
                st.session_state.current_state = create_initial_state(
                    task_id=st.session_state.project_id,
                    project_name=st.session_state.project_name,
                    requirements=st.session_state.requirements,
                    workspace_path=str(workspace_path),
                    user_context={"enable_research": True}
                )
                log_message(f"Starting project: {st.session_state.project_name}", "info")
                st.rerun()
            else:
                st.warning("Reqs needed!")

    with col2:
        if st.button("🔄 Reset"):
            st.session_state.workflow_running = False
            st.session_state.workflow_stage = "idle"
            st.session_state.current_state = None
            st.session_state.output_log = []
            st.session_state.project_id = f"proj-{uuid.uuid4().hex[:8]}"
            st.rerun()

    st.markdown("---")
    st.markdown("### Status")
    if st.session_state.workflow_running:
        st.success(f"Running: {st.session_state.workflow_stage.upper()}")
    else:
        st.info("Idle")

# --- Main Content ---
st.title(f"Project: {st.session_state.project_name}")

# Workflow Stages Visualization
stages = ["requirements", "architecture", "developer", "qa", "devops"]
current_stage_idx = -1
if st.session_state.workflow_stage in stages:
    current_stage_idx = stages.index(st.session_state.workflow_stage)
elif st.session_state.workflow_stage == "finalize" or st.session_state.workflow_stage == "done":
    current_stage_idx = len(stages)

# Custom Progress Bar
cols = st.columns(len(stages))
for i, stage in enumerate(stages):
    color = "var(--text-secondary)"
    weight = "400"
    if i < current_stage_idx:
        color = "var(--success-color)" # Completed
        weight = "600"
    elif i == current_stage_idx:
        color = "var(--primary-color)" # Current
        weight = "700"
    
    cols[i].markdown(f"<div style='text-align:center; color:{color}; font-weight:{weight}'>{stage.capitalize()}</div>", unsafe_allow_html=True)
st.progress(max(0, min(100, int((current_stage_idx / len(stages)) * 100))))
st.markdown("---")

# --- Workflow Execution Logic ---
if st.session_state.workflow_running and st.session_state.workflow_stage != "idle":
    loop = get_or_create_event_loop()
    init_tools_if_needed()
    tools = st.session_state.tools
    orchestrator = CentralOrchestrator(tools)

    # Handle Checkpoints/Interrupts
    if st.session_state.get('awaiting_user_action'):
        cp = st.session_state.get('checkpoint')
        if cp:
            st.warning(f"✋ Checkpoint: {cp['step']}")
            
            with st.expander("Inspect Generated Content", expanded=True):
                payload = cp.get('payload', {})
                if payload.get('preview'):
                    st.code(payload.get('preview'), language='python')
                else:
                    st.json(payload)

            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Approve & Continue"):
                orchestrator.resume_checkpoint(cp['id'], 'continue')
                st.session_state.awaiting_user_action = False
                st.session_state.checkpoint = None
                st.rerun()
            
            if c2.button("🔁 Retry Step"):
                 orchestrator.resume_checkpoint(cp['id'], 'retry_agent', {})
                 st.session_state.awaiting_user_action = False
                 st.session_state.checkpoint = None
                 st.rerun()
                 
            if c3.button("🛑 Abort"):
                orchestrator.resume_checkpoint(cp['id'], 'abort')
                st.session_state.workflow_running = False
                st.session_state.workflow_stage = "idle"
                st.session_state.awaiting_user_action = False
                st.rerun()
            
            st.stop() # Halt execution until user acts

    # State Machine
    try:
        if st.session_state.workflow_stage == "start":
             st.session_state.workflow_stage = "requirements"
             st.rerun()

        elif st.session_state.workflow_stage == "requirements":
            with st.spinner("Analysing Requirements..."):
                agent = RequirementsAgent(tools)
                output = loop.run_until_complete(agent.execute(st.session_state.current_state))
                st.session_state.current_state.update(output)
                st.session_state.current_state["steps_completed"].append("requirements")
                
                log_message("Requirements analysis complete", "success")
                
                # Create Checkpoint
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, "requirements", output)
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    st.rerun()
                
                st.session_state.workflow_stage = "architecture"
                st.rerun()

        elif st.session_state.workflow_stage == "architecture":
            with st.spinner("Designing Architecture..."):
                agent = ArchitectAgent(tools)
                output = loop.run_until_complete(agent.execute(st.session_state.current_state))
                st.session_state.current_state.update(output)
                st.session_state.current_state["steps_completed"].append("architecture")
                
                log_message("Architecture design complete", "success")

                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, "architecture", output)
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    st.rerun()

                st.session_state.workflow_stage = "developer"
                st.rerun()

        elif st.session_state.workflow_stage == "developer":
            with st.spinner("Generating Code..."):
                # Register agents for orchestrator to use
                dev_agent = DeveloperAgent(tools)
                qa_agent = QAAgent(tools)
                orchestrator.register_agents({'developer': dev_agent, 'qa': qa_agent})

                # Use orchestrator's smart build plan execution
                build_res = loop.run_until_complete(orchestrator.execute_build_plan(st.session_state.current_state))
                
                if build_res.get('interrupted'):
                    st.session_state.checkpoint = build_res.get('checkpoint')
                    st.session_state.awaiting_user_action = True
                    st.rerun()
                
                st.session_state.current_state["developer_output"] = build_res
                st.session_state.current_state["steps_completed"].append("developer")
                log_message(f"Code generation complete. Files: {len(build_res.get('generated_files', []))}", "success")
                
                st.session_state.workflow_stage = "qa"
                st.rerun()

        elif st.session_state.workflow_stage == "qa":
            with st.spinner("Running QA..."):
                agent = QAAgent(tools)
                output = loop.run_until_complete(agent.execute(st.session_state.current_state))
                st.session_state.current_state.update(output)
                st.session_state.current_state["steps_completed"].append("qa")
                log_message("QA complete", "success")

                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, "qa", output)
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    st.rerun()

                st.session_state.workflow_stage = "devops"
                st.rerun()

        elif st.session_state.workflow_stage == "devops":
            with st.spinner("Configuring DevOps..."):
                agent = DevOpsAgent(tools)
                output = loop.run_until_complete(agent.execute(st.session_state.current_state))
                st.session_state.current_state.update(output)
                st.session_state.current_state["steps_completed"].append("devops")
                log_message("DevOps config complete", "success")

                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, "devops", output)
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    st.rerun()

                st.session_state.workflow_stage = "finalize"
                st.rerun()

        elif st.session_state.workflow_stage == "finalize":
            st.session_state.workflow_stage = "done"
            st.session_state.workflow_running = False
            st.success("Workflow Completed Successfully!")
            st.rerun()

    except Exception as e:
        log_message(f"Error: {str(e)}", "error")
        st.error(f"An error occurred: {e}")
        st.session_state.workflow_running = False

# --- Results Display ---
if st.session_state.current_state:
    state = st.session_state.current_state
    
    # Tabs for details
    tab1, tab2, tab3, tab4 = st.tabs(["Files", "Architecture", "QA Report", "Raw State"])
    
    with tab1:
        st.subheader("Generated Files")
        files = state.get("generated_files", [])
        if files:
            selected_file = st.selectbox("Select file to view", files)
            if selected_file:
                try:
                    path = Path(Config.WORKSPACE_DIR) / st.session_state.project_name / selected_file
                    if path.exists():
                        st.code(path.read_text(encoding='utf-8'))
                    else:
                        st.warning("File not found on disk")
                except Exception as e:
                     st.error(f"Could not read file: {e}")
        else:
            st.info("No files generated yet.")

    with tab2:
        st.subheader("Architecture Blueprint")
        if state.get("architecture_output"):
            st.json(state["architecture_output"])
        else:
            st.info("Architecture not yet designed.")

    with tab3:
        st.subheader("Quality Assurance")
        if state.get("qa_output"):
            metrics = state.get("qa_output", {}).get("qa_output", {})
            c1, c2 = st.columns(2)
            c1.metric("Quality Score", metrics.get("code_quality_score", 0))
            c2.metric("Test Coverage", f"{metrics.get('test_coverage', 0)}%")
            st.json(metrics)
        else:
            st.info("QA not yet run.")
            
    with tab4:
        st.json(state)

render_log()