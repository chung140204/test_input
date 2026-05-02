# setup.py — Bước 1: Convert PDF → page images (dùng PyMuPDF)
import fitz  # pymupdf
from pathlib import Path

PDF_PATH = 'input/de-toan.pdf'
OUT_DIR  = Path('input')

def main():
    print(f"Converting {PDF_PATH}...")
    doc = fitz.open(PDF_PATH)

    for i, page in enumerate(doc):
        mat = fitz.Matrix(200 / 72, 200 / 72)  # 200 DPI
        pix = page.get_pixmap(matrix=mat)
        out = OUT_DIR / f"page_{i+1}.png"
        pix.save(str(out))
        print(f"  Saved page_{i+1}.png — size=({pix.width}, {pix.height})")

    print(f"\nDone! {len(doc)} pages saved to {OUT_DIR}/")

if __name__ == '__main__':
    main()
