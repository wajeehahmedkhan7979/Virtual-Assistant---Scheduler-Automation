"""
Project initialization script.
Creates necessary directories and files if they don't exist.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TESTS_DIR = PROJECT_ROOT / "tests"


def init_project():
    """Initialize project structure."""
    print("Initializing VA Scheduler project structure...")
    
    # Backend directories
    backend_dirs = [
        BACKEND_DIR / "api",
        BACKEND_DIR / "connectors",
        BACKEND_DIR / "llm",
        BACKEND_DIR / "security",
        BACKEND_DIR / "storage",
        BACKEND_DIR / "engine",
        BACKEND_DIR / "worker" / "tasks",
    ]
    
    # Frontend directories
    frontend_dirs = [
        FRONTEND_DIR / "pages",
        FRONTEND_DIR / "components",
        FRONTEND_DIR / "lib",
        FRONTEND_DIR / "styles",
    ]
    
    # Create all directories
    for directory in backend_dirs + frontend_dirs + [TESTS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory.relative_to(PROJECT_ROOT)}")
    
    # Create __init__.py files
    init_files = [
        BACKEND_DIR / "__init__.py",
        BACKEND_DIR / "api" / "__init__.py",
        BACKEND_DIR / "connectors" / "__init__.py",
        BACKEND_DIR / "llm" / "__init__.py",
        BACKEND_DIR / "security" / "__init__.py",
        BACKEND_DIR / "storage" / "__init__.py",
        BACKEND_DIR / "engine" / "__init__.py",
        BACKEND_DIR / "worker" / "__init__.py",
        BACKEND_DIR / "worker" / "tasks" / "__init__.py",
        TESTS_DIR / "__init__.py",
    ]
    
    for init_file in init_files:
        if not init_file.exists():
            init_file.touch()
            print(f"✓ Created {init_file.relative_to(PROJECT_ROOT)}")
    
    print("\n✅ Project structure initialized successfully!")
    print("\nNext steps:")
    print("1. Set up environment: python -m venv venv && venv\\Scripts\\activate")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Copy .env.example to .env and add your credentials")
    print("4. Start containers: docker-compose up -d")
    print("5. View API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    init_project()
