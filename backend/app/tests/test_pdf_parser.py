import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from ingestion.parsers.common.pdf import _chunk_text, parse_pdf
from pypdf import PdfWriter


class PdfParserTests(unittest.TestCase):
    def test_parse_blank_pdf_records_metadata_and_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "blank.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with pdf_path.open("wb") as handle:
                writer.write(handle)

            parsed = parse_pdf(pdf_path)

            self.assertEqual(parsed.source, str(pdf_path))
            self.assertEqual(parsed.metadata["parser"], "pdf")
            self.assertEqual(parsed.metadata["page_count"], 1)
            self.assertEqual(parsed.metadata["chunk_count"], 0)
            self.assertEqual(parsed.chunks, [])
            self.assertIn("Page 1: no extractable text", parsed.warnings)

    def test_parse_binary_stream_uses_provided_filename(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        stream = BytesIO()
        writer.write(stream)
        stream.seek(0)

        parsed = parse_pdf(stream, filename="upload.pdf")

        self.assertEqual(parsed.source, "upload.pdf")
        self.assertEqual(parsed.metadata["source"], "upload.pdf")
        self.assertEqual(parsed.metadata["page_count"], 1)

    def test_chunk_text_uses_overlap(self):
        chunks = _chunk_text("abcdefghij", chunk_size=4, chunk_overlap=1)

        self.assertEqual(chunks, ["abcd", "defg", "ghij"])


if __name__ == "__main__":
    unittest.main()
