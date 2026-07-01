import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .connection import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    experience_years = Column(Float, nullable=True)
    education = Column(String(255), nullable=True)
    raw_resume_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    skills = relationship("Skill", back_populates="candidate", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="candidate", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="candidate", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="candidate", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(100), nullable=False, index=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="skills")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    technologies = Column(String(255), nullable=True) # comma-separated list

    # Relationships
    candidate = relationship("Candidate", back_populates="projects")


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="experiences")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rankings = relationship("Ranking", back_populates="job", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="job", cascade="all, delete-orphan")


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    score_band = Column(String(50), nullable=True)
    recommendation = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True) # JSON serialized list of strings
    risks = Column(Text, nullable=True) # JSON serialized list of strings
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="rankings")
    candidate = relationship("Candidate", back_populates="rankings")


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)
    vector_type = Column(String(50), nullable=False) # e.g. 'resume', 'skills', 'experience', 'projects', 'behavior'
    embedding_vector = Column(Text, nullable=False) # JSON serialized float array

    # Relationships
    candidate = relationship("Candidate", back_populates="embeddings")
    job = relationship("Job", back_populates="embeddings")
