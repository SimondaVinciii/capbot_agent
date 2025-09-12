"""Agent 1: Topic Suggestion Agent - Generates topic ideas based on trending areas."""

import json
import httpx
from typing import Dict, Any, List
from datetime import datetime
from app.agents.base_agent import BaseAgent, AgentResult
from app.schemas.schemas import TopicSuggestion, TopicSuggestionsResponse, TrendingTopicData
from config import config

class TopicSuggestionAgent(BaseAgent):
    """Agent responsible for suggesting topic ideas based on trending research areas."""
    
    def __init__(self):
        super().__init__("TopicSuggestionAgent", "gemini-1.5-flash")
        self.trending_api_url = config.TRENDING_API_URL
        self.trending_api_key = config.TRENDING_API_KEY
    
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
            
            # Get trending data from external API
            trending_data = await self._fetch_trending_data()
            
            # Generate suggestions using AI
            suggestions = await self._generate_suggestions(
                trending_data=trending_data,
                category_preference=category_preference,
                keywords=keywords,
                supervisor_expertise=supervisor_expertise,
                student_level=student_level
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
    
    async def _fetch_trending_data(self) -> List[TrendingTopicData]:
        """Fetch trending topic data from external API or generate mock data."""
        try:
            # Try to fetch from external API
            if self.trending_api_url and self.trending_api_url != "https://api.example.com/trending-topics":
                async with httpx.AsyncClient() as client:
                    headers = {}
                    if self.trending_api_key:
                        headers["Authorization"] = f"Bearer {self.trending_api_key}"
                    
                    response = await client.get(self.trending_api_url, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    return [TrendingTopicData(**item) for item in data.get("trending_areas", [])]
            
            # Fallback to mock trending data
            return self._get_mock_trending_data()
            
        except Exception as e:
            self.log_error("Error fetching trending data, using mock data", e)
            return self._get_mock_trending_data()
    
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
        student_level: str
    ) -> List[TopicSuggestion]:
        """Generate topic suggestions using AI based on trending data and preferences."""
        
        # Create prompt for AI
        prompt = self._create_suggestion_prompt(
            trending_data, category_preference, keywords, supervisor_expertise, student_level
        )
        
        # Generate suggestions using AI
        response_text = await self.generate_text(
            prompt,
            temperature=0.8,
            max_tokens=3000
        )
        
        # Parse AI response
        suggestions = await self._parse_ai_suggestions(response_text)
        
        return suggestions
    
    def _create_suggestion_prompt(
        self,
        trending_data: List[TrendingTopicData],
        category_preference: str,
        keywords: List[str],
        supervisor_expertise: List[str],
        student_level: str
    ) -> str:
        """Create prompt for AI to generate topic suggestions."""
        
        trending_areas_text = "\n".join([
            f"- {data.area}: {data.description} (Keywords: {', '.join(data.keywords)})"
            for data in trending_data
        ])
        
        prompt = f"""
Bạn là một chuyên gia tư vấn đề tài nghiên cứu. Hãy đề xuất 5-8 đề tài đồ án phù hợp dựa trên thông tin sau:

## Xu hướng nghiên cứu hiện tại:
{trending_areas_text}

## Thông tin đặc biệt:
- Lĩnh vực ưa thích: {category_preference}
- Từ khóa quan tâm: {', '.join(keywords) if keywords else 'Không có'}
- Chuyên môn giảng viên: {', '.join(supervisor_expertise) if supervisor_expertise else 'Chung'}
- Cấp độ sinh viên: {student_level}

## Yêu cầu:
1. Mỗi đề tài phải có tính ứng dụng thực tế cao
2. Phù hợp với khả năng của sinh viên {student_level}
3. Tận dụng xu hướng nghiên cứu hiện tại
4. Có tính khả thi trong thời gian thực hiện đồ án

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
      "rationale": "Lý do tại sao đề tài này phù hợp với xu hướng hiện tại"
    }}
  ]
}}

Đảm bảo các đề tài đa dạng và bao phủ các xu hướng khác nhau.
"""
        return prompt
    
    async def _parse_ai_suggestions(self, response_text: str) -> List[TopicSuggestion]:
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
                suggestion = TopicSuggestion(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    objectives=item.get("objectives", ""),
                    methodology=item.get("methodology", ""),
                    expected_outcomes=item.get("expected_outcomes", ""),
                    category=item.get("category", ""),
                    rationale=item.get("rationale", "")
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            self.log_error("Error parsing AI suggestions", e)
            # Return fallback suggestions
            return self._get_fallback_suggestions()
    
    def _get_fallback_suggestions(self) -> List[TopicSuggestion]:
        """Provide fallback suggestions if AI parsing fails."""
        return [
            TopicSuggestion(
                title="Hệ thống nhận diện đối tượng thời gian thực sử dụng Deep Learning",
                description="Xây dựng ứng dụng nhận diện và theo dõi đối tượng trong video thời gian thực",
                objectives="Nghiên cứu và triển khai thuật toán deep learning cho nhận diện đối tượng",
                methodology="Sử dụng YOLO hoặc R-CNN, training trên dataset tùy chỉnh",
                expected_outcomes="Ứng dụng demo có thể nhận diện đối tượng với độ chính xác > 85%",
                category="Artificial Intelligence",
                rationale="AI và Computer Vision đang rất hot trong xu hướng nghiên cứu hiện tại"
            ),
            TopicSuggestion(
                title="Ứng dụng IoT giám sát môi trường thông minh",
                description="Phát triển hệ thống sensor network giám sát chất lượng không khí và môi trường",
                objectives="Tạo hệ thống IoT thu thập và phân tích dữ liệu môi trường",
                methodology="Arduino/Raspberry Pi, cảm biến môi trường, cloud computing",
                expected_outcomes="Dashboard theo dõi và cảnh báo chất lượng môi trường real-time",
                category="Internet of Things",
                rationale="IoT cho smart cities là xu hướng quan trọng hiện nay"
            )
        ]

