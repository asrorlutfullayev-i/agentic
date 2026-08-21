# services/tools/github_search.py
import aiohttp
from config import GITHUB_TOKEN


async def github_search(query: str, search_type: str = "repositories") -> str:
    """GitHub API orqali repo yoki kod qidirish."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    url = f"https://api.github.com/search/{search_type}?q={query}&per_page=5&sort=stars"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            return "GitHub'da hech narsa topilmadi."

        lines = [f"?? **GitHub qidiruv: {query}**\n"]
        for r in items:
            lines.append(f"**{r['full_name']}** ? {r.get('stargazers_count', 0):,}")
            lines.append(f"?? {r.get('description', 'Tavsif yo\'q')}")
            lines.append(f"?? {r['html_url']}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"GitHub qidiruv xatosi: {e}"
