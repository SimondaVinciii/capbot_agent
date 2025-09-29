"""Service layer for topic-related business logic."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.repositories.topic_repository import TopicRepository
from app.agents.main_agent import MainAgent
from app.agents.check_rubric_agent import CheckRubricAgent
from app.schemas.schemas import (
    TopicRequest, TopicResponse, TopicVersionRequest, TopicVersionResponse,
    AgentProcessRequest, DuplicateCheckResult, TopicSuggestionsResponse,
    RubricEvaluationRequest
)
import logging

class TopicService:
    """Service layer for topic operations."""
    
    def __init__(self):
        self.logger = logging.getLogger("topic_service")
        self.main_agent = MainAgent()
        self.rubric_agent = CheckRubricAgent()
    
    async def submit_topic_with_ai_support(
        self,
        topic_request: TopicRequest,
        check_duplicates: bool = True,
        get_suggestions: bool = False,
        auto_modify: bool = True
    ) -> Dict[str, Any]:
        """Submit a topic with full AI agent support.
        
        Args:
            topic_request: Topic submission data
            check_duplicates: Whether to check for duplicates
            get_suggestions: Whether to get trending suggestions
            auto_modify: Whether to auto-modify if duplicates found
            
        Returns:
            Complete processing result
        """
        try:
            self.logger.info(f"Submitting topic with AI support: {topic_request.title}")
            
            # Prepare agent process request
            agent_request = AgentProcessRequest(
                topic_request=topic_request,
                check_duplicates=check_duplicates,
                get_suggestions=get_suggestions,
                auto_modify=auto_modify
            )
            
            # Process through main agent
            result = await self.main_agent.process(agent_request.dict())
            
            self.logger.info(f"Topic submission processed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in submit_topic_with_ai_support: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": [f"Lỗi xử lý: {str(e)}"]
            }
    
    async def check_topic_duplicates(self, topic_request: TopicRequest) -> Dict[str, Any]:
        """Check for topic duplicates only.
        
        Args:
            topic_request: Topic data to check
            
        Returns:
            Duplicate check results
        """
        try:
            self.logger.info(f"Checking duplicates for topic: {topic_request.title}")
            
            topic_data = {
                "topic_title": topic_request.title,
                "topic_description": topic_request.description or "",
                "topic_objectives": topic_request.objectives or "",
                "topic_methodology": getattr(topic_request, 'methodology', '') or "",
                "semester_id": topic_request.semester_id
            }
            
            result = await self.main_agent.process_duplicate_check_only(topic_data)
            
            self.logger.info(f"Duplicate check completed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in check_topic_duplicates: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_trending_suggestions(
        self,
        semester_id: int,
        category_preference: str = "",
        keywords: List[str] = None,
        supervisor_expertise: List[str] = None,
        student_level: str = "undergraduate",
        team_size: int = 4
    ) -> Dict[str, Any]:
        """Get trending topic suggestions.
        
        Args:
            semester_id: Target semester ID
            category_preference: Preferred category
            keywords: Keywords of interest
            supervisor_expertise: Supervisor's expertise areas
            student_level: Student level (undergraduate/graduate)
            
        Returns:
            Topic suggestions based on trends
        """
        try:
            self.logger.info(f"Getting trending suggestions for semester: {semester_id}")
            
            suggestion_data = {
                "semester_id": semester_id,
                "category_preference": category_preference,
                "keywords": keywords or [],
                "supervisor_expertise": supervisor_expertise or [],
                "student_level": student_level,
                "team_size": team_size
            }
            
            result = await self.main_agent.process_suggestion_only(suggestion_data)
            
            self.logger.info(f"Suggestions generated: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in get_trending_suggestions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def modify_topic_for_uniqueness(
        self,
        topic_request: TopicRequest,
        duplicate_results: Dict[str, Any],
        preserve_core_idea: bool = True
    ) -> Dict[str, Any]:
        """Modify topic to reduce duplicates.
        
        Args:
            topic_request: Original topic data
            duplicate_results: Results from duplicate check
            preserve_core_idea: Whether to preserve the core idea
            
        Returns:
            Modified topic suggestions
        """
        try:
            self.logger.info(f"Modifying topic for uniqueness: {topic_request.title}")
            
            modification_data = {
                "original_topic": topic_request.dict(),
                "duplicate_results": duplicate_results,
                "modification_preferences": {},
                "preserve_core_idea": preserve_core_idea
            }
            
            result = await self.main_agent.process_modification_only(modification_data)
            
            self.logger.info(f"Topic modification completed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in modify_topic_for_uniqueness: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def evaluate_topic_rubric(self, req: RubricEvaluationRequest) -> Dict[str, Any]:
        """Evaluate a topic proposal using the rubric agent."""
        try:
            self.logger.info("Evaluating topic rubric")
            result = await self.rubric_agent.process(req.dict())
            return result
        except Exception as e:
            self.logger.error(f"Error in evaluate_topic_rubric: {e}")
            return {"success": False, "error": str(e)}
    
    def create_topic_simple(self, topic_request: TopicRequest) -> Dict[str, Any]:
        """Create topic without AI processing (simple creation).
        
        Args:
            topic_request: Topic data to create
            
        Returns:
            Creation result
        """
        try:
            self.logger.info(f"Creating topic simple: {topic_request.title}")
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                
                # Check if topic exists
                if repository.topic_exists_by_title(topic_request.title, topic_request.semester_id):
                    return {
                        "success": False,
                        "error": "Đề tài với tiêu đề này đã tồn tại trong học kỳ"
                    }
                
                # Create topic
                topic = repository.create_topic(topic_request)
                
                # Convert to response
                topic_response = TopicResponse(
                    id=topic.Id,
                    title=topic.Title,
                    eN_Title=topic.Title,
                    abbreviation=getattr(topic, "Abbreviation", None),
                    description=topic.Description,
                    objectives=topic.Objectives,
                    supervisor_id=topic.SupervisorId,
                    category_id=topic.CategoryId,
                    semester_id=topic.SemesterId,
                    max_students=topic.MaxStudents,
                    is_approved=topic.IsApproved,
                    created_at=topic.CreatedAt
                )
                
                self.logger.info(f"Topic created successfully: {topic.Id}")
                
                return {
                    "success": True,
                    "data": {
                        "topic_id": topic.Id,
                        "topic": topic_response.dict(by_alias=True)
                    }
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in create_topic_simple: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_topic_by_id(self, topic_id: int) -> Optional[TopicResponse]:
        """Get topic by ID.
        
        Args:
            topic_id: Topic ID
            
        Returns:
            Topic data or None
        """
        try:
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                topic = repository.get_topic_by_id(topic_id)
                
                if not topic:
                    return None
                
                return TopicResponse(
                    id=topic.Id,
                    title=topic.Title,
                    eN_Title=topic.Title,
                    abbreviation=getattr(topic, "Abbreviation", None),
                    description=topic.Description,
                    objectives=topic.Objectives,
                    supervisor_id=topic.SupervisorId,
                    category_id=topic.CategoryId,
                    semester_id=topic.SemesterId,
                    max_students=topic.MaxStudents,
                    is_approved=topic.IsApproved,
                    created_at=topic.CreatedAt
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting topic {topic_id}: {e}")
            return None
    
    def get_topics_by_semester(self, semester_id: int, limit: int = 100, approved_only: bool = False) -> List[TopicResponse]:
        """Get topics by semester.
        
        Args:
            semester_id: Semester ID
            limit: Maximum number of topics to return
            approved_only: Whether to return only approved topics
            
        Returns:
            List of topics
        """
        try:
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                topics = repository.get_topics_by_semester(semester_id, limit, approved_only)
                
                return [
                    TopicResponse(
                        id=topic.Id,
                        title=topic.Title,
                        eN_Title=topic.Title,
                        abbreviation=getattr(topic, "Abbreviation", None),
                        description=topic.Description,
                        objectives=topic.Objectives,
                        supervisor_id=topic.SupervisorId,
                        category_id=topic.CategoryId,
                        semester_id=topic.SemesterId,
                        max_students=topic.MaxStudents,
                        is_approved=topic.IsApproved,
                        created_at=topic.CreatedAt
                    )
                    for topic in topics
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting topics for semester {semester_id}: {e}")
            return []
    
    def search_topics(self, title_keywords: List[str], semester_id: Optional[int] = None) -> List[TopicResponse]:
        """Search topics by title keywords.
        
        Args:
            title_keywords: Keywords to search for
            semester_id: Optional semester filter
            
        Returns:
            List of matching topics
        """
        try:
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                topics = repository.search_topics_by_title(title_keywords, semester_id)
                
                return [
                    TopicResponse(
                        id=topic.Id,
                        title=topic.Title,
                        eN_Title=topic.Title,
                        abbreviation=getattr(topic, "Abbreviation", None),
                        description=topic.Description,
                        objectives=topic.Objectives,
                        supervisor_id=topic.SupervisorId,
                        category_id=topic.CategoryId,
                        semester_id=topic.SemesterId,
                        max_students=topic.MaxStudents,
                        is_approved=topic.IsApproved,
                        created_at=topic.CreatedAt
                    )
                    for topic in topics
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error searching topics: {e}")
            return []
    
    async def initialize_system(self) -> Dict[str, Any]:
        """Initialize the AI system (ChromaDB indexing, etc.).
        
        Returns:
            Initialization result
        """
        try:
            self.logger.info("Initializing AI system")
            
            # Initialize topic index in ChromaDB
            result = await self.main_agent.initialize_topic_index()
            
            self.logger.info(f"AI system initialization: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error initializing system: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics.
        
        Returns:
            System statistics
        """
        try:
            return self.main_agent.get_agent_stats()
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {"error": str(e)}
    
    # Topic Version Management Methods
    
    def get_topic_versions(self, topic_id: int) -> List[TopicVersionResponse]:
        """Get all versions of a topic."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                versions = repository.get_topic_versions_by_topic_id(topic_id)
                
                return [
                    TopicVersionResponse(
                        id=version.Id,
                        topic_id=version.TopicId,
                        version_number=version.VersionNumber,
                        title=version.Title,
                        description=version.Description,
                        objectives=version.Objectives,
                        methodology=version.Methodology,
                        expected_outcomes=version.ExpectedOutcomes,
                        requirements=version.Requirements,
                        status=version.Status,
                        submitted_at=version.SubmittedAt,
                        submitted_by=version.SubmittedBy,
                        created_at=version.CreatedAt
                    )
                    for version in versions
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting topic versions for topic {topic_id}: {e}")
            return []
    
    def get_latest_topic_version(self, topic_id: int) -> Optional[TopicVersionResponse]:
        """Get latest version of a topic."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                version = repository.get_latest_topic_version(topic_id)
                
                if not version:
                    return None
                
                return TopicVersionResponse(
                    id=version.Id,
                    topic_id=version.TopicId,
                    version_number=version.VersionNumber,
                    title=version.Title,
                    description=version.Description,
                    objectives=version.Objectives,
                    methodology=version.Methodology,
                    expected_outcomes=version.ExpectedOutcomes,
                    requirements=version.Requirements,
                    status=version.Status,
                    submitted_at=version.SubmittedAt,
                    submitted_by=version.SubmittedBy,
                    created_at=version.CreatedAt
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting latest version for topic {topic_id}: {e}")
            return None
    
    def get_approved_topic_version(self, topic_id: int) -> Optional[TopicVersionResponse]:
        """Get approved version of a topic."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                version = repository.get_approved_topic_version(topic_id)
                
                if not version:
                    return None
                
                return TopicVersionResponse(
                    id=version.Id,
                    topic_id=version.TopicId,
                    version_number=version.VersionNumber,
                    title=version.Title,
                    description=version.Description,
                    objectives=version.Objectives,
                    methodology=version.Methodology,
                    expected_outcomes=version.ExpectedOutcomes,
                    requirements=version.Requirements,
                    status=version.Status,
                    submitted_at=version.SubmittedAt,
                    submitted_by=version.SubmittedBy,
                    created_at=version.CreatedAt
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting approved version for topic {topic_id}: {e}")
            return None
    
    def create_topic_version(self, topic_id: int, version_request: TopicVersionRequest) -> Optional[TopicVersionResponse]:
        """Create a new version of a topic."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                
                # Get existing versions to determine next version number
                existing_versions = repository.get_topic_versions_by_topic_id(topic_id)
                next_version_number = len(existing_versions) + 1
                
                # Convert version request to topic request format
                topic_data = TopicRequest(
                    title=version_request.title,
                    description=version_request.description,
                    objectives=version_request.objectives,
                    methodology=version_request.methodology,
                    expected_outcomes=version_request.expected_outcomes,
                    requirements=version_request.requirements,
                    supervisor_id=1,  # Will be overridden
                    semester_id=1,  # Will be overridden
                    category_id=None,
                    max_students=1
                )
                
                version = repository.create_topic_version(
                    topic_id=topic_id,
                    version_data=topic_data,
                    version_number=next_version_number,
                    status=version_request.status
                )
                
                return TopicVersionResponse(
                    id=version.Id,
                    topic_id=version.TopicId,
                    version_number=version.VersionNumber,
                    title=version.Title,
                    description=version.Description,
                    objectives=version.Objectives,
                    methodology=version.Methodology,
                    expected_outcomes=version.ExpectedOutcomes,
                    requirements=version.Requirements,
                    status=version.Status,
                    submitted_at=version.SubmittedAt,
                    submitted_by=version.SubmittedBy,
                    created_at=version.CreatedAt
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error creating version for topic {topic_id}: {e}")
            return None
    
    def approve_topic_version(self, version_id: int) -> bool:
        """Approve a topic version."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                success = repository.approve_topic_version(version_id)
                
                # If approved, index this version in ChromaDB
                if success:
                    self._index_approved_version(version_id)
                
                return success
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error approving version {version_id}: {e}")
            return False
    
    def reject_topic_version(self, version_id: int, reason: str = None) -> bool:
        """Reject a topic version."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                return repository.reject_topic_version(version_id, reason)
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error rejecting version {version_id}: {e}")
            return False
    
    def get_approved_topic_versions(self, semester_id: Optional[int] = None, limit: int = 100) -> List[TopicVersionResponse]:
        """Get all approved topic versions."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                versions_data = repository.get_approved_topic_versions(limit)
                
                # Filter by semester if provided
                if semester_id:
                    versions_data = [v for v in versions_data if v["semester_id"] == semester_id]
                
                return [
                    TopicVersionResponse(
                        id=data["version_id"],
                        topic_id=data["topic_id"],
                        version_number=data["version_number"],
                        title=data["title"],
                        description=data["description"],
                        objectives=data["objectives"],
                        methodology=data["methodology"],
                        expected_outcomes=data["expected_outcomes"],
                        requirements=data["requirements"],
                        status=data["status"],
                        submitted_at=None,  # Not in the data
                        submitted_by=None,  # Not in the data
                        created_at=data["created_at"]
                    )
                    for data in versions_data
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting approved versions: {e}")
            return []
    
    async def _index_approved_version(self, version_id: int):
        """Index an approved version in ChromaDB."""
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                version = repository.get_topic_version_by_id(version_id)
                
                if not version or version.Status != 4:  # Not approved
                    return
                
                # Get topic info
                topic = repository.get_topic_by_id(version.TopicId)
                if not topic:
                    return
                
                # Combine content for indexing
                content_parts = []
                if version.Title:
                    content_parts.append(version.Title)
                if version.Description:
                    content_parts.append(version.Description)
                if version.Objectives:
                    content_parts.append(version.Objectives)
                if version.Methodology:
                    content_parts.append(version.Methodology)
                if version.ExpectedOutcomes:
                    content_parts.append(version.ExpectedOutcomes)
                if version.Requirements:
                    content_parts.append(version.Requirements)
                
                full_content = " ".join(content_parts)
                
                # Index data
                index_data = {
                    "id": f"{topic.Id}_{version.Id}",
                    "title": version.Title,
                    "content": full_content,
                    "metadata": {
                        "topic_id": topic.Id,
                        "version_id": version.Id,
                        "version_number": version.VersionNumber,
                        "semester_id": topic.SemesterId,
                        "category_id": topic.CategoryId,
                        "supervisor_id": topic.SupervisorId,
                        "status": version.Status,
                        "created_at": version.CreatedAt.isoformat() if version.CreatedAt else None,
                        # New fields from TopicVersion
                        "vn_title": getattr(version, "VN_title", None),
                        "document_url": version.DocumentUrl,
                        "submitted_at": version.SubmittedAt.isoformat() if version.SubmittedAt else None,
                        "submitted_by": version.SubmittedBy,
                        "created_by": version.CreatedBy,
                        "last_modified_at": version.LastModifiedAt.isoformat() if version.LastModifiedAt else None,
                        "last_modified_by": version.LastModifiedBy,
                        "deleted_at": version.DeletedAt.isoformat() if version.DeletedAt else None,
                        "context": version.Context,
                        "content_section": version.Content,
                        "problem": version.Problem,
                        # Topic-level extras
                        "abbreviation": getattr(topic, "Abbreviation", None),
                        "is_approved": getattr(topic, "IsApproved", None)
                    }
                }
                
                # Index in ChromaDB via duplicate agent
                await self.main_agent.duplicate_agent.index_topic(index_data)
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error indexing approved version {version_id}: {e}")
