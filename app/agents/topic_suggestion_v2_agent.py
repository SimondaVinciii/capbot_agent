"""Agent 1 V2: Topic Suggestion Agent V2 - Generates topic ideas with additional fields."""

import json
from typing import Dict, Any, List
from datetime import datetime
from app.agents.base_agent import BaseAgent, AgentResult
from app.schemas.schemas import TopicSuggestionV2, TopicSuggestionsV2Response, TrendingTopicData
from app.models.database import SessionLocal, Semester
import re

class TopicSuggestionV2Agent(BaseAgent):
    """Agent responsible for suggesting topic ideas with additional fields (eN_Title, abbreviation, vN_title, etc.)."""
    
    def __init__(self):
        super().__init__("TopicSuggestionV2Agent", "gemini-2.0-flash")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request to generate topic suggestions v2.
        
        Args:
            input_data: Contains semester_id, category_preference, keywords, etc.
            
        Returns:
            Dict containing topic suggestions v2 and trending areas
        """
        try:
            import time
            started_at = time.time()
            self.log_info("Starting topic suggestion v2 generation")
            
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
            suggestions = await self._generate_suggestions_v2(
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
            response = TopicSuggestionsV2Response(
                suggestions=suggestions,
                trending_areas=[data.area for data in trending_data],
                generated_at=datetime.now(),
                processing_time=processing_time
            )
            
            self.log_info(f"Generated {len(suggestions)} topic suggestions v2")
            
            return AgentResult(
                success=True,
                data=response.dict(),
                metadata={"trending_areas_count": len(trending_data)}
            ).to_dict()
            
        except Exception as e:
            self.log_error("Error generating topic suggestions v2", e)
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
    
    async def _generate_suggestions_v2(
        self,
        trending_data: List[TrendingTopicData],
        category_preference: str,
        keywords: List[str],
        supervisor_expertise: List[str],
        student_level: str,
        team_size: int
    ) -> List[TopicSuggestionV2]:
        """Generate topic suggestions v2 using AI based on trending data and preferences."""
        
        # Create prompt for AI
        prompt = self._create_suggestion_v2_prompt(
            trending_data, category_preference, keywords, supervisor_expertise, student_level, team_size
        )
        
        # Generate suggestions using AI
        response_text = await self.generate_text(
            prompt,
            temperature=0.8,
            max_tokens=4000
        )
        
        # Parse AI response
        suggestions = await self._parse_ai_suggestions_v2(response_text, team_size)
        
        return suggestions
    
    def _create_suggestion_v2_prompt(
        self,
        trending_data: List[TrendingTopicData],
        category_preference: str,
        keywords: List[str],
        supervisor_expertise: List[str],
        student_level: str,
        team_size: int
    ) -> str:
        """Create prompt for AI to generate topic suggestions v2."""
        
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

## FORMAT JSON BẮT BUỘC:
Bạn PHẢI trả về CHÍNH XÁC format JSON này với TẤT CẢ các field, KHÔNG có gì khác:

{{
  "suggestions": [
    {{
      "eN_Title": "English title here",
      "abbreviation": "ABC",
      "vN_title": "Tiêu đề tiếng Việt",
      "problem": "Mô tả vấn đề cần giải quyết",
      "context": "Bối cảnh nghiên cứu",
      "content": "Nội dung chính của nghiên cứu",
      "description": "Mô tả chi tiết về đề tài",
      "objectives": "Mục tiêu cụ thể",
      "category": "Danh mục",
      "rationale": "Lý do phù hợp với xu hướng",
      "difficulty_level": "Advanced",
      "estimated_duration": "14 weeks",
      "team_size": {team_size},
      "suggested_roles": {roles_json}
    }}
  ]
}}

## YÊU CẦU BẮT BUỘC:
- PHẢI có đầy đủ TẤT CẢ 13 field cho mỗi suggestion
- KHÔNG được bỏ qua bất kỳ field nào: eN_Title, abbreviation, vN_title, problem, context, content, description, objectives, category, rationale, difficulty_level, estimated_duration, team_size, suggested_roles

## 🚨 QUY TẮC JSON CỰC KỲ NGHIÊM NGẶT - BẮT BUỘC 100%:

⚠️ CRITICAL: JSON PHẢI CHÍNH XÁC TUYỆT ĐỐI - KHÔNG THỂ SAI!

 ✅ TEMPLATE ĐÚNG - COPY CHÍNH XÁC:
 {{
   "suggestions": [
     {{
       "eN_Title": "AI Platform", 
       "abbreviation": "AIP",
       "vN_title": "Nền tảng AI",
       "problem": "Mô tả vấn đề",
       "context": "Bối cảnh", 
       "content": "Nội dung",
       "description": "Mô tả",
       "objectives": "Mục tiêu"
     }}
   ]
 }}

## 🔥 LỖI THƯỜNG GẶP - TRÁNH TUYỆT ĐỐI:
❌ "title": "AI Platform"abbreviation": "AI"  ← THIẾU DẤU PHẨY!
✅ "title": "AI Platform", "abbreviation": "AI"

❌ "title": "Some text'  ← DẤU NHÁY ĐƠN!
✅ "title": "Some text"

## QUY TẮC JSON NGHIÊM NGẶT:
1. CHỈ trả về JSON thuần túy, KHÔNG có ```json hoặc ``` bao quanh
2. KHÔNG có text giải thích, comment, hoặc bất kỳ nội dung nào khác
3. Tất cả string phải được bao quanh bởi dấu ngoặc kép ĐÚNG: "text"
4. TUYỆT ĐỐI KHÔNG dùng dấu nháy đơn: KHÔNG được viết "text' hoặc \'
5. KHÔNG có dấu phẩy thừa ở cuối object/array
6. KHÔNG sử dụng dấu ngoặc kép TRONG nội dung string (thay bằng dấu nháy đơn)
7. KHÔNG sử dụng ký tự đặc biệt gây lỗi JSON parsing
8. eN_Title: tiếng Anh, vN_title: tiếng Việt
9. abbreviation: 3-5 ký tự, viết hoa
10. Tất cả text phải là ký tự in được (printable characters)
11. KHÔNG có control characters hoặc ký tự đặc biệt
12. TUYỆT ĐỐI KHÔNG kết thúc string bằng \' - CHỈ dùng "
13. Định dạng JSON phải hợp lệ 100% theo chuẩn RFC 7159

 ## VÍ DỤ ĐÚNG:
 {{{{
   "suggestions": [
     {{{{
       "eN_Title": "AI Learning System",
       "abbreviation": "ALS",
       "vN_title": "Hệ thống học tập AI",
       "problem": "Vấn đề học tập cá nhân hóa",
       "context": "Bối cảnh giáo dục hiện đại",
       "content": "Nghiên cứu AI trong giáo dục",
       "description": "Hệ thống học tập thông minh",
       "objectives": "Cải thiện hiệu quả học tập",
       "category": "AI",
       "rationale": "Xu hướng AI trong giáo dục",
       "difficulty_level": "Advanced",
       "estimated_duration": "14 weeks",
       "team_size": 4,
       "suggested_roles": ["Team Lead", "Backend Dev", "Frontend Dev", "AI Engineer"]
     }}}}
   ]
 }}

## CHÚ Ý QUAN TRỌNG:
- Tất cả string value PHẢI kết thúc bằng " (dấu ngoặc kép)
- TUYỆT ĐỐI KHÔNG được kết thúc bằng ' (dấu nháy đơn)  
- VÍ DỤ SAI: "title": "Some text'  ← SAI!
- VÍ DỤ ĐÚNG: "title": "Some text"  ← ĐÚNG!

 BẮT ĐẦU TRẢ LỜI NGAY BẰNG DẤU {{{{ VÀ KẾT THÚC BẰNG DẤU }}}}:
"""
        return prompt
    
    async def _parse_ai_suggestions_v2(self, response_text: str, team_size: int) -> List[TopicSuggestionV2]:
        """Parse AI response to extract topic suggestions v2 - SIMPLIFIED ROOT FIX."""
        try:
            import re
            import json
            
            # Step 1: Clean and extract JSON
            json_text = response_text.strip()
            
            # Remove markdown code blocks
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0].strip()
            elif '```' in json_text:
                json_text = json_text.split('```')[1].split('```')[0].strip()
            
            # Extract JSON boundaries
            json_start = json_text.find('{')
            json_end = json_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_text = json_text[json_start:json_end]
            
            self.log_info(f"Raw AI response preview: {json_text[:200]}...")
            
            # Step 2: FIRST - Try parsing as-is (AI might be correct)
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and 'suggestions' in data:
                    suggestions = data['suggestions']
                    if isinstance(suggestions, list) and len(suggestions) > 0:
                        self.log_info("SUCCESS: AI generated valid JSON!")
                        return self._convert_to_suggestion_objects_v2(suggestions)
            except json.JSONDecodeError:
                self.log_info("AI JSON needs fixing...")
            
            # Step 3: Apply ONLY the critical fix (THE ROOT PROBLEM)
            # Fix missing commas between key-value pairs: "value"key": -> "value", "key":
            json_text = re.sub(r'"([^"]*?)"([a-zA-Z_]+)"(\s*):', r'"\1", "\2"\3:', json_text)
            
            self.log_info(f"After critical fix: {json_text[:200]}...")
            
            # Step 4: Try parsing again
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and 'suggestions' in data:
                    suggestions = data['suggestions']
                    if isinstance(suggestions, list) and len(suggestions) > 0:
                        self.log_info("SUCCESS: Fixed with critical fix!")
                        return self._convert_to_suggestion_objects_v2(suggestions)
            except json.JSONDecodeError as e:
                self.log_error(f"Critical fix failed: {e}")
            
            # Step 5: ONLY if still broken, apply aggressive fix
            self.log_info("Applying aggressive fix as last resort...")
            json_text = self._aggressive_json_fix(json_text)
            
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and 'suggestions' in data:
                    suggestions = data['suggestions']
                    if isinstance(suggestions, list) and len(suggestions) > 0:
                        self.log_info("SUCCESS: Aggressive fix worked!")
                        return self._convert_to_suggestion_objects_v2(suggestions)
            except json.JSONDecodeError as e:
                self.log_error(f"All fixes failed: {e}")
            
            # Fallback
            return self._get_fallback_suggestions_v2(team_size)
            
        except Exception as e:
            self.log_error("Error parsing AI suggestions v2", e)
            return self._get_fallback_suggestions_v2(team_size)
    
    def _convert_to_suggestion_objects_v2(self, suggestions: list) -> List[TopicSuggestionV2]:
        """Convert parsed suggestion data to TopicSuggestionV2 objects."""
        result = []
        for suggestion_data in suggestions:
            try:
                suggestion_obj = self._create_suggestion_v2_object(suggestion_data)
                if suggestion_obj:
                    result.append(suggestion_obj)
            except Exception as e:
                self.log_error(f"Error converting suggestion object: {e}")
                continue
        return result if result else self._get_fallback_suggestions_v2(4)
    
    def _create_suggestion_v2_object(self, suggestion_data: dict) -> TopicSuggestionV2:
        """Create a TopicSuggestionV2 object from parsed data."""
        try:
            return TopicSuggestionV2(
                eN_Title=suggestion_data.get('eN_Title', 'Untitled Project'),
                abbreviation=suggestion_data.get('abbreviation', 'UNT'),
                vN_title=suggestion_data.get('vN_title', 'Dự án không tiêu đề'),
                problem=suggestion_data.get('problem', 'Problem description not provided'),
                context=suggestion_data.get('context', 'Context not provided'),
                content=suggestion_data.get('content', 'Content not provided'),
                description=suggestion_data.get('description', 'Description not provided'),
                objectives=suggestion_data.get('objectives', 'Objectives not provided'),
                category=suggestion_data.get('category', 'General'),
                rationale=suggestion_data.get('rationale', 'Rationale not provided'),
                team_size=suggestion_data.get('team_size', 4),
                difficulty_level=suggestion_data.get('difficulty_level', 'medium'),
                estimated_duration=suggestion_data.get('estimated_duration', '6 months'),
                suggested_roles=suggestion_data.get('suggested_roles', ['Developer', 'Analyst'])
            )
        except Exception as e:
            self.log_error(f"Error creating suggestion object: {e}")
            return None
    
    def _aggressive_json_fix(self, json_text: str) -> str:
        """Apply aggressive JSON fixes."""
        try:
            import re
            import json
            
            # Clean control characters
            json_text = ''.join(char for char in json_text if ord(char) >= 32 or char in '\n\r\t')
            json_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_text)
            
            # Apply the critical fixes
            json_text = re.sub(r'"([^"]*?)"([a-zA-Z_]+)"(\s*):', r'"\1", "\2"\3:', json_text)
            json_text = re.sub(r'\\\'', '"', json_text)
            json_text = re.sub(r'([^\\])[\'"](\s*[,}\]])', r'\1"\2', json_text)
            json_text = re.sub(r'([,{\s])([a-zA-Z_]+)(\s*):', r'\1"\2"\3:', json_text)
            json_text = re.sub(r':\s*([A-Za-z][^,}\]"]*?)(\s*[,}\]])', r': "\1"\2', json_text)
            
            return json_text
            
        except Exception as e:
            self.log_error("Error in aggressive JSON fixing", e)
            return json_text
    
    def _get_fallback_suggestions_v2(self, team_size: int = 4) -> List[TopicSuggestionV2]:
        """Provide fallback suggestions v2 if AI parsing fails."""
        roles = self._default_roles_for_team(team_size if team_size in (4, 5) else 4)
        return [
            TopicSuggestionV2(
                eN_Title="Real-time Object Recognition System using Deep Learning",
                abbreviation="RORS",
                vN_title="Hệ thống nhận diện đối tượng thời gian thực sử dụng Deep Learning",
                problem="Cần giải quyết vấn đề nhận diện và theo dõi đối tượng trong video thời gian thực với độ chính xác cao",
                context="Trong bối cảnh phát triển AI và Computer Vision, việc nhận diện đối tượng thời gian thực trở nên quan trọng cho nhiều ứng dụng",
                content="Nghiên cứu và phát triển hệ thống nhận diện đối tượng sử dụng deep learning với khả năng xử lý video thời gian thực",
                description="Xây dựng ứng dụng nhận diện và theo dõi đối tượng trong video thời gian thực sử dụng các thuật toán deep learning tiên tiến",
                objectives="Nghiên cứu và triển khai thuật toán deep learning cho nhận diện đối tượng, tối ưu hóa hiệu suất xử lý thời gian thực",
                category="Artificial Intelligence",
                rationale="AI và Computer Vision đang rất hot trong xu hướng nghiên cứu hiện tại",
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
