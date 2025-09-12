"""Main API router that combines all sub-routers."""

from fastapi import APIRouter
from app.api.topic_router import router as topic_router
from app.api.version_router import router as version_router
from app.api.system_router import router as system_router
from app.api.chroma_router import router as chroma_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(topic_router)
#router.include_router(version_router)
router.include_router(system_router)
router.include_router(chroma_router)
