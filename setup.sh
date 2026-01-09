#!/bin/bash
# Quick-start setup script for AI Agent Virtual Assistant & Task Scheduler
# Run: bash setup.sh

set -e

PROJECT_NAME="AI Agent - Virtual Assistant & Scheduler"
PROJECT_DIR=$(pwd)

echo "==========================================="
echo "$PROJECT_NAME"
echo "Quick-Start Setup Script"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${BLUE}[1/8]${NC} Checking prerequisites..."
if ! command -v git &> /dev/null; then
    echo "ERROR: git is not installed"
    exit 1
fi
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi
if ! command -v docker &> /dev/null; then
    echo "WARNING: Docker is not installed (needed for deployment)"
fi
echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Step 2: Create virtual environment
echo -e "${BLUE}[2/8]${NC} Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}! Virtual environment already exists${NC}"
fi
source venv/bin/activate
echo ""

# Step 3: Install dependencies
echo -e "${BLUE}[3/8]${NC} Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 4: Setup environment files
echo -e "${BLUE}[4/8]${NC} Setting up environment files..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from .env.example${NC}"
    echo -e "${YELLOW}! IMPORTANT: Edit .env with your actual API keys (OPENAI_API_KEY, GMAIL_CLIENT_ID, etc.)${NC}"
else
    echo -e "${YELLOW}! .env already exists${NC}"
fi
echo ""

# Step 5: Create directory structure
echo -e "${BLUE}[5/8]${NC} Creating directory structure..."
mkdir -p backend/{api,connectors,llm,security,storage,engine,worker/tasks}
mkdir -p frontend/{pages,components,lib,styles,public}
mkdir -p tests docs

touch backend/__init__.py backend/api/__init__.py backend/connectors/__init__.py
touch backend/llm/__init__.py backend/security/__init__.py backend/storage/__init__.py
touch backend/engine/__init__.py backend/worker/__init__.py backend/worker/tasks/__init__.py
echo -e "${GREEN}✓ Directory structure created${NC}"
echo ""

# Step 6: Initialize database (if docker-compose is running)
echo -e "${BLUE}[6/8]${NC} Database setup..."
echo "NOTE: Run 'docker-compose up' to start postgres and redis"
echo "Then run: python backend/database.py  (to create tables)"
echo ""

# Step 7: Show file locations
echo -e "${BLUE}[7/8]${NC} Key files created:"
echo "  Backend:"
echo "    - backend/main.py (FastAPI app - to be created)"
echo "    - backend/models.py (Database schema - to be created)"
echo "    - backend/config.py (Configuration - to be created)"
echo "  Frontend:"
echo "    - frontend/pages/ (Next.js pages)"
echo "  Configuration:"
echo -e "    - .env (local environment - ${YELLOW}EDIT REQUIRED${NC})"
echo "    - docker-compose.yml (Docker Compose config)"
echo "    - Dockerfile (Backend Docker image)"
echo ""

# Step 8: Display next steps
echo -e "${BLUE}[8/8]${NC} Next Steps:"
echo "==========================================="
echo "1. CONFIGURE ENVIRONMENT:"
echo "   Edit .env and add your API keys:"
echo "   - OPENAI_API_KEY"
echo "   - GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET"
echo "   - ENCRYPTION_KEY (run: from cryptography.fernet import Fernet; print(Fernet.generate_key()))"
echo ""
echo "2. START DOCKER SERVICES:"
echo "   docker-compose up --build"
echo ""
echo "3. CREATE DATABASE TABLES:"
echo "   In another terminal:"
echo "   source venv/bin/activate"
echo "   python -c \"from backend.database import engine, Base; Base.metadata.create_all(bind=engine)\""
echo ""
echo "4. RUN TESTS:"
echo "   pytest tests/ -v"
echo ""
echo "5. VERIFY SETUP:"
echo "   curl http://localhost:8000/health"
echo ""
echo "6. NEXT PHASE:"
echo "   See SETUP.md for detailed documentation"
echo "==========================================="
echo ""
echo -e "${GREEN}Setup complete!${NC}"
