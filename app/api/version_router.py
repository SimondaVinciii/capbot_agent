"""Topic Version Management API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.schemas.schemas import (
    TopicVersionRequest, TopicVersionResponse, ErrorResponse
)
from app.services.topic_service import TopicService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router with detailed metadata
router = APIRouter(
    prefix="/api/v1",
    tags=["📋 Topic Version Management"],
    responses={
        404: {"description": "Version not found", "model": ErrorResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)

# Initialize service
topic_service = TopicService()

@router.get(
    "/topics/{topic_id}/versions",
    response_model=List[TopicVersionResponse],
    summary="📄 Get All Topic Versions",
    description="""
    ## Get all versions of a specific topic
    
    ### 📊 Version History:
    - Returns complete version history for a topic
    - Includes all statuses (draft, submitted, approved, rejected)
    - Shows version progression and changes over time
    
    ### 🔍 Use Cases:
    - Review topic evolution
    - Track modification history
    - Compare different versions
    - Audit trail for topic development
    """,
    responses={
        200: {
            "description": "Topic versions retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "topic_id": 123,
                            "version_number": 1,
                            "title": "Hệ thống quản lý thư viện",
                            "description": "Xây dựng hệ thống quản lý thư viện hiện đại",
                            "objectives": "Tự động hóa quy trình quản lý",
                            "methodology": "Web Development, Database Design",
                            "expected_outcomes": "Hoàn thiện hệ thống quản lý",
                            "requirements": "HTML, CSS, JavaScript, SQL",
                            "status": 4,
                            "submitted_at": "2024-01-15T10:30:00Z",
                            "submitted_by": 1,
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_topic_versions(topic_id: int) -> List[TopicVersionResponse]:
    """Get all versions of a topic."""
    try:
        versions = topic_service.get_topic_versions(topic_id)
        return versions
        
    except Exception as e:
        logger.error(f"Error getting topic versions for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/topics/{topic_id}/versions/latest",
    response_model=TopicVersionResponse,
    summary="🆕 Get Latest Topic Version",
    description="""
    ## Get the most recent version of a topic
    
    ### 📊 Latest Version:
    - Returns the newest version by creation date
    - Useful for getting current topic state
    - Includes all latest modifications and updates
    
    ### 🔍 Use Cases:
    - Display current topic information
    - Check latest changes
    - Get most up-to-date content
    """,
    responses={
        200: {
            "description": "Latest topic version retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 3,
                        "topic_id": 123,
                        "version_number": 3,
                        "title": "Hệ thống quản lý thư viện thông minh với AI",
                        "description": "Xây dựng hệ thống quản lý thư viện hiện đại với AI và IoT",
                        "objectives": "Tự động hóa quy trình quản lý và tối ưu hóa trải nghiệm",
                        "methodology": "AI/ML, IoT, Web Development, Database Design",
                        "expected_outcomes": "Hoàn thiện hệ thống thông minh với AI",
                        "requirements": "Python, TensorFlow, IoT sensors, Web technologies",
                        "status": 2,
                        "submitted_at": "2024-01-20T14:30:00Z",
                        "submitted_by": 1,
                        "created_at": "2024-01-20T14:30:00Z"
                    }
                }
            }
        }
    }
)
async def get_latest_topic_version(topic_id: int) -> TopicVersionResponse:
    """Get latest version of a topic."""
    try:
        version = topic_service.get_latest_topic_version(topic_id)
        if not version:
            raise HTTPException(status_code=404, detail="Topic version not found")
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest topic version for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/topics/{topic_id}/versions/approved",
    response_model=TopicVersionResponse,
    summary="✅ Get Approved Topic Version",
    description="""
    ## Get the approved version of a topic
    
    ### 📊 Approved Version:
    - Returns the version with status = 4 (Approved)
    - Used for indexing in ChromaDB
    - Represents the final, validated version
    
    ### 🔍 Use Cases:
    - Get official topic content
    - Index for duplicate detection
    - Reference for comparisons
    - Quality assurance validation
    """,
    responses={
        200: {
            "description": "Approved topic version retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 2,
                        "topic_id": 123,
                        "version_number": 2,
                        "title": "Hệ thống quản lý thư viện thông minh",
                        "description": "Xây dựng hệ thống quản lý thư viện hiện đại với AI",
                        "objectives": "Tự động hóa quy trình quản lý và tối ưu hóa trải nghiệm người dùng",
                        "methodology": "AI/ML, Web Development, Database Design",
                        "expected_outcomes": "Hoàn thiện hệ thống thông minh",
                        "requirements": "Python, Machine Learning, Web technologies",
                        "status": 4,
                        "submitted_at": "2024-01-18T11:15:00Z",
                        "submitted_by": 1,
                        "created_at": "2024-01-18T11:15:00Z"
                    }
                }
            }
        }
    }
)
async def get_approved_topic_version(topic_id: int) -> TopicVersionResponse:
    """Get approved version of a topic."""
    try:
        version = topic_service.get_approved_topic_version(topic_id)
        if not version:
            raise HTTPException(status_code=404, detail="No approved version found for this topic")
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting approved topic version for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/topics/{topic_id}/versions",
    response_model=TopicVersionResponse,
    summary="➕ Create New Topic Version",
    description="""
    ## Create a new version of an existing topic
    
    ### 📊 Version Creation:
    - Creates a new version with incremented version number
    - Maintains topic history and audit trail
    - Allows iterative topic development
    
    ### 🔍 Use Cases:
    - Revise topic after feedback
    - Update topic content
    - Create alternative versions
    - Track topic evolution
    
    ### ⚙️ Version Status:
    - **1**: Draft
    - **2**: Submitted
    - **3**: Under Review
    - **4**: Approved
    - **5**: Rejected
    """,
    responses={
        200: {
            "description": "New topic version created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 4,
                        "topic_id": 123,
                        "version_number": 4,
                        "title": "Hệ thống quản lý thư viện thông minh với AI và IoT",
                        "description": "Xây dựng hệ thống quản lý thư viện hiện đại với AI, IoT và Blockchain",
                        "objectives": "Tự động hóa quy trình quản lý, tối ưu hóa trải nghiệm và bảo mật dữ liệu",
                        "methodology": "AI/ML, IoT, Blockchain, Web Development",
                        "expected_outcomes": "Hoàn thiện hệ thống thông minh và bảo mật",
                        "requirements": "Python, TensorFlow, IoT sensors, Blockchain, Web technologies",
                        "status": 1,
                        "submitted_at": None,
                        "submitted_by": None,
                        "created_at": "2024-01-22T09:45:00Z"
                    }
                }
            }
        }
    }
)
async def create_topic_version(
    topic_id: int,
    version_request: TopicVersionRequest
) -> TopicVersionResponse:
    """Create a new version of an existing topic."""
    try:
        version = topic_service.create_topic_version(topic_id, version_request)
        if not version:
            raise HTTPException(status_code=400, detail="Failed to create topic version")
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating topic version for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/versions/{version_id}/approve",
    summary="✅ Approve Topic Version",
    description="""
    ## Approve a topic version
    
    ### 📊 Approval Process:
    - Sets version status to 4 (Approved)
    - Automatically indexes the version in ChromaDB
    - Makes the version available for duplicate detection
    - Triggers system notifications
    
    ### 🔍 Use Cases:
    - Final approval after review
    - Quality assurance validation
    - Making content available for indexing
    - Completing review workflow
    
    ### ⚠️ Important:
    - Only one version per topic can be approved
    - Previous approved versions are automatically deactivated
    - Approved versions are indexed in ChromaDB for duplicate detection
    """,
    responses={
        200: {
            "description": "Topic version approved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Topic version approved successfully"
                    }
                }
            }
        }
    }
)
async def approve_topic_version(version_id: int) -> Dict[str, str]:
    """Approve a topic version."""
    try:
        success = topic_service.approve_topic_version(version_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to approve topic version")
        
        return {"message": "Topic version approved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving topic version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/versions/{version_id}/reject",
    summary="❌ Reject Topic Version",
    description="""
    ## Reject a topic version
    
    ### 📊 Rejection Process:
    - Sets version status to 5 (Rejected)
    - Records rejection reason (optional)
    - Maintains version history for audit
    - Allows creation of new versions
    
    ### 🔍 Use Cases:
    - Reject after review process
    - Quality control and validation
    - Feedback and improvement guidance
    - Workflow management
    
    ### 📝 Rejection Reasons:
    - Content quality issues
    - Duplicate content
    - Incomplete information
    - Technical feasibility concerns
    - Academic standards not met
    """,
    responses={
        200: {
            "description": "Topic version rejected successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Topic version rejected successfully"
                    }
                }
            }
        }
    }
)
async def reject_topic_version(
    version_id: int,
    reason: str = Query(None, description="Optional rejection reason")
) -> Dict[str, str]:
    """Reject a topic version."""
    try:
        success = topic_service.reject_topic_version(version_id, reason)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reject topic version")
        
        return {"message": "Topic version rejected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting topic version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/versions/approved",
    response_model=List[TopicVersionResponse],
    summary="📊 Get All Approved Versions",
    description="""
    ## Get all approved topic versions
    
    ### 📊 Approved Versions:
    - Returns all versions with status = 4 (Approved)
    - Used for system indexing and duplicate detection
    - Includes metadata for filtering and analysis
    
    ### 🔍 Use Cases:
    - System initialization and indexing
    - Duplicate detection reference
    - Quality assurance reporting
    - Academic analytics and statistics
    
    ### ⚙️ Filtering Options:
    - `semester_id`: Filter by specific semester
    - `limit`: Maximum number of versions to return
    """,
    responses={
        200: {
            "description": "Approved versions retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 2,
                            "topic_id": 123,
                            "version_number": 2,
                            "title": "Hệ thống quản lý thư viện thông minh",
                            "description": "Xây dựng hệ thống quản lý thư viện hiện đại với AI",
                            "objectives": "Tự động hóa quy trình quản lý và tối ưu hóa trải nghiệm",
                            "methodology": "AI/ML, Web Development, Database Design",
                            "expected_outcomes": "Hoàn thiện hệ thống thông minh",
                            "requirements": "Python, Machine Learning, Web technologies",
                            "status": 4,
                            "submitted_at": "2024-01-18T11:15:00Z",
                            "submitted_by": 1,
                            "created_at": "2024-01-18T11:15:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_all_approved_versions(
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
    limit: int = Query(100, description="Maximum number of versions to return")
) -> List[TopicVersionResponse]:
    """Get all approved topic versions for indexing and duplicate checking."""
    try:
        versions = topic_service.get_approved_topic_versions(semester_id, limit)
        return versions
        
    except Exception as e:
        logger.error(f"Error getting approved versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
