"""Main FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.endpoints import router
from config import config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="CapBot AI Agent System",
    description="""
    # 🚀 CapBot AI Agent - Hệ thống AI hỗ trợ quản lý đề tài đồ án

    ## 📋 Tổng quan hệ thống

    CapBot AI Agent là hệ thống thông minh hỗ trợ sinh viên và giảng viên trong việc đề xuất, quản lý và đánh giá đề tài đồ án. Hệ thống sử dụng 3 AI Agent chuyên biệt được điều phối bởi Main Agent.

    ## 🤖 Các AI Agent chính

    ### 1. 💡 Topic Suggestion Agent
    - **Chức năng**: Gợi ý đề tài dựa trên xu hướng nghiên cứu hiện tại
    - **Công nghệ**: Google AI (Gemini) + External API
    - **Đầu vào**: Semester ID, chuyên môn giảng viên, từ khóa quan tâm
    - **Đầu ra**: Danh sách đề tài gợi ý với mô tả chi tiết

    ### 2. 🔍 Duplicate Detection Agent
    - **Chức năng**: Kiểm tra trùng lặp đề tài sử dụng AI
    - **Công nghệ**: ChromaDB + Sentence Transformers + Cosine Similarity
    - **Đầu vào**: Nội dung đề tài (tiêu đề, mô tả, mục tiêu, phương pháp)
    - **Đầu ra**: Báo cáo trùng lặp với similarity score và đề xuất

    ### 3. ✏️ Topic Modification Agent
    - **Chức năng**: Gợi ý chỉnh sửa khi đề tài bị trùng lặp
    - **Công nghệ**: Google AI (Gemini) cho modification strategies
    - **Đầu vào**: Đề tài gốc + kết quả duplicate check
    - **Đầu ra**: Đề tài đã chỉnh sửa với rationale và improvement estimation

    ### 4. 🎯 Main Agent
    - **Chức năng**: Điều phối và orchestrate tất cả sub-agents
    - **Workflow**: Suggestion → Duplicate Check → Auto Modification → Database Creation
    - **Features**: Auto-retry, error handling, comprehensive logging

    ## 🏗️ Kiến trúc hệ thống

    ```
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   FastAPI App   │    │   AI Agents     │    │   Database      │
    │                 │    │                 │    │                 │
    │ • REST API      │◄──►│ • Main Agent    │◄──►│ • SQL Server    │
    │ • Documentation │    │ • Suggestion    │    │ • ChromaDB      │
    │ • Validation    │    │ • Duplicate     │    │ • Vector Store  │
    │ • Error Handle  │    │ • Modification  │    │                 │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
    ```

    ## 🛠️ Công nghệ sử dụng

    - **🤖 AI/ML**: Google AI Development Kit (Gemini 1.5 Flash)
    - **🗄️ Database**: SQL Server + ChromaDB (Vector Database)
    - **🌐 Web Framework**: FastAPI với async support
    - **🔍 Vector Search**: Sentence Transformers + Cosine Similarity
    - **📊 Data Validation**: Pydantic schemas
    - **🔄 ORM**: SQLAlchemy với async support

    ## 📚 API Documentation

    ### 🔄 Topic Management APIs
    - **Submit Topic**: Nộp đề tài với full AI processing
    - **Check Duplicates**: Kiểm tra trùng lặp độc lập
    - **Get Suggestions**: Lấy gợi ý đề tài trending
    - **Modify Topic**: Chỉnh sửa đề tài để giảm trùng lặp

    ### 📋 Topic Version Management
    - **Version Control**: Quản lý nhiều phiên bản đề tài
    - **Approval Workflow**: Quy trình duyệt và phê duyệt
    - **Status Tracking**: Theo dõi trạng thái đề tài

    ### 🔧 System Management
    - **Health Check**: Kiểm tra tình trạng hệ thống
    - **Statistics**: Thống kê và monitoring
    - **Initialization**: Khởi tạo hệ thống AI

    ## 🚀 Getting Started

    1. **Khởi tạo hệ thống**: `POST /api/v1/system/initialize`
    2. **Kiểm tra health**: `GET /api/v1/health`
    3. **Submit đề tài**: `POST /api/v1/topics/submit`
    4. **Xem thống kê**: `GET /api/v1/system/stats`

    ## ⚙️ Configuration

    - **Similarity Threshold**: Điều chỉnh độ nhạy phát hiện trùng lặp (0.6-1.0)
    - **ChromaDB**: Cấu hình vector database
    - **Google AI**: API key và model settings
    - **Database**: Connection string và ORM settings

    ## 📊 Performance & Monitoring

    - **Real-time Statistics**: Theo dõi performance của các agents
    - **Error Tracking**: Comprehensive logging và error handling
    - **Health Monitoring**: System health checks và status reporting
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "CapBot AI Team",
        "email": "support@capbot.ai",
        "url": "https://capbot.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.capbot.ai",
            "description": "Production server"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if config.DEBUG else "Contact system administrator"
        }
    )

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting AI Agent Topic Submission System")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    logger.info("System startup completed")

@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down AI Agent Topic Submission System")

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "AI Agent Topic Submission System",
        "version": "1.0.0",
        "description": "Hệ thống AI Agent hỗ trợ việc nộp đề tài đồ án",
        "docs": "/docs",
        "health": "/api/v1/health",
        "agents": {
            "suggestion": "Gợi ý đề tài từ xu hướng nghiên cứu",
            "duplicate_detection": "Kiểm tra trùng lặp với ChromaDB",
            "modification": "Chỉnh sửa đề tài để tăng độc đáo"
        }
    }

# Run application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG,
        log_level="info"
    )

