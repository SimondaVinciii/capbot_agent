"""Pydantic schemas for request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TopicVersionStatus(Enum):
    """Topic version status enumeration."""
    DRAFT = 1
    SUBMITTED = 2
    UNDER_REVIEW = 3
    APPROVED = 4
    REJECTED = 5
    REVISION_REQUIRED = 6


class TopicStatus(Enum):
    """Topic status enumeration (deprecated - use TopicVersionStatus)."""
    DRAFT = 1
    SUBMITTED = 2
    UNDER_REVIEW = 3
    APPROVED = 4
    REJECTED = 5
    REVISION_REQUIRED = 6


class DuplicationStatus(Enum):
    """Duplication check status."""
    NO_DUPLICATE = "no_duplicate"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    DUPLICATE_FOUND = "duplicate_found"


class TopicVersionRequest(BaseModel):
    """Schema for topic version submission request."""
    title: str = Field(
        ..., 
        max_length=500, 
        description="Topic title",
        example="Hệ thống quản lý thư viện thông minh với AI"
    )
    description: Optional[str] = Field(
        None, 
        description="Detailed topic description",
        example="Xây dựng hệ thống quản lý thư viện hiện đại sử dụng AI và IoT để tự động hóa quy trình quản lý sách và tối ưu hóa trải nghiệm người dùng"
    )
    objectives: Optional[str] = Field(
        None, 
        description="Learning and research objectives",
        example="Nghiên cứu và triển khai AI trong quản lý thư viện, tự động hóa quy trình mượn trả sách, và phát triển hệ thống gợi ý sách thông minh"
    )
    methodology: Optional[str] = Field(
        None, 
        description="Research methodology and technical approach",
        example="Machine Learning, Computer Vision, IoT sensors, Web Development, Database Design"
    )
    expected_outcomes: Optional[str] = Field(
        None, 
        description="Expected deliverables and outcomes",
        example="Hoàn thiện hệ thống quản lý thư viện thông minh với khả năng nhận diện sách tự động, gợi ý sách cá nhân hóa, và báo cáo thống kê chi tiết"
    )
    requirements: Optional[str] = Field(
        None, 
        description="Technical requirements and prerequisites",
        example="Python, TensorFlow, OpenCV, IoT sensors, Web technologies (HTML, CSS, JavaScript), Database (SQL Server/MySQL)"
    )
    status: int = Field(
        default=2, 
        description="Version status: 1=Draft, 2=Submitted, 3=Under Review, 4=Approved, 5=Rejected",
        example=2
    )


# ===== Submission gating schemas (submit/resubmit) =====

class SubmissionGateConfig(BaseModel):
    """Config to decide pass/fail based on rubric results."""
    min_overall_score: float = Field(70.0, ge=0.0, le=100.0, description="Minimum overall score to pass")
    min_criterion_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional per-criterion minimums keyed by criterion id (0..10 scale)",
        example={"problem_clarity": 6.0, "approach_fit": 6.5}
    )


class SubmissionSubmitRequest(BaseModel):
    """Request to gate a submission using rubric evaluation before submit."""
    rubric_request: RubricEvaluationRequest
    gate: SubmissionGateConfig = Field(default_factory=SubmissionGateConfig)


class BlockingCriterion(BaseModel):
    id: str
    question: str
    score: float
    required_min: float


class SubmissionSubmitResponse(BaseModel):
    """Decision result for submit attempt based on rubric."""
    allowed: bool
    decision_reason: str
    overall_score: float
    overall_rating: str
    blocking_criteria: List[BlockingCriterion] = Field(default_factory=list)
    rubric: RubricEvaluationResponse
    suggestions: List[str] = Field(default_factory=list)


class SubmissionResubmitRequest(BaseModel):
    """Request to gate a resubmission using rubric improvement threshold."""
    rubric_request: RubricEvaluationRequest
    previous_overall_score: float = Field(..., ge=0.0, le=100.0)
    improvement_threshold: float = Field(5.0, ge=0.0, le=100.0, description="Minimum points improvement required")
    gate: SubmissionGateConfig = Field(default_factory=SubmissionGateConfig)


class SubmissionResubmitResponse(BaseModel):
    allowed: bool
    decision_reason: str
    overall_score: float
    overall_rating: str
    improvement: float
    blocking_criteria: List[BlockingCriterion] = Field(default_factory=list)
    rubric: RubricEvaluationResponse
    suggestions: List[str] = Field(default_factory=list)


class TopicRequest(BaseModel):
    """Schema for topic submission request."""
    eN_Title: Optional[str] = Field(
        None,
        description="English title duplicate for systems expecting EN_Title",
        example="AI-Powered Library Management System"
    )
    abbreviation: Optional[str] = Field(
        None,
        description="Short abbreviation derived from the title",
        example="APLMS"
    )
    title: str = Field(
        ..., 
        max_length=500, 
        description="Topic title",
        example="Hệ thống quản lý thư viện thông minh với AI"
    )
    description: Optional[str] = Field(
        None, 
        description="Detailed topic description",
        example="Xây dựng hệ thống quản lý thư viện hiện đại sử dụng AI và IoT để tự động hóa quy trình quản lý sách và tối ưu hóa trải nghiệm người dùng"
    )
    objectives: Optional[str] = Field(
        None, 
        description="Learning and research objectives",
        example="Nghiên cứu và triển khai AI trong quản lý thư viện, tự động hóa quy trình mượn trả sách, và phát triển hệ thống gợi ý sách thông minh"
    )
    problem: Optional[str] = Field(
        None, 
        description="Problem statement and research question",
        example="Cần giải quyết vấn đề quản lý thư viện thủ công, thiếu tự động hóa và khả năng gợi ý sách cá nhân hóa"
    )
    context: Optional[str] = Field(
        None, 
        description="Research context and background",
        example="Trong bối cảnh phát triển công nghệ AI và IoT, việc ứng dụng vào quản lý thư viện trở nên cần thiết để nâng cao hiệu quả và trải nghiệm người dùng"
    )
    content: Optional[str] = Field(
        None, 
        description="Main research content and scope",
        example="Nghiên cứu và phát triển hệ thống quản lý thư viện thông minh sử dụng AI để nhận diện sách, gợi ý cá nhân hóa và IoT để theo dõi tài sản"
    )
    category_id: Optional[int] = Field(
        None,
        description="Topic category ID",
        example=2,
        alias="categoryId",
    )
    supervisor_id: int = Field(
        ...,
        description="Supervisor user ID",
        example=1,
        alias="supervisorId",
    )
    semester_id: int = Field(
        ...,
        description="Semester ID",
        example=1,
        alias="semesterId",
    )
    max_students: int = Field(
        default=1, 
        description="Maximum number of students",
        example=2
    )

    # Pydantic v2 config: allow population by field name when aliases exist
    model_config = ConfigDict(populate_by_name=True)


class TopicVersionResponse(BaseModel):
    """Schema for topic version response."""
    id: int
    topic_id: int
    version_number: int
    title: str
    description: Optional[str]
    objectives: Optional[str]
    methodology: Optional[str]
    expected_outcomes: Optional[str]
    requirements: Optional[str]
    status: int
    submitted_at: Optional[datetime]
    submitted_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TopicResponse(BaseModel):
    """Schema for topic response."""
    id: int
    title: str
    eN_Title: str
    abbreviation: Optional[str]
    description: Optional[str]
    objectives: Optional[str]
    supervisor_id: int = Field(alias="supervisorId")
    category_id: Optional[int] = Field(alias="categoryId")
    semester_id: int = Field(alias="semesterId")
    max_students: int
    is_approved: bool
    created_at: datetime
    latest_version: Optional[TopicVersionResponse] = None
    approved_version: Optional[TopicVersionResponse] = None

    # Pydantic v2 config
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DuplicateCheckResult(BaseModel):
    """Schema for duplicate check result."""
    status: DuplicationStatus = Field(
        ..., 
        description="Duplicate detection status",
        example="POTENTIAL_DUPLICATE"
    )
    similarity_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Similarity score between 0 and 1",
        example=0.75
    )
    similar_topics: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of similar topics found",
        example=[
            {
                "topic_id": 45,
                "title": "Hệ thống quản lý học tập",
                "similarity_score": 0.75,
                "reason": "Similar objectives and methodology"
            }
        ]
    )
    threshold: float = Field(
        ..., 
        description="Similarity threshold used for detection",
        example=0.8
    )
    message: str = Field(
        ..., 
        description="Human-readable message about the result",
        example="Phát hiện đề tài có khả năng trùng lặp với độ tương tự 75%"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
        example=[
            "Consider adding specific technology focus",
            "Differentiate the target audience",
            "Modify the methodology approach"
        ]
    )
    processing_time: float = Field(
        ..., 
        description="Time taken for duplicate check in seconds",
        example=1.234
    )


class TopicSuggestion(BaseModel):
    """Schema for topic suggestions."""
    title: str = Field(
        ..., 
        description="Suggested topic title",
        example="AI-Powered Personalized Learning System"
    )
    description: str = Field(
        ..., 
        description="Detailed topic description",
        example="Develop an intelligent learning platform that adapts to individual student needs using machine learning algorithms and natural language processing"
    )
    objectives: str = Field(
        ..., 
        description="Learning and research objectives",
        example="Create personalized learning paths, implement adaptive assessment, improve learning outcomes through AI-driven insights"
    )
    problem: str = Field(
        ..., 
        description="Problem statement and research question",
        example="Cần giải quyết vấn đề cá nhân hóa học tập cho từng sinh viên với nhu cầu và khả năng khác nhau"
    )
    context: str = Field(
        ..., 
        description="Research context and background",
        example="Trong bối cảnh giáo dục hiện đại, việc cá nhân hóa học tập trở nên quan trọng để nâng cao hiệu quả giáo dục"
    )
    content: str = Field(
        ..., 
        description="Main research content and scope",
        example="Nghiên cứu và phát triển hệ thống học tập thông minh sử dụng AI để phân tích nhu cầu học tập và đề xuất nội dung phù hợp"
    )
    category: str = Field(
        ..., 
        description="Suggested topic category",
        example="Artificial Intelligence in Education"
    )
    rationale: str = Field(
        ..., 
        description="Why this topic is trending/relevant",
        example="Trending in educational technology with high research potential and practical applications in modern learning environments"
    )
    difficulty_level: str = Field(
        default="Intermediate",
        description="Difficulty level of the topic",
        example="Advanced"
    )
    estimated_duration: str = Field(
        default="6 months",
        description="Estimated project duration",
        example="6 months"
    )
    team_size: int = Field(
        default=4,
        description="Recommended team size (4 or 5)",
        example=4
    )
    suggested_roles: List[str] = Field(
        default_factory=list,
        description="Suggested team roles for effective collaboration",
        example=["Team Lead/PM", "Backend Developer", "Frontend Developer", "AI/ML Engineer"]
    )


class TopicSuggestionV2(BaseModel):
    """Schema for topic suggestions v2 with additional fields."""
    eN_Title: str = Field(
        ..., 
        description="English title of the topic",
        example="AI-Powered Personalized Learning System"
    )
    abbreviation: str = Field(
        ..., 
        description="Short abbreviation derived from the title",
        example="APLS"
    )
    vN_title: str = Field(
        ..., 
        description="Vietnamese title of the topic",
        example="Hệ thống học tập cá nhân hóa sử dụng AI"
    )
    problem: str = Field(
        ..., 
        description="Problem statement and research question",
        example="Cần giải quyết vấn đề cá nhân hóa học tập cho từng sinh viên với nhu cầu và khả năng khác nhau"
    )
    context: str = Field(
        ..., 
        description="Research context and background",
        example="Trong bối cảnh giáo dục hiện đại, việc cá nhân hóa học tập trở nên quan trọng để nâng cao hiệu quả giáo dục"
    )
    content: str = Field(
        ..., 
        description="Main research content and scope",
        example="Nghiên cứu và phát triển hệ thống học tập thông minh sử dụng AI để phân tích nhu cầu học tập và đề xuất nội dung phù hợp"
    )
    description: str = Field(
        ..., 
        description="Detailed topic description",
        example="Phát triển nền tảng học tập thông minh có khả năng thích ứng với nhu cầu cá nhân của từng sinh viên sử dụng thuật toán machine learning và xử lý ngôn ngữ tự nhiên"
    )
    objectives: str = Field(
        ..., 
        description="Learning and research objectives",
        example="Tạo ra các lộ trình học tập cá nhân hóa, triển khai đánh giá thích ứng, cải thiện kết quả học tập thông qua các phân tích dựa trên AI"
    )
    category: str = Field(
        ..., 
        description="Suggested topic category",
        example="Artificial Intelligence in Education"
    )
    rationale: str = Field(
        ..., 
        description="Why this topic is trending/relevant",
        example="Đang là xu hướng trong công nghệ giáo dục với tiềm năng nghiên cứu cao và ứng dụng thực tế trong môi trường học tập hiện đại"
    )
    difficulty_level: str = Field(
        default="Intermediate",
        description="Difficulty level of the topic",
        example="Advanced"
    )
    estimated_duration: str = Field(
        default="14 weeks",
        description="Estimated project duration",
        example="14 weeks"
    )
    team_size: int = Field(
        default=4,
        description="Recommended team size (4 or 5)",
        example=4
    )
    suggested_roles: List[str] = Field(
        default_factory=list,
        description="Suggested team roles for effective collaboration",
        example=["Team Lead/PM", "Backend Developer", "Frontend Developer", "AI/ML Engineer"]
    )


class TopicSuggestionsResponse(BaseModel):
    """Schema for topic suggestions response."""
    suggestions: List[TopicSuggestion] = Field(
        ..., 
        description="List of topic suggestions",
        example=[
            {
                 "title": "AI-Powered Personalized Learning System",
                 "description": "Develop an intelligent learning platform that adapts to individual student needs using machine learning algorithms",
                 "objectives": "Create personalized learning paths, implement adaptive assessment, and improve learning outcomes",
                 "problem": "Cần giải quyết vấn đề cá nhân hóa học tập cho từng sinh viên với nhu cầu và khả năng khác nhau",
                 "context": "Trong bối cảnh giáo dục hiện đại, việc cá nhân hóa học tập trở nên quan trọng để nâng cao hiệu quả giáo dục",
                 "content": "Nghiên cứu và phát triển hệ thống học tập thông minh sử dụng AI để phân tích nhu cầu học tập và đề xuất nội dung phù hợp",
                 "category": "Artificial Intelligence in Education",
                 "rationale": "Trending in educational technology with high research potential",
                 "difficulty_level": "Advanced",
                 "estimated_duration": "6 months"
            }
        ]
    )
    trending_areas: List[str] = Field(
        ..., 
        description="Current trending research areas",
        example=["AI in Education", "Personalized Learning", "Adaptive Systems", "Educational Data Mining"]
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, 
        description="When suggestions were generated",
        example="2024-01-22T10:30:00Z"
    )
    trending_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis of current trends",
        example={
            "hot_topics": ["AI in Education", "Personalized Learning", "Adaptive Systems"],
            "research_gaps": ["Cross-cultural adaptation", "Accessibility features"],
            "technology_trends": ["GPT integration", "Real-time analytics"]
        }
    )
    processing_time: float = Field(
        ..., 
        description="Time taken to generate suggestions in seconds",
        example=3.456
    )


class TopicSuggestionsV2Response(BaseModel):
    """Schema for topic suggestions v2 response."""
    suggestions: List[TopicSuggestionV2] = Field(
        ..., 
        description="List of topic suggestions v2",
        example=[
            {
                 "eN_Title": "AI-Powered Personalized Learning System",
                 "abbreviation": "APLS",
                 "vN_title": "Hệ thống học tập cá nhân hóa sử dụng AI",
                 "problem": "Cần giải quyết vấn đề cá nhân hóa học tập cho từng sinh viên với nhu cầu và khả năng khác nhau",
                 "context": "Trong bối cảnh giáo dục hiện đại, việc cá nhân hóa học tập trở nên quan trọng để nâng cao hiệu quả giáo dục",
                 "content": "Nghiên cứu và phát triển hệ thống học tập thông minh sử dụng AI để phân tích nhu cầu học tập và đề xuất nội dung phù hợp",
                 "description": "Phát triển nền tảng học tập thông minh có khả năng thích ứng với nhu cầu cá nhân của từng sinh viên sử dụng thuật toán machine learning và xử lý ngôn ngữ tự nhiên",
                 "objectives": "Tạo ra các lộ trình học tập cá nhân hóa, triển khai đánh giá thích ứng, cải thiện kết quả học tập thông qua các phân tích dựa trên AI",
                 "category": "Artificial Intelligence in Education",
                 "rationale": "Đang là xu hướng trong công nghệ giáo dục với tiềm năng nghiên cứu cao và ứng dụng thực tế trong môi trường học tập hiện đại",
                 "difficulty_level": "Advanced",
                 "estimated_duration": "14 weeks"
            }
        ]
    )
    trending_areas: List[str] = Field(
        ..., 
        description="Current trending research areas",
        example=["AI in Education", "Personalized Learning", "Adaptive Systems", "Educational Data Mining"]
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, 
        description="When suggestions were generated",
        example="2024-01-22T10:30:00Z"
    )
    trending_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis of current trends",
        example={
            "hot_topics": ["AI in Education", "Personalized Learning", "Adaptive Systems"],
            "research_gaps": ["Cross-cultural adaptation", "Accessibility features"],
            "technology_trends": ["GPT integration", "Real-time analytics"]
        }
    )
    processing_time: float = Field(
        ..., 
        description="Time taken to generate suggestions in seconds",
        example=3.456
    )


class TopicModificationRequest(BaseModel):
    """Schema for topic modification request."""
    original_topic: TopicRequest
    similar_topics: List[Dict[str, Any]]
    modification_type: str = Field(..., description="Type of modification needed")


class TopicModificationResponse(BaseModel):
    """Schema for topic modification response."""
    modified_topic: TopicRequest = Field(
        ..., 
        description="The modified topic with improvements",
        example={
            "title": "AI-Powered Smart Library Management System with IoT Integration",
            "description": "Develop an intelligent library management system using AI and IoT sensors for real-time book tracking and user behavior analysis",
            "objectives": "Implement AI-driven book recommendations, IoT-based inventory management, and predictive analytics for library operations",
            "problem": "Traditional library management lacks automation and personalized recommendations",
            "context": "Modern libraries need intelligent systems to handle increasing collections and user demands",
            "content": "Research and develop AI-powered library management with IoT integration for real-time tracking and user analytics"
        }
    )
    modifications_made: List[str] = Field(
        ..., 
        description="List of modifications applied",
        example=[
            "Added IoT integration to differentiate from existing systems",
            "Included predictive analytics for unique value proposition",
            "Enhanced with computer vision for advanced book tracking"
        ]
    )
    rationale: str = Field(
        ..., 
        description="Explanation of why modifications were made",
        example="Modifications were made to address similarity concerns by adding unique technological components (IoT, predictive analytics) while preserving the core library management concept"
    )
    similarity_improvement: float = Field(
        ..., 
        description="Expected improvement in uniqueness score",
        example=0.85
    )
    improvement_estimation: Dict[str, float] = Field(
        default_factory=dict,
        description="Detailed improvement metrics",
        example={
            "uniqueness_score": 0.85,
            "feasibility_score": 0.78,
            "innovation_score": 0.82
        }
    )
    changes_summary: Dict[str, bool] = Field(
        default_factory=dict,
        description="Summary of what was changed",
        example={
            "title_changed": True,
            "description_enhanced": True,
            "objectives_expanded": True,
            "methodology_updated": True
        }
    )
    processing_time: float = Field(
        ..., 
        description="Time taken for modification in seconds",
        example=2.123
    )


class AgentProcessRequest(BaseModel):
    """Schema for main agent processing request."""
    topic_request: TopicRequest
    check_duplicates: bool = Field(default=True, description="Whether to check for duplicates")
    get_suggestions: bool = Field(default=False, description="Whether to get trending suggestions first")
    auto_modify: bool = Field(default=True, description="Whether to automatically modify if duplicates found")


class AgentProcessResponse(BaseModel):
    """Schema for main agent processing response."""
    success: bool = Field(
        ..., 
        description="Whether the processing was successful",
        example=True
    )
    topic_id: Optional[int] = Field(
        None, 
        description="Created topic ID if successful",
        example=123
    )
    duplicate_check: Optional[DuplicateCheckResult] = Field(
        None, 
        description="Results of duplicate detection if performed"
    )
    suggestions: Optional[TopicSuggestionsResponse] = Field(
        None, 
        description="Topic suggestions if requested"
    )
    modifications: Optional[TopicModificationResponse] = Field(
        None, 
        description="Topic modifications if duplicates were found and auto-modify was enabled"
    )
    final_topic: Optional[TopicResponse] = Field(
        None, 
        description="Final topic data after all processing"
    )
    messages: List[str] = Field(
        default_factory=list, 
        description="Processing messages and status updates",
        example=[
            "Đề tài có tính độc đáo tốt, không phát hiện trùng lặp",
            "Đã tạo đề tài thành công trong cơ sở dữ liệu",
            "Đã lưu trữ đề tài vào hệ thống tìm kiếm"
        ]
    )
    processing_time: float = Field(
        ..., 
        description="Total processing time in seconds",
        example=2.345
    )


class TrendingTopicData(BaseModel):
    """Schema for trending topic data from external API."""
    area: str = Field(..., description="Research area")
    keywords: List[str] = Field(..., description="Trending keywords")
    description: str = Field(..., description="Area description")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


class ChromaDocument(BaseModel):
    """Schema for ChromaDB document."""
    id: str
    text: str
    metadata: Dict[str, Any]


class SimilaritySearchResult(BaseModel):
    """Schema for similarity search result."""
    document_id: str
    topic_id: int
    title: str
    similarity_score: float
    metadata: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(
        ..., 
        description="Error type or code",
        example="ValidationError"
    )
    message: str = Field(
        ..., 
        description="Human-readable error message",
        example="Topic title is required and cannot be empty"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error details and context",
        example={
            "field": "title",
            "value": "",
            "constraint": "required"
        }
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Error timestamp",
        example="2024-01-22T10:30:00Z"
    )



# ===== Rubric evaluation schemas =====

class RubricCriterionEvaluation(BaseModel):
    """Evaluation detail for a single rubric criterion."""
    id: str = Field(..., description="Stable identifier for the criterion", example="title_alignment")
    question: str = Field(..., description="Rubric question in Vietnamese")
    score: float = Field(..., ge=0.0, le=10.0, description="Score 0-10 for this criterion", example=8.5)
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight of the criterion in overall score", example=0.1)
    assessment: str = Field(..., description="Short assessment for this criterion")
    evidence: str = Field(default="", description="Evidence quoted or inferred from the proposal")
    recommendations: List[str] = Field(default_factory=list, description="Actionable improvements (short bullets)")


class RubricEvaluationResponse(BaseModel):
    """Aggregated rubric evaluation for a topic proposal."""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted total score on 0-100 scale", example=82.0)
    overall_rating: str = Field(..., description="Rating band derived from overall score", example="Good")
    summary: str = Field(..., description="One-paragraph summary of the evaluation")
    criteria: List[RubricCriterionEvaluation] = Field(..., description="Per-criterion results (10 items)")
    missing_fields: List[str] = Field(default_factory=list, description="Missing or weak sections detected")
    risks: List[str] = Field(default_factory=list, description="Top risks or uncertainties")
    next_steps: List[str] = Field(default_factory=list, description="Concrete next steps to improve the proposal")
    processing_time: float = Field(..., description="Time taken for evaluation in seconds", example=1.234)


class RubricEvaluationRequest(BaseModel):
    """Input for rubric evaluation of a topic proposal."""
    topic_request: TopicRequest
    context: Optional[str] = Field(None, description="Ngữ cảnh nơi sản phẩm được triển khai")
    problem_statement: Optional[str] = Field(None, description="Vấn đề cần giải quyết")
    main_actors: Optional[List[str]] = Field(None, description="Người dùng chính")
    main_flows: Optional[str] = Field(None, description="Các luồng xử lý/chức năng chính")
    customers_sponsors: Optional[str] = Field(None, description="Khách hàng/nhà tài trợ")
    approach_theory: Optional[str] = Field(None, description="Hướng tiếp cận về lý thuyết")
    applied_technology: Optional[str] = Field(None, description="Công nghệ áp dụng")
    main_deliverables: Optional[str] = Field(None, description="Các sản phẩm cần tạo ra")
    scope: Optional[str] = Field(None, description="Phạm vi đề tài")
    size_of_product: Optional[str] = Field(None, description="Độ lớn sản phẩm")
    packages_breakdown: Optional[List[str]] = Field(None, description="Phân chia thành các gói công việc")
    complexity: Optional[str] = Field(None, description="Độ phức tạp/tính kỹ thuật")
    applicability: Optional[str] = Field(None, description="Tính ứng dụng thực tế")
    feasibility: Optional[str] = Field(None, description="Tính khả thi về công nghệ và thời gian")
    proposal_text: Optional[str] = Field(
        None,
        description="Toàn bộ thuyết minh/đề cương (nếu có) để đánh giá thêm"
    )