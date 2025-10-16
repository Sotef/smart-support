from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import Base

class UserRole(str, Enum):
    client = "client"
    operator = "operator"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    corporate_code = Column(String(32), unique=True, nullable=True)
    operator_number = Column(Integer, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SessionStatus(str, Enum):
    open = "open"
    pending = "pending"
    resolved = "resolved"
    closed = "closed"

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.open, index=True)
    language = Column(String(10), default="ru")
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

class SenderType(str, Enum):
    client = "client"
    operator = "operator"
    bot = "bot"
    system = "system"

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True, nullable=False)
    sender_type = Column(SQLEnum(SenderType), nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)

class LogEntry(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)