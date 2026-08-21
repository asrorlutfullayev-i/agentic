# services/db.py — Database connection va CRUD operatsiyalar
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, delete
from config import DATABASE_URL
from models.base import Base
from models.user import User
from models.conversation import Conversation, ConversationSummary
from models.memory import MemoryFact
from models.reminder import Reminder

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# --- USER CRUD ---
async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


# --- CONVERSATION CRUD ---
async def save_message(user_id: int, role: str, content: str) -> None:
    async with AsyncSessionLocal() as session:
        msg = Conversation(user_id=user_id, role=role, content=content)
        session.add(msg)
        await session.commit()


async def get_recent_messages(user_id: int, limit: int = 10) -> list[Conversation]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))


async def clear_history(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Conversation).where(Conversation.user_id == user_id))
        await session.commit()


# --- SUMMARY CRUD ---
async def save_summary(user_id: int, summary: str, last_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ConversationSummary).where(ConversationSummary.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.summary_text = summary
            existing.last_processed_id = last_id
            existing.updated_at = datetime.utcnow()
        else:
            session.add(ConversationSummary(user_id=user_id, summary_text=summary, last_processed_id=last_id))
        await session.commit()


async def get_summary(user_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ConversationSummary).where(ConversationSummary.user_id == user_id)
        )
        s = result.scalar_one_or_none()
        return s.summary_text if s else None


# --- MEMORY CRUD ---
async def add_memory(user_id: int, category: str, encrypted_fact: str) -> MemoryFact:
    async with AsyncSessionLocal() as session:
        fact = MemoryFact(user_id=user_id, category=category, encrypted_fact=encrypted_fact)
        session.add(fact)
        await session.commit()
        await session.refresh(fact)
        return fact


async def get_memories(user_id: int, category: str = None) -> list[MemoryFact]:
    async with AsyncSessionLocal() as session:
        q = select(MemoryFact).where(MemoryFact.user_id == user_id)
        if category:
            q = q.where(MemoryFact.category == category)
        result = await session.execute(q.order_by(MemoryFact.created_at.desc()))
        return result.scalars().all()


async def delete_memory(memory_id: int, user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemoryFact).where(MemoryFact.id == memory_id, MemoryFact.user_id == user_id)
        )
        fact = result.scalar_one_or_none()
        if fact:
            await session.delete(fact)
            await session.commit()
            return True
        return False


# --- REMINDER CRUD (Eslatmalar foydalanuvchi ma'lumotlari bilan yuklanadi) ---
async def add_reminder(user_id: int, title: str, remind_at: datetime) -> Reminder:
    async with AsyncSessionLocal() as session:
        r = Reminder(user_id=user_id, title=title, remind_at=remind_at)
        session.add(r)
        await session.commit()
        await session.refresh(r)
        return r


async def get_pending_reminders(user_id: int) -> list[Reminder]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.status == "pending")
            .order_by(Reminder.remind_at)
        )
        return result.scalars().all()


async def get_all_pending_reminders() -> list[Reminder]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder)
            .options(selectinload(Reminder.user))
            .where(Reminder.status == "pending")
            .order_by(Reminder.remind_at)
        )
        return list(result.scalars().all())


async def mark_reminder_sent(reminder_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reminder).where(Reminder.id == reminder_id))
        r = result.scalar_one_or_none()
        if r:
            r.status = "sent"
            await session.commit()


async def cancel_reminder(reminder_id: int, user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        )
        r = result.scalar_one_or_none()
        if r:
            r.status = "cancelled"
            await session.commit()
            return True
        return False