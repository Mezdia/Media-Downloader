import os
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL
DATABASE_URL = "sqlite+aiosqlite:///./bot_database.db"

# Create Async Engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session Local
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    joined_date = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    language = Column(String, default="fa")

class Variable(Base):
    """
    Key-Value store for bot settings and dynamic texts.
    """
    __tablename__ = "variables"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(String, nullable=True)

class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  # Telegram ID
    link = Column(String)
    media_type = Column(String)  # video, audio, playlist, instagram_post, etc.
    title = Column(String, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    download_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="completed")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
