"""Prints real PyMuPDF-extracted text per page for the sample demo PDFs.

Use this after regenerating sample_data/*.pdf (see generate_sample_data.py)
to re-verify that every excerpt in app/services/demo_fixtures.py still
appears verbatim in the source text.
"""

from pathlib import Path

import fitz

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

if __name__ == "__main__":
    for path in sorted(SAMPLE_DIR.glob("*.pdf")):
        doc = fitz.open(path)
        print(f"===== {path.name} (pages: {doc.page_count}) =====")
        for i in range(doc.page_count):
            print(f"--- page {i + 1} ---")
            print(doc.load_page(i).get_text())
        doc.close()
