"""Database ORM models."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, JSON, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentforge.db.base import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String(50), default='free')
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    agents = relationship('Agent', back_populates='owner', cascade='all, delete-orphan')
    tasks = relationship('Task', back_populates='owner', cascade='all, delete-orphan')

class Agent(Base):
    __tablename__ = 'agents'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    framework: Mapped[str] = mapped_column(String(100), default='native')
    system_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(100), default='gpt-4o')
    skills: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner = relationship('User', back_populates='agents')
    tasks = relationship('Task', back_populates='agent', cascade='all, delete-orphan')

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('agents.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='pending')
    skills_used: Mapped[list] = mapped_column(JSON, default=list)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    metadata_: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    owner = relationship('User', back_populates='tasks')
    agent = relationship('Agent', back_populates='tasks')
