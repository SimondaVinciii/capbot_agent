"""Agent 1: Topic Suggestion Agent - Generates topic ideas based on semester trends."""

import json
from typing import Dict, Any, List
from datetime import datetime
from app.agents.base_agent import BaseAgent, AgentResult
from app.schemas.schemas import TopicSuggestion, TopicSuggestionsResponse, TrendingTopicData
from app.models.database import SessionLocal, Semester
import re

class TopicSuggestionAgent(BaseAgent):
    """Agent responsible for suggesting topic ideas based on trending research areas."""
    
    def __init__(self):
        super().__init__("TopicSuggestionAgent", "gemini-1.5-flash")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request to generate topic suggestions.
        
        Args:
            input_data: Contains semester_id, category_preference, keywords, etc.
            
        Returns:
            Dict containing topic suggestions and trending areas
        """
        try:
            import time
            started_at = time.time()
            self.log_info("Starting topic suggestion generation")
            
            # Extract input parameters
            semester_id = input_data.get("semester_id")
            category_preference = input_data.get("category_preference", "")
            keywords = input_data.get("keywords", [])
            supervisor_expertise = input_data.get("supervisor_expertise", [])
            student_level = input_data.get("student_level", "undergraduate")
            team_size = input_data.get("team_size", 4)
            if team_size not in (4, 5):
                team_size = 4
            
            # Get semester trend description from DB (only current or next semester allowed)
            trending_data = await self._fetch_semester_trends(semester_id)
            
            # Generate suggestions using AI
            suggestions = await self._generate_suggestions(
                trending_data=trending_data,
                category_preference=category_preference,
                keywords=[],  # no external keywords; rely on semester trend
                supervisor_expertise=supervisor_expertise,
                # enforce final-term IT student context
                student_level="Sinh viên ngành Công nghệ Thông tin kỳ cuối",
                team_size=team_size
            )
            
            # Format response with required processing_time
            processing_time = round(time.time() - started_at, 3)
            response = TopicSuggestionsResponse(
                suggestions=suggestions,
                trending_areas=[data.area for data in trending_data],
                generated_at=datetime.now(),
                processing_time=processing_time
            )
            
            self.log_info(f"Generated {len(suggestions)} topic suggestions")
            
            return AgentResult(
                success=True,
                data=response.dict(),
                metadata={"trending_areas_count": len(trending_data)}
            ).to_dict()
            
        except Exception as e:
            self.log_error("Error generating topic suggestions", e)
            return AgentResult(
                success=False,
                error=str(e)
            ).to_dict()
    
    async def _fetch_semester_trends(self, requested_semester_id: int) -> List[TrendingTopicData]:
        """Fetch semester trend description from database and return as trending data.
        Only allows current semester or the immediate next semester.
        """
        try:
            from datetime import datetime as dt
            db = SessionLocal()
            now = dt.utcnow()

            # Determine current and next semester
            current = db.query(Semester).filter(
                Semester.IsActive == True,
                Semester.StartDate <= now,
                Semester.EndDate >= now
            ).first()

            next_semester = db.query(Semester).filter(
                Semester.IsActive == True,
                Semester.StartDate > now
            ).order_by(Semester.StartDate.asc()).first()

            allowed_ids = set()
            if current:
                allowed_ids.add(current.Id)
            if next_semester:
                allowed_ids.add(next_semester.Id)

            # Resolve selected semester
            if requested_semester_id is None:
                selected = current or next_semester
            else:
                if requested_semester_id not in allowed_ids:
                    allowed_readable = ", ".join([
                        str(sid) for sid in allowed_ids
                    ]) or "(không có học kỳ hợp lệ)"
                    raise ValueError(
                        f"Chỉ được chọn học kỳ hiện tại hoặc học kỳ sau. Cho phép: {allowed_readable}"
                    )
                selected = current if (current and requested_semester_id == current.Id) else next_semester

            if not selected:
                raise ValueError("Không tìm thấy học kỳ hiện tại hoặc học kỳ sau trong cơ sở dữ liệu")

            description_text = (selected.Description or "").strip()
            area_name = selected.Name or f"Học kỳ {selected.Id}"
            keywords = self._extract_keywords_from_text(description_text)

            return [TrendingTopicData(
                area=f"Xu hướng học kỳ {area_name}",
                keywords=keywords,
                description=description_text or "Xu hướng học kỳ dựa trên mô tả trong hệ thống",
                relevance_score=1.0
            )]
        except Exception as e:
            self.log_error("Error fetching semester trends", e)
            # Fallback to a neutral trend if DB is unavailable
            return [TrendingTopicData(
                area="Xu hướng học kỳ",
                keywords=[],
                description="Không thể truy xuất mô tả học kỳ. Sử dụng gợi ý chung cho CNTT.",
                relevance_score=0.5
            )]
        finally:
            try:
                db.close()
            except Exception:
                pass
    
    def _get_mock_trending_data(self) -> List[TrendingTopicData]:
        """Generate mock trending data for demonstration."""
        return [
            TrendingTopicData(
                area="Artificial Intelligence & Machine Learning",
                keywords=["deep learning", "neural networks", "computer vision", "NLP", "reinforcement learning"],
                description="AI and ML continue to dominate research with applications in healthcare, finance, and automation.",
                relevance_score=0.95
            ),
            TrendingTopicData(
                area="Sustainable Technology",
                keywords=["green energy", "carbon capture", "sustainable computing", "renewable energy", "eco-friendly"],
                description="Growing focus on sustainable technology solutions for climate change mitigation.",
                relevance_score=0.88
            ),
            TrendingTopicData(
                area="Cybersecurity & Privacy",
                keywords=["blockchain security", "privacy protection", "zero-trust", "quantum cryptography", "data privacy"],
                description="Increasing importance of cybersecurity in our interconnected digital world.",
                relevance_score=0.82
            ),
            TrendingTopicData(
                area="Internet of Things (IoT)",
                keywords=["smart cities", "edge computing", "sensor networks", "industrial IoT", "home automation"],
                description="IoT expansion into smart cities, industrial applications, and everyday life.",
                relevance_score=0.78
            ),
            TrendingTopicData(
                area="Healthcare Technology",
                keywords=["telemedicine", "health monitoring", "medical AI", "digital health", "biotechnology"],
                description="Digital transformation in healthcare accelerated by recent global events.",
                relevance_score=0.85
            ),
            TrendingTopicData(
                area="Quantum Computing",
                keywords=["quantum algorithms", "quantum simulation", "quantum networking", "quantum supremacy"],
                description="Emerging quantum technologies with potential to revolutionize computing.",
                relevance_score=0.72
            )
        ]
    
    async def _generate_suggestions(
        self,
        trending_data: List[TrendingTopicData],
        category_preference: str,
        keywords: List[str],
        supervisor_expertise: List[str],
        student_level: str,
        team_size: int
    ) -> List[TopicSuggestion]:
        """Generate topic suggestions using AI based on trending data and preferences."""
        
        # Create prompt for AI
        prompt = self._create_suggestion_prompt(
            trending_data, category_preference, keywords, supervisor_expertise, student_level, team_size
        )
        
        # Generate suggestions using AI
        response_text = await self.generate_text(
            prompt,
            temperature=0.8,
            max_tokens=3000
        )
        
        # Parse AI response
        suggestions = await self._parse_ai_suggestions(response_text, team_size)
        
        return suggestions
    
    def _create_suggestion_prompt(
        self,
        trending_data: List[TrendingTopicData],
        category_preference: str,
        keywords: List[str],
        supervisor_expertise: List[str],
        student_level: str,
        team_size: int
    ) -> str:
        """Create prompt for AI to generate topic suggestions."""
        
        trending_areas_text = "\n".join([
            f"- {data.area}: {data.description} (Keywords: {', '.join(data.keywords)})"
            for data in trending_data
        ])
        # Precompute default roles JSON for inline usage to avoid f-string brace issues
        base_roles = [
            "Team Lead/PM",
            "Backend Developer",
            "Frontend Developer",
            "AI/ML Engineer",
        ]
        if team_size == 5:
            base_roles.append("QA/DevOps")
        roles_json = json.dumps(base_roles, ensure_ascii=False)

        prompt = f"""
Bạn là một chuyên gia tư vấn đề tài nghiên cứu. Hãy đề xuất 5-8 đề tài đồ án phù hợp dựa trên thông tin sau:

## Xu hướng nghiên cứu hiện tại:
{trending_areas_text}

## Thông tin đặc biệt:
- Lĩnh vực ưa thích: {category_preference}
- Từ khóa quan tâm: (sử dụng xu hướng của học kỳ, bỏ qua input)
- Chuyên môn giảng viên: {', '.join(supervisor_expertise) if supervisor_expertise else 'Chung'}
- Cấp độ sinh viên: {student_level}
- Quy mô nhóm: {team_size} sinh viên (4 hoặc 5)

## Yêu cầu:
1. Mỗi đề tài phải có tính ứng dụng thực tế cao
2. Phù hợp với sinh viên ngành Công nghệ Thông tin kỳ cuối (final-term IT)
3. Thời gian thực hiện trọn vẹn trong 14 tuần (kế hoạch khả thi)
4. Tận dụng xu hướng nghiên cứu của học kỳ hiện tại
5. Công nghệ, phạm vi và độ khó phù hợp với đồ án tốt nghiệp CNTT
6. Phân công vai trò rõ ràng cho {team_size} thành viên và kế hoạch công việc 14 tuần

Hãy trả về kết quả trong format JSON như sau:
{{
  "suggestions": [
    {{
      "title": "Tên đề tài cụ thể",
      "description": "Mô tả chi tiết về đề tài",
      "objectives": "Mục tiêu cụ thể của đề tài",
      "methodology": "Phương pháp thực hiện đề xuất",
      "expected_outcomes": "Kết quả mong đợi",
      "category": "Danh mục/lĩnh vực",
      "rationale": "Lý do tại sao đề tài này phù hợp với xu hướng hiện tại",
      "difficulty_level": "Mức độ khó phù hợp với kỳ cuối (ví dụ: Advanced)",
      "estimated_duration": "14 weeks",
      "team_size": {team_size},
      "suggested_roles": {roles_json}
    }}
  ]
}}

Đảm bảo các đề tài đa dạng và bao phủ các xu hướng khác nhau.
"""
        return prompt
    
    async def _parse_ai_suggestions(self, response_text: str, team_size: int) -> List[TopicSuggestion]:
        """Parse AI response to extract topic suggestions."""
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Find JSON content in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            suggestions = []
            for item in data.get("suggestions", []):
                item_team_size = item.get("team_size", team_size if team_size in (4, 5) else 4)
                roles = item.get("suggested_roles")
                if not roles or not isinstance(roles, list):
                    roles = self._default_roles_for_team(item_team_size)
                suggestion = TopicSuggestion(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    objectives=item.get("objectives", ""),
                    methodology=item.get("methodology", ""),
                    expected_outcomes=item.get("expected_outcomes", ""),
                    category=item.get("category", ""),
                    rationale=item.get("rationale", ""),
                    difficulty_level=item.get("difficulty_level", "Advanced"),
                    estimated_duration="14 weeks",
                    team_size=item_team_size,
                    suggested_roles=roles
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            self.log_error("Error parsing AI suggestions", e)
            # Return fallback suggestions
            return self._get_fallback_suggestions(team_size)
    
    def _get_fallback_suggestions(self, team_size: int = 4) -> List[TopicSuggestion]:
        """Provide fallback suggestions if AI parsing fails."""
        roles = self._default_roles_for_team(team_size if team_size in (4, 5) else 4)
        return [
            TopicSuggestion(
                title="Hệ thống nhận diện đối tượng thời gian thực sử dụng Deep Learning",
                description="Xây dựng ứng dụng nhận diện và theo dõi đối tượng trong video thời gian thực",
                objectives="Nghiên cứu và triển khai thuật toán deep learning cho nhận diện đối tượng",
                methodology="Sử dụng YOLO hoặc R-CNN, training trên dataset tùy chỉnh",
                expected_outcomes="Ứng dụng demo có thể nhận diện đối tượng với độ chính xác > 85%",
                category="Artificial Intelligence",
                rationale="AI và Computer Vision đang rất hot trong xu hướng nghiên cứu hiện tại",
                difficulty_level="Advanced",
                estimated_duration="14 weeks",
                team_size=team_size,
                suggested_roles=roles
            ),
            TopicSuggestion(
                title="Ứng dụng IoT giám sát môi trường thông minh",
                description="Phát triển hệ thống sensor network giám sát chất lượng không khí và môi trường",
                objectives="Tạo hệ thống IoT thu thập và phân tích dữ liệu môi trường",
                methodology="Arduino/Raspberry Pi, cảm biến môi trường, cloud computing",
                expected_outcomes="Dashboard theo dõi và cảnh báo chất lượng môi trường real-time",
                category="Internet of Things",
                rationale="IoT cho smart cities là xu hướng quan trọng hiện nay",
                difficulty_level="Advanced",
                estimated_duration="14 weeks",
                team_size=team_size,
                suggested_roles=roles
            )
        ]

    def _default_roles_for_team(self, team_size: int) -> List[str]:
        """Return sensible default roles for a team of 4 or 5 students."""
        base_roles = [
            "Team Lead/PM",
            "Backend Developer",
            "Frontend Developer",
            "AI/ML Engineer"
        ]
        if team_size == 5:
            base_roles.append("QA/DevOps")
        return base_roles

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Naively extract up to 10 keyword-like terms from a description text."""
        if not text:
            return []
        # Extract word tokens (unicode-aware) and filter simple stopwords
        tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
        stopwords = {
            "và","là","của","cho","trong","với","các","công","nghệ","thông","tin",
            "một","được","đến","từ","the","and","of","for","in","to","on","a","an"
        }
        words = [w for w in tokens if len(w) >= 4 and w not in stopwords]
        # Preserve order while unique
        seen = set()
        keywords: List[str] = []
        for w in words:
            if w not in seen:
                seen.add(w)
                keywords.append(w)
            if len(keywords) >= 10:
                break
        return keywords

