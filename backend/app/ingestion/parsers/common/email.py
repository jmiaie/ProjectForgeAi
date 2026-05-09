from fastapi import UploadFile


async def parse_email(file: UploadFile) -> list[str]:
    content = await file.read()
    text = content.decode(errors="ignore")
    if not text:
        return [f"email:{file.filename}:empty"]
    return [text[:4000]]
