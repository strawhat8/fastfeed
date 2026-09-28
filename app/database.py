from collections.abc import AsyncGenerator
import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

sqlalchemy_database_url = "sqlite+aiosqlite:///./test.db"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )


class posts(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    caption: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(Text, nullable=True)
    file_type: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    )


async_engine = create_async_engine(sqlalchemy_database_url, echo=False)
async_sessionmaker = sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def create_db_and_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker() as session:
        yield session
