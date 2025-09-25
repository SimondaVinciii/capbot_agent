"""Topic Management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, UploadFile, File, Form
from typing import List, Optional, Dict, Any, Union
from app.schemas.schemas import (
    TopicRequest, TopicResponse, TopicVersionRequest, TopicVersionResponse,
    DuplicateCheckResult, TopicSuggestionsResponse, TopicModificationResponse,
    AgentProcessResponse, ErrorResponse
)
from pydantic import BaseModel, Field
from app.services.topic_service import TopicService
from app.agents.duplicate_detection_agent import DuplicateDetectionAgent
from app.agents.topic_modification_agent import TopicModificationAgent
from app.agents.check_rubric_agent import CheckRubricAgent
from app.schemas.schemas import RubricEvaluationRequest, RubricEvaluationResponse
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
rubric_agent = CheckRubricAgent()

class DuplicateAdvancedRequest(BaseModel):
    eN_Title: str = Field(..., description="English title")
    abbreviation: Optional[str] = None
    vN_title: Optional[str] = None
    problem: Optional[str] = None
    context: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[str] = None
    categoryId: Optional[int] = None
    semesterId: Optional[int] = None
    maxStudents: Optional[int] = None
    fileId: Optional[int] = None


@router.post(
    "/check-duplicate-advanced",
    summary="🧠 Check duplicate and auto-suggest modifications",
    description="""
    ## Advanced duplicate check with auto-modification
    - Input fields follow new vector logic: en_title, vn_title, problem, context, content, description, objectives
    - Uses DuplicateDetectionAgent to detect duplicates from ChromaDB
    - If duplicate or potential duplicate, invokes TopicModificationAgent to suggest improvements
    - Returns duplicate analysis and optional modification proposal
    """,
)
async def check_duplicate_advanced(
    req: Union[DuplicateAdvancedRequest, TopicRequest],
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Similarity threshold to consider duplicate"),
    semester_id: Optional[int] = Query(None, description="Optional semester filter for duplicate search"),
    last_n_semesters: int = Query(3, ge=1, le=10, description="Number of recent semesters to search")
):
    try:
        import time
        t0 = time.time()
        # Normalize request to new schema regardless of legacy/new input
        if isinstance(req, DuplicateAdvancedRequest):
            en_title = req.eN_Title or ""
            vn_title = req.vN_title or ""
            problem = req.problem or ""
            context_val = req.context or ""
            content_section = req.content or ""
            description = req.description or ""
            objectives = req.objectives or ""
            body_semester_id = req.semesterId
            category_id = req.categoryId
        else:
            # Legacy TopicRequest mapping
            en_title = req.title or ""
            vn_title = ""
            problem = ""
            context_val = ""
            content_section = ""
            description = (req.description or "")
            objectives = (req.objectives or "")
            body_semester_id = getattr(req, 'semester_id', None)
            category_id = getattr(req, 'category_id', None)

        # Build combined content exactly like indexing logic (same field order)
        combined_description = " ".join([
            part for part in [
                en_title,
                vn_title,
                problem,
                context_val,
                content_section,
                description,
                objectives,
            ] if part
        ])
        # Determine semesters to search (current or provided + last_n_semesters)
        from app.models.database import get_db, Semester
        from sqlalchemy.orm import Session
        from sqlalchemy import desc, and_
        from datetime import datetime
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            # Prefer explicit query param; fallback to body.semesterId; else detect current
            base_semester_id = semester_id if semester_id is not None else body_semester_id
            if base_semester_id is None:
                now = datetime.utcnow()
                current = db.query(Semester).filter(
                    and_(
                        Semester.IsActive == True,
                        Semester.StartDate <= now,
                        Semester.EndDate >= now
                    )
                ).first()
                base_semester_id = current.Id if current else None

            semester_ids: List[int] = []
            if base_semester_id:
                semesters = db.query(Semester).filter(Semester.IsActive == True).order_by(desc(Semester.StartDate)).all()
                ordered_ids = [s.Id for s in semesters]
                start_idx = ordered_ids.index(base_semester_id) if base_semester_id in ordered_ids else 0
                semester_ids = ordered_ids[start_idx:start_idx + last_n_semesters]
            else:
                semesters = db.query(Semester).filter(Semester.IsActive == True).order_by(desc(Semester.StartDate)).limit(last_n_semesters).all()
                semester_ids = [s.Id for s in semesters]
        finally:
            db.close()

        where = {"semesterId": {"$in": semester_ids}} if semester_ids else None
        detection_input = {
            # Use title for better matching and pass combined content in description
            "topic_title": (en_title or vn_title or ""),
            "topic_description": combined_description,
            "topic_objectives": "",
            "topic_methodology": "",
            "semester_id": base_semester_id,
            "threshold": threshold,
            "where": where,
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
                "original_topic": req.dict(),
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


@router.post(
    "/check-rubric",
    response_model=RubricEvaluationResponse,
    summary="📝 Đánh giá đề tài theo rubric 10 tiêu chí",
    description="Đánh giá đề tài theo các tiêu chí: tiêu đề, ngữ cảnh, vấn đề, người dùng, luồng/chức năng, khách hàng/tài trợ, hướng tiếp cận & công nghệ & deliverables, phạm vi & packages & khả thi 14 tuần, độ phức tạp kỹ thuật, tính ứng dụng & khả thi công nghệ.",
)
async def check_rubric(req: RubricEvaluationRequest) -> RubricEvaluationResponse:
    try:
        import time
        t0 = time.time()
        result = await rubric_agent.process(req.dict())
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rubric evaluation failed"))

        data = result.get("data", {})
        # Ensure processing_time exists
        if "processing_time" not in data:
            data["processing_time"] = round(time.time() - t0, 3)
        return RubricEvaluationResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_rubric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/check-rubric-file",
    response_model=RubricEvaluationResponse,
    summary="📎 Upload .docx để chấm rubric",
    description="Nhận file .docx, trích xuất văn bản và chấm rubric tự động. Có thể gửi kèm metadata tối thiểu (title, supervisor_id, semester_id).",
)
async def check_rubric_file(
    file: UploadFile = File(..., description="Word .docx file"),
    title: str = Form("", description="Tiêu đề đề tài (tùy chọn, nếu không có sẽ cố gắng suy luận") ,
    supervisor_id: int = Form(1, description="Mã GV hướng dẫn (tùy chọn)"),
    semester_id: int = Form(1, description="Mã học kỳ (tùy chọn)"),
    category_id: int = Form(0, description="Danh mục (tùy chọn)"),
    max_students: int = Form(4, description="Số SV tối đa (tùy chọn)")
) -> RubricEvaluationResponse:
    try:
        import time
        import io
        try:
            from docx import Document
        except Exception:
            raise HTTPException(status_code=500, detail="Missing dependency: python-docx. Please install and restart the server.")
        t0 = time.time()

        if not file.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail="Only .docx files are supported")

        # Read file into memory and parse with python-docx
        content = await file.read()
        try:
            document = Document(io.BytesIO(content))
        except Exception as ex:
            raise HTTPException(status_code=400, detail=f"Failed to parse .docx: {ex}")

        # Extract text with simple paragraph join. Tables are appended linearly.
        parts: list[str] = []
        for p in document.paragraphs:
            txt = (p.text or "").strip()
            if txt:
                parts.append(txt)
        # Tables
        for tbl in getattr(document, "tables", []) or []:
            for row in tbl.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell and cell.text]
                if any(row_text):
                    parts.append(" | ".join(row_text))

        extracted_text = "\n".join(parts)

        # Build minimal topic_request. If title is blank, attempt a heuristic from first line.
        inferred_title = title.strip()
        if not inferred_title:
            first_line = extracted_text.splitlines()[0].strip() if extracted_text else ""
            inferred_title = first_line[:200] if first_line else "Đề tài chưa đặt tên"

        rubric_payload = {
            "topic_request": {
                "title": inferred_title,
                "description": None,
                "objectives": None,
                "methodology": None,
                "expected_outcomes": None,
                "requirements": None,
                "supervisor_id": supervisor_id,
                "semester_id": semester_id,
                "category_id": (category_id if category_id != 0 else None),
                "max_students": max_students,
            },
            "proposal_text": extracted_text,
        }

        result = await rubric_agent.process(rubric_payload)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rubric evaluation failed"))

        data = result.get("data", {})
        if "processing_time" not in data:
            data["processing_time"] = round(time.time() - t0, 3)
        return RubricEvaluationResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_rubric_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post(
    "/submit-with-ai",
    response_model=AgentProcessResponse,
    summary="🤖 Submit Topic with Full AI Support",
    description="""
    ## Submit topic with comprehensive AI agent support
    
    ### �� AI Features:
    - **Duplicate Detection**: Uses ChromaDB to check for similar topics
    - **Auto-Modification**: Automatically modifies topic if duplicates found
    - **Trending Suggestions**: Gets AI-powered topic suggestions
    - **Full Processing**: Complete workflow with all AI agents
    
    ### 📊 Processing Workflow:
    1. **Suggestion Generation** (if enabled): Get trending topic suggestions
    2. **Duplicate Detection** (if enabled): Check for similar existing topics
    3. **Auto-Modification** (if duplicates found): Modify topic to reduce similarity
    4. **Topic Creation**: Create topic in database
    5. **Indexing**: Index new topic for future duplicate detection
    
    ### ⚙️ Parameters:
    - `check_duplicates`: Enable ChromaDB duplicate detection
    - `get_suggestions`: Get trending topic suggestions
    - `auto_modify`: Auto-modify topic if duplicates found
    
    ### 📋 Response includes:
    - Complete processing results
    - Duplicate analysis and similarity scores
    - Modification suggestions (if applicable)
    - Final topic data and database ID
    - Processing statistics and timing
    """,
    responses={
        200: {
            "description": "Topic submitted successfully with AI support",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "topic_id": 123,
                        "duplicate_check": {
                            "status": "unique",
                            "similarity_score": 0.15,
                            "similar_topics": []
                        },
                        "suggestions": [],
                        "modifications": None,
                        "final_topic": {
                            "id": 123,
                            "title": "AI-Powered Learning System",
                            "description": "An intelligent learning platform...",
                            "objectives": "Create personalized learning paths...",
                            "supervisor_id": 1,
                            "category_id": 2,
                            "semester_id": 1,
                            "max_students": 4,
                            "is_approved": False,
                            "created_at": "2024-01-22T10:30:00Z"
                        },
                        "messages": [
                            "Đề tài có tính độc đáo tốt, không phát hiện trùng lặp",
                            "Đã tạo đề tài thành công trong cơ sở dữ liệu",
                            "Đã lưu trữ đề tài vào hệ thống tìm kiếm"
                        ],
                        "processing_time": 2.456
                    }
                }
            }
        }
    }
)
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
    student_level: str = Query("undergraduate", description="Student level: undergraduate or graduate"),
    team_size: int = Query(4, description="Team size (only 4 or 5 supported)")
) -> TopicSuggestionsResponse:
    try:
        logger.info(f"Getting trending suggestions for semester: {semester_id}")
        
        # Enforce only 4 or 5
        if team_size not in (4, 5):
            team_size = 4
        
        result = await topic_service.get_trending_suggestions(
            semester_id=semester_id,
            category_preference=category_preference,
            keywords=keywords,
            supervisor_expertise=supervisor_expertise,
            student_level=student_level,
            team_size=team_size
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
