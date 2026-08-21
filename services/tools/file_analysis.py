# services/tools/file_analysis.py — PDF, TXT, DOCX tahlili
import io


async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Fayl turini aniqlash va matn ajratib olish."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".txt") or filename_lower.endswith(".md"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")

    elif filename_lower.endswith(".pdf"):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:10000] or "PDF bo'sh yoki matn ajratib bo'lmadi."
        except Exception as e:
            return f"PDF o'qishda xato: {e}"

    elif filename_lower.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)[:10000]
        except Exception as e:
            return f"DOCX o'qishda xato: {e}"

    else:
        return f"'{filename}' fayl turi qo'llab-quvvatlanmaydi. Qabul qilinadi: .pdf, .txt, .md, .docx"
