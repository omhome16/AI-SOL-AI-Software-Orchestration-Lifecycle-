# AI-SOL - AI Software Orchestration Lifecycle

**Fully Functional AI-Powered Software Development System**

AI-SOL is an intelligent multi-agent system that transforms project requirements into complete, production-ready codebases using advanced LLMs and orchestration.

---

## ✨ Features

- 🤖 **Multi-Agent Architecture**: Specialized agents for requirements, architecture, development, QA, and DevOps
- 🧠 **Gemini 2.5 Pro Integration**: Powered by Google's latest AI model
- 📊 **Real-Time Dashboard**: Live workflow tracking with WebSocket updates
- 🎨 **Modern UI**: Built with React, TypeScript, Vite, and TailwindCSS
- 🔄 **Resume/Pause Workflow**: Interactive checkpoints for human review
- 💬 **AI Chat Interface**: Communicate with the orchestrator during development
- 📁 **File Explorer**: Browse and view generated project files in real-time
- 🖼️ **Image Upload**: Provide visual inspiration for UI/UX generation
- 🐙 **GitHub Integration**: Automatic repository creation and pushing
- 🔒 **State Persistence**: Projects survive server restarts

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ with venv support
- Node.js 18+ and npm
- Google API Key for Gemini (required)
- Optional: GitHub Personal Access Token, other LLM API keys

### 1. Clone & Setup

```powershell
# Clone the repository
cd projects/AI-SOL

# Create virtual environment
python -m venv .venv

# Activate venv (PowerShell)
.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here
MODEL_PROVIDER=google
MODEL_NAME=gemini-2.5-pro

# Optional
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Settings
TEMPERATURE=0.1
MAX_TOKENS=8000
WORKSPACE_DIR=workspace
ENABLE_WEB_SEARCH=True
ENABLE_CODE_ANALYSIS=True
```

### 3. Start the Application

#### Option A: Use Helper Scripts (Recommended)

**Backend:**
```powershell
# Ensures .venv Python is used
.\start_backend.ps1
```

**Frontend:**
```powershell
cd frontend
npm run dev
```

#### Option B: Manual Start

**Backend:**
```powershell
.venv\Scripts\python.exe backend/main.py
```

**Frontend:**
```powershell
cd frontend
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📖 Usage Guide

### Creating a Project

1. Navigate to http://localhost:5173
2. Click "**Start Building**"
3. Fill in project details:
   - **Project Name**: e.g., "TicTacToe Game"
   - **Requirements**: Describe what you want to build
   - **Project Type**: Select from dropdown (website, api, mobile, etc.)
   - **Upload Images** (optional): Provide UI/UX inspiration
   - **Advanced Options** (optional):
     - Enable GitHub Integration
     - Generate Test Suite
     - Generate DevOps Config

4. Click "**Start Building**"
5. You'll be redirected to the Dashboard

### Using the Dashboard

**Left Panel:**
- **Workflow Steps**: Track progress through 5 stages
- **Project Files**: Browse generated files

**Middle Panel:**
- **Live Logs**: Real-time system output with color-coding
  - 🔵 Blue: Stage start
  - 🟢 Green: Success/completion
  - 🔴 Red: Errors
  - ⚪ Gray: General logs

**Right Panel:**
- **AI Chat**: Communicate with the orchestrator
- Ask questions
- Request modifications
- Resume paused workflow by saying "proceed"

### Workflow Stages

1. **Requirements** - Analyzes specs, classifies project type
2. **Architecture** - Designs system architecture and file structure
3. **Developer** - Generates all code files
4. **QA** (optional) - Creates tests and validation
5. **DevOps** (optional) - Sets up deployment configs and GitHub repo

### Pause & Resume

The workflow automatically pauses after each stage for review:
- Review the logs and generated files
- Chat with the AI to request changes
- Click "**Review & Proceed**" or type "proceed" in chat to continue

---

## 🧪 Testing

### CLI Workflow Test

Test the complete workflow without the frontend:

```powershell
.venv\Scripts\python.exe test_workflow_cli.py
```

This will:
- Run all agents in sequence
- Generate a complete project
- Save detailed logs to `test_workflow.log`
- Create files in `workspace/test_simple_game/`

### Individual Agent Tests

```powershell
.venv\Scripts\python.exe test_llm_init.py  # Test LLM initialization
```

---

## 📂 Project Structure

```
AI-SOL/
├── .venv/                    # Python virtual environment (gitignored)
├── backend/
│   ├── main.py               # FastAPI entry point
│   ├── api/
│   │   ├── routes.py         # API endpoints
│   │   └── websocket.py      # WebSocket manager
│   ├── core/
│   │   ├── workflow.py       # Workflow engine
│   │   └── state_manager.py  # Persistent state management
│   └── services/
│       └── vlm_service.py    # Vision LLM service
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.tsx   # Landing page with spotlight effect
│   │   │   ├── Requirements.tsx  # Project creation form
│   │   │   └── Dashboard.tsx # Real-time workflow dashboard
│   │   └── components/
│   │       └── SpotlightBackground.tsx  # Cursor-following animation
│   └── package.json
├── agents/
│   ├── base.py               # Base agent class
│   ├── requirements.py       # Requirements analyst
│   ├── architect.py          # System architect
│   ├── developer.py          # Code generator
│   ├── qa.py                 # QA engineer
│   └── devops.py             # DevOps specialist
├── core/
│   ├── config.py             # Configuration management
│   ├── state.py              # State management
│   └── tools.py              # Agent tools
├── orchestrator/
│   └── central.py            # Central orchestrator
├── utils/
│   ├── context_manager.py    # Project context
│   └── project_classifier.py # AI project classifier
├── workspace/
│   ├── .state/               # Persistent project states (JSON)
│   └── [project_name]/       # Generated project files
├── requirements.txt          # Python dependencies
├── start_backend.ps1         # Backend startup script
└── test_workflow_cli.py      # CLI testing script
```

---

## 🔧 API Endpoints

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects/create` - Create new project
- `GET /api/v1/projects/{id}` - Get project details
- `GET /api/v1/projects/{id}/status` - Get workflow status
- `DELETE /api/v1/projects/{id}` - Delete project

### Workflow Control
- `POST /api/v1/projects/{id}/resume` - Resume paused workflow
- `POST /api/v1/projects/{id}/restart` - Restart from beginning or specific stage

### Files
- `GET /api/v1/projects/{id}/files` - List generated files
- `GET /api/v1/projects/{id}/files/content?path=...` - Get file content
- `GET /workspace/[project]/[file]` - Direct file access (static)

### Chat
- `POST /api/v1/chat` - Send message to orchestrator

### System
- `GET /api/v1/health` - Health check
- `GET /api/v1/config` - Get system configuration

### WebSocket
- `WS /ws/{project_id}` - Real-time workflow updates

---

## ⚙️ Configuration

### Model Selection

Supported providers and models:

**Google (Recommended):**
- `gemini-2.5-pro` - Most powerful, best for complex projects
- `gemini-1.5-pro` - Stable, production-ready
- `gemini-2.0-flash-exp` - Faster, experimental

**OpenAI:**
- `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`

**Anthropic:**
- `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`

**XAI (Grok):**
- `grok-beta`

**Mistral:**
- `mistral-large-latest`, `mistral-medium`

### Workspace Configuration

By default, projects are created in `workspace/`. Change in `.env`:

```env
WORKSPACE_DIR=custom/path
```

### GitHub Integration

To enable automatic repo creation:

1. Generate a Personal Access Token: https://github.com/settings/tokens
2. Add to `.env`:
```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_username
```

3. Check "Enable GitHub Integration" when creating a project

---

## 🐛 Troubleshooting

### "LLM not initialized" Error

**Cause**: Not using `.venv` Python  
**Fix**: Always use `.venv\Scripts\python.exe` or  `.\start_backend.ps1`

### "Module not found" Errors

**Cause**: Dependencies not installed in venv  
**Fix**:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### WorkflowStuck

**Cause**: Long-running LLM calls  
**Fix**: Check logs for `Working...` messages - this is normal. The workflow sends heartbeats every 10 seconds.

### WebSocket Connection Failed

**Cause**: Backend not running or CORS issue  
**Fix**: Ensure backend is running on port 8000

### Images Not Displaying

**Cause**: Static files not mounted  
**Fix**: Update to latest `backend/main.py` which includes StaticFiles mounting

---

## 📊 Performance Tips

1. **Use gemini-2.5-pro** for best results  
2. **Disable research** for faster execution: Set `enable_research: false` in advanced options
3. **Skip optional stages**: Uncheck "Generate Tests" and "Generate DevOps" for simpler projects
4. **Use smaller context**: Shorter requirements = faster generation

---

## 🎯 Example Projects

### Simple Tic-Tac-Toe Game

**Requirements:**
```
Create a web-based Tic-Tac-Toe game.
- 3x3 grid
- Two players (X and O)
- Win detection (rows, columns, diagonals)
- Reset button
- Score tracking
```

**Result:** Complete HTML/CSS/JS game in < 5 minutes

### REST API with Database

**Requirements:**
```
Create a FastAPI backend for a task management system.
- User authentication (JWT)
- CRUD operations for tasks
- PostgreSQL database
- Filtering by status and priority
- Due date reminders
```

**Result:** Full FastAPI backend with SQLAlchemy models, Pydantic schemas, and

 auth

### Full-Stack E-Commerce

**Requirements:**
```
Build an e-commerce platform.
- Product catalog with search
- Shopping cart
- User accounts
- Payment integration (Stripe)
- Admin dashboard
- Order tracking
```

**Result:** Complete React frontend + FastAPI backend in ~15 minutes

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with CLI test script
5. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Google Gemini** - Advanced AI capabilities
- **LangChain** - LLM orchestration framework
- **FastAPI** - High-performance backend framework
- **React & Vite** - Modern frontend stack

---

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@ai-sol.dev (if applicable)

---

## 🗺️ Roadmap

- [ ] Support for more LLM providers
- [ ] Plugin system for custom agents
- [ ] Cloud deployment templates
- [ ] Project templates library
- [ ] Collaborative multi-user support
- [ ] Version control integration beyond GitHub
- [ ] Code review agent
- [ ] Performance optimization agent
- [ ] Mobile app for monitoring

---

**Built with ❤️ by the AI-SOL Team**

*Transform ideas into production code with the power of AI.*
