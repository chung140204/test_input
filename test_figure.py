# test_figure.py — Test FIGURE detection dùng PyMuPDF
import fitz
from pathlib import Path

OUT_DIR = Path('output/figures')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (tên, trang, y_start, y_end) — pixel coords tại 200 DPI
CASES = [
    ('cau5_do_thi_ham_so',       'input/page_1.png', 1650, 2050),
    ('cau11_hinh_hop',           'input/page_2.png',  814, 1021),
    ('cau12_do_thi_dong_bien',   'input/page_2.png', 1021, 1360),
]

SCALE = 72 / 200  # 200-DPI pixels → PDF points

def page_idx(page_path):
    return int(Path(page_path).stem.split('_')[1]) - 1

def main():
    doc = fitz.open('input/de-toan.pdf')
    summary = []

    for name, page_path, y0, y1 in CASES:
        page = doc[page_idx(page_path)]
        W = page.rect.width
        clip = fitz.Rect(0, y0 * SCALE, W, y1 * SCALE)

        # Lưu crop để kiểm tra bằng mắt
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        pix.save(str(OUT_DIR / f"{name}_crop.png"))

        # Tìm hình ảnh nhúng trong vùng này
        figures = []
        for img in page.get_images(full=True):
            xref = img[0]
            rects = page.get_image_rects(xref)
            for rect in rects:
                # Kiểm tra overlap với vùng clip
                if rect.y1 > y0 * SCALE and rect.y0 < y1 * SCALE:
                    figures.append((xref, rect))

        print(f"{'='*55}")
        print(f"  {name}")
        print(f"{'='*55}")
        print(f"  Crop saved   : output/figures/{name}_crop.png")
        print(f"  Figures found: {len(figures)}")

        for i, (xref, rect) in enumerate(figures):
            img_data = doc.extract_image(xref)
            ext = img_data['ext']
            fname = OUT_DIR / f"{name}_fig_{i}.{ext}"
            fname.write_bytes(img_data['image'])
            print(f"  → Figure {i}: bbox={tuple(round(v,1) for v in rect)} → {fname.name}")

        summary.append((name, len(figures)))
        print()

    print("="*55)
    print("  TỔNG KẾT")
    print("="*55)
    for name, count in summary:
        status = "✅" if count > 0 else "❌ miss"
        print(f"  {status}  {name}: {count} figure(s)")

if __name__ == '__main__':
    main()
