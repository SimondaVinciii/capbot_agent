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
    limit: int = Query(200, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    include_documents: bool = Query(False, description="Include document text"),
    include_embeddings: bool = Query(False, description="Include embeddings (large)"),
    topic_id: Optional[str] = Query(None, description="Filter by exact topic id"),
    supervisor_id: Optional[int] = Query(None, description="Filter by supervisor_id in metadata"),
    semester_id: Optional[int] = Query(None, description="Filter by semester (semesterId) in metadata"),
):
    try:
        where: Dict[str, Any] = {}
        if supervisor_id is not None:
            where["supervisor_id"] = supervisor_id
        if semester_id is not None:
            # Use new key used during indexing
            where["semesterId"] = semester_id

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
        ids_list = results.get("ids")
        if ids_list is None:
            ids_list = []
        docs_list = results.get("documents")
        if docs_list is None:
            docs_list = []
        metas_list = results.get("metadatas")
        if metas_list is None:
            metas_list = []
        embs_list = results.get("embeddings")
        if embs_list is None:
            embs_list = []

        for i, item_id in enumerate(ids_list):
            meta = metas_list[i] if i < len(metas_list) else {}
            doc = docs_list[i] if (include_documents and i < len(docs_list)) else None
            emb = embs_list[i] if (include_embeddings and i < len(embs_list)) else None
            # Ensure embedding is JSON-serializable (convert numpy arrays to lists)
            if emb is not None:
                try:
                    if hasattr(emb, "tolist"):
                        emb = emb.tolist()
                    elif isinstance(emb, tuple):
                        emb = list(emb)
                except Exception:
                    emb = None
            preview = None
            if include_documents and isinstance(doc, str):
                preview = (doc[:300] + ("..." if len(doc) > 300 else ""))
            items.append({
                "id": item_id,
                "metadata": meta,
                "document_preview": preview,
                "embedding_vector": emb
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
    summary="📊 Index Approved Submissions",
    description="""
    ## Index based on approved Submissions (Status = 7)
    
    ### 📊 What gets indexed:
    - Select all `Submission` with `Status = 7` (Approved)
    - If a submission has `TopicVersionId` (not null): index using fields from `TopicVersion`
    - If `TopicVersionId` is null: index using fields from `Topic`
    - Combines fields: Title, Description, Objectives, Methodology, ExpectedOutcomes, Requirements
    - Document ID format:
      - TopicVersion-based: {topic_id}_{version_id}
      - Topic-based: {topic_id}
    - Metadata includes: topic_id, optional version_id/version_number, semester_id, category_id, supervisor_id
    
    ### 🔍 Use Cases:
    - Initial system setup
    - Refresh ChromaDB with latest approved content
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
    limit: int = Query(1000, description="Maximum number of submissions to index")
):
    """Index documents based on approved Submissions (Status = 7)."""
    try:
        import time
        start_time = time.time()
        
        # Open DB and build payload based on approved submissions
        from app.models.database import get_db, Submission, Topic, TopicVersion
        from sqlalchemy.orm import Session
        from sqlalchemy import and_
        
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            # Query approved submissions (Status = 7)
            conditions = [Submission.Status == 7]
            if semester_id is not None:
                # Join with Topic via TopicId to filter by semester
                submissions = db.query(Submission, Topic).join(
                    Topic, Submission.TopicId == Topic.Id
                ).filter(and_(*conditions, Topic.SemesterId == semester_id)).order_by(Submission.CreatedAt.desc()).limit(limit).all()
            else:
                submissions = db.query(Submission, Topic).join(
                    Topic, Submission.TopicId == Topic.Id
                ).filter(and_(*conditions)).order_by(Submission.CreatedAt.desc()).limit(limit).all()

            topics_to_index: List[Dict[str, Any]] = []
            total_candidates = len(submissions)

            for submission, topic in submissions:
                if submission.TopicVersionId:
                    version = db.query(TopicVersion).filter(
                        and_(TopicVersion.Id == submission.TopicVersionId, TopicVersion.IsActive == True)
                    ).first()
                    if not version:
                        continue
                    en_title = version.Title
                    vn_title = getattr(version, "VN_title", None)
                    problem = getattr(version, "Problem", None)
                    context_val = getattr(version, "Context", None)
                    content_section = getattr(version, "Content", None)
                    description = version.Description
                    objectives = version.Objectives
                    categoryId = topic.CategoryId
                    semesterId = topic.SemesterId
                    parts: List[str] = []
                    for val in [en_title, vn_title, problem, context_val, content_section, description, objectives]:
                        if val:
                            parts.append(str(val))
                    full_content = " ".join(parts)
                    topics_to_index.append({
                        "id": f"{topic.Id}_{version.Id}",
                        "title": en_title or version.Title,
                        "content": full_content,
                        "metadata": {
                            "topic_id": topic.Id,
                            "version_id": version.Id,
                            "version_number": version.VersionNumber,
                            "semesterId": semesterId,
                            "categoryId": categoryId,
                            "supervisor_id": topic.SupervisorId,
                            "en_title": en_title,
                            "vn_title": vn_title,
                            "problem": problem,
                            "context": context_val,
                            "content": content_section,
                            "description": description,
                            "objectives": objectives,
                            "document_url": version.DocumentUrl,
                            "status": version.Status,
                            "submitted_at": version.SubmittedAt.isoformat() if version.SubmittedAt else None,
                            "submitted_by": version.SubmittedBy,
                            "created_at": version.CreatedAt.isoformat() if version.CreatedAt else None,
                            "created_by": getattr(version, "CreatedBy", None),
                            "last_modified_at": version.LastModifiedAt.isoformat() if version.LastModifiedAt else None,
                            "last_modified_by": getattr(version, "LastModifiedBy", None),
                            "deleted_at": version.DeletedAt.isoformat() if getattr(version, "DeletedAt", None) else None,
                            "source": "Submission-TopicVersion",
                            "submission_id": submission.Id,
                            "embedding_provider": chroma.embedding_provider
                        }
                    })
                else:
                    en_title = topic.Title
                    vn_title = getattr(topic, "VN_title", None)
                    problem = getattr(topic, "Problem", None)
                    context_val = getattr(topic, "Context", None)
                    content_section = getattr(topic, "Content", None)
                    description = topic.Description
                    objectives = topic.Objectives
                    categoryId = topic.CategoryId
                    semesterId = topic.SemesterId
                    parts: List[str] = []
                    for val in [en_title, vn_title, problem, context_val, content_section, description, objectives]:
                        if val:
                            parts.append(str(val))
                    full_content = " ".join(parts)
                    topics_to_index.append({
                        "id": f"{topic.Id}",
                        "title": en_title or topic.Title,
                        "content": full_content,
                        "metadata": {
                            "topic_id": topic.Id,
                            "semesterId": semesterId,
                            "categoryId": categoryId,
                            "supervisor_id": topic.SupervisorId,
                            "is_approved": getattr(topic, "IsApproved", None),
                            "en_title": en_title,
                            "vn_title": vn_title,
                            "problem": problem,
                            "context": context_val,
                            "content": content_section,
                            "description": description,
                            "objectives": objectives,
                            "created_at": topic.CreatedAt.isoformat() if getattr(topic, "CreatedAt", None) else None,
                            "created_by": getattr(topic, "CreatedBy", None),
                            "last_modified_at": topic.LastModifiedAt.isoformat() if getattr(topic, "LastModifiedAt", None) else None,
                            "last_modified_by": getattr(topic, "LastModifiedBy", None),
                            "deleted_at": topic.DeletedAt.isoformat() if getattr(topic, "DeletedAt", None) else None,
                            "source": "Submission-Topic",
                            "submission_id": submission.Id,
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
                "message": "Successfully indexed approved submissions",
                "indexed_count": indexed_count,
                "total_candidates": total_candidates,
                "processing_time": round(processing_time, 2)
            }
        finally:
            db.close()
        
    except Exception as e:
        raise HTTPException(500, f"Failed to index approved topics: {str(e)}")








@router.post(
    "/index-single",
    summary="➕ Index a single document by submissionId",
    description="""
    Index exactly one record into ChromaDB using a `submissionId`.
    
    Rules:
    - The submission must have Status = 7 (Approved)
    - If `TopicVersionId` is present: index using `TopicVersion` fields with id `{topic_id}_{version_id}`
    - If `TopicVersionId` is null: index using `Topic` fields with id `{topic_id}`
    """,
)
def index_single_submission(
    submission_id: int = Query(..., description="Submission ID to index")
):
    try:
        from app.models.database import get_db, Submission, Topic, TopicVersion
        from sqlalchemy.orm import Session
        from sqlalchemy import and_

        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            sub: Submission = db.query(Submission).filter(Submission.Id == submission_id).first()
            if not sub:
                raise HTTPException(404, f"Submission {submission_id} not found")
            if sub.Status != 7:
                raise HTTPException(400, "Submission is not approved (Status != 7)")

            topic: Topic = db.query(Topic).filter(Topic.Id == sub.TopicId).first()
            if not topic:
                raise HTTPException(404, f"Topic {sub.TopicId} not found")

            # Build item
            if sub.TopicVersionId:
                version: TopicVersion = db.query(TopicVersion).filter(
                    and_(TopicVersion.Id == sub.TopicVersionId, TopicVersion.IsActive == True)
                ).first()
                if not version:
                    raise HTTPException(404, f"TopicVersion {sub.TopicVersionId} not found or inactive")

                en_title = version.Title
                vn_title = getattr(version, "VN_title", None)
                problem = getattr(version, "Problem", None)
                context_val = getattr(version, "Context", None)
                content_section = getattr(version, "Content", None)
                description = version.Description
                objectives = version.Objectives
                categoryId = topic.CategoryId
                semesterId = topic.SemesterId
                parts: List[str] = []
                for val in [en_title, vn_title, problem, context_val, content_section, description, objectives]:
                    if val:
                        parts.append(str(val))
                full_content = " ".join(parts)

                ok = chroma.add_topic(
                    topic_id=f"{topic.Id}_{version.Id}",
                    title=en_title or version.Title,
                    content=full_content,
                    metadata={
                        "topic_id": topic.Id,
                        "version_id": version.Id,
                        "version_number": version.VersionNumber,
                        "semesterId": semesterId,
                        "categoryId": categoryId,
                        "supervisor_id": topic.SupervisorId,
                        "en_title": en_title,
                        "vn_title": vn_title,
                        "problem": problem,
                        "context": context_val,
                        "content": content_section,
                        "description": description,
                        "objectives": objectives,
                        "document_url": version.DocumentUrl,
                        "status": version.Status,
                        "submitted_at": version.SubmittedAt.isoformat() if version.SubmittedAt else None,
                        "submitted_by": version.SubmittedBy,
                        "created_at": version.CreatedAt.isoformat() if version.CreatedAt else None,
                        "created_by": getattr(version, "CreatedBy", None),
                        "last_modified_at": version.LastModifiedAt.isoformat() if version.LastModifiedAt else None,
                        "last_modified_by": getattr(version, "LastModifiedBy", None),
                        "deleted_at": version.DeletedAt.isoformat() if getattr(version, "DeletedAt", None) else None,
                        "source": "Submission-TopicVersion",
                        "submission_id": sub.Id,
                        "embedding_provider": chroma.embedding_provider
                    }
                )
            else:
                en_title = topic.Title
                vn_title = getattr(topic, "VN_title", None)
                problem = getattr(topic, "Problem", None)
                context_val = getattr(topic, "Context", None)
                content_section = getattr(topic, "Content", None)
                description = topic.Description
                objectives = topic.Objectives
                categoryId = topic.CategoryId
                semesterId = topic.SemesterId
                parts: List[str] = []
                for val in [en_title, vn_title, problem, context_val, content_section, description, objectives]:
                    if val:
                        parts.append(str(val))
                full_content = " ".join(parts)

                ok = chroma.add_topic(
                    topic_id=f"{topic.Id}",
                    title=en_title or topic.Title,
                    content=full_content,
                    metadata={
                        "topic_id": topic.Id,
                        "semesterId": semesterId,
                        "categoryId": categoryId,
                        "supervisor_id": topic.SupervisorId,
                        "is_approved": getattr(topic, "IsApproved", None),
                        "en_title": en_title,
                        "vn_title": vn_title,
                        "problem": problem,
                        "context": context_val,
                        "content": content_section,
                        "description": description,
                        "objectives": objectives,
                        "created_at": topic.CreatedAt.isoformat() if getattr(topic, "CreatedAt", None) else None,
                        "created_by": getattr(topic, "CreatedBy", None),
                        "last_modified_at": topic.LastModifiedAt.isoformat() if getattr(topic, "LastModifiedAt", None) else None,
                        "last_modified_by": getattr(topic, "LastModifiedBy", None),
                        "deleted_at": topic.DeletedAt.isoformat() if getattr(topic, "DeletedAt", None) else None,
                        "source": "Submission-Topic",
                        "submission_id": sub.Id,
                        "embedding_provider": chroma.embedding_provider
                    }
                )

            if not ok:
                raise HTTPException(500, "Failed to add document to ChromaDB")

            return {"message": "Indexed submission successfully", "submission_id": submission_id}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to index submission: {str(e)}")

