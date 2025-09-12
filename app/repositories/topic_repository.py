"""Repository layer for topic data access."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.database import Topic, TopicVersion, TopicCategory, Semester, User
from app.schemas.schemas import TopicRequest
from datetime import datetime

class TopicRepository:
    """Repository for topic data access operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_topic(self, topic_data: TopicRequest) -> Topic:
        """Create a new topic."""
        db_topic = Topic(
            Title=topic_data.title,  # Base title for reference
            Description=topic_data.description,  # Base description
            Objectives=topic_data.objectives,  # Base objectives
            SupervisorId=topic_data.supervisor_id,
            CategoryId=topic_data.category_id,
            SemesterId=topic_data.semester_id,
            MaxStudents=topic_data.max_students,
            CreatedAt=datetime.utcnow(),
            IsActive=True,
            IsApproved=False  # Topic approval is now based on versions
        )
        
        self.db.add(db_topic)
        self.db.commit()
        self.db.refresh(db_topic)
        
        # Create initial topic version
        self.create_topic_version(
            topic_id=db_topic.Id,
            version_data=topic_data,
            version_number=1
        )
        
        return db_topic

    def create_topic_version(self, topic_id: int, version_data: TopicRequest, version_number: int, status: int = 2) -> TopicVersion:
        """Create a new version of a topic."""
        db_version = TopicVersion(
            TopicId=topic_id,
            VersionNumber=version_number,
            Title=version_data.title,
            Description=version_data.description,
            Objectives=version_data.objectives,
            Methodology=getattr(version_data, 'methodology', None),
            ExpectedOutcomes=getattr(version_data, 'expected_outcomes', None),
            Requirements=getattr(version_data, 'requirements', None),
            Status=status,  # 1=Draft, 2=Submitted, 3=Under Review, 4=Approved, 5=Rejected
            SubmittedAt=datetime.utcnow() if status >= 2 else None,
            CreatedAt=datetime.utcnow(),
            IsActive=True
        )
        
        self.db.add(db_version)
        self.db.commit()
        self.db.refresh(db_version)
        return db_version

    def get_topic_by_id(self, topic_id: int) -> Optional[Topic]:
        """Get topic by ID."""
        return self.db.query(Topic).filter(
            and_(Topic.Id == topic_id, Topic.IsActive == True)
        ).first()

    def get_topics_by_semester(self, semester_id: int, limit: int = 100, approved_only: bool = False) -> List[Topic]:
        """Get topics by semester."""
        conditions = [
            Topic.SemesterId == semester_id,
            Topic.IsActive == True
        ]
        
        if approved_only:
            conditions.append(Topic.IsApproved == True)
            
        return self.db.query(Topic).filter(
            and_(*conditions)
        ).limit(limit).all()

    def get_all_active_topics(self, limit: int = 1000) -> List[Topic]:
        """Get all active topics for similarity comparison (deprecated)."""
        return self.db.query(Topic).filter(
            Topic.IsActive == True
        ).order_by(desc(Topic.CreatedAt)).limit(limit).all()
    
    def get_approved_topic_versions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get approved topic versions for similarity comparison."""
        approved_versions = self.db.query(TopicVersion, Topic).join(
            Topic, TopicVersion.TopicId == Topic.Id
        ).filter(
            and_(
                TopicVersion.IsActive == True,
                TopicVersion.Status == 4,  # APPROVED status
                Topic.IsActive == True
            )
        ).order_by(desc(TopicVersion.CreatedAt)).limit(limit).all()
        
        result = []
        for version, topic in approved_versions:
            result.append({
                "topic_id": topic.Id,
                "version_id": version.Id,
                "version_number": version.VersionNumber,
                "title": version.Title,
                "description": version.Description,
                "objectives": version.Objectives,
                "methodology": version.Methodology,
                "expected_outcomes": version.ExpectedOutcomes,
                "requirements": version.Requirements,
                "semester_id": topic.SemesterId,
                "category_id": topic.CategoryId,
                "supervisor_id": topic.SupervisorId,
                "status": version.Status,
                "created_at": version.CreatedAt
            })
        
        return result

    def search_topics_by_title(self, title_keywords: List[str], semester_id: Optional[int] = None) -> List[Topic]:
        """Search topics by title keywords."""
        query = self.db.query(Topic).filter(Topic.IsActive == True)
        
        # Add title search conditions
        title_conditions = []
        for keyword in title_keywords:
            title_conditions.append(Topic.Title.ilike(f"%{keyword}%"))
        
        if title_conditions:
            query = query.filter(or_(*title_conditions))
        
        # Add semester filter if provided
        if semester_id:
            query = query.filter(Topic.SemesterId == semester_id)
        
        return query.order_by(desc(Topic.CreatedAt)).limit(50).all()

    def get_approved_topic_versions_with_content(self) -> List[Dict[str, Any]]:
        """Get approved topic versions with full content for ChromaDB indexing."""
        # Get approved topic versions with their topics
        approved_versions = self.db.query(TopicVersion, Topic).join(
            Topic, TopicVersion.TopicId == Topic.Id
        ).filter(
            and_(
                TopicVersion.IsActive == True,
                TopicVersion.Status == 4,  # APPROVED status
                Topic.IsActive == True
            )
        ).order_by(desc(TopicVersion.CreatedAt)).all()
        
        result = []
        for version, topic in approved_versions:
            # Combine all text content from topic version
            content_parts = []
            
            if version.Title:
                content_parts.append(version.Title)
            if version.Description:
                content_parts.append(version.Description)
            if version.Objectives:
                content_parts.append(version.Objectives)
            if version.Methodology:
                content_parts.append(version.Methodology)
            if version.ExpectedOutcomes:
                content_parts.append(version.ExpectedOutcomes)
            if version.Requirements:
                content_parts.append(version.Requirements)
            
            full_content = " ".join(content_parts)
            
            result.append({
                "id": f"{topic.Id}_{version.Id}",  # Unique ID combining topic and version
                "title": version.Title,
                "content": full_content,
                "topic_id": topic.Id,
                "version_id": version.Id,
                "version_number": version.VersionNumber,
                "semester_id": topic.SemesterId,
                "category_id": topic.CategoryId,
                "supervisor_id": topic.SupervisorId,
                "created_at": version.CreatedAt.isoformat() if version.CreatedAt else None,
                "status": version.Status
            })
        
        return result

    def get_topics_with_content(self) -> List[Dict[str, Any]]:
        """Deprecated: Use get_approved_topic_versions_with_content instead."""
        return self.get_approved_topic_versions_with_content()

    def update_topic(self, topic_id: int, update_data: Dict[str, Any]) -> Optional[Topic]:
        """Update topic with new data."""
        topic = self.get_topic_by_id(topic_id)
        if not topic:
            return None
        
        for key, value in update_data.items():
            if hasattr(topic, key) and value is not None:
                setattr(topic, key, value)
        
        topic.LastModifiedAt = datetime.utcnow()
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def get_topic_categories(self) -> List[TopicCategory]:
        """Get all active topic categories."""
        return self.db.query(TopicCategory).filter(
            TopicCategory.IsActive == True
        ).all()

    def get_active_semesters(self) -> List[Semester]:
        """Get all active semesters."""
        return self.db.query(Semester).filter(
            Semester.IsActive == True
        ).order_by(desc(Semester.StartDate)).all()

    def get_current_semester(self) -> Optional[Semester]:
        """Get current active semester."""
        now = datetime.utcnow()
        return self.db.query(Semester).filter(
            and_(
                Semester.IsActive == True,
                Semester.StartDate <= now,
                Semester.EndDate >= now
            )
        ).first()

    def topic_exists_by_title(self, title: str, semester_id: int, exclude_id: Optional[int] = None) -> bool:
        """Check if topic with exact title exists in semester."""
        query = self.db.query(Topic).filter(
            and_(
                Topic.Title == title,
                Topic.SemesterId == semester_id,
                Topic.IsActive == True
            )
        )
        
        if exclude_id:
            query = query.filter(Topic.Id != exclude_id)
        
        return query.first() is not None
    
    def get_approved_topics_for_duplicate_check(self, semester_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get approved topics with content for duplicate checking."""
        query = self.db.query(Topic).filter(
            and_(
                Topic.IsActive == True,
                Topic.IsApproved == True
            )
        )
        
        # Filter by semester if provided
        if semester_id:
            query = query.filter(Topic.SemesterId == semester_id)
            
        topics = query.order_by(desc(Topic.CreatedAt)).limit(limit).all()
        
        result = []
        for topic in topics:
            # Get latest version
            latest_version = self.db.query(TopicVersion).filter(
                and_(
                    TopicVersion.TopicId == topic.Id,
                    TopicVersion.IsActive == True
                )
            ).order_by(desc(TopicVersion.VersionNumber)).first()
            
            # Combine all text content
            content_parts = [topic.Title or ""]
            if topic.Description:
                content_parts.append(topic.Description)
            if topic.Objectives:
                content_parts.append(topic.Objectives)
            
            if latest_version:
                if latest_version.Methodology:
                    content_parts.append(latest_version.Methodology)
                if latest_version.ExpectedOutcomes:
                    content_parts.append(latest_version.ExpectedOutcomes)
                if latest_version.Requirements:
                    content_parts.append(latest_version.Requirements)
            
            full_content = " ".join(content_parts)
            
            result.append({
                "id": str(topic.Id),
                "title": topic.Title,
                "content": full_content,
                "topic_id": topic.Id,
                "semester_id": topic.SemesterId,
                "category_id": topic.CategoryId,
                "supervisor_id": topic.SupervisorId,
                "created_at": topic.CreatedAt.isoformat() if topic.CreatedAt else None,
                "is_approved": topic.IsApproved
            })
        
        return result
    
    def get_topic_version_by_id(self, version_id: int) -> Optional[TopicVersion]:
        """Get topic version by ID."""
        return self.db.query(TopicVersion).filter(
            and_(TopicVersion.Id == version_id, TopicVersion.IsActive == True)
        ).first()
    
    def get_topic_versions_by_topic_id(self, topic_id: int) -> List[TopicVersion]:
        """Get all versions of a topic."""
        return self.db.query(TopicVersion).filter(
            and_(
                TopicVersion.TopicId == topic_id,
                TopicVersion.IsActive == True
            )
        ).order_by(desc(TopicVersion.VersionNumber)).all()
    
    def get_latest_topic_version(self, topic_id: int) -> Optional[TopicVersion]:
        """Get latest version of a topic."""
        return self.db.query(TopicVersion).filter(
            and_(
                TopicVersion.TopicId == topic_id,
                TopicVersion.IsActive == True
            )
        ).order_by(desc(TopicVersion.VersionNumber)).first()
    
    def get_approved_topic_version(self, topic_id: int) -> Optional[TopicVersion]:
        """Get approved version of a topic."""
        return self.db.query(TopicVersion).filter(
            and_(
                TopicVersion.TopicId == topic_id,
                TopicVersion.IsActive == True,
                TopicVersion.Status == 4  # APPROVED
            )
        ).order_by(desc(TopicVersion.VersionNumber)).first()
    
    def approve_topic_version(self, version_id: int) -> bool:
        """Approve a topic version."""
        try:
            version = self.get_topic_version_by_id(version_id)
            if not version:
                return False
            
            version.Status = 4  # APPROVED
            version.LastModifiedAt = datetime.utcnow()
            
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def reject_topic_version(self, version_id: int, reason: str = None) -> bool:
        """Reject a topic version."""
        try:
            version = self.get_topic_version_by_id(version_id)
            if not version:
                return False
            
            version.Status = 5  # REJECTED
            version.LastModifiedAt = datetime.utcnow()
            
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
