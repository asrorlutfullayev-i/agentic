# services/tools/web_search.py
from duckduckgo_search import DDGS


async def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo orqali web qidirish."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "Hech narsa topilmadi."
        lines = [f"?? **Qidiruv natijalari: {query}**\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"**{i}. {r.get('title', '')}**")
            lines.append(f"?? {r.get('body', '')[:200]}...")
            lines.append(f"?? {r.get('href', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Qidiruv xatosi: {e}"


async def image_search(query: str, max_results: int = 5) -> list[dict]:
    """Rasm qidirish."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=max_results))
        return [{"title": r.get("title"), "url": r.get("image"), "source": r.get("url")} for r in results]
    except Exception as e:
        return []
