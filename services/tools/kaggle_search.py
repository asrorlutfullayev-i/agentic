# services/tools/kaggle_search.py
import aiohttp


async def kaggle_search(query: str) -> str:
    """HuggingFace Datasets (tekin, API keysiz) orqali dataset qidirish."""
    url = f"https://huggingface.co/api/datasets?search={query}&limit=5"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if not data:
            return "Dataset topilmadi."

        lines = [f"?? **Dataset qidiruv: {query}**\n"]
        for d in data[:5]:
            name = d.get("id", "Noma'lum")
            downloads = d.get("downloads", 0)
            lines.append(f"**{name}** ?? {downloads:,} yuklab olish")
            lines.append(f"?? https://huggingface.co/datasets/{name}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Dataset qidiruv xatosi: {e}"
