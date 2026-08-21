# services/tools/web_search.py — Real-time Web Search Engine
import httpx
import bs4
import urllib.parse


async def web_search(query: str, max_results: int = 5) -> str:
    """Jonli internetdan real-vaqt ma'lumotlarini qidirish."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://html.duckduckgo.com/html/"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(url, data={"q": query}, headers=headers)
            soup = bs4.BeautifulSoup(resp.text, "html.parser")

        titles = soup.select(".result__title")
        snippets = soup.select(".result__snippet")
        urls = soup.select(".result__url")

        if not titles:
            return f"'{query}' bo'yicha internetda aniq natija topilmadi."

        lines = [f"🌐 **Internetdan topilgan so'nggi ma'lumotlar ({query}):**\n"]
        for i in range(min(max_results, len(titles))):
            t = titles[i].get_text(strip=True)
            s = snippets[i].get_text(strip=True) if i < len(snippets) else ""
            u = urls[i].get_text(strip=True) if i < len(urls) else ""
            lines.append(f"**{i+1}. {t}**")
            if s:
                lines.append(f"📌 {s}")
            if u:
                lines.append(f"🔗 https://{u.strip()}\n")

        return "\n".join(lines)
    except Exception as e:
        return f"Qidiruvda xatolik: {e}"


async def search_and_augment(query: str) -> str:
    """LLM konteksti uchun real-vaqt qidiruv xulosasi."""
    res = await web_search(query, max_results=3)
    return f"[JONLI INTERNET QIDIRUV NATIJALARI - 2026-YIL]:\n{res}\n"