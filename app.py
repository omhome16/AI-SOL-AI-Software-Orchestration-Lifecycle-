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
from orchestrator.graph import WorkflowGraph, ChatModifier
from orchestrator.central import CentralOrchestrator

# Load environment variables
load_dotenv()
Config.reload()

st.set_page_config(layout="wide")

# Load external CSS if present for a more professional UI
css_file = Path("static/css/main.css")
if css_file.exists():
    try:
        css_text = css_file.read_text(encoding='utf-8')
        st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)
    except Exception:
        # Fallback: small inline snippet
        st.markdown("<style>.stApp header{display:none}</style>", unsafe_allow_html=True)

# Display logo in sidebar if available
logo_path = Path("static/img/logo.svg")
if logo_path.exists():
    try:
        with st.sidebar:
            st.image(str(logo_path), width=140)
    except Exception:
        pass

# --- Session State Initialization ---
if 'project_name' not in st.session_state:
    st.session_state.project_name = ""
if 'requirements' not in st.session_state:
    st.session_state.requirements = ""
if 'workflow_running' not in st.session_state:
    st.session_state.workflow_running = False
if 'current_state' not in st.session_state:
    st.session_state.current_state = None
if 'output_log' not in st.session_state:
    st.session_state.output_log = []
if 'workflow_stage' not in st.session_state:
    st.session_state.workflow_stage = "idle"  # "idle", "requirements", "architecture", ... "done"


# --- Helper Functions ---
def log_message(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.output_log.append(f"[{timestamp}] [{level.upper()}] {message}")


# --- FIX: Asyncio Event Loop Helper ---
def get_or_create_event_loop():
    """Gets the existing event loop or creates a new one if none exists."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


# --- Streamlit UI ---
st.title("AI-SOL: AI Software Lifecycle Orchestrator")

with st.sidebar:
    st.header("Project Configuration")
    project_name_input = st.text_input("Project Name",
                                       value=st.session_state.project_name or f"project-{uuid.uuid4().hex[:8]}",
                                       disabled=st.session_state.workflow_running)

    requirements_input = st.text_area("Project Requirements", height=200, value=st.session_state.requirements,
                                      disabled=st.session_state.workflow_running)

    if st.button("Start AI-SOL Workflow", type="primary",
                 disabled=st.session_state.workflow_running or not requirements_input):
        if requirements_input:
            # --- FIX: Button only sets state, doesn't run the loop ---
            st.session_state.project_name = project_name_input
            st.session_state.requirements = requirements_input
            st.session_state.workflow_running = True
            st.session_state.workflow_stage = "start"
            st.session_state.output_log = []

            # Create the initial state
            workspace_path = Path(Config.WORKSPACE_DIR) / st.session_state.project_name
            user_context = {"enable_research": True, "github_repo": None}
            st.session_state.current_state = create_initial_state(
                task_id=st.session_state.project_name,
                project_name=st.session_state.project_name,
                requirements=st.session_state.requirements,
                workspace_path=str(workspace_path),
                user_context=user_context
            )

            log_message(f"🚀 Starting new project: {st.session_state.project_name}")
            log_message(f"📝 Requirements: {st.session_state.requirements}")
            st.rerun()  # Start the process
        else:
            st.warning("Please enter project requirements.")

    if st.session_state.workflow_running:
        st.info("Workflow is running... Check main area for updates.")

    if st.button("Clear Log / Reset"):
        st.session_state.output_log = []
        st.session_state.current_state = None
        st.session_state.project_name = f"project-{uuid.uuid4().hex[:8]}"
        st.session_state.requirements = ""
        st.session_state.workflow_running = False
        st.session_state.workflow_stage = "idle"
        st.rerun()

# --- Main Content Area ---
st.header("Workflow Progress and Output")

# --- FIX: Refactored Workflow State Machine ---
# This block runs on every rerun, checking the current stage and executing the next step.
if st.session_state.workflow_running and st.session_state.workflow_stage != "idle":

    loop = get_or_create_event_loop()

    # --- Load tools and agents (needed for each step) ---
    workspace_path = Path(Config.WORKSPACE_DIR) / st.session_state.project_name
    workspace_path.mkdir(parents=True, exist_ok=True)
    tools = Tools(workspace_path=str(workspace_path))
    Config.WORKSPACE_DIR = str(workspace_path)  # Update for current project

    try:
        Config.validate()
    except ValueError as e:
        log_message(f"Configuration Error: {e}", "error")
        st.session_state.workflow_running = False
        st.session_state.workflow_stage = "idle"

    # Instantiate orchestrator so we can create checkpoints and resume
    orchestrator = CentralOrchestrator(tools)

    # --- State Machine ---
    try:
        if st.session_state.workflow_stage == "start":
            st.session_state.workflow_stage = "requirements"
            st.rerun()
        # If we are awaiting human action on a checkpoint, show the review UI first
        if st.session_state.get('awaiting_user_action'):
            cp = st.session_state.get('checkpoint')
            if cp:
                # Load checkpoint payload for display
                try:
                    with open(cp['path'], 'r', encoding='utf-8') as f:
                        record = json.load(f)
                except Exception as e:
                    record = {"error": str(e)}

                st.warning(f"Paused for human review: checkpoint {cp['id']}")
                st.subheader("Checkpoint Preview")
                payload = record.get('payload', {})
                if payload.get('preview'):
                    st.code(payload.get('preview'), language='python')
                elif payload.get('output_summary'):
                    st.json(payload.get('output_summary'))
                else:
                    st.json(payload)

                colc, colm, colr, cola = st.columns(4)
                if colc.button("Continue"):
                    res = orchestrator.resume_checkpoint(cp['id'], 'continue')
                    log_message(f"Resume result: {res}")
                    st.session_state.awaiting_user_action = False
                    st.session_state.checkpoint = None
                    # advance to next stage
                    mapping = {
                        'requirements': 'architecture',
                        'architecture': 'developer',
                        'developer': 'qa',
                        'qa': 'devops',
                        'devops': 'finalize'
                    }
                    st.session_state.workflow_stage = mapping.get(st.session_state.workflow_stage, 'idle')
                    st.rerun()

                if colm.button("Modify File"):
                    # Show editor for modification
                    file_rel = payload.get('file') or payload.get('path_on_disk') or payload.get('file')
                    # If path_on_disk, try to convert to relative
                    if isinstance(file_rel, str) and file_rel.startswith('./workspace'):
                        # make relative to project
                        parts = file_rel.split(f"/workspace/{st.session_state.project_name}/")
                        if len(parts) == 2:
                            file_rel = parts[1]

                    st.session_state.modify_target_file = file_rel
                    st.session_state.modify_text = payload.get('preview', '')
                    # experimental_rerun may not exist in some Streamlit versions; use st.rerun() if available
                    try:
                        if hasattr(st, 'rerun'):
                            st.rerun()
                        elif hasattr(st, 'experimental_rerun'):
                            st.experimental_rerun()
                    except Exception:
                        # fallback: stop execution and wait for user to interact
                        st.stop()

                if colr.button("Retry Agent"):
                    res = orchestrator.resume_checkpoint(cp['id'], 'retry_agent', {})
                    log_message(f"Retry intent recorded: {res}")
                    st.session_state.awaiting_user_action = False
                    st.session_state.checkpoint = None
                    st.rerun()

                if cola.button("Abort Project"):
                    res = orchestrator.resume_checkpoint(cp['id'], 'abort')
                    log_message(f"Abort result: {res}")
                    st.session_state.workflow_running = False
                    st.session_state.workflow_stage = 'idle'
                    st.session_state.awaiting_user_action = False
                    st.rerun()

                # If modify action was initialized, show editor
                if st.session_state.get('modify_target_file'):
                    st.subheader(f"Modify: {st.session_state.modify_target_file}")
                    new_content = st.text_area("Edit file content", value=st.session_state.get('modify_text', ''), height=400)
                    if st.button("Save Modified File"):
                        payload = {"file": st.session_state.modify_target_file, "new_content": new_content}
                        res = orchestrator.resume_checkpoint(cp['id'], 'modify_file', payload)
                        log_message(f"Modify result: {res}")
                        # clear modify state and continue
                        st.session_state.modify_target_file = None
                        st.session_state.modify_text = None
                        st.session_state.awaiting_user_action = False
                        st.session_state.checkpoint = None
                        # re-run same stage
                        st.rerun()

                # Stop workflow progression until human acts
                st.stop()
        elif st.session_state.workflow_stage == "requirements":
            log_message("--- Requirements Analysis ---", "info")
            requirements_agent = RequirementsAgent(tools)
            req_output = loop.run_until_complete(requirements_agent.execute(st.session_state.current_state))
            st.session_state.current_state["requirements_output"] = req_output["requirements_output"]
            st.session_state.current_state["steps_completed"].append("requirements")
            log_message(f"Requirements Analysis Complete: {req_output['requirements_output'].get('success', False)}",
                        "success" if req_output['requirements_output'].get('success', False) else "error")
            # Update project state and create a human-review checkpoint for requirements
            try:
                requirements_agent.update_project_state(st.session_state.project_name, 'requirements', req_output.get('requirements_output', {}))
            except Exception:
                pass

            try:
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, requirements_agent.get_agent_name(), req_output.get("requirements_output", {}))
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    # Pause for human review
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.stop()
            except Exception:
                pass

            st.session_state.workflow_stage = "architecture"
            st.rerun()

        elif st.session_state.workflow_stage == "architecture":
            log_message("--- Architecture Design ---", "info")
            architect_agent = ArchitectAgent(tools)
            arch_output = loop.run_until_complete(architect_agent.execute(st.session_state.current_state))
            st.session_state.current_state["architecture_output"] = arch_output["architecture_output"]
            st.session_state.current_state["steps_completed"].append("architecture")
            log_message(f"Architecture Design Complete: {arch_output['architecture_output'].get('success', False)}",
                        "success" if arch_output['architecture_output'].get('success', False) else "error")
            # Update project state and create a checkpoint for architecture for human inspection
            try:
                architect_agent.update_project_state(st.session_state.project_name, 'architecture', arch_output.get('architecture_output', {}))
            except Exception:
                pass

            try:
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, architect_agent.get_agent_name(), arch_output.get("architecture_output", {}))
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.stop()
            except Exception:
                pass

            st.session_state.workflow_stage = "developer"
            st.rerun()

        elif st.session_state.workflow_stage == "developer":
            log_message("--- Code Generation ---", "info")
            developer_agent = DeveloperAgent(tools)
            # Prefer using orchestrator build plan if available
            try:
                # If developer supports execute_build_plan flow via orchestrator, call it
                build_resp = loop.run_until_complete(orchestrator.execute_build_plan(st.session_state.current_state))
                # If interrupted due to checkpoint, record it and pause
                if isinstance(build_resp, dict) and build_resp.get('interrupted'):
                    st.session_state.checkpoint = build_resp.get('checkpoint')
                    st.session_state.awaiting_user_action = True
                    st.rerun()

                # Otherwise, expect generated_files in response
                st.session_state.current_state.setdefault('generated_files', [])
                if build_resp.get('generated_files'):
                    st.session_state.current_state['generated_files'].extend(build_resp.get('generated_files'))
                st.session_state.current_state['developer_output'] = {"success": build_resp.get('success', False), "data": build_resp}
                st.session_state.current_state['steps_completed'].append('developer')
                log_message(f"Code Generation Complete: {build_resp.get('success', False)}", "success" if build_resp.get('success', False) else "error")
                # Update project state
                try:
                    developer_agent.update_project_state(st.session_state.project_name, 'developer', st.session_state.current_state.get('developer_output', {}))
                except Exception:
                    pass
            except Exception:
                # Fallback to legacy developer.execute()
                dev_output = loop.run_until_complete(developer_agent.execute(st.session_state.current_state))
                st.session_state.current_state["developer_output"] = dev_output["developer_output"]
                st.session_state.current_state.setdefault('generated_files', [])
                st.session_state.current_state["generated_files"].extend(dev_output.get("generated_files", []))
                st.session_state.current_state["steps_completed"].append("developer")
                log_message(f"Code Generation Complete: {dev_output['developer_output'].get('success', False)}",
                            "success" if dev_output['developer_output'].get('success', False) else "error")

            # Create a checkpoint for developer stage if interrupts enabled
            try:
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, developer_agent.get_agent_name(), st.session_state.current_state.get('developer_output', {}))
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.stop()
            except Exception:
                pass

            st.session_state.workflow_stage = "qa"
            st.rerun()

        elif st.session_state.workflow_stage == "qa":
            log_message("--- Quality Assurance ---", "info")
            qa_agent = QAAgent(tools)
            qa_output = loop.run_until_complete(qa_agent.execute(st.session_state.current_state))
            st.session_state.current_state["qa_output"] = qa_output["qa_output"]
            st.session_state.current_state["code_quality_score"] = qa_output.get("code_quality_score", 0.0)
            st.session_state.current_state["test_coverage"] = qa_output.get("test_coverage", 0.0)
            st.session_state.current_state["security_issues"] = qa_output.get("security_issues", [])
            st.session_state.current_state["steps_completed"].append("qa")
            log_message(f"Quality Assurance Complete: {qa_output['qa_output'].get('success', False)}",
                        "success" if qa_output['qa_output'].get('success', False) else "error")
            # Update project state and create QA checkpoint for review
            try:
                qa_agent.update_project_state(st.session_state.project_name, 'qa', qa_output.get('qa_output', {}))
            except Exception:
                pass

            try:
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, qa_agent.get_agent_name(), qa_output.get("qa_output", {}))
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.stop()
            except Exception:
                pass

            st.session_state.workflow_stage = "devops"
            st.rerun()

        elif st.session_state.workflow_stage == "devops":
            log_message("--- DevOps Configuration ---", "info")
            devops_agent = DevOpsAgent(tools)
            devops_output = loop.run_until_complete(devops_agent.execute(st.session_state.current_state))
            st.session_state.current_state["devops_output"] = devops_output["devops_output"]
            st.session_state.current_state["generated_files"].extend(devops_output.get("generated_files", []))
            st.session_state.current_state["steps_completed"].append("devops")
            log_message(f"DevOps Configuration Complete: {devops_output['devops_output'].get('success', False)}",
                        "success" if devops_output['devops_output'].get('success', False) else "error")
            # Update project state and create checkpoint for devops
            try:
                devops_agent.update_project_state(st.session_state.project_name, 'devops', devops_output.get('devops_output', {}))
            except Exception:
                pass

            try:
                if orchestrator.interrupts_enabled:
                    cp = orchestrator.checkpoint_agent_output(st.session_state.project_name, devops_agent.get_agent_name(), devops_output.get("devops_output", {}))
                    st.session_state.checkpoint = cp
                    st.session_state.awaiting_user_action = True
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.stop()
            except Exception:
                pass

            st.session_state.workflow_stage = "finalize"
            st.rerun()

        elif st.session_state.workflow_stage == "finalize":
            log_message("--- Finalizing Project ---", "info")
            workflow = WorkflowGraph(tools=tools)  # Only need the graph for _finalize
            final_state = loop.run_until_complete(workflow._finalize(st.session_state.current_state))
            log_message(
                f"✅ Project '{st.session_state.project_name}' completed with status: {final_state['status'].value}",
                "success")
            st.session_state.current_state = final_state.copy()
            st.session_state.workflow_running = False
            st.session_state.workflow_stage = "done"
            st.rerun()

    except Exception as e:
        log_message(f"❌ An error occurred during workflow execution: {e}", "error")

        # Let the Orchestrator LLM decide whether to retry, proceed, or abort
        try:
            orchestrator = CentralOrchestrator(tools)
            decision = loop.run_until_complete(
                orchestrator.reason_and_act(
                    st.session_state.current_state,
                    f"Runtime exception occurred during workflow: {e}"
                )
            )
            action = decision.get('action') if isinstance(decision, dict) else 'proceed'
            log_message(f"Orchestrator decision after error: {action}", "info")

            if action in ('retry', 'delegate_to_agent'):
                # retry the current stage
                st.session_state.workflow_running = True
                # keep the same stage so rerun will attempt it again
                st.rerun()
            elif action == 'proceed':
                # attempt to advance to the next logical stage
                # mark current stage completed and move on
                current = st.session_state.workflow_stage
                if current and current not in st.session_state.current_state.get('steps_completed', []):
                    st.session_state.current_state.setdefault('steps_completed', []).append(current)
                # advance stage
                # simple mapping: requirements->architecture->developer->qa->devops->finalize
                mapping = {
                    'requirements': 'architecture',
                    'architecture': 'developer',
                    'developer': 'qa',
                    'qa': 'devops',
                    'devops': 'finalize'
                }
                st.session_state.workflow_stage = mapping.get(st.session_state.workflow_stage, 'idle')
                st.session_state.workflow_running = True
                st.rerun()
            else:
                # abort by default
                st.session_state.workflow_running = False
                st.session_state.workflow_stage = 'idle'
                st.rerun()

        except Exception as inner_e:
            log_message(f"Orchestrator decision failed: {inner_e}", "error")
            st.session_state.workflow_running = False
            st.session_state.workflow_stage = "idle"
            st.rerun()

# Display Log
st.subheader("Execution Log")
log_container = st.container()
with log_container:
    # Progress bar based on steps completed (5 main stages)
    steps = st.session_state.current_state.get('steps_completed', []) if st.session_state.current_state else []
    total_stages = 5
    progress = int(len(steps) / total_stages * 100) if total_stages else 0
    st.progress(progress / 100 if isinstance(progress, int) else 0)

    for entry in st.session_state.output_log:
        if "[ERROR]" in entry:
            st.error(entry)
        elif "[WARNING]" in entry:
            st.warning(entry)
        elif "[SUCCESS]" in entry:
            st.success(entry)
        else:
            st.info(entry)

# Display Current State (if available)
if st.session_state.current_state:
    st.subheader("Current Project State")
    state = st.session_state.current_state

    # st.json(state) # Display full state for debugging

    col1, col2, col3 = st.columns(3)
    col1.metric("Project Status", state.get('status', TaskStatus.PENDING).value)
    col2.metric("Current Stage", st.session_state.workflow_stage)
    col3.metric("Steps Completed", len(state.get('steps_completed', [])))

    st.text(f"Steps: {', '.join(state.get('steps_completed', []))}")

    # Display Agent Outputs
    with st.expander("Agent Outputs (JSON)", expanded=False):
        if state.get("requirements_output"):
            st.json(state["requirements_output"], expanded=False)
        if state.get("architecture_output"):
            st.json(state["architecture_output"], expanded=False)
        if state.get("developer_output"):
            st.json(state["developer_output"], expanded=False)
        if state.get("qa_output"):
            st.json(state["qa_output"], expanded=False)
        if state.get("devops_output"):
            st.json(state["devops_output"], expanded=False)

    # Display Generated Files
    if state.get("generated_files"):
        st.subheader("Generated Files")
        for file_path in state.get("generated_files", []):
            st.code(f"{file_path}", language="text")

    if state.get("generated_documents"):
        st.subheader("Generated Documents")
        for doc_info in state.get("generated_documents", []):
            st.markdown(f"**{doc_info['type']}**: `{doc_info['path']}`")
