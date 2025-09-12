<<<<<<< HEAD
# capbot_agent
=======
# AI Agent Topic Submission System

Hệ thống AI Agent hỗ trợ việc nộp đề tài đồ án với kiến trúc phân tầng, sử dụng Google AI Development Kit, Python, và ChromaDB.

## 🎯 Tổng quan

Hệ thống gồm 3 sub-agent chính được điều phối bởi Main Agent:

### 🤖 Agent 1: Topic Suggestion Agent
- **Chức năng**: Gợi ý ý tưởng đề tài dựa trên xu hướng nghiên cứu hiện tại
- **Công nghệ**: Google AI (Gemini) + External API
- **Đầu vào**: Semester ID, chuyên môn giảng viên, từ khóa quan tâm
- **Đầu ra**: Danh sách đề tài gợi ý với mô tả chi tiết và rationale

### 🔍 Agent 2: Duplicate Detection Agent  
- **Chức năng**: Kiểm tra trùng lặp đề tài sử dụng cosine similarity
- **Công nghệ**: ChromaDB + Sentence Transformers
- **Đầu vào**: Nội dung đề tài (tiêu đề, mô tả, mục tiêu, phương pháp)
- **Đầu ra**: Báo cáo trùng lặp với similarity score và đề xuất
- **Logic mới**: Chỉ so sánh với **TopicVersion** đã được approve (`Status = 4`)

### ✏️ Agent 3: Topic Modification Agent
- **Chức năng**: Gợi ý chỉnh sửa khi đề tài bị trùng lặp
- **Công nghệ**: Google AI (Gemini) cho modification strategies
- **Đầu vào**: Đề tài gốc + kết quả duplicate check
- **Đầu ra**: Đề tài đã chỉnh sửa với rationale và improvement estimation

### 🎯 Main Agent
- **Chức năng**: Điều phối và orchestrate tất cả sub-agents
- **Workflow**: Suggestion → Duplicate Check → Auto Modification → Database Creation
- **Features**: Auto-retry, error handling, comprehensive logging

## 🏗️ Kiến trúc hệ thống

```
Agent/
├── app/
│   ├── agents/          # AI Agents layer
│   │   ├── base_agent.py
│   │   ├── topic_suggestion_agent.py
│   │   ├── duplicate_detection_agent.py
│   │   ├── topic_modification_agent.py
│   │   └── main_agent.py
│   ├── services/        # Service layer
│   │   ├── chroma_service.py
│   │   └── topic_service.py
│   ├── repositories/    # Data access layer
│   │   └── topic_repository.py
│   ├── models/          # Database models
│   │   └── database.py
│   ├── schemas/         # Pydantic schemas
│   │   └── schemas.py
│   └── api/            # API endpoints
│       └── endpoints.py
├── data/
│   └── chroma/         # ChromaDB storage
├── config.py           # Configuration
├── main.py            # FastAPI application
└── requirements.txt   # Dependencies
```

## 🛠️ Công nghệ sử dụng

- **Google AI Development Kit**: Gemini 1.5 Flash cho natural language processing
- **ChromaDB**: Vector database cho similarity search
- **FastAPI**: Modern web framework cho REST API
- **SQLAlchemy**: ORM cho database operations
- **Sentence Transformers**: Embedding model cho text similarity
- **Pydantic**: Data validation và serialization

## 📋 Yêu cầu hệ thống

- Python 3.8+
- SQL Server (theo schema từ capbotsql.sql)
- ChromaDB storage
- Google AI API key

## 🚀 Cài đặt và chạy

### 1. Clone repository và cài đặt dependencies

```bash
git clone <repository-url>
cd Agent
pip install -r requirements.txt
```

### 2. Cấu hình environment

Tạo file `.env` từ `config.env.example`:

```bash
cp config.env.example .env
```

Chỉnh sửa file `.env`:

```env
# Google AI Configuration
GOOGLE_API_KEY=your_google_ai_api_key_here

# Database Configuration  
DATABASE_URL=mssql+pyodbc://username:password@server/capbot_db?driver=ODBC+Driver+17+for+SQL+Server

# ChromaDB Configuration
CHROMA_DB_PATH=./data/chroma
CHROMA_COLLECTION_NAME=topics_collection

# API Configuration
SIMILARITY_THRESHOLD=0.8
```

### 3. Khởi tạo database

Chạy SQL script để tạo database schema:

```sql
-- Execute capbotsql.sql trong SQL Server Management Studio
```

### 4. Chạy ứng dụng

```bash
python main.py
```

Hoặc sử dụng uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Khởi tạo hệ thống AI

Gọi API để khởi tạo ChromaDB index:

```bash
curl -X POST "http://localhost:8000/api/v1/system/initialize"
```

## 📚 API Documentation

Khi ứng dụng chạy, truy cập:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Các endpoint chính:

#### 🔄 Topic Submission với AI Support
```http
POST /api/v1/topics/submit
```
- **Chức năng**: Submit đề tài với full AI processing
- **Parameters**: `check_duplicates`, `get_suggestions`, `auto_modify`
- **Response**: Complete processing result với suggestions, duplicate check, modifications

#### 🔍 Duplicate Check Only
```http
POST /api/v1/topics/check-duplicates
```
- **Chức năng**: Chỉ kiểm tra trùng lặp không tạo đề tài
- **Response**: Duplicate analysis với similarity scores

#### 💡 Trending Suggestions
```http
GET /api/v1/topics/suggestions
```
- **Chức năng**: Lấy gợi ý đề tài từ xu hướng nghiên cứu
- **Parameters**: `semester_id`, `category_preference`, `keywords`

#### 📋 Get Approved Topics
```http
GET /api/v1/topics/approved
```
- **Chức năng**: Lấy danh sách đề tài đã được approve
- **Parameters**: `semester_id`, `limit`
- **Sử dụng**: Cho indexing và duplicate checking

### 📝 Topic Version Management

#### 📄 Get Topic Versions
```http
GET /api/v1/topics/{topic_id}/versions
```
- **Chức năng**: Lấy tất cả versions của một topic
- **Response**: List các TopicVersionResponse

#### 📄 Get Latest Version
```http
GET /api/v1/topics/{topic_id}/versions/latest
```
- **Chức năng**: Lấy version mới nhất của topic

#### ✅ Get Approved Version
```http
GET /api/v1/topics/{topic_id}/versions/approved
```
- **Chức năng**: Lấy version đã được approve của topic

#### ➕ Create New Version
```http
POST /api/v1/topics/{topic_id}/versions
```
- **Chức năng**: Tạo version mới cho topic
- **Body**: TopicVersionRequest

#### ✅ Approve Version
```http
PUT /api/v1/versions/{version_id}/approve
```
- **Chức năng**: Approve một version (sẽ được index vào ChromaDB)

#### ❌ Reject Version
```http
PUT /api/v1/versions/{version_id}/reject
```
- **Chức năng**: Reject một version
- **Parameters**: `reason` (optional)

#### 📊 Get All Approved Versions
```http
GET /api/v1/versions/approved
```
- **Chức năng**: Lấy tất cả approved versions (cho admin/system)
- **Parameters**: `semester_id`, `limit`

#### ✏️ Topic Modification
```http
POST /api/v1/topics/modify
```
- **Chức năng**: Chỉnh sửa đề tài để giảm trùng lặp
- **Input**: Original topic + duplicate results
- **Response**: Modified topic với rationale

## 🔧 Configuration

### Similarity Threshold

Điều chỉnh ngưỡng similarity trong `.env`:

```env
SIMILARITY_THRESHOLD=0.8  # 80% threshold
```

- **0.9-1.0**: Very strict (ít trùng lặp được detect)
- **0.8-0.9**: Balanced (recommended)
- **0.6-0.8**: Sensitive (nhiều potential duplicates)

### ChromaDB Settings

```env
CHROMA_DB_PATH=./data/chroma           # Storage path
CHROMA_COLLECTION_NAME=topics_collection  # Collection name
```

### Google AI Settings

```env
GOOGLE_API_KEY=your_api_key
# Model được sử dụng: gemini-1.5-flash
```

## 📊 Monitoring và Statistics

### System Stats API
```http
GET /api/v1/system/stats
```

Trả về:
- Processing statistics (total requests, success rate)
- ChromaDB collection info
- Agent status và performance metrics

### Health Check
```http
GET /api/v1/health
```

## 🧪 Testing

### Test với sample data

```python
# Example topic submission
topic_data = {
    "title": "Hệ thống nhận diện đối tượng sử dụng Deep Learning",
    "description": "Xây dựng ứng dụng nhận diện đối tượng trong video real-time",
    "objectives": "Nghiên cứu và triển khai deep learning cho object detection",
    "supervisor_id": 1,
    "semester_id": 1,
    "max_students": 2
}
```

## 🔀 Workflow xử lý (Updated Logic)

### **Topic Creation Workflow:**
1. **Input**: Đề tài từ user
2. **Create Topic**: Tạo Topic container + TopicVersion đầu tiên (Status = 2: Submitted)
3. **Suggestion Agent**: Tạo trending suggestions (optional)
4. **Duplicate Agent**: So sánh với approved TopicVersions trong ChromaDB
5. **Modification Agent**: AI sửa đề tài nếu trùng lặp
6. **Database**: Lưu Topic + TopicVersion vào SQL Server

### **Review & Approval Workflow:**
1. **Review**: Giảng viên/Admin review TopicVersion
2. **Approve**: Set Status = 4 (Approved) → Auto index vào ChromaDB
3. **Reject**: Set Status = 5 (Rejected) → Có thể tạo version mới
4. **New Version**: Tạo version mới để revise nếu cần

### **Duplicate Detection Logic:**
- Chỉ compare với **TopicVersion có Status = 4** (Approved)
- Index ID format: `{topic_id}_{version_id}`
- ChromaDB chỉ chứa approved content

## 🚨 Error Handling

Hệ thống có comprehensive error handling:

- **Validation errors**: Pydantic schema validation
- **Database errors**: SQLAlchemy exception handling  
- **AI errors**: Fallback responses và retry logic
- **ChromaDB errors**: Graceful degradation
- **API errors**: Structured error responses

## 📈 Performance Optimization

- **Batch processing**: ChromaDB bulk operations
- **Async operations**: FastAPI async endpoints
- **Connection pooling**: SQLAlchemy session management
- **Caching**: Result caching cho frequent requests

## 🔒 Security Considerations

- **API Key protection**: Environment variables
- **SQL Injection**: Parameterized queries
- **Input validation**: Pydantic schemas
- **CORS**: Configurable origins

## 📝 Logging

Comprehensive logging system:

- **Agent operations**: Detailed agent processing logs
- **API requests**: Request/response logging
- **Database operations**: Query logging
- **Error tracking**: Stack trace và error context

Logs location: Console output với structured formatting

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Implement changes với proper testing
4. Update documentation
5. Submit pull request

## 📄 License

[Specify license type]

## 📞 Support

For issues và feature requests:
- Create GitHub issue
- Include detailed description
- Provide logs và reproduction steps
>>>>>>> 4af67b8 (chore: init repo with .gitignore and project files)
