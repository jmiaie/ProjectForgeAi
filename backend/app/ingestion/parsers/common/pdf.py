from io import BytesIO

from fastapi import UploadFile


def _chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, 0)
    return chunks


async def parse_pdf(file: UploadFile) -> list[str]:
    content = await file.read()
    if not content:
        return []

    extracted_text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
        extracted_text = "\n".join([value for value in page_text if value])
    except Exception:
        # If PDF parsing fails, keep ingestion resilient with a lossy text fallback.
        extracted_text = content.decode(errors="ignore")

    chunks = _chunk_text(extracted_text)
    if chunks:
        return chunks
    return [f"pdf:{file.filename}:no-extractable-text"]
