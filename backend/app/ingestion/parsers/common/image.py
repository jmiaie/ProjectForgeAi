from fastapi import UploadFile


async def parse_image(file: UploadFile) -> list[str]:
    # OCR integration placeholder.
    return [f"image:{file.filename}"]
