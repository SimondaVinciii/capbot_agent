"""Main Agent - Orchestrates the 3 sub-agents for topic submission support."""

import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.topic_suggestion_agent import TopicSuggestionAgent
from app.agents.duplicate_detection_agent import DuplicateDetectionAgent
from app.agents.topic_modification_agent import TopicModificationAgent
from app.schemas.schemas import (
    AgentProcessRequest, AgentProcessResponse, TopicRequest,
    DuplicationStatus, TopicResponse
)
from app.repositories.topic_repository import TopicRepository
from app.models.database import get_db
from sqlalchemy.orm import Session

class MainAgent(BaseAgent):
    """Main orchestrating agent that coordinates all sub-agents for topic submission support."""
    
    def __init__(self):
        super().__init__("MainAgent", "gemini-1.5-flash")
        
        # Initialize sub-agents
        self.suggestion_agent = TopicSuggestionAgent()
        self.duplicate_agent = DuplicateDetectionAgent()
        self.modification_agent = TopicModificationAgent()
        
        # Processing statistics
        self.processing_stats = {
            "total_requests": 0,
            "successful_submissions": 0,
            "duplicates_found": 0,
            "modifications_made": 0
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing workflow for topic submission support.
        
        Args:
            input_data: AgentProcessRequest data
            
        Returns:
            AgentProcessResponse data
        """
        start_time = time.time()
        
        try:
            self.log_info("Starting main agent processing workflow")
            self.processing_stats["total_requests"] += 1
            
            # Parse input request
            request = AgentProcessRequest(**input_data)
            
            # Initialize response data
            response_data = {
                "success": False,
                "topic_id": None,
                "duplicate_check": None,
                "suggestions": None,
                "modifications": None,
                "final_topic": None,
                "messages": [],
                "processing_time": 0.0
            }
            
            # Step 1: Get trending suggestions if requested
            if request.get_suggestions:
                suggestions_result = await self._get_trending_suggestions(request)
                if suggestions_result["success"]:
                    response_data["suggestions"] = suggestions_result["data"]
                    response_data["messages"].append("Đã tạo gợi ý đề tài dựa trên xu hướng nghiên cứu hiện tại")
                else:
                    response_data["messages"].append(f"Lỗi khi tạo gợi ý: {suggestions_result.get('error', 'Unknown error')}")
            
            # Step 2: Check for duplicates if requested
            if request.check_duplicates:
                duplicate_result = await self._check_duplicates(request.topic_request)
                if duplicate_result["success"]:
                    response_data["duplicate_check"] = duplicate_result["data"]
                    
                    # Analyze duplicate status
                    duplicate_status = duplicate_result["data"]["status"]
                    similarity_score = duplicate_result["data"]["similarity_score"]
                    
                    if duplicate_status == DuplicationStatus.DUPLICATE_FOUND.value:
                        self.processing_stats["duplicates_found"] += 1
                        response_data["messages"].append(f"Phát hiện đề tài trùng lặp với độ tương tự {similarity_score:.2%}")
                        
                        # Step 3: Auto-modify if requested and duplicates found
                        if request.auto_modify:
                            modification_result = await self._modify_topic(
                                request.topic_request, duplicate_result["data"]
                            )
                            
                            if modification_result["success"]:
                                response_data["modifications"] = modification_result["data"]
                                self.processing_stats["modifications_made"] += 1
                                
                                # Update topic request with modified version
                                modified_topic_data = modification_result["data"]["modified_topic"]
                                request.topic_request = TopicRequest(**modified_topic_data)
                                
                                response_data["messages"].append("Đã tự động chỉnh sửa đề tài để giảm trùng lặp")
                                
                                # Re-check duplicates for modified topic
                                recheck_result = await self._check_duplicates(request.topic_request)
                                if recheck_result["success"]:
                                    response_data["duplicate_check"] = recheck_result["data"]
                                    new_similarity = recheck_result["data"]["similarity_score"]
                                    response_data["messages"].append(f"Sau chỉnh sửa, độ tương tự giảm xuống {new_similarity:.2%}")
                            else:
                                response_data["messages"].append(f"Lỗi khi chỉnh sửa đề tài: {modification_result.get('error', 'Unknown error')}")
                                
                    elif duplicate_status == DuplicationStatus.POTENTIAL_DUPLICATE.value:
                        response_data["messages"].append(f"Phát hiện đề tài có khả năng trùng lặp với độ tương tự {similarity_score:.2%}")
                    else:
                        response_data["messages"].append("Đề tài có tính độc đáo tốt, không phát hiện trùng lặp")
                        
                else:
                    response_data["messages"].append(f"Lỗi khi kiểm tra trùng lặp: {duplicate_result.get('error', 'Unknown error')}")
            
            # Step 4: Create topic in database
            topic_creation_result = await self._create_topic(request.topic_request)
            if topic_creation_result["success"]:
                response_data["topic_id"] = topic_creation_result["data"]["topic_id"]
                response_data["final_topic"] = topic_creation_result["data"]["topic"]
                response_data["success"] = True
                self.processing_stats["successful_submissions"] += 1
                response_data["messages"].append("Đã tạo đề tài thành công trong cơ sở dữ liệu")
                
                # Index the new topic for future duplicate checks
                await self._index_new_topic(topic_creation_result["data"])
                response_data["messages"].append("Đã lưu trữ đề tài vào hệ thống tìm kiếm")
                
            else:
                response_data["messages"].append(f"Lỗi khi tạo đề tài: {topic_creation_result.get('error', 'Unknown error')}")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            response_data["processing_time"] = round(processing_time, 3)
            
            self.log_info(f"Main agent processing completed in {processing_time:.3f}s")
            
            return AgentResult(
                success=True,
                data=response_data,
                metadata=self.processing_stats.copy()
            ).to_dict()
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.log_error("Error in main agent processing", e)
            
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"processing_time": processing_time}
            ).to_dict()
    
    async def _get_trending_suggestions(self, request: AgentProcessRequest) -> Dict[str, Any]:
        """Get trending topic suggestions from suggestion agent."""
        try:
            self.log_info("Getting trending topic suggestions")
            
            suggestion_input = {
                "semester_id": request.topic_request.semester_id,
                "category_preference": "", 
                "keywords": [],
                "supervisor_expertise": [],
                "student_level": "undergraduate"
            }
            
            result = await self.suggestion_agent.process(suggestion_input)
            return result
            
        except Exception as e:
            self.log_error("Error getting trending suggestions", e)
            return {"success": False, "error": str(e)}
    
    async def _check_duplicates(self, topic_request: TopicRequest) -> Dict[str, Any]:
        """Check for topic duplicates using duplicate detection agent."""
        try:
            self.log_info("Checking for topic duplicates")
            
            duplicate_input = {
                "topic_title": topic_request.title,
                "topic_description": topic_request.description or "",
                "topic_objectives": topic_request.objectives or "",
                "topic_methodology": getattr(topic_request, 'methodology', '') or "",
                "semester_id": topic_request.semester_id
            }
            
            result = await self.duplicate_agent.process(duplicate_input)
            return result
            
        except Exception as e:
            self.log_error("Error checking duplicates", e)
            return {"success": False, "error": str(e)}
    
    async def _modify_topic(self, topic_request: TopicRequest, duplicate_results: Dict[str, Any]) -> Dict[str, Any]:
        """Modify topic to reduce duplicates using modification agent."""
        try:
            self.log_info("Modifying topic to reduce duplicates")
            
            modification_input = {
                "original_topic": topic_request.dict(),
                "duplicate_results": duplicate_results,
                "modification_preferences": {},
                "preserve_core_idea": True
            }
            
            result = await self.modification_agent.process(modification_input)
            return result
            
        except Exception as e:
            self.log_error("Error modifying topic", e)
            return {"success": False, "error": str(e)}
    
    async def _create_topic(self, topic_request: TopicRequest) -> Dict[str, Any]:
        """Create topic in database."""
        try:
            self.log_info("Creating topic in database")
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                # Create topic using repository
                repository = TopicRepository(db)
                
                # Check if topic with same title exists in semester
                if repository.topic_exists_by_title(topic_request.title, topic_request.semester_id):
                    return {"success": False, "error": "Đề tài với tiêu đề này đã tồn tại trong học kỳ"}
                
                # Create the topic
                topic = repository.create_topic(topic_request)
                
                # Convert to response format
                topic_response = TopicResponse(
                    id=topic.Id,
                    title=topic.Title,
                    description=topic.Description,
                    objectives=topic.Objectives,
                    supervisor_id=topic.SupervisorId,
                    category_id=topic.CategoryId,
                    semester_id=topic.SemesterId,
                    max_students=topic.MaxStudents,
                    is_approved=topic.IsApproved,
                    created_at=topic.CreatedAt
                )
                
                return {
                    "success": True,
                    "data": {
                        "topic_id": topic.Id,
                        "topic": topic_response.dict()
                    }
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.log_error("Error creating topic in database", e)
            return {"success": False, "error": str(e)}
    
    async def _index_new_topic(self, topic_data: Dict[str, Any]) -> bool:
        """Index newly created topic for future duplicate detection."""
        try:
            topic_id = topic_data["topic_id"]
            topic_info = topic_data["topic"]
            
            # Prepare topic content for indexing
            content_parts = [topic_info["title"]]
            if topic_info.get("description"):
                content_parts.append(topic_info["description"])
            if topic_info.get("objectives"):
                content_parts.append(topic_info["objectives"])
            
            full_content = " ".join(content_parts)
            
            # Index the topic
            index_data = {
                "id": str(topic_id),
                "title": topic_info["title"],
                "content": full_content,
                "metadata": {
                    "topic_id": topic_id,
                    "semester_id": topic_info["semester_id"],
                    "category_id": topic_info.get("category_id"),
                    "supervisor_id": topic_info["supervisor_id"],
                    "created_at": topic_info["created_at"]
                }
            }
            
            success = await self.duplicate_agent.index_topic(index_data)
            if success:
                self.log_info(f"Successfully indexed topic {topic_id}")
            else:
                self.log_error(f"Failed to index topic {topic_id}")
            
            return success
            
        except Exception as e:
            self.log_error("Error indexing new topic", e)
            return False
    
    async def initialize_topic_index(self) -> Dict[str, Any]:
        """Initialize ChromaDB with existing topics from database."""
        try:
            self.log_info("Initializing topic index from database")
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                repository = TopicRepository(db)
                
                # Get all topics with content
                topics_data = repository.get_topics_with_content()
                
                if not topics_data:
                    return {"success": True, "message": "No topics to index", "count": 0}
                
                # Index topics in batch
                indexed_count = await self.duplicate_agent.index_topics_batch(topics_data)
                
                self.log_info(f"Successfully indexed {indexed_count} topics")
                
                return {
                    "success": True,
                    "message": f"Successfully indexed {indexed_count} topics",
                    "count": indexed_count
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.log_error("Error initializing topic index", e)
            return {"success": False, "error": str(e)}
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get processing statistics for all agents."""
        return {
            "main_agent": self.processing_stats.copy(),
            "chroma_collection": self.duplicate_agent.get_collection_stats(),
            "agents_status": {
                "suggestion_agent": self.suggestion_agent.name,
                "duplicate_agent": self.duplicate_agent.name,
                "modification_agent": self.modification_agent.name
            }
        }
    
    async def process_suggestion_only(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only topic suggestions without creation."""
        try:
            self.log_info("Processing suggestion-only request")
            
            result = await self.suggestion_agent.process(input_data)
            return result
            
        except Exception as e:
            self.log_error("Error in suggestion-only processing", e)
            return {"success": False, "error": str(e)}
    
    async def process_duplicate_check_only(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only duplicate checking without creation."""
        try:
            self.log_info("Processing duplicate check only")
            
            result = await self.duplicate_agent.process(topic_data)
            return result
            
        except Exception as e:
            self.log_error("Error in duplicate-check-only processing", e)
            return {"success": False, "error": str(e)}
    
    async def process_modification_only(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process only topic modification without creation."""
        try:
            self.log_info("Processing modification-only request")
            
            result = await self.modification_agent.process(input_data)
            return result
            
        except Exception as e:
            self.log_error("Error in modification-only processing", e)
            return {"success": False, "error": str(e)}

