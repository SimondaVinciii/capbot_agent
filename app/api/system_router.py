"""System Management API endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from app.schemas.schemas import ErrorResponse
from app.services.topic_service import TopicService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router with detailed metadata
router = APIRouter(
    prefix="/api/v1",
    tags=["🔧 System Management"],
    responses={
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)

# Initialize service
topic_service = TopicService()

@router.post(
    "/system/initialize",
    summary=" Initialize AI System",
    description="""
    ## Initialize the AI Agent system
    
    
    """,
    responses={
        200: {
            "description": "System initialization started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "System initialization started in background",
                        "status": "processing"
                    }
                }
            }
        }
    }
)
async def initialize_system(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Initialize the AI system."""
    try:
        logger.info("Initializing AI system")
        
        # Run initialization in background
        background_tasks.add_task(topic_service.initialize_system)
        
        return {
            "message": "System initialization started in background",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/system/stats",
    summary=" Get System Statistics",
    description="""
    ## Get comprehensive system statistics and health information
    
    
    """,
    responses={
        200: {
            "description": "System statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "main_agent": {
                            "total_requests": 1250,
                            "successful_submissions": 1180,
                            "duplicates_found": 45,
                            "modifications_made": 38
                        },
                        "chroma_collection": {
                            "name": "topics_collection",
                            "count": 892,
                            "size_mb": 45.6,
                            "health_status": "healthy"
                        },
                        "agents_status": {
                            "suggestion_agent": "TopicSuggestionAgent",
                            "duplicate_agent": "DuplicateDetectionAgent",
                            "modification_agent": "TopicModificationAgent"
                        },
                        "system_health": {
                            "status": "healthy",
                            "uptime_hours": 168.5,
                            "memory_usage_mb": 256.8,
                            "cpu_usage_percent": 12.3
                        },
                        "performance_metrics": {
                            "avg_response_time_ms": 1250,
                            "success_rate_percent": 94.4,
                            "error_rate_percent": 5.6
                        }
                    }
                }
            }
        }
    }
)
async def get_system_stats() -> Dict[str, Any]:
    """Get system statistics and health information."""
    try:
        stats = topic_service.get_system_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/health",
    summary="Health Check",
    description="""
    ## System health check endpoint
    """,
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "message": "AI Agent system is running",
                        "version": "2.0.0",
                        "timestamp": "2024-01-22T10:30:00Z",
                        "services": {
                            "database": "healthy",
                            "chromadb": "healthy",
                            "ai_services": "healthy",
                            "system_resources": "healthy"
                        }
                    }
                }
            }
        },
        503: {
            "description": "System is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "message": "System experiencing issues",
                        "version": "2.0.0",
                        "timestamp": "2024-01-22T10:30:00Z",
                        "services": {
                            "database": "unhealthy",
                            "chromadb": "healthy",
                            "ai_services": "healthy",
                            "system_resources": "healthy"
                        },
                        "errors": [
                            "Database connection timeout",
                            "SQL Server unavailable"
                        ]
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "AI Agent system is running",
        "version": "2.0.0"
    }
