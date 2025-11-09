"""Mock end-to-end harness for the new plan-driven flow.

This script demonstrates (locally) how the ArchitectAgent -> Orchestrator -> DeveloperAgent -> QA flow
can be exercised with mocked LLM behavior. It does NOT call real LLMs. Use for quick integration testing.
"""
import asyncio
from pathlib import Path
from typing import Dict, Any

from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from orchestrator.central import CentralOrchestrator
from utils.context_manager import ContextManager, AgentContext, ProjectBlueprint, FileTask
from utils.project_classifier import ProjectType


class MockLLM:
    def __init__(self, role):
        self.role = role

    async def ainvoke(self, prompt):
        # Mock behavior: return small, valid outputs depending on role and hints in prompt
        if self.role == 'architect':
            # return a ProjectBlueprint-like dict
            return {
                'explanation': 'Mock FastAPI app',
                'folder_structure': ['app/models', 'app/services', 'app'],
                'build_plan': [
                    {'path': 'app/models/user.py', 'purpose': 'User model', 'dependencies': []},
                    {'path': 'app/services/user_service.py', 'purpose': 'User service', 'dependencies': ['app/models/user.py']},
                    {'path': 'app/main.py', 'purpose': 'Main FastAPI app', 'dependencies': ['app/services/user_service.py']},
                    {'path': 'requirements.txt', 'purpose': 'Aggregate dependencies', 'dependencies': []},
                    {'path': 'README.md', 'purpose': 'Project README', 'dependencies': []}
                ]
            }
        elif self.role == 'developer':
            # Return mock code based on file type mentioned in prompt
            if '.py' in prompt and 'models' in prompt:
                return '# Mock User model\n\nclass User:\n    def __init__(self, name: str):\n        self.name = name\n'
            elif '.py' in prompt and 'services' in prompt:
                return '# Mock User service\n\nfrom ..models.user import User\n\nclass UserService:\n    def get_user(self, name: str) -> User:\n        return User(name)\n'
            elif '.py' in prompt and 'main.py' in prompt:
                return '# Mock FastAPI app\n\nfrom fastapi import FastAPI\nfrom .services.user_service import UserService\n\napp = FastAPI()\nuser_service = UserService()\n\n@app.get("/user/{name}")\ndef get_user(name: str):\n    return user_service.get_user(name)\n'
            elif 'requirements.txt' in prompt:
                return 'fastapi==0.100.0\nuvicorn==0.20.0\n'
            elif 'README.md' in prompt:
                return '# Mock Project\n\nA simple FastAPI mock app.\n\n## Setup\n\n```bash\npip install -r requirements.txt\n```\n'
            else:
                # Default Python file
                return 'def hello():\n    return "hello"\n'
        elif self.role == 'qa':
            return {'valid': True, 'error': None}
        return ''


async def run_mock_build():
    # Setup context
    project_id = 'mock_project'
    ctx_mgr = ContextManager(base_dir='./workspace/.context')
    # Use a valid ProjectType for test context (BACKEND_API fits a simple API)
    context = ctx_mgr.create_initial_context(project_id, project_id, 'Create a simple API', project_type=ProjectType.BACKEND_API)
    # inject minimal technology stack
    context.technology_stack = context.technology_stack
    context.project_root = './workspace/mock_project'
    ctx_mgr.save_context(project_id, context)

    # Minimal tools object used by agents and orchestrator in tests
    class MockTools:
        def count_tokens(self, text: str) -> int:
            return len(text.split())

        def write_file(self, path: str, content: str) -> Dict[str, Any]:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return {"success": True}

        def generate_code(self, **kwargs):
            # Parse task hints from kwargs
            task_obj = kwargs.get('task', {})
            task_path = getattr(task_obj, 'path', None)
            if not task_path and isinstance(task_obj, dict):
                task_path = task_obj.get('path', '')

            # Return mock code based on file type and path hints
            if task_path and '.py' in task_path and 'models' in task_path:
                return '# Mock User model\n\nclass User:\n    def __init__(self, name: str):\n        self.name = name\n'
            elif task_path and '.py' in task_path and 'services' in task_path:
                return '# Mock User service\n\nfrom ..models.user import User\n\nclass UserService:\n    def get_user(self, name: str) -> User:\n        return User(name)\n'
            elif task_path and '.py' in task_path and 'main.py' in task_path:
                return '# Mock FastAPI app\n\nfrom fastapi import FastAPI\nfrom .services.user_service import UserService\n\napp = FastAPI()\nuser_service = UserService()\n\n@app.get("/user/{name}")\ndef get_user(name: str):\n    return user_service.get_user(name)\n'
            elif task_path and 'requirements.txt' in task_path:
                return 'fastapi==0.100.0\nuvicorn==0.20.0\n'
            elif task_path and 'README.md' in task_path:
                return '# Mock Project\n\nA simple FastAPI mock app.\n\n## Setup\n\n```bash\npip install -r requirements.txt\n```\n'
            else:
                # Default Python file
                return 'def hello():\n    return "hello"\n'

    tools = MockTools()

    # Create agents with mock LLMs. ArchitectAgent/DeveloperAgent/QAAgent expect a 'tools' arg;
    # set .llm manually to the MockLLM to avoid calling real providers during tests.
    arch = ArchitectAgent(tools=tools)
    arch.llm = MockLLM('architect')
    dev = DeveloperAgent(tools=tools)
    dev.llm = MockLLM('developer')
    qa = QAAgent(tools=tools)
    qa.llm = MockLLM('qa')

    # Orchestrator with human interaction enabled
    orchestrator = CentralOrchestrator(tools=tools)
    orchestrator.interrupts_enabled = True  # Enable interrupts for human checkpoints
    orchestrator.register_agents({'developer': dev, 'qa': qa})
    
    # Mock human interaction handler
    async def handle_human_checkpoint(checkpoint):
        print(f"\n=== HUMAN CHECKPOINT ===")
        print(f"Step: {checkpoint.get('step', 'unknown')}")
        print(f"Options: [1] Continue  [2] Modify  [3] Retry  [4] Abort")
        print("Selected: Continue (automated for test)")
        return {"action": "continue"}

    # Initialize project state and timeline
    state = {
        'project_name': project_id,
        'current_step': 'architecture',
        'steps_completed': [],
        'stage_status': {}
    }
    
    # Run architect to create blueprint with human checkpoint
    print("\n=== Running System Architect ===")
    arch_result = await arch.execute(state)
    
    # Create human checkpoint for architecture review
    checkpoint = orchestrator.checkpoint_agent_output(project_id, 'architect', arch_result)
    human_response = await handle_human_checkpoint(checkpoint)
    
    if human_response.get('action') == 'abort':
        print("Project aborted by human after architecture")
        return
    
    print('Architect result (mock):', arch_result)
    
    # Update state with completion
    state['steps_completed'].append('architecture')
    state['stage_status']['architecture'] = 'completed'

    # Manually set blueprint into context for this mock (handle wrapped/unwrapped shapes)
    bp_data = None
    if isinstance(arch_result, dict):
        bp_data = (
            arch_result.get('blueprint')
            or arch_result.get('architecture_output', {}).get('data', {}).get('blueprint')
            or arch_result
        )
    else:
        bp_data = arch_result

    blueprint = ProjectBlueprint.parse_obj(bp_data)
    context.blueprint = blueprint
    ctx_mgr.save_context(project_id, context)

    # Ensure agents are registered on the orchestrator (idempotent)
    orchestrator.register_agents({'developer': dev, 'qa': qa})
    # Ensure direct attributes on orchestrator for robustness in tests
    try:
        orchestrator.agents['developer'] = dev
        orchestrator.agents['qa'] = qa
    except Exception:
        pass
    try:
        if isinstance(orchestrator.tools, dict):
            orchestrator.tools['developer'] = dev
            orchestrator.tools['qa'] = qa
    except Exception:
        pass

    # Run build plan with human checkpoints
    state = {'project_name': project_id, 'current_step': 'build', 'steps_completed': []}
    
    while True:
        build_result = await orchestrator.execute_build_plan(state)
        
        # Check for human checkpoint
        if build_result.get('interrupted'):
            checkpoint = build_result.get('checkpoint', {})
            human_response = await handle_human_checkpoint(checkpoint)
            
            if human_response.get('action') == 'abort':
                print("Build aborted by human")
                break
            elif human_response.get('action') == 'modify':
                # Handle file modification if needed
                print("File modification requested (skipped in test)")
                continue
            elif human_response.get('action') == 'retry':
                # Reset current file/step for retry
                print("Retrying current step")
                continue
            # else continue
            
            # Update state with human response
            state['human_response'] = human_response.get('action')
        
        # Check for completion
        if build_result.get('success'):
            print('Build completed successfully')
            break
        elif build_result.get('error'):
            print(f"Build failed: {build_result.get('error')}")
            break
    
    print('Build result:', build_result)


if __name__ == '__main__':
    asyncio.run(run_mock_build())
