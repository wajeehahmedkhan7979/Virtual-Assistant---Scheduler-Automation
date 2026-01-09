"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from config import settings
from database import init_db

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown.
    """
    # Startup
    logger.info(f"Starting VA Scheduler API in {settings.fastapi_env} mode")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down VA Scheduler API")


# Create FastAPI application
app = FastAPI(
    title="Virtual Assistant & Scheduler API",
    description="AI-powered email management and task scheduling engine",
    version="0.1.0",
    root_path=settings.api_root_path,
    lifespan=lifespan,
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.fastapi_env,
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    """API root endpoint."""
    return {
        "message": "Welcome to VA Scheduler API",
        "docs": "/docs",
        "openapi_schema": "/openapi.json",
    }


# Import and include routers
from api.auth import router as auth_router
from api.email import router as email_router

# Include authentication routes
app.include_router(auth_router)

# Include email routes
app.include_router(email_router)

# Placeholder for future routers
# from api.jobs import router as jobs_router
# app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
