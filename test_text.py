# test_text.py — Test TEXT extraction dùng PyMuPDF
import fitz
from pathlib import Path

OUT_DIR = Path('output/text')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (tên, trang, y_start, y_end) — pixel coords tại 200 DPI
CASES = [
    ('cau1_nguyen_ham',    'input/page_1.png',  430,  620),
    ('cau2_the_tich',      'input/page_1.png',  590,  910),
    ('cau4_duong_thang',   'input/page_1.png', 1361, 1693),
]

SCALE = 72 / 200  # 200-DPI pixels → PDF points

def page_idx(page_path):
    return int(Path(page_path).stem.split('_')[1]) - 1

def main():
    doc = fitz.open('input/de-toan.pdf')

    for name, page_path, y0, y1 in CASES:
        page = doc[page_idx(page_path)]
        W = page.rect.width
        clip = fitz.Rect(0, y0 * SCALE, W, y1 * SCALE)

        # Lưu ảnh crop để kiểm tra bằng mắt
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        pix.save(str(OUT_DIR / f"{name}_crop.png"))

        # Extract text
        text = page.get_text(clip=clip)
        out_file = OUT_DIR / f"{name}.txt"
        out_file.write_text(text, encoding='utf-8')

        print(f"{'='*55}")
        print(f"  {name}")
        print(f"{'='*55}")
        print(text[:300] or '(không extract được text — có thể là ảnh scan)')
        print(f"\n  Có ký tự toán : {'$' in text or '∫' in text or '√' in text}")
        print(f"  Saved text   : {out_file}")
        print()

if __name__ == '__main__':
    main()
