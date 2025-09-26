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
        super().__init__("TopicModificationAgent", "gemini-2.0-flash")
    
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
            # Normalize and backfill required fields for TopicRequest
            modified_topic = self._normalize_modified_topic(modified_topic, original_topic)
            
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
            f"- {topic.get('eN_Title') or topic.get('vN_title') or topic.get('title', 'N/A')} (Similarity: {topic.get('similarity_score', 0):.2%})"
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
        
        # Prefer new schema title if provided
        orig_title = original_topic.get('title') or original_topic.get('eN_Title') or original_topic.get('vN_title') or ''
        prompt = f"""
Bạn là chuyên gia tư vấn đề tài nghiên cứu. Nhiệm vụ: chỉnh sửa đề tài để giảm độ trùng lặp.

## ĐỀ TÀI GỐC:
Tiêu đề: {orig_title}
Mô tả: {original_topic.get('description', '')}
Mục tiêu: {original_topic.get('objectives', '')}
Vấn đề (problem): {original_topic.get('problem', '')}
Bối cảnh (context): {original_topic.get('context', '')}
Nội dung (content): {original_topic.get('content', '')}

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
        - Điều chỉnh title để rõ ràng và khác biệt
        - Làm rõ problem, context và content theo hướng khác biệt
        - Tinh chỉnh objectives và description để nhấn mạnh điểm mới
        - Không thêm các trường cũ: methodology, expected_outcomes, requirements
        - Không thay đổi supervisor_id, semester_id, category_id, max_students

Trả về kết quả trong format JSON. BẮT BUỘC chỉ sử dụng các trường sau, KHÔNG được thêm trường khác:
{{
  "title": "Tiêu đề EN đã chỉnh sửa",
  "description": "Mô tả đã chỉnh sửa", 
  "objectives": "Mục tiêu đã chỉnh sửa",
  "problem": "Vấn đề cần giải quyết (BẮT BUỘC có nội dung)",
  "context": "Bối cảnh nghiên cứu (BẮT BUỘC có nội dung)",
  "content": "Nội dung chính của nghiên cứu (BẮT BUỘC có nội dung)",
  "supervisor_id": {original_topic.get('supervisor_id') or original_topic.get('supervisorId') or 1},
  "semester_id": {original_topic.get('semester_id') or original_topic.get('semesterId') or 1},
  "category_id": {original_topic.get('category_id') or original_topic.get('categoryId') or 0},
  "max_students": {original_topic.get('max_students', 1)},
  "modifications_made": [
    "Danh sách các thay đổi đã thực hiện"
  ],
  "rationale": "Giải thích chi tiết về lý do và cách thức chỉnh sửa"
}}

QUAN TRỌNG: 
- KHÔNG được thêm methodology, expected_outcomes, requirements
- BẮT BUỘC phải có problem, context, content với nội dung cụ thể
- Các *id phải là số nguyên
- Trả lời hoàn toàn bằng tiếng Việt
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
            
            # Ensure all required fields are present (and ints for ids)
            required_fields = ['title', 'description', 'objectives', 'supervisor_id', 'semester_id']
            for field in required_fields:
                if field not in modified_data:
                    if field in original_topic:
                        modified_data[field] = original_topic[field]
                    else:
                        modified_data[field] = ""

            # Backfill category_id and max_students if missing
            if 'category_id' not in modified_data:
                modified_data['category_id'] = original_topic.get('category_id') or original_topic.get('categoryId') or 0
            if 'max_students' not in modified_data:
                modified_data['max_students'] = original_topic.get('max_students', 1)

            # Coerce numeric fields to int if possible
            for k in ['supervisor_id', 'semester_id', 'category_id', 'max_students']:
                try:
                    if modified_data.get(k) is not None and modified_data.get(k) != "":
                        modified_data[k] = int(modified_data[k])
                except Exception:
                    # Fallback to original values or safe defaults
                    if k in original_topic and original_topic.get(k) is not None:
                        try:
                            modified_data[k] = int(original_topic.get(k))
                        except Exception:
                            pass
            
            # Aggressively remove ALL deprecated fields - be very thorough
            deprecated_fields = [
                "methodology", "expected_outcomes", "requirements", 
                "expectedOutcomes", "methodology", "requirements",
                "methodology", "expected_outcomes", "requirements"
            ]
            for drop_key in deprecated_fields:
                if drop_key in modified_data:
                    modified_data.pop(drop_key, None)
            
            # Also remove any fields that contain these keywords
            keys_to_remove = []
            for key in modified_data.keys():
                if any(dep in key.lower() for dep in ["methodology", "expected", "requirements"]):
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                modified_data.pop(key, None)

            # Ensure new vector fields exist with proper content - these are REQUIRED
            for new_key in ["problem", "context", "content"]:
                if new_key not in modified_data or not modified_data.get(new_key):
                    # Generate meaningful content for new fields if missing
                    if new_key == "problem":
                        modified_data[new_key] = f"Vấn đề cần giải quyết trong nghiên cứu {modified_data.get('title', 'này')}: {modified_data.get('description', '')[:100]}..."
                    elif new_key == "context":
                        modified_data[new_key] = f"Bối cảnh nghiên cứu liên quan đến {modified_data.get('title', 'đề tài này')}: {modified_data.get('description', '')[:100]}..."
                    elif new_key == "content":
                        modified_data[new_key] = f"Nội dung chính của nghiên cứu {modified_data.get('title', 'này')}: {modified_data.get('description', '')[:100]}..."
                    else:
                        modified_data[new_key] = original_topic.get(new_key, "")

            # Final cleanup - remove any remaining deprecated fields
            final_cleanup_fields = ["methodology", "expected_outcomes", "requirements", "expectedOutcomes"]
            for field in final_cleanup_fields:
                if field in modified_data:
                    modified_data.pop(field, None)
            
            # Ensure modifications_made and rationale are present
            if 'modifications_made' not in modified_data:
                modified_data['modifications_made'] = ["Đã thực hiện các điều chỉnh để giảm trùng lặp"]
            
            if 'rationale' not in modified_data:
                modified_data['rationale'] = "Đề tài đã được chỉnh sửa để tăng tính độc đáo và giảm trùng lặp."
            
            return modified_data
            
        except Exception as e:
            self.log_error("Error parsing modification response", e)
            return self._create_fallback_modification(original_topic)

    def _normalize_modified_topic(self, modified_topic: Dict[str, Any], original_topic: Dict[str, Any]) -> Dict[str, Any]:
        """Backfill and coerce fields to satisfy TopicRequest schema.
        - Ensure required strings present
        - Ensure numeric ids are ints
        - Prefer existing values; fallback to original or sensible defaults
        """
        normalized = dict(modified_topic or {})

        # Required textual fields
        for key in ["title", "description", "objectives"]:
            if not normalized.get(key):
                # prefer original fields, including new schema keys for title
                if key == "title":
                    normalized[key] = (
                        original_topic.get("title")
                        or original_topic.get("eN_Title")
                        or original_topic.get("vN_title")
                        or ""
                    )
                else:
                    normalized[key] = original_topic.get(key, "")

        # Ensure new vector fields are present and meaningful
        for key in ["problem", "context", "content"]:
            if not normalized.get(key):
                # Generate meaningful content based on title and description
                title = normalized.get("title", "")
                description = normalized.get("description", "")
                if key == "problem":
                    normalized[key] = f"Vấn đề cần giải quyết trong nghiên cứu {title}: {description[:100]}..."
                elif key == "context":
                    normalized[key] = f"Bối cảnh nghiên cứu liên quan đến {title}: {description[:100]}..."
                elif key == "content":
                    normalized[key] = f"Nội dung chính của nghiên cứu {title}: {description[:100]}..."
                else:
                    normalized[key] = original_topic.get(key, "")

        # Numeric fields with coercion
        def pick_int(*candidates, default=None):
            for val in candidates:
                if val is None or val == "":
                    continue
                try:
                    return int(val)
                except Exception:
                    continue
            return default

        normalized["supervisor_id"] = pick_int(
            normalized.get("supervisor_id"),
            original_topic.get("supervisor_id"),
            original_topic.get("supervisorId"),
            default=1
        )
        normalized["semester_id"] = pick_int(
            normalized.get("semester_id"),
            original_topic.get("semester_id"),
            original_topic.get("semesterId"),
            default=1
        )
        normalized["category_id"] = pick_int(
            normalized.get("category_id"),
            original_topic.get("category_id"),
            original_topic.get("categoryId"),
            default=0
        )
        normalized["max_students"] = pick_int(
            normalized.get("max_students"),
            original_topic.get("max_students"),
            default=1
        )

        # Final cleanup - remove any deprecated fields that might have slipped through
        deprecated_fields = ["methodology", "expected_outcomes", "requirements", "expectedOutcomes"]
        for field in deprecated_fields:
            if field in normalized:
                normalized.pop(field, None)

        # Ensure arrays/strings present
        if not normalized.get("modifications_made"):
            normalized["modifications_made"] = modified_topic.get("modifications_made", [
                "Điều chỉnh tiêu đề để tăng tính khác biệt",
                "Bổ sung phương pháp tiếp cận độc đáo"
            ])
        if not normalized.get("rationale"):
            normalized["rationale"] = modified_topic.get(
                "rationale",
                "Đề tài đã được chỉnh sửa để tăng tính độc đáo và giảm trùng lặp."
            )

        return normalized
    
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
        
        # Add specific objectives
        original_objectives = original_topic.get('objectives', '')
        modified_objectives = f"{original_objectives} Đặc biệt chú trọng vào tính khác biệt và giá trị ứng dụng trong bối cảnh hiện tại."
        
        return {
            "title": modified_title,
            "description": original_topic.get('description', ''),
            "objectives": modified_objectives,
            "problem": original_topic.get('problem', '') or f"Vấn đề cần giải quyết trong nghiên cứu {modified_title}",
            "context": original_topic.get('context', '') or f"Bối cảnh nghiên cứu liên quan đến {modified_title}",
            "content": original_topic.get('content', '') or f"Nội dung chính của nghiên cứu {modified_title}",
            "supervisor_id": original_topic.get('supervisor_id') or original_topic.get('supervisorId') or 1,
            "semester_id": original_topic.get('semester_id') or original_topic.get('semesterId') or 1,
            "category_id": original_topic.get('category_id') or original_topic.get('categoryId') or 0,
            "max_students": original_topic.get('max_students', 1),
            "modifications_made": [
                "Điều chỉnh tiêu đề để tăng tính khác biệt",
                "Làm rõ problem, context, content theo hướng khác biệt",
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

