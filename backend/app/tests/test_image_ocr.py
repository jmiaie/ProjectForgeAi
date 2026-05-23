import unittest
from io import BytesIO
from unittest.mock import patch

from core.config import settings
from ingestion.parsers.common.image import parse_image

MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


class ImageOcrParserTests(unittest.TestCase):
    def test_image_parser_skips_ocr_when_disabled(self):
        with patch.object(settings, "IMAGE_OCR_ENABLED", False):
            parsed = parse_image(BytesIO(MINI_PNG), filename="site-photo.png")

        self.assertEqual(parsed.metadata["parser"], "image")
        self.assertEqual(parsed.metadata["chunk_count"], 0)
        self.assertFalse(parsed.metadata["ocr_used"])
        self.assertTrue(any("IMAGE_OCR_ENABLED is false" in warning for warning in parsed.warnings))

    def test_image_parser_warns_when_tesseract_missing(self):
        with patch.object(settings, "IMAGE_OCR_ENABLED", True), patch(
            "ingestion.parsers.common.image._tesseract_available",
            return_value=False,
        ):
            parsed = parse_image(BytesIO(MINI_PNG), filename="site-photo.png")

        self.assertEqual(parsed.metadata["chunk_count"], 0)
        self.assertFalse(parsed.metadata["ocr_used"])
        self.assertTrue(any("Tesseract OCR binary is not available" in warning for warning in parsed.warnings))


if __name__ == "__main__":
    unittest.main()
