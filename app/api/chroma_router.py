"""ChromaDB Management API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.services.chroma_service import ChromaService
from app.services.topic_service import TopicService

router = APIRouter(
    prefix="/api/v1/chroma",
    tags=["🧠 Chroma Management"],
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)

chroma = ChromaService()
topic_service = TopicService()


class IndexItem(BaseModel):
    id: str = Field(..., description="Unique doc ID", example="topic_123")
    title: str = Field(..., description="Document title", example="Hệ thống quản lý thư viện")
    content: str = Field(..., description="Full text content", example="Mô tả chi tiết đề tài...")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class IndexBatchRequest(BaseModel):
    items: List[IndexItem] = Field(..., description="Items to index")


class UpdateItem(BaseModel):
    id: str = Field(..., description="Document ID to update")
    title: Optional[str] = Field(None, description="New title")
    content: Optional[str] = Field(None, description="New content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")


class SearchResponseItem(BaseModel):
    id: str
    title: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]


@router.post(
    "/reset",
    summary="🧹 Reset collection",
    description="Delete and recreate the Chroma collection."
)
def reset_collection():
    ok = chroma.reset_collection()
    if not ok:
        raise HTTPException(500, "Failed to reset collection")
    return {"message": "Collection reset successfully"}


@router.get(
    "/collection",
    summary="📚 View Chroma collection contents",
    description="List items in the Chroma collection with pagination and optional previews.",
)
def list_collection(
    limit: int = Query(20, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    include_documents: bool = Query(False, description="Include document text"),
    include_embeddings: bool = Query(False, description="Include embeddings (large)"),
    topic_id: Optional[str] = Query(None, description="Filter by exact topic id"),
    supervisor_id: Optional[int] = Query(None, description="Filter by supervisor_id in metadata"),
    semester_id: Optional[int] = Query(None, description="Filter by semester_id in metadata"),
):
    try:
        where: Dict[str, Any] = {}
        if supervisor_id is not None:
            where["supervisor_id"] = supervisor_id
        if semester_id is not None:
            where["semester_id"] = semester_id

        ids = [topic_id] if topic_id else None
        results = chroma.list_items(
            limit=limit,
            offset=offset,
            include_documents=include_documents,
            include_embeddings=include_embeddings,
            ids=ids,
            where=(where or None)
        )

        # Normalize response
        items = []
        ids_list = results.get("ids") or []
        docs_list = results.get("documents") or []
        metas_list = results.get("metadatas") or []

        for i, item_id in enumerate(ids_list):
            meta = metas_list[i] if i < len(metas_list) else {}
            doc = docs_list[i] if (include_documents and i < len(docs_list)) else None
            preview = None
            if include_documents and isinstance(doc, str):
                preview = (doc[:300] + ("..." if len(doc) > 300 else ""))
            items.append({
                "id": item_id,
                "metadata": meta,
                "document_preview": preview
            })

        return {
            "count": len(items),
            "offset": offset,
            "limit": limit,
            "items": items
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to list collection: {e}")






@router.post(
    "/index-approved-topics",
    summary="📊 Index Approved Topics from Database",
    description="""
    ## Index latest active TopicVersion per Topic, with Topic fallback
    
    ### 📊 What gets indexed:
    - Prefer latest (max VersionNumber) TopicVersion where IsActive = true
    - If a Topic has no active TopicVersion, index the Topic itself when Topic.IsApproved = true and Topic.IsActive = true
    - Combines fields: Title, Description, Objectives, Methodology, ExpectedOutcomes, Requirements
    - Document ID format:
      - TopicVersion: {topic_id}_{version_id}
      - Topic fallback: {topic_id}
    - Metadata includes: topic_id, optional version_id/version_number, semester_id, category_id, supervisor_id
    
    ### 🔍 Use Cases:
    - Initial system setup
    - Refresh ChromaDB with latest active content
    - After database migrations or updates
    - Performance optimization and re-indexing
    """,
    responses={
        200: {
            "description": "Approved topics indexed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully indexed approved topics from database",
                        "indexed_count": 45,
                        "total_approved": 45,
                        "processing_time": 12.34
                    }
                }
            }
        }
    }
)
async def index_approved_topics_from_db(
    semester_id: Optional[int] = Query(None, description="Filter by semester ID"),
    limit: int = Query(1000, description="Maximum number of topics to index")
):
    """Index latest active TopicVersion per Topic, with approved Topic fallback."""
    try:
        import time
        start_time = time.time()
        
        # Open DB and build payload using latest active versions, with topic fallback
        from app.models.database import get_db
        from app.repositories.topic_repository import TopicRepository
        from sqlalchemy.orm import Session
        
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            repo = TopicRepository(db)
            if semester_id:
                topics = repo.get_topics_by_semester(semester_id=semester_id, limit=limit, approved_only=False)
            else:
                topics = repo.get_all_active_topics(limit=limit)
            
            topics_to_index: List[Dict[str, Any]] = []
            total_candidates = 0
            
            for topic in topics:
                total_candidates += 1
                latest_version = repo.get_latest_topic_version(topic.Id)
                if latest_version:
                    # Build from TopicVersion
                    content_parts: List[str] = []
                    if latest_version.Title:
                        content_parts.append(f"Title: {latest_version.Title}")
                    if latest_version.Description:
                        content_parts.append(f"Description: {latest_version.Description}")
                    if latest_version.Objectives:
                        content_parts.append(f"Objectives: {latest_version.Objectives}")
                    if latest_version.Methodology:
                        content_parts.append(f"Methodology: {latest_version.Methodology}")
                    if latest_version.ExpectedOutcomes:
                        content_parts.append(f"Expected Outcomes: {latest_version.ExpectedOutcomes}")
                    if latest_version.Requirements:
                        content_parts.append(f"Requirements: {latest_version.Requirements}")
                    full_content = " ".join(content_parts)
                    topics_to_index.append({
                        "id": f"{topic.Id}_{latest_version.Id}",
                        "title": latest_version.Title,
                        "content": full_content,
                        "metadata": {
                            "topic_id": topic.Id,
                            "version_id": latest_version.Id,
                            "version_number": latest_version.VersionNumber,
                            "semester_id": topic.SemesterId,
                            "category_id": topic.CategoryId,
                            "supervisor_id": topic.SupervisorId,
                            "description": latest_version.Description,
                            "objectives": latest_version.Objectives,
                            "methodology": latest_version.Methodology,
                            # New fields from TopicVersion schema
                            "vn_title": getattr(latest_version, "VN_title", None),
                            "context": getattr(latest_version, "Context", None),
                            "content_section": getattr(latest_version, "Content", None),
                            "problem": getattr(latest_version, "Problem", None),
                            "document_url": latest_version.DocumentUrl,
                            "status": latest_version.Status,
                            "submitted_at": latest_version.SubmittedAt.isoformat() if latest_version.SubmittedAt else None,
                            "submitted_by": latest_version.SubmittedBy,
                            "created_at": latest_version.CreatedAt.isoformat() if latest_version.CreatedAt else None,
                            "created_by": getattr(latest_version, "CreatedBy", None),
                            "last_modified_at": latest_version.LastModifiedAt.isoformat() if latest_version.LastModifiedAt else None,
                            "last_modified_by": getattr(latest_version, "LastModifiedBy", None),
                            "deleted_at": latest_version.DeletedAt.isoformat() if getattr(latest_version, "DeletedAt", None) else None,
                            "source": "TopicVersion",
                            "embedding_provider": chroma.embedding_provider
                        }
                    })
                else:
                    # Fallback to Topic only when approved and active
                    if getattr(topic, "IsApproved", False) and getattr(topic, "IsActive", False):
                        content_parts: List[str] = []
                        if topic.Title:
                            content_parts.append(f"Title: {topic.Title}")
                        if topic.Description:
                            content_parts.append(f"Description: {topic.Description}")
                        if topic.Objectives:
                            content_parts.append(f"Objectives: {topic.Objectives}")
                        full_content = " ".join(content_parts)
                        topics_to_index.append({
                            "id": f"{topic.Id}",
                            "title": topic.Title,
                            "content": full_content,
                            "metadata": {
                                "topic_id": topic.Id,
                                "semester_id": topic.SemesterId,
                                "category_id": topic.CategoryId,
                                "supervisor_id": topic.SupervisorId,
                                "is_approved": topic.IsApproved,
                                "description": topic.Description,
                                "objectives": topic.Objectives,
                                "methodology": None,
                                # New fields from Topic schema
                                "vn_title": getattr(topic, "VN_title", None),
                                "abbreviation": getattr(topic, "Abbreviation", None),
                                "context": getattr(topic, "Context", None),
                                "content_section": getattr(topic, "Content", None),
                                "problem": getattr(topic, "Problem", None),
                                "created_at": topic.CreatedAt.isoformat() if getattr(topic, "CreatedAt", None) else None,
                                "created_by": getattr(topic, "CreatedBy", None),
                                "last_modified_at": topic.LastModifiedAt.isoformat() if getattr(topic, "LastModifiedAt", None) else None,
                                "last_modified_by": getattr(topic, "LastModifiedBy", None),
                                "deleted_at": topic.DeletedAt.isoformat() if getattr(topic, "DeletedAt", None) else None,
                                "source": "Topic",
                                "embedding_provider": chroma.embedding_provider
                            }
                        })
            
            if not topics_to_index:
                return {
                    "message": "No topics or versions eligible for indexing",
                    "indexed_count": 0,
                    "total_candidates": total_candidates,
                    "processing_time": 0.0
                }
            
            indexed_count = chroma.add_topics_batch(topics_to_index)
            processing_time = time.time() - start_time
            return {
                "message": "Successfully indexed latest active versions with topic fallback",
                "indexed_count": indexed_count,
                "total_candidates": total_candidates,
                "processing_time": round(processing_time, 2)
            }
        finally:
            db.close()
        
    except Exception as e:
        raise HTTPException(500, f"Failed to index approved topics: {str(e)}")








