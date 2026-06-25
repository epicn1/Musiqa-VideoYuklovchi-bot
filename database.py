import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, select, text
from datetime import datetime

load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://postgres:1@localhost/musiqabot")

engine = create_async_engine(DB_URL, echo=False, pool_size=20, max_overflow=50)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    language = Column(String(5), default="uz")
    request_count = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        # Jadval yo'q bo'lsa yaratish
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS request_count INTEGER DEFAULT 0"))

async def get_user(user_id: int):
    async with AsyncSessionLocal() as session:
        return await session.get(User, user_id)

async def create_user(user_id: int, language: str = "uz"):
    async with AsyncSessionLocal() as session:
        user = User(id=user_id, language=language)
        session.add(user)
        try:
            await session.commit()
            return user
        except Exception:
            await session.rollback()
            return await get_user(user_id)

async def increment_user_requests(user_id: int):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, language="uz", request_count=0)
            session.add(user)
        user.request_count = (user.request_count or 0) + 1
        await session.commit()
        return user.request_count

async def get_all_user_ids():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.id))
        return [row[0] for row in result.all()]

async def update_user_language(user_id: int, language: str):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            user.language = language
            await session.commit()
        else:
            await create_user(user_id, language)
