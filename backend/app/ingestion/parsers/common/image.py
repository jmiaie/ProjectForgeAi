from fastapi import UploadFile


async def parse_image(file: UploadFile) -> list[str]:
    content = await file.read()
    # OCR integration placeholder.
    return [
        "\n".join(
            [
                f"image:{file.filename}",
                f"content_type:{file.content_type or 'unknown'}",
                f"byte_size:{len(content)}",
            ]
        )
    ]
