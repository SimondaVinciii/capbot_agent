"""Pydantic schemas for request/response models."""

from pydantic import BaseModel, Field
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


class TopicRequest(BaseModel):
    """Schema for topic submission request."""
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
    category_id: Optional[int] = Field(
        None, 
        description="Topic category ID",
        example=2
    )
    supervisor_id: int = Field(
        ..., 
        description="Supervisor user ID",
        example=1
    )
    semester_id: int = Field(
        ..., 
        description="Semester ID",
        example=1
    )
    max_students: int = Field(
        default=1, 
        description="Maximum number of students",
        example=2
    )


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
    description: Optional[str]
    objectives: Optional[str]
    supervisor_id: int
    category_id: Optional[int]
    semester_id: int
    max_students: int
    is_approved: bool
    created_at: datetime
    latest_version: Optional[TopicVersionResponse] = None
    approved_version: Optional[TopicVersionResponse] = None

    class Config:
        from_attributes = True


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
    methodology: str = Field(
        ..., 
        description="Suggested research methodology",
        example="Machine Learning, Natural Language Processing, Educational Data Mining, User Experience Design"
    )
    expected_outcomes: str = Field(
        ..., 
        description="Expected deliverables and outcomes",
        example="A fully functional personalized learning platform with AI recommendations, detailed analytics dashboard, and research paper on adaptive learning"
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
                "methodology": "Machine Learning, Natural Language Processing, Educational Data Mining",
                "expected_outcomes": "A fully functional personalized learning platform with AI recommendations",
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
            "methodology": "Machine Learning, IoT sensors, Computer Vision, Data Analytics"
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


