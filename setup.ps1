# Quick-start setup script for AI Agent Virtual Assistant & Task Scheduler (Windows)
# Run: powershell -ExecutionPolicy Bypass -File setup.ps1

param(
    [switch]$SkipPython = $false,
    [switch]$SkipDocker = $false
)

$ProjectName = "AI Agent - Virtual Assistant & Scheduler"
$ProjectDir = (Get-Location).Path

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host $ProjectName -ForegroundColor Cyan
Write-Host "Quick-Start Setup Script (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prerequisites
Write-Host "[1/8] Checking prerequisites..." -ForegroundColor Blue

$hasPython = $null -ne (Get-Command python -ErrorAction SilentlyContinue)
$hasGit = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
$hasDocker = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)

if (-not $hasPython) {
    Write-Host "ERROR: Python is not installed" -ForegroundColor Red
    Write-Host "Download from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

if (-not $hasGit) {
    Write-Host "ERROR: Git is not installed" -ForegroundColor Red
    Write-Host "Download from https://git-scm.com/" -ForegroundColor Yellow
    exit 1
}

if (-not $hasDocker) {
    Write-Host "WARNING: Docker is not installed (needed for deployment)" -ForegroundColor Yellow
}

Write-Host "✓ Prerequisites OK" -ForegroundColor Green
Write-Host ""

# Step 2: Create virtual environment
Write-Host "[2/8] Creating Python virtual environment..." -ForegroundColor Blue

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "! Virtual environment already exists" -ForegroundColor Yellow
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"
Write-Host ""

# Step 3: Install dependencies
Write-Host "[3/8] Installing Python dependencies..." -ForegroundColor Blue

pip install --upgrade pip setuptools wheel | Out-Null
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt | Out-Null
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "! requirements.txt not found (create it with core dependencies)" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Setup environment files
Write-Host "[4/8] Setting up environment files..." -ForegroundColor Blue

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Created .env from .env.example" -ForegroundColor Green
        Write-Host "! IMPORTANT: Edit .env with your actual API keys" -ForegroundColor Yellow
        Write-Host "  - OPENAI_API_KEY" -ForegroundColor Yellow
        Write-Host "  - GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET" -ForegroundColor Yellow
        Write-Host "  - ENCRYPTION_KEY" -ForegroundColor Yellow
    }
} else {
    Write-Host "! .env already exists" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Create directory structure
Write-Host "[5/8] Creating directory structure..." -ForegroundColor Blue

$dirs = @(
    "backend/api",
    "backend/connectors",
    "backend/llm",
    "backend/security",
    "backend/storage",
    "backend/engine",
    "backend/worker/tasks",
    "frontend/pages",
    "frontend/components",
    "frontend/lib",
    "frontend/styles",
    "frontend/public",
    "tests",
    "docs"
)

foreach ($dir in $dirs) {
    $fullPath = Join-Path $ProjectDir $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }
}

Write-Host "✓ Directory structure created" -ForegroundColor Green
Write-Host ""

# Step 6: Create __init__.py files
Write-Host "[6/8] Creating Python package files..." -ForegroundColor Blue

$initPaths = @(
    "backend/__init__.py",
    "backend/api/__init__.py",
    "backend/connectors/__init__.py",
    "backend/llm/__init__.py",
    "backend/security/__init__.py",
    "backend/storage/__init__.py",
    "backend/engine/__init__.py",
    "backend/worker/__init__.py",
    "backend/worker/tasks/__init__.py"
)

foreach ($filePath in $initPaths) {
    $fullPath = Join-Path $ProjectDir $filePath
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType File -Path $fullPath -Force | Out-Null
    }
}

Write-Host "✓ Python package files created" -ForegroundColor Green
Write-Host ""

# Step 7: Display file locations
Write-Host "[7/8] Key files:" -ForegroundColor Blue
Write-Host "  Backend:"
Write-Host "    - backend/main.py (FastAPI app - to be created)"
Write-Host "    - backend/models.py (Database schema - to be created)"
Write-Host "    - backend/config.py (Configuration - to be created)"
Write-Host "  Frontend:"
Write-Host "    - frontend/pages/ (Next.js pages)"
Write-Host "  Configuration:"
Write-Host "    - .env (local environment - " -NoNewline
Write-Host "EDIT REQUIRED" -ForegroundColor Yellow -NoNewline
Write-Host ")"
Write-Host "    - docker-compose.yml (Docker Compose config)"
Write-Host "    - Dockerfile (Backend Docker image)"
Write-Host ""

# Step 8: Display next steps
Write-Host "[8/8] Next Steps:" -ForegroundColor Blue
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "1. CONFIGURE ENVIRONMENT:" -ForegroundColor Yellow
Write-Host "   Edit .env and add your API keys:"
Write-Host "   - OPENAI_API_KEY"
Write-Host "   - GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET"
Write-Host "   - ENCRYPTION_KEY"
Write-Host ""

Write-Host "2. START DOCKER SERVICES:" -ForegroundColor Yellow
Write-Host "   docker-compose up --build"
Write-Host ""

Write-Host "3. CREATE DATABASE TABLES:" -ForegroundColor Yellow
Write-Host "   In another PowerShell terminal:"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   python -c ""from backend.database import engine, Base; Base.metadata.create_all(bind=engine)"""
Write-Host ""

Write-Host "4. RUN TESTS:" -ForegroundColor Yellow
Write-Host "   pytest tests/ -v"
Write-Host ""

Write-Host "5. VERIFY SETUP:" -ForegroundColor Yellow
Write-Host "   curl http://localhost:8000/health"
Write-Host ""

Write-Host "6. DOCUMENTATION:" -ForegroundColor Yellow
Write-Host "   See SETUP.md and README.md for detailed guides"
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Virtual environment is active. You can now run:" -ForegroundColor Cyan
Write-Host "  python -m pip install --upgrade pip" -ForegroundColor White
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host ""
