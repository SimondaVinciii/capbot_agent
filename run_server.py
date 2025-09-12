"""Development server runner script."""

import uvicorn
from config import config

if __name__ == "__main__":
    print("🚀 Starting AI Agent Topic Submission System...")
    print(f"📍 Server will run on: http://{config.APP_HOST}:{config.APP_PORT}")
    print(f"📚 API Documentation: http://{config.APP_HOST}:{config.APP_PORT}/docs")
    print(f"🔍 Alternative docs: http://{config.APP_HOST}:{config.APP_PORT}/redoc")
    print(f"💚 Health check: http://{config.APP_HOST}:{config.APP_PORT}/api/v1/health")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG,
        log_level="info",
        access_log=True
    )

