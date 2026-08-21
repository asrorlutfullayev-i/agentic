# services/memory_manager.py — Xotira shifrlash va boshqaruv
from cryptography.fernet import Fernet
from config import ENCRYPTION_KEY
from services import db


class MemoryManager:
    def __init__(self):
        key = ENCRYPTION_KEY.encode() if ENCRYPTION_KEY else Fernet.generate_key()
        self.fernet = Fernet(key)

    def encrypt(self, text: str) -> str:
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            return "[o'qib bo'lmadi]"

    async def remember(self, user_id: int, category: str, fact: str) -> int:
        """Yangi fakt saqlash."""
        encrypted = self.encrypt(fact)
        result = await db.add_memory(user_id, category, encrypted)
        return result.id

    async def recall(self, user_id: int, category: str = None) -> list[dict]:
        """Barcha faktlarni o'qish."""
        facts = await db.get_memories(user_id, category)
        return [
            {
                "id": f.id,
                "category": f.category,
                "fact": self.decrypt(f.encrypted_fact),
                "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for f in facts
        ]

    async def forget(self, memory_id: int, user_id: int) -> bool:
        """Faktni o'chirish."""
        return await db.delete_memory(memory_id, user_id)

    async def format_for_context(self, user_id: int) -> str:
        """LLM uchun xotira kontekstini tayyorlash."""
        facts = await self.recall(user_id)
        if not facts:
            return ""
        lines = ["[Foydalanuvchi haqidagi muhim ma'lumotlar:]"]
        for f in facts[:20]:  # Max 20 ta fakt
            lines.append(f"  [{f['category']}] {f['fact']}")
        return "\n".join(lines)


memory_manager = MemoryManager()
