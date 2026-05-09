from fastapi import UploadFile


async def parse_pdf(file: UploadFile) -> list[str]:
    content = await file.read()
    # Placeholder extraction until full parser lands.
    text = content.decode(errors="ignore")
    return [text[:2000]]
