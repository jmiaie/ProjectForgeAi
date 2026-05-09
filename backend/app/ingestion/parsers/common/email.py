from fastapi import UploadFile


async def parse_email(file: UploadFile) -> list[str]:
    content = await file.read()
    return [content.decode(errors="ignore")[:2000]]
