"""
generate_inspection_gallery.py
==============================
Generates an interactive, responsive HTML gallery for quick visual validation
of auto-annotated Indian traffic sign images.
"""

import os
import base64
import argparse
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Custom Indian TSR Dataset Gallery</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
    h1 { margin-bottom: 8px; font-size: 26px; }
    p.subtitle { color: #94a3b8; margin-top: 0; margin-bottom: 20px; }
    .filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }
    .btn { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
    .btn:hover, .btn.active { background: #3b82f6; border-color: #60a5fa; color: #fff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
    .card { background: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155; transition: transform 0.2s; }
    .card:hover { transform: translateY(-3px); border-color: #60a5fa; }
    .card img { width: 100%; height: 180px; object-fit: cover; display: block; background: #090d16; }
    .card-info { padding: 10px; font-size: 12px; }
    .card-name { font-weight: 600; color: #38bdf8; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .card-file { color: #94a3b8; font-size: 11px; word-break: break-all; }
  </style>
  <script>
    function filterClass(cls) {
      document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      const cards = document.querySelectorAll('.card');
      cards.forEach(c => {
        if (cls === 'all' || c.getAttribute('data-class') === cls) {
          c.style.display = 'block';
        } else {
          c.style.display = 'none';
        }
      });
    }
  </script>
</head>
<body>
  <h1>Indian Traffic Sign Recognition - Annotation Gallery</h1>
  <p class="subtitle">Showing preview bounding boxes and authentic Indian street photos. Green = Detector, Orange = Contour, Red = Centered Crop.</p>
  
  <div class="filters">
    <button class="btn active" onclick="filterClass('all')">All Classes (__TOTAL_COUNT__)</button>
    __BUTTONS__
  </div>

  <div class="grid">
    __CARDS__
  </div>
</body>
</html>
"""

def generate_gallery(preview_dir: Path, output_html: Path, max_per_class: int = 25):
    if not preview_dir.exists():
        print(f"[ERROR] Preview directory '{preview_dir}' does not exist.")
        return

    images = sorted([f for f in preview_dir.glob("*.jpg")])
    if not images:
        print("[WARNING] No preview images found.")
        return

    # Group by class ID
    from collections import defaultdict
    class_images = defaultdict(list)
    for p in images:
        cid = p.name.split("_")[0]
        class_images[cid].append(p)

    buttons_html = []
    cards_html = []
    total_shown = 0

    for cid in sorted(class_images.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        imgs = class_images[cid][:max_per_class]
        btn = f'<button class="btn" onclick="filterClass(\'{cid}\')">Class {cid} ({len(class_images[cid])})</button>'
        buttons_html.append(btn)

        for img_path in imgs:
            total_shown += 1
            # Relative path to HTML
            rel_path = os.path.relpath(img_path, output_html.parent).replace("\\", "/")
            card = f"""
            <div class="card" data-class="{cid}">
              <img src="{rel_path}" loading="lazy" alt="{img_path.name}">
              <div class="card-info">
                <div class="card-name">Class {cid}</div>
                <div class="card-file">{img_path.name}</div>
              </div>
            </div>
            """
            cards_html.append(card)

    rendered = HTML_TEMPLATE.replace("__TOTAL_COUNT__", str(len(images)))
    rendered = rendered.replace("__BUTTONS__", "\n    ".join(buttons_html))
    rendered = rendered.replace("__CARDS__", "\n    ".join(cards_html))

    output_html.parent.mkdir(parents=True, exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"[SUCCESS] Inspection gallery generated at: {output_html.resolve()} ({total_shown} sample cards)")


def main():
    parser = argparse.ArgumentParser(description="Generate visual inspection HTML gallery.")
    parser.add_argument("--preview_dir", type=str, default="dataset/annotated/preview",
                        help="Path to preview images directory")
    parser.add_argument("--output_html", type=str, default="results/annotation_gallery.html",
                        help="Path for generated HTML gallery")
    parser.add_argument("--max_per_class", type=int, default=25,
                        help="Max samples per class in gallery (default: 25)")
    args = parser.parse_args()

    generate_gallery(Path(args.preview_dir), Path(args.output_html), args.max_per_class)


if __name__ == "__main__":
    main()
