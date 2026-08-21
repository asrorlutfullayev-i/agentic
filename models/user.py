# models/user.py
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete")
    memory_facts: Mapped[list["MemoryFact"]] = relationship(back_populates="user", cascade="all, delete")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user", cascade="all, delete")
    summaries: Mapped[list["ConversationSummary"]] = relationship(back_populates="user", cascade="all, delete")
