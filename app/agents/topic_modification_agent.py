"""Agent 3: Topic Modification Agent - Suggests modifications when duplicates are found."""

import json
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent, AgentResult
from app.schemas.schemas import (
    TopicModificationRequest, TopicModificationResponse, 
    TopicRequest, DuplicateCheckResult, DuplicationStatus
)

class TopicModificationAgent(BaseAgent):
    """Agent responsible for suggesting topic modifications when duplicates are detected."""
    
    def __init__(self):
        super().__init__("TopicModificationAgent", "gemini-1.5-flash")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request to modify topic based on duplicate detection results.
        
        Args:
            input_data: Contains original_topic, duplicate_results, modification_preferences
            
        Returns:
            Dict containing modified topic and explanation
        """
        try:
            import time
            started_at = time.time()
            self.log_info("Starting topic modification process")
            
            # Extract input data
            original_topic = input_data.get("original_topic", {})
            duplicate_results = input_data.get("duplicate_results", {})
            modification_preferences = input_data.get("modification_preferences", {})
            preserve_core_idea = input_data.get("preserve_core_idea", True)
            
            # Analyze duplicate results to determine modification strategy
            modification_strategy = self._determine_modification_strategy(duplicate_results)
            
            # Generate modifications using AI
            modified_topic = await self._generate_modifications(
                original_topic=original_topic,
                duplicate_results=duplicate_results,
                strategy=modification_strategy,
                preferences=modification_preferences,
                preserve_core_idea=preserve_core_idea
            )
            
            # Calculate expected similarity improvement
            similarity_improvement = self._estimate_similarity_improvement(
                original_topic, modified_topic, duplicate_results
            )
            
            # Create response (include processing_time)
            response = TopicModificationResponse(
                modified_topic=TopicRequest(**modified_topic),
                modifications_made=modified_topic.get("modifications_made", []),
                rationale=modified_topic.get("rationale", ""),
                similarity_improvement=similarity_improvement,
                processing_time=round(time.time() - started_at, 3)
            )
            
            self.log_info("Topic modification completed successfully")
            
            return AgentResult(
                success=True,
                data=response.dict(),
                metadata={
                    "strategy_used": modification_strategy,
                    "similarity_improvement": similarity_improvement
                }
            ).to_dict()
            
        except Exception as e:
            self.log_error("Error in topic modification", e)
            return AgentResult(
                success=False,
                error=str(e)
            ).to_dict()
    
    def _determine_modification_strategy(self, duplicate_results: Dict[str, Any]) -> str:
        """Determine the modification strategy based on duplicate detection results."""
        
        status = duplicate_results.get("status", "")
        similarity_score = duplicate_results.get("similarity_score", 0.0)
        similar_topics_count = len(duplicate_results.get("similar_topics", []))
        
        if status == DuplicationStatus.DUPLICATE_FOUND.value:
            if similarity_score >= 0.95:
                return "major_redesign"  # Completely redesign the topic
            elif similarity_score >= 0.85:
                return "significant_changes"  # Make significant changes
            else:
                return "moderate_changes"  # Make moderate changes
        
        elif status == DuplicationStatus.POTENTIAL_DUPLICATE.value:
            if similar_topics_count > 3:
                return "differentiation_focus"  # Focus on differentiation
            else:
                return "minor_adjustments"  # Make minor adjustments
        
        else:
            return "enhancement_only"  # Only enhance existing content
    
    async def _generate_modifications(
        self,
        original_topic: Dict[str, Any],
        duplicate_results: Dict[str, Any],
        strategy: str,
        preferences: Dict[str, Any],
        preserve_core_idea: bool
    ) -> Dict[str, Any]:
        """Generate topic modifications using AI based on the strategy."""
        
        # Create detailed prompt for AI
        prompt = self._create_modification_prompt(
            original_topic, duplicate_results, strategy, preferences, preserve_core_idea
        )
        
        # Generate modifications using AI
        response_text = await self.generate_text(
            prompt,
            temperature=0.8,
            max_tokens=2500
        )
        
        # Parse AI response
        modified_topic = await self._parse_modification_response(response_text, original_topic)
        
        return modified_topic
    
    def _create_modification_prompt(
        self,
        original_topic: Dict[str, Any],
        duplicate_results: Dict[str, Any],
        strategy: str,
        preferences: Dict[str, Any],
        preserve_core_idea: bool
    ) -> str:
        """Create detailed prompt for AI to generate topic modifications."""
        
        # Get similar topics information
        similar_topics = duplicate_results.get("similar_topics", [])
        similarity_score = duplicate_results.get("similarity_score", 0.0)
        
        similar_topics_text = "\n".join([
            f"- {topic.get('title', 'N/A')} (Similarity: {topic.get('similarity_score', 0):.2%})"
            for topic in similar_topics[:3]
        ])
        
        # Strategy descriptions
        strategy_descriptions = {
            "major_redesign": "Cần thiết kế lại hoàn toàn đề tài với hướng tiếp cận khác biệt",
            "significant_changes": "Cần thay đổi đáng kể về mục tiêu, phương pháp hoặc phạm vi",
            "moderate_changes": "Cần điều chỉnh một số phần để tăng tính khác biệt",
            "differentiation_focus": "Tập trung vào việc tạo sự khác biệt rõ ràng",
            "minor_adjustments": "Chỉ cần điều chỉnh nhỏ để tăng tính độc đáo",
            "enhancement_only": "Chỉ cần cải thiện và làm rõ nội dung"
        }
        
        preserve_instruction = (
            "BẮT BUỘC giữ nguyên ý tưởng cốt lõi của đề tài gốc." if preserve_core_idea 
            else "Có thể thay đổi ý tưởng cốt lõi nếu cần thiết."
        )
        
        prompt = f"""
Bạn là chuyên gia tư vấn đề tài nghiên cứu. Nhiệm vụ: chỉnh sửa đề tài để giảm độ trùng lặp.

## ĐỀ TÀI GỐC:
Tiêu đề: {original_topic.get('title', '')}
Mô tả: {original_topic.get('description', '')}
Mục tiêu: {original_topic.get('objectives', '')}
Phương pháp: {original_topic.get('methodology', '')}
Kết quả mong đợi: {original_topic.get('expected_outcomes', '')}

## PHÂN TÍCH TRÙNG LẶP:
Độ tương tự cao nhất: {similarity_score:.2%}
Các đề tài tương tự:
{similar_topics_text}

## CHIẾN LƯỢC CHỈNH SỬA:
{strategy_descriptions.get(strategy, strategy)}

## YÊU CẦU:
1. {preserve_instruction}
2. Đảm bảo tính khả thi và phù hợp với cấp độ sinh viên
3. Tạo sự khác biệt rõ ràng với các đề tài tương tự
4. Giữ nguyên các thông tin cơ bản (supervisor_id, semester_id, category_id, max_students)

## HƯỚNG DẪN CHỈNH SỬA:
- Thay đổi góc độ tiếp cận hoặc phạm vi nghiên cứu
- Điều chỉnh mục tiêu cụ thể hoặc phương pháp thực hiện
- Thêm yếu tố độc đáo hoặc ứng dụng mới
- Thay đổi đối tượng nghiên cứu hoặc lĩnh vực ứng dụng

Trả về kết quả trong format JSON:
{{
  "title": "Tiêu đề đã chỉnh sửa",
  "description": "Mô tả đã chỉnh sửa", 
  "objectives": "Mục tiêu đã chỉnh sửa",
  "methodology": "Phương pháp đã chỉnh sửa",
  "expected_outcomes": "Kết quả mong đợi đã chỉnh sửa",
  "requirements": "Yêu cầu đã chỉnh sửa",
  "supervisor_id": {original_topic.get('supervisor_id')},
  "semester_id": {original_topic.get('semester_id')},
  "category_id": {original_topic.get('category_id')},
  "max_students": {original_topic.get('max_students', 1)},
  "modifications_made": [
    "Danh sách các thay đổi đã thực hiện"
  ],
  "rationale": "Giải thích chi tiết về lý do và cách thức chỉnh sửa"
}}

Đảm bảo JSON hợp lệ và đầy đủ thông tin.
"""
        return prompt
    
    async def _parse_modification_response(self, response_text: str, original_topic: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response to extract modified topic."""
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Find JSON content
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[json_start:json_end]
            modified_data = json.loads(json_text)
            
            # Ensure all required fields are present
            required_fields = ['title', 'description', 'objectives', 'supervisor_id', 'semester_id']
            for field in required_fields:
                if field not in modified_data:
                    if field in original_topic:
                        modified_data[field] = original_topic[field]
                    else:
                        modified_data[field] = ""
            
            # Ensure modifications_made and rationale are present
            if 'modifications_made' not in modified_data:
                modified_data['modifications_made'] = ["Đã thực hiện các điều chỉnh để giảm trùng lặp"]
            
            if 'rationale' not in modified_data:
                modified_data['rationale'] = "Đề tài đã được chỉnh sửa để tăng tính độc đáo và giảm trùng lặp."
            
            return modified_data
            
        except Exception as e:
            self.log_error("Error parsing modification response", e)
            return self._create_fallback_modification(original_topic)
    
    def _create_fallback_modification(self, original_topic: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback modification when AI parsing fails."""
        
        # Simple modifications based on common patterns
        original_title = original_topic.get('title', '')
        
        # Add differentiating terms
        if "hệ thống" not in original_title.lower():
            modified_title = f"Hệ thống {original_title}"
        elif "ứng dụng" not in original_title.lower():
            modified_title = f"Ứng dụng {original_title}"
        else:
            modified_title = f"{original_title} - Phiên bản cải tiến"
        
        # Add unique methodology elements
        original_methodology = original_topic.get('methodology', '')
        modified_methodology = f"{original_methodology} Đề tài sẽ tập trung vào phương pháp tiếp cận độc đáo và tính ứng dụng thực tế cao."
        
        # Add specific objectives
        original_objectives = original_topic.get('objectives', '')
        modified_objectives = f"{original_objectives} Đặc biệt chú trọng vào tính khác biệt và giá trị ứng dụng trong bối cảnh hiện tại."
        
        return {
            "title": modified_title,
            "description": original_topic.get('description', ''),
            "objectives": modified_objectives,
            "methodology": modified_methodology,
            "expected_outcomes": original_topic.get('expected_outcomes', ''),
            "requirements": original_topic.get('requirements', ''),
            "supervisor_id": original_topic.get('supervisor_id'),
            "semester_id": original_topic.get('semester_id'),
            "category_id": original_topic.get('category_id'),
            "max_students": original_topic.get('max_students', 1),
            "modifications_made": [
                "Điều chỉnh tiêu đề để tăng tính khác biệt",
                "Bổ sung phương pháp tiếp cận độc đáo",
                "Làm rõ mục tiêu và tính ứng dụng"
            ],
            "rationale": "Đề tài đã được điều chỉnh để giảm độ tương tự với các đề tài hiện có trong cơ sở dữ liệu."
        }
    
    def _estimate_similarity_improvement(
        self,
        original_topic: Dict[str, Any],
        modified_topic: Dict[str, Any],
        duplicate_results: Dict[str, Any]
    ) -> float:
        """Estimate the improvement in similarity score after modifications."""
        
        original_similarity = duplicate_results.get("similarity_score", 0.0)
        modifications_count = len(modified_topic.get("modifications_made", []))
        
        # Estimate improvement based on number and type of modifications
        base_improvement = 0.1  # Base improvement
        modification_improvement = modifications_count * 0.05  # Each modification adds 5%
        
        # Additional improvement based on original similarity
        if original_similarity >= 0.9:
            additional_improvement = 0.3  # High similarity needs more improvement
        elif original_similarity >= 0.8:
            additional_improvement = 0.2
        elif original_similarity >= 0.7:
            additional_improvement = 0.15
        else:
            additional_improvement = 0.1
        
        total_improvement = min(
            base_improvement + modification_improvement + additional_improvement,
            original_similarity * 0.6  # Maximum 60% improvement
        )
        
        return round(total_improvement, 3)
    
    async def suggest_alternative_approaches(self, topic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest alternative approaches for a topic to avoid duplicates."""
        try:
            prompt = f"""
Đề xuất 3 cách tiếp cận khác nhau cho đề tài sau để tránh trùng lặp:

Đề tài gốc:
Tiêu đề: {topic_data.get('title', '')}
Mô tả: {topic_data.get('description', '')}

Hãy đề xuất 3 hướng tiếp cận khác nhau:
1. Thay đổi góc độ nghiên cứu
2. Thay đổi phạm vi ứng dụng  
3. Thay đổi phương pháp thực hiện

Trả về JSON format:
{{
  "alternatives": [
    {{
      "approach": "Tên cách tiếp cận",
      "title": "Tiêu đề mới",
      "description": "Mô tả ngắn gọn",
      "key_differences": ["Điểm khác biệt chính"]
    }}
  ]
}}
"""
            
            response = await self.generate_text(prompt, temperature=0.8, max_tokens=1500)
            
            # Parse response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > 0:
                json_text = response[json_start:json_end]
                data = json.loads(json_text)
                return data.get("alternatives", [])
            
            return []
            
        except Exception as e:
            self.log_error("Error suggesting alternative approaches", e)
            return []

