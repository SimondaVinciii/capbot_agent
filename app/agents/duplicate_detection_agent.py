"""Agent 2: Duplicate Detection Agent - Checks for topic duplicates using ChromaDB and cosine similarity."""

from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent, AgentResult
from app.services.chroma_service import ChromaService
from app.schemas.schemas import DuplicateCheckResult, DuplicationStatus, SimilaritySearchResult
from config import config

class DuplicateDetectionAgent(BaseAgent):
    """Agent responsible for detecting duplicate topics using ChromaDB and cosine similarity."""
    
    def __init__(self):
        super().__init__("DuplicateDetectionAgent", "gemini-1.5-flash")
        self.chroma_service = ChromaService()
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request to check for topic duplicates.
        
        Args:
            input_data: Contains topic_title, topic_description, topic_content, etc.
            
        Returns:
            Dict containing duplicate check results
        """
        try:
            import time
            started_at = time.time()
            self.log_info("Starting duplicate detection process")
            
            # Extract input data
            topic_title = input_data.get("topic_title", "")
            topic_description = input_data.get("topic_description", "")
            topic_objectives = input_data.get("topic_objectives", "")
            topic_methodology = input_data.get("topic_methodology", "")
            semester_id = input_data.get("semester_id")
            exclude_topic_id = input_data.get("exclude_topic_id")  # For updates
            threshold = input_data.get("threshold", self.similarity_threshold)
            
            # Combine all topic content for similarity check
            full_content = self._combine_topic_content(
                title=topic_title,
                description=topic_description,
                objectives=topic_objectives,
                methodology=topic_methodology
            )
            
            # Search for similar topics in ChromaDB
            similar_topics = self.chroma_service.search_similar_topics(
                query_content=full_content,
                n_results=10,
                similarity_threshold=0.3,  # Lower threshold to get more candidates
                where=input_data.get("where")
            )
            
            # Filter out excluded topic if provided
            if exclude_topic_id:
                similar_topics = [
                    topic for topic in similar_topics 
                    if topic["id"] != str(exclude_topic_id)
                ]
            else:
                # Also try to avoid self-match when the query content matches an existing doc exactly.
                # If any result has similarity_score >= 0.999 and same title as input, drop it.
                similar_topics = [
                    t for t in similar_topics
                    if not (
                        t.get("title", "").strip() == topic_title.strip() and t.get("similarity_score", 0.0) >= 0.999
                    )
                ]
            
            # Filter by semester if provided, but fallback to no filter if empty
            if semester_id:
                pre_filter = list(similar_topics)
                similar_topics = [
                    topic for topic in similar_topics
                    if topic.get("metadata", {}).get("semester_id") == semester_id
                ]
                if not similar_topics:
                    # Fallback: no semester filter (to avoid false negatives when old docs lack semester_id)
                    similar_topics = pre_filter
            
            # Analyze similarity results
            duplicate_result = await self._analyze_similarity_results(
                similar_topics=similar_topics,
                threshold=threshold,
                original_content=full_content
            )
            # Ensure required processing_time is present
            if "processing_time" not in duplicate_result:
                duplicate_result["processing_time"] = round(time.time() - started_at, 3)
            
            self.log_info(f"Duplicate check completed - Status: {duplicate_result.get('status')}")
            
            return AgentResult(
                success=True,
                data=duplicate_result,
                metadata={
                    "candidates_found": len(similar_topics),
                    "threshold_used": threshold
                }
            ).to_dict()
            
        except Exception as e:
            self.log_error("Error in duplicate detection", e)
            return AgentResult(
                success=False,
                error=str(e)
            ).to_dict()
    
    def _combine_topic_content(
        self, 
        title: str, 
        description: str = "", 
        objectives: str = "", 
        methodology: str = ""
    ) -> str:
        """Combine all topic content into a single string for similarity comparison."""
        content_parts = []
        
        if title:
            content_parts.append(f"Title: {title}")
        if description:
            content_parts.append(f"Description: {description}")
        if objectives:
            content_parts.append(f"Objectives: {objectives}")
        if methodology:
            content_parts.append(f"Methodology: {methodology}")
        
        return " ".join(content_parts)
    
    async def _analyze_similarity_results(
        self,
        similar_topics: List[Dict[str, Any]],
        threshold: float,
        original_content: str
    ) -> Dict[str, Any]:
        """Analyze similarity results and determine duplication status.
        Returns a plain dict; the caller will enrich with processing_time and wrap as needed.
        """
        
        if not similar_topics:
            return {
                "status": DuplicationStatus.NO_DUPLICATE,
                "similarity_score": 0.0,
                "similar_topics": [],
                "threshold": threshold,
                "message": "Không tìm thấy đề tài tương tự trong cơ sở dữ liệu.",
                "recommendations": []
            }
        
        # Find highest similarity score
        max_similarity = max(topic["similarity_score"] for topic in similar_topics)
        
        # Filter topics above threshold
        duplicate_candidates = [t for t in similar_topics if t["similarity_score"] >= threshold]
        # If none above threshold but there are near-duplicates (>= 0.9), consider potential duplicates
        if not duplicate_candidates:
            near_dups = [t for t in similar_topics if t["similarity_score"] >= 0.9]
            if near_dups:
                duplicate_candidates = near_dups
        
        # Determine status based on similarity scores
        if max_similarity >= threshold:
            if max_similarity >= 0.8:  # Very high similarity
                status = DuplicationStatus.DUPLICATE_FOUND
                message = f"Phát hiện đề tài trùng lặp với độ tương tự {max_similarity:.2%}. Đề tài cần được chỉnh sửa đáng kể."
            else:
                status = DuplicationStatus.POTENTIAL_DUPLICATE
                message = f"Phát hiện đề tài có khả năng trùng lặp với độ tương tự {max_similarity:.2%}. Khuyến nghị chỉnh sửa để tăng tính độc đáo."
        else:
            # Check for potential duplicates with lower threshold
            potential_duplicates = [
                topic for topic in similar_topics
                if topic["similarity_score"] >= 0.6
            ]
            
            if potential_duplicates:
                status = DuplicationStatus.POTENTIAL_DUPLICATE
                message = f"Tìm thấy đề tài tương tự với độ tương tự {max_similarity:.2%}. Có thể cân nhắc điều chỉnh để tăng tính khác biệt."
            else:
                status = DuplicationStatus.NO_DUPLICATE
                message = f"Đề tài có tính độc đáo tốt. Độ tương tự cao nhất: {max_similarity:.2%}."
        
        # Enhanced analysis using AI for contextual understanding
        recommendations = []
        if duplicate_candidates:
            enhanced_analysis = await self._perform_enhanced_analysis(
                original_content, duplicate_candidates
            )
            if enhanced_analysis:
                message += f" {enhanced_analysis}"
                # Extract recommendations from analysis
                recommendations = await self._extract_recommendations_from_analysis(
                    enhanced_analysis, duplicate_candidates
                )
        
        # Format similar topics for response
        formatted_similar_topics = []
        for topic in similar_topics[:5]:  # Top 5 most similar
            metadata = topic.get("metadata", {})  # Thêm dòng này
            formatted_topic = {
                "topic_id": int(topic["id"]),
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "objectives": metadata.get("objectives", ""),
                "methodology": metadata.get("methodology", ""),
                "similarity_score": topic["similarity_score"],
                "semester_id": metadata.get("semester_id"),
                "category_id": metadata.get("category_id"),
                "supervisor_id": metadata.get("supervisor_id"),
                "created_at": metadata.get("created_at")
            }
            formatted_similar_topics.append(formatted_topic)
        
        return {
            "status": status,
            "similarity_score": max_similarity,
            "similar_topics": formatted_similar_topics,
            "threshold": threshold,
            "message": message,
            "recommendations": recommendations
        }
    
    async def _perform_enhanced_analysis(
        self,
        original_content: str,
        duplicate_candidates: List[Dict[str, Any]]
    ) -> str:
        """Perform enhanced analysis using AI to understand contextual similarities."""
        try:
            # Create prompt for AI analysis
            candidates_text = "\n".join([
                f"- Đề tài {i+1}: {topic.get('metadata', {}).get('title', 'N/A')} (Similarity: {topic['similarity_score']:.2%})"
                for i, topic in enumerate(duplicate_candidates[:3])
            ])
            
            prompt = f"""
Phân tích độ tương tự giữa đề tài gốc và các đề tài tương tự đã tìm thấy:

## Đề tài gốc:
{original_content}

## Các đề tài tương tự:
{candidates_text}

Hãy đưa ra nhận xét ngắn gọn (1-2 câu) về:
1. Điểm tương đồng chính
2. Mức độ trùng lặp thực tế
3. Khuyến nghị cụ thể để giảm trùng lặp

Trả lời bằng tiếng Việt, ngắn gọn và cụ thể.
"""
            
            analysis = await self.generate_text(
                prompt,
                temperature=0.3,
                max_tokens=200
            )
            
            return analysis.strip()
            
        except Exception as e:
            self.log_error("Error in enhanced analysis", e)
            return ""
    
    async def _extract_recommendations_from_analysis(
        self, 
        enhanced_analysis: str, 
        duplicate_candidates: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract actionable recommendations from enhanced analysis."""
        try:
            prompt = f"""
Dựa trên phân tích sau về độ tương tự của đề tài:

{enhanced_analysis}

Hãy đưa ra danh sách 3-5 khuyến nghị cụ thể để giảm trùng lặp:
- Mỗi khuyến nghị không quá 20 từ
- Tập trung vào các thay đổi thực tế có thể áp dụng
- Sắp xếp theo mức độ ưu tiên

Trả về format:
1. [khuyến nghị 1]
2. [khuyến nghị 2]
3. [khuyến nghị 3]
"""

            recommendations_text = await self.generate_text(
                prompt,
                temperature=0.3,
                max_tokens=150
            )
            
            # Parse recommendations from numbered list
            recommendations = []
            for line in recommendations_text.strip().split('\n'):
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '-'))):
                    # Remove numbering and clean up
                    rec = line.split('.', 1)[-1].strip()
                    if rec:
                        recommendations.append(rec)
            
            return recommendations[:5]  # Max 5 recommendations
            
        except Exception as e:
            self.log_error("Error extracting recommendations", e)
            # Fallback recommendations based on similarity level
            if duplicate_candidates:
                max_sim = max(topic["similarity_score"] for topic in duplicate_candidates)
                if max_sim >= 0.9:
                    return [
                        "Thay đổi phương pháp luận cụ thể",
                        "Bổ sung công nghệ mới hoặc framework khác",
                        "Điều chỉnh đối tượng mục tiêu hoặc phạm vi ứng dụng"
                    ]
                else:
                    return [
                        "Làm rõ tính độc đáo của đề tài",
                        "Bổ sung chi tiết về cách tiếp cận",
                        "Nhấn mạnh điểm khác biệt chính"
                    ]
            return []
    
    async def index_topic(self, topic_data: Dict[str, Any]) -> bool:
        """Index a topic in ChromaDB for future similarity searches.
        
        Args:
            topic_data: Topic data including id, title, content, metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            topic_id = str(topic_data["id"])
            title = topic_data.get("title", "")
            content = topic_data.get("content", "")
            metadata = topic_data.get("metadata", {})
            
            # Add topic to ChromaDB
            success = self.chroma_service.add_topic(
                topic_id=topic_id,
                title=title,
                content=content,
                metadata=metadata
            )
            
            if success:
                self.log_info(f"Successfully indexed topic {topic_id}")
            else:
                self.log_error(f"Failed to index topic {topic_id}")
            
            return success
            
        except Exception as e:
            self.log_error(f"Error indexing topic: {e}")
            return False
    
    async def index_topics_batch(self, topics: List[Dict[str, Any]]) -> int:
        """Index multiple topics in ChromaDB batch operation.
        
        Args:
            topics: List of topic data dictionaries
            
        Returns:
            Number of successfully indexed topics
        """
        try:
            count = self.chroma_service.add_topics_batch(topics)
            self.log_info(f"Successfully indexed {count} topics in batch")
            return count
            
        except Exception as e:
            self.log_error(f"Error in batch indexing: {e}")
            return 0
    
    async def update_topic_index(self, topic_id: str, topic_data: Dict[str, Any]) -> bool:
        """Update an existing topic in the ChromaDB index.
        
        Args:
            topic_id: Topic ID to update
            topic_data: Updated topic data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            title = topic_data.get("title")
            content = topic_data.get("content")
            metadata = topic_data.get("metadata")
            
            success = self.chroma_service.update_topic(
                topic_id=topic_id,
                title=title,
                content=content,
                metadata=metadata
            )
            
            if success:
                self.log_info(f"Successfully updated topic index {topic_id}")
            else:
                self.log_error(f"Failed to update topic index {topic_id}")
            
            return success
            
        except Exception as e:
            self.log_error(f"Error updating topic index: {e}")
            return False
    
    async def remove_topic_index(self, topic_id: str) -> bool:
        """Remove a topic from the ChromaDB index.
        
        Args:
            topic_id: Topic ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.chroma_service.delete_topic(topic_id)
            
            if success:
                self.log_info(f"Successfully removed topic index {topic_id}")
            else:
                self.log_error(f"Failed to remove topic index {topic_id}")
            
            return success
            
        except Exception as e:
            self.log_error(f"Error removing topic index: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB collection."""
        return self.chroma_service.get_collection_stats()

