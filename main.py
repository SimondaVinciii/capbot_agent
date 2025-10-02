"""Main FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.endpoints import router
from config import config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="CapBot AI Agent System",
    description="""
    #  CapBot AI Agent - Hệ thống AI hỗ trợ quản lý đề tài đồ án

    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "CapBot AI Team",
        "email": "support@capbot.ai",
        "url": "https://capbot.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.capbot.ai",
            "description": "Production server"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if config.DEBUG else "Contact system administrator"
        }
    )

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting AI Agent Topic Submission System")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    logger.info("System startup completed")

@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down AI Agent Topic Submission System")

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "AI Agent Topic Submission System",
        "version": "1.0.0",
        "description": "Hệ thống AI Agent hỗ trợ việc nộp đề tài đồ án",
        "docs": "/docs",
        "health": "/api/v1/health",
        "agents": {
            "suggestion": "Gợi ý đề tài từ xu hướng nghiên cứu",
            "duplicate_detection": "Kiểm tra trùng lặp với ChromaDB",
            "modification": "Chỉnh sửa đề tài để tăng độc đáo"
        }
    }

# Run application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG,
        log_level="info"
    )

