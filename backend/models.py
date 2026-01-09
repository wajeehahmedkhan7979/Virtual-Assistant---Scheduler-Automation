"""
SQLAlchemy ORM models for the application.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    email_accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")
    email_jobs = relationship("EmailJob", back_populates="user", cascade="all, delete-orphan")
    rules = relationship("AutoReplyRule", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("ScheduledTask", back_populates="user", cascade="all, delete-orphan")
    data_analysis_jobs = relationship("DataAnalysisJob", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_user_email", "email"),)


class EmailAccount(Base):
    """Email account connected via OAuth2."""
    __tablename__ = "email_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # gmail, outlook, etc.
    email = Column(String, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="email_accounts")
    email_jobs = relationship("EmailJob", back_populates="email_account")

    __table_args__ = (
        Index("idx_email_account_user", "user_id"),
        Index("idx_email_account_provider", "provider"),
    )


class EmailJob(Base):
    """Email processing job (inbox management)."""
    __tablename__ = "email_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_account_id = Column(String, ForeignKey("email_accounts.id"), nullable=False)
    email_id = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    classification = Column(String, nullable=True)  # important, spam, followup, etc.
    classification_confidence = Column(Integer, nullable=True)  # 0-100 confidence score (stored as int percentage)
    classification_explanation = Column(Text, nullable=True)  # Explanation of classification
    is_flagged = Column(Boolean, default=False)
    auto_reply_sent = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    classified_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="email_jobs")
    email_account = relationship("EmailAccount", back_populates="email_jobs")

    __table_args__ = (
        Index("idx_email_job_user", "user_id"),
        Index("idx_email_job_processed", "is_processed"),
        Index("idx_email_job_classification", "classification"),
    )


class AutoReplyRule(Base):
    """Rules for auto-reply emails."""
    __tablename__ = "auto_reply_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rule_config = Column(JSON, nullable=False)  # { "conditions": [...], "actions": [...] }
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="rules")

    __table_args__ = (Index("idx_auto_reply_rule_user", "user_id"),)


class ScheduledTask(Base):
    """Scheduled background tasks."""
    __tablename__ = "scheduled_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String, nullable=False)  # email_sync, data_analysis, etc.
    schedule = Column(String, nullable=False)  # cron expression or interval
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    task_metadata = Column(JSON, nullable=True)  # Task-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")

    __table_args__ = (
        Index("idx_scheduled_task_user", "user_id"),
        Index("idx_scheduled_task_type", "task_type"),
    )


class DataAnalysisJob(Base):
    """Data analysis jobs (on-demand)."""
    __tablename__ = "data_analysis_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)  # S3 path
    analysis_type = Column(String, nullable=False)  # summary, insights, forecast, etc.
    prompt = Column(Text, nullable=False)  # User's analysis request
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result = Column(Text, nullable=True)  # Analysis result
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="data_analysis_jobs")

    __table_args__ = (
        Index("idx_data_analysis_job_user", "user_id"),
        Index("idx_data_analysis_job_status", "status"),
    )
