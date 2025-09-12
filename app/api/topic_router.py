"""Topic Management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from app.schemas.schemas import (
    TopicRequest, TopicResponse, TopicVersionRequest, TopicVersionResponse,
    DuplicateCheckResult, TopicSuggestionsResponse, TopicModificationResponse,
    AgentProcessResponse, ErrorResponse
)
from app.services.topic_service import TopicService
from app.agents.duplicate_detection_agent import DuplicateDetectionAgent
from app.agents.topic_modification_agent import TopicModificationAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router with detailed metadata
router = APIRouter(
    prefix="/api/v1/topics",
    tags=["🔄 Topic Management"],
    responses={
        404: {"description": "Topic not found", "model": ErrorResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)

# Initialize service
topic_service = TopicService()
duplicate_agent = DuplicateDetectionAgent()
modification_agent = TopicModificationAgent()

@router.post(
    "/check-duplicate-advanced",
    summary="🧠 Check duplicate and auto-suggest modifications",
    description="""
    ## Advanced duplicate check with auto-modification
    - Uses DuplicateDetectionAgent to detect duplicates from ChromaDB
    - If duplicate or potential duplicate, invokes TopicModificationAgent to suggest improvements
    - Returns duplicate analysis and optional modification proposal
    """,
)
async def check_duplicate_advanced(
    topic_request: TopicRequest,
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Similarity threshold to consider duplicate")
):
    try:
        import time
        t0 = time.time()
        # Run duplicate detection
        detection_input = {
            "topic_title": topic_request.title,
            "topic_description": topic_request.description or "",
            "topic_objectives": topic_request.objectives or "",
            "topic_methodology": getattr(topic_request, "methodology", "") or "",
            "semester_id": topic_request.semester_id,
            "threshold": threshold,
        }
        detection_result = await duplicate_agent.process(detection_input)

        if not detection_result.get("success"):
            raise HTTPException(500, detail=detection_result.get("error", "Duplicate detection failed"))

        dup_data = detection_result.get("data", {})
        if "processing_time" not in dup_data:
            dup_data["processing_time"] = round(time.time() - t0, 3)
        status = dup_data.get("status")
        # Normalize to lowercase string to handle Enum/string cases uniformly
        status = str(getattr(status, "value", status)).lower() if status is not None else ""

        response: Dict[str, Any] = {
            "duplicate_check": dup_data
        }

        # If duplicate or potential duplicate -> propose modifications
        if status in ("duplicate_found", "potential_duplicate"):
            modification_input = {
                "original_topic": topic_request.dict(),
                "duplicate_results": dup_data,
                "modification_preferences": {},
                "preserve_core_idea": True,
            }
            modification_result = await modification_agent.process(modification_input)
            if modification_result.get("success"):
                response["modification_proposal"] = modification_result.get("data")
            else:
                response["modification_error"] = modification_result.get("error", "Modification failed")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_duplicate_advanced: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def submit_topic_with_ai(
    topic_request: TopicRequest,
    check_duplicates: bool = Query(True, description="Enable duplicate detection using ChromaDB"),
    get_suggestions: bool = Query(False, description="Get trending topic suggestions"),
    auto_modify: bool = Query(True, description="Auto-modify topic if duplicates found")
) -> AgentProcessResponse:
    try:
        logger.info(f"Submitting topic with AI: {topic_request.title}")
        
        result = await topic_service.submit_topic_with_ai_support(
            topic_request=topic_request,
            check_duplicates=check_duplicates,
            get_suggestions=get_suggestions,
            auto_modify=auto_modify
        )
        
        if result.get("success"):
            return AgentProcessResponse(**result["data"])
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Unknown error occurred")
            )
            
    except Exception as e:
        logger.error(f"Error in submit_topic_with_ai: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def create_topic_simple(topic_request: TopicRequest) -> TopicResponse:
    try:
        logger.info(f"Creating simple topic: {topic_request.title}")
        
        result = topic_service.create_topic_simple(topic_request)
        
        if result.get("success"):
            return TopicResponse(**result["data"]["topic"])
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create topic")
            )
            
    except Exception as e:
        logger.error(f"Error in create_topic_simple: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_topic_duplicates(topic_request: TopicRequest) -> DuplicateCheckResult:
    try:
        logger.info(f"Checking duplicates for: {topic_request.title}")
        import time
        t0 = time.time()
        
        result = await topic_service.check_topic_duplicates(topic_request)
        
        if result.get("success"):
            data = result.get("data", {})
            if "processing_time" not in data:
                data["processing_time"] = round(time.time() - t0, 3)
            return DuplicateCheckResult(**data)
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to check duplicates")
            )
            
    except Exception as e:
        logger.error(f"Error in check_topic_duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/suggestions",
    response_model=TopicSuggestionsResponse,
    summary="💡 Get Trending Topic Suggestions",
    description="""
    ## Get AI-powered topic suggestions based on current research trends
    
    ### 🤖 AI Features:
    - Analyzes current research trends using external APIs
    - Generates topic suggestions using Google AI (Gemini)
    - Customizes suggestions based on supervisor expertise
    - Considers student level and category preferences
    
    ### 📊 Input Parameters:
    - `semester_id`: Target semester for suggestions
    - `category_preference`: Preferred topic category
    - `keywords`: Keywords of interest for customization
    - `supervisor_expertise`: Supervisor's expertise areas
    - `student_level`: Student level (undergraduate/graduate)
    
    ### 📋 Response includes:
    - List of suggested topics with detailed descriptions
    - Rationale for each suggestion
    - Trending analysis and research insights
    - Customization based on input parameters
    """,
    responses={
        200: {
            "description": "Topic suggestions generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "suggestions": [
                            {
                                "title": "AI-Powered Personalized Learning System",
                                "description": "Develop an intelligent learning platform that adapts to individual student needs using machine learning algorithms",
                                "objectives": "Create personalized learning paths, implement adaptive assessment, and improve learning outcomes",
                                "methodology": "Machine Learning, Natural Language Processing, Educational Data Mining",
                                "rationale": "Trending in educational technology with high research potential",
                                "difficulty_level": "Advanced",
                                "estimated_duration": "6 months"
                            }
                        ],
                        "trending_analysis": {
                            "hot_topics": ["AI in Education", "Personalized Learning", "Adaptive Systems"],
                            "research_gaps": ["Cross-cultural adaptation", "Accessibility features"],
                            "technology_trends": ["GPT integration", "Real-time analytics"]
                        },
                        "processing_time": 3.456
                    }
                }
            }
        }
    }
)
async def get_trending_suggestions(
    semester_id: int = Query(..., description="Target semester ID for suggestions"),
    category_preference: str = Query("", description="Preferred topic category (e.g., 'AI', 'Web Development')"),
    keywords: List[str] = Query([], description="Keywords of interest for customization"),
    supervisor_expertise: List[str] = Query([], description="Supervisor's expertise areas"),
    student_level: str = Query("undergraduate", description="Student level: undergraduate or graduate")
) -> TopicSuggestionsResponse:
    try:
        logger.info(f"Getting trending suggestions for semester: {semester_id}")
        
        result = await topic_service.get_trending_suggestions(
            semester_id=semester_id,
            category_preference=category_preference,
            keywords=keywords,
            supervisor_expertise=supervisor_expertise,
            student_level=student_level
        )
        
        if result.get("success"):
            # Ensure processing_time exists
            import time
            data = result.get("data", {})
            if "processing_time" not in data:
                data["processing_time"] = round(0.001, 3)  # minimal placeholder if agent didn't set
            return TopicSuggestionsResponse(**data)
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to get suggestions")
            )
            
    except Exception as e:
        logger.error(f"Error in get_trending_suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def modify_topic_for_uniqueness(
    topic_request: TopicRequest,
    duplicate_results: Dict[str, Any],
    preserve_core_idea: bool = Query(True, description="Preserve the core idea while modifying")
) -> TopicModificationResponse:
    try:
        logger.info(f"Modifying topic for uniqueness: {topic_request.title}")
        
        result = await topic_service.modify_topic_for_uniqueness(
            topic_request=topic_request,
            duplicate_results=duplicate_results,
            preserve_core_idea=preserve_core_idea
        )
        
        if result.get("success"):
            return TopicModificationResponse(**result["data"])
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to modify topic")
            )
            
    except Exception as e:
        logger.error(f"Error in modify_topic_for_uniqueness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_topic_by_id(topic_id: int) -> TopicResponse:
    """Get a topic by its ID."""
    try:
        topic = topic_service.get_topic_by_id(topic_id)
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        return topic
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_topics(
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
    limit: int = Query(100, description="Maximum number of topics to return"),
    approved_only: bool = Query(False, description="Return only approved topics")
) -> List[TopicResponse]:
    """Get topics, optionally filtered by semester and approval status."""
    try:
        if semester_id:
            topics = topic_service.get_topics_by_semester(semester_id, limit, approved_only)
        else:
            # For simplicity, if no semester_id provided, return empty list
            # In a real implementation, you might want to get all topics
            topics = []
        
        return topics
        
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def search_topics(
    keywords: List[str] = Query(..., description="Keywords to search for in topic titles"),
    semester_id: Optional[int] = Query(None, description="Filter by semester ID")
) -> List[TopicResponse]:
    """Search topics by title keywords."""
    try:
        topics = topic_service.search_topics(keywords, semester_id)
        return topics
        
    except Exception as e:
        logger.error(f"Error searching topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_approved_topics(
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
    limit: int = Query(100, description="Maximum number of topics to return")
) -> List[TopicResponse]:
    """Get only approved topics for indexing and duplicate checking."""
    try:
        topics = topic_service.get_topics_by_semester(semester_id or 0, limit, approved_only=True)
        return topics
        
    except Exception as e:
        logger.error(f"Error getting approved topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
