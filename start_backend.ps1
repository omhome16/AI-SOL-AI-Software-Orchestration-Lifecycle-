# Start AI-SOL Backend with correct Python environment
Write-Host "🚀 Starting AI-SOL Backend with .venv Python..." -ForegroundColor Cyan

# Check if .venv exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "❌ Virtual environment not found at .venv\" -ForegroundColor Red
    Write-Host "Please create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Check if backend/main.py exists
if (-not (Test-Path "backend\main.py")) {
    Write-Host "❌ backend/main.py not found!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Using: .venv\Scripts\python.exe" -ForegroundColor Green
Write-Host "✅ Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host ""

# Run with .venv Python
& .venv\Scripts\python.exe backend/main.py
