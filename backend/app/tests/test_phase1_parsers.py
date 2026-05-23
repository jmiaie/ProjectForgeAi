import tempfile
import unittest
import zipfile
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

from ingestion.parsers.common.email import parse_email
from ingestion.parsers.common.image import parse_image
from ingestion.parsers.common.office import parse_office


class Phase1ParserTests(unittest.TestCase):
    def test_email_parser_extracts_body_and_headers(self):
        message = EmailMessage()
        message["Subject"] = "Kickoff"
        message["From"] = "owner@example.com"
        message["To"] = "pm@example.com"
        message["Message-ID"] = "<projectforge-test@example.com>"
        message.set_content("Project kickoff is approved.\nPlease prepare the schedule.")

        parsed = parse_email(BytesIO(message.as_bytes()), filename="kickoff.eml")

        self.assertEqual(parsed.metadata["parser"], "email")
        self.assertEqual(parsed.metadata["subject"], "Kickoff")
        self.assertEqual(parsed.metadata["chunk_count"], 1)
        self.assertIn("Project kickoff is approved", parsed.chunks[0].text)
        self.assertEqual(parsed.warnings, [])

    def test_office_parser_extracts_docx_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "scope.docx"
            with zipfile.ZipFile(docx_path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    (
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                        "<w:body><w:p><w:r><w:t>Scope baseline approved</w:t></w:r></w:p></w:body>"
                        "</w:document>"
                    ),
                )

            parsed = parse_office(docx_path)

            self.assertEqual(parsed.metadata["parser"], "office")
            self.assertEqual(parsed.metadata["file_type"], "docx")
            self.assertEqual(parsed.metadata["chunk_count"], 1)
            self.assertIn("Scope baseline approved", parsed.chunks[0].text)

    def test_image_parser_records_metadata_warning_without_ocr(self):
        parsed = parse_image(BytesIO(b"not-a-real-image"), filename="site-photo.png")

        self.assertEqual(parsed.metadata["parser"], "image")
        self.assertEqual(parsed.metadata["source"], "site-photo.png")
        self.assertEqual(parsed.metadata["chunk_count"], 0)
        self.assertFalse(parsed.metadata["ocr_used"])
        self.assertTrue(
            any(
                phrase in warning
                for warning in parsed.warnings
                for phrase in (
                    "OCR is not configured",
                    "Tesseract OCR binary is not available",
                    "image parsing failed",
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
