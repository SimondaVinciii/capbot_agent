# Topic Suggestion V2 Agent - Hướng dẫn sử dụng

## 🎯 Tổng quan

Topic Suggestion V2 Agent là phiên bản nâng cấp của Topic Suggestion Agent với các trường bổ sung để tạo đề tài nghiên cứu chi tiết hơn.

## 🔧 Các trường mới

### Các trường bổ sung so với phiên bản gốc:
- **`eN_Title`**: Tiêu đề tiếng Anh
- **`abbreviation`**: Viết tắt ngắn gọn (3-5 ký tự)
- **`vN_title`**: Tiêu đề tiếng Việt
- **`problem`**: Vấn đề cần giải quyết
- **`context`**: Bối cảnh nghiên cứu
- **`content`**: Nội dung chính của nghiên cứu
- **`description`**: Mô tả chi tiết
- **`objectives`**: Mục tiêu cụ thể

## 🚀 Sử dụng API

### Endpoint mới:
```
GET /api/v1/topics/suggestions-v2
```

### Tham số:
- `semester_id` (required): ID học kỳ
- `category_preference` (optional): Lĩnh vực ưa thích
- `keywords` (optional): Từ khóa quan tâm
- `supervisor_expertise` (optional): Chuyên môn giảng viên
- `student_level` (optional): Cấp độ sinh viên
- `team_size` (optional): Quy mô nhóm (4 hoặc 5)

### Ví dụ request:
```bash
curl "http://localhost:8000/api/v1/topics/suggestions-v2?semester_id=3&category_preference=AI&team_size=4"
```

### Ví dụ response:
```json
{
  "suggestions": [
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
      "estimated_duration": "14 weeks",
      "team_size": 4,
      "suggested_roles": ["Team Lead/PM", "Backend Developer", "Frontend Developer", "AI/ML Engineer"]
    }
  ],
  "trending_areas": ["AI in Education", "Personalized Learning"],
  "generated_at": "2024-01-22T10:30:00Z",
  "processing_time": 3.456
}
```

## 🔧 Sử dụng trực tiếp Agent

```python
from app.agents.topic_suggestion_v2_agent import TopicSuggestionV2Agent

# Tạo agent
agent = TopicSuggestionV2Agent()

# Dữ liệu đầu vào
input_data = {
    "semester_id": 3,
    "category_preference": "AI",
    "keywords": [],
    "supervisor_expertise": ["Machine Learning"],
    "student_level": "undergraduate",
    "team_size": 4
}

# Xử lý
result = await agent.process(input_data)

if result["success"]:
    suggestions = result["data"]["suggestions"]
    for suggestion in suggestions:
        print(f"English: {suggestion['eN_Title']}")
        print(f"Vietnamese: {suggestion['vN_title']}")
        print(f"Abbreviation: {suggestion['abbreviation']}")
```

## 🛠️ Cải tiến kỹ thuật

### 1. JSON Parsing mạnh mẽ hơn
- Xử lý lỗi JSON parsing tốt hơn
- Retry mechanism với prompt đơn giản hơn
- Fallback suggestions khi AI response không hợp lệ

### 2. Prompt engineering
- Prompt rõ ràng hơn về format JSON
- Yêu cầu AI chỉ trả về JSON
- Tránh ký tự đặc biệt gây lỗi parsing

### 3. Error handling
- Logging chi tiết để debug
- Multiple fallback strategies
- Graceful degradation

## 🐛 Troubleshooting

### Lỗi JSON parsing:
- Agent sẽ tự động retry với prompt đơn giản hơn
- Nếu vẫn thất bại, sẽ sử dụng fallback suggestions
- Kiểm tra logs để xem chi tiết lỗi

### Lỗi semester không hợp lệ:
- Chỉ cho phép học kỳ hiện tại hoặc học kỳ sau
- Kiểm tra semester_id có tồn tại trong database không

## 📝 Lưu ý

1. **Temperature**: Sử dụng temperature=0.8 cho creativity, 0.3 cho consistency
2. **Max tokens**: 4000 tokens cho response đầy đủ
3. **Team size**: Chỉ hỗ trợ 4 hoặc 5 thành viên
4. **Language**: eN_Title phải tiếng Anh, vN_title phải tiếng Việt

## 🔄 So sánh với phiên bản gốc

| Tính năng | V1 | V2 |
|-----------|----|----|
| Basic fields | ✅ | ✅ |
| eN_Title | ❌ | ✅ |
| abbreviation | ❌ | ✅ |
| vN_title | ❌ | ✅ |
| Enhanced problem/context | ❌ | ✅ |
| Better JSON parsing | ❌ | ✅ |
| Retry mechanism | ❌ | ✅ |
