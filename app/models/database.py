"""Database models and connection setup."""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import config

# Create database engine
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Topic(Base):
    """Topic model based on the database schema."""
    __tablename__ = "topics"

    Id = Column(Integer, primary_key=True, index=True)
    Title = Column(String(500), nullable=False)
    Description = Column(Text)
    Objectives = Column(Text)
    SupervisorId = Column(Integer, ForeignKey("users.Id"), nullable=False)
    CategoryId = Column(Integer, ForeignKey("topic_categories.Id"))
    SemesterId = Column(Integer, ForeignKey("semesters.Id"), nullable=False)
    MaxStudents = Column(Integer, default=1)
    IsLegacy = Column(Boolean, default=False)
    IsApproved = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    LastModifiedAt = Column(DateTime)
    IsActive = Column(Boolean, default=False)

    # Relationships
    versions = relationship("TopicVersion", back_populates="topic")
    submissions = relationship("Submission", back_populates="topic")

class TopicVersion(Base):
    """Topic version model."""
    __tablename__ = "topic_versions"

    Id = Column(Integer, primary_key=True, index=True)
    TopicId = Column(Integer, ForeignKey("topics.Id"), nullable=False)
    VersionNumber = Column(Integer, nullable=False)
    Title = Column(String(500), nullable=False)
    Description = Column(Text)
    Objectives = Column(Text)
    Methodology = Column(Text)
    ExpectedOutcomes = Column(Text)
    Requirements = Column(Text)
    DocumentUrl = Column(String(500))
    Status = Column(Integer, default=1)
    SubmittedAt = Column(DateTime)
    SubmittedBy = Column(Integer, ForeignKey("users.Id"))
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive = Column(Boolean, default=False)

    # Relationships
    topic = relationship("Topic", back_populates="versions")

class TopicCategory(Base):
    """Topic category model."""
    __tablename__ = "topic_categories"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(100), nullable=False)
    Description = Column(Text)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive = Column(Boolean, default=False)

class Semester(Base):
    """Semester model."""
    __tablename__ = "semesters"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(50), nullable=False, unique=True)
    StartDate = Column(DateTime, nullable=False)
    EndDate = Column(DateTime, nullable=False)
    IsActive = Column(Boolean, nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    Description = Column(Text)

class User(Base):
    """User model."""
    __tablename__ = "users"

    Id = Column(Integer, primary_key=True, index=True)
    UserName = Column(String)
    Email = Column(String)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    LastModifiedAt = Column(DateTime)

class Submission(Base):
    """Submission model."""
    __tablename__ = "submissions"

    Id = Column(Integer, primary_key=True, index=True)
    TopicVersionId = Column(Integer, ForeignKey("topic_versions.Id"))
    TopicId = Column(Integer, ForeignKey("topics.Id"), nullable=False)
    PhaseId = Column(Integer, ForeignKey("phases.Id"), nullable=False)
    SubmittedBy = Column(Integer, ForeignKey("users.Id"), nullable=False)
    SubmissionRound = Column(Integer, default=1)
    DocumentUrl = Column(String(500))
    AdditionalNotes = Column(Text)
    AiCheckStatus = Column(Integer, default=1)
    AiCheckScore = Column(Numeric(5, 2))
    AiCheckDetails = Column(Text)
    Status = Column(Integer, default=1)
    SubmittedAt = Column(DateTime)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive = Column(Boolean, default=False)

    # Relationships
    topic = relationship("Topic", back_populates="submissions")

class Phase(Base):
    """Phase model."""
    __tablename__ = "phases"

    Id = Column(Integer, primary_key=True, index=True)
    SemesterId = Column(Integer, ForeignKey("semesters.Id"), nullable=False)
    PhaseTypeId = Column(Integer, ForeignKey("phase_types.Id"), nullable=False)
    Name = Column(String(100), nullable=False)
    StartDate = Column(DateTime, nullable=False)
    EndDate = Column(DateTime, nullable=False)
    SubmissionDeadline = Column(DateTime)
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow)

class PhaseType(Base):
    """Phase type model."""
    __tablename__ = "phase_types"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(50), nullable=False)
    Description = Column(Text)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive = Column(Boolean, default=False)

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

