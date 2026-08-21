# services/tools/arxiv_search.py
import aiohttp
import xml.etree.ElementTree as ET


async def arxiv_search(query: str, max_results: int = 5) -> str:
    """ArXiv API orqali ilmiy maqola qidirish."""
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{query.replace(' ', '+')}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=relevance&sortOrder=descending"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                xml_data = await resp.text()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        if not entries:
            return "ArXiv'da maqola topilmadi."

        lines = [f"?? **ArXiv maqolalari: {query}**\n"]
        for e in entries:
            title = e.find("atom:title", ns).text.strip()
            summary = e.find("atom:summary", ns).text.strip()[:200]
            link = e.find("atom:id", ns).text.strip()
            lines.append(f"**{title}**")
            lines.append(f"?? {summary}...")
            lines.append(f"?? {link}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"ArXiv qidiruv xatosi: {e}"
