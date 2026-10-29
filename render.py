#!/usr/bin/env python3
"""Render Verwood CC social graphics (1080x1350 PNG) from a JSON data file.

Usage:  python3 render.py data/results.json [out_dir]

JSON "kind" is one of: results, fixtures, match (see data/sample_*.json).
Lists longer than ROWS_PER_PAGE become several images (an Instagram carousel).
Uses assets/badge.png if present, otherwise the stand-in assets/badge.svg.
"""
import base64, json, math, sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
ROWS_PER_PAGE = 6


def badge_uri():
    png, svg = ROOT / "assets/badge.png", ROOT / "assets/badge.svg"
    if png.exists():
        return "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()
    return "data:image/svg+xml;base64," + base64.b64encode(svg.read_bytes()).decode()


FONT_WEIGHTS = {"Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}


def font_css():
    """Embed the bundled Inter Display files so rendering never falls back to a serif."""
    rules = []
    for name, weight in FONT_WEIGHTS.items():
        f = ROOT / f"assets/fonts/InterDisplay-{name}.otf"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            rules.append(f'@font-face{{font-family:"VCC";font-weight:{weight};'
                         f'src:url(data:font/otf;base64,{b64}) format("opentype");}}')
    return "\n".join(rules)


def build_pages(data):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    common = {"css": font_css() + (ROOT / "templates/base.css").read_text(), "badge": badge_uri()}
    if data["kind"] == "match":
        return [env.get_template("match.html").render(m=data, **common)]
    rows = data["matches"]
    if not rows:
        return []
    pages = math.ceil(len(rows) / ROWS_PER_PAGE)
    per = math.ceil(len(rows) / pages)  # spread rows evenly across pages
    tpl = env.get_template("list.html")
    return [tpl.render(kind=data["kind"], title=data["title"], date_range=data["date_range"],
                       rows=rows[i * per:(i + 1) * per], page=i + 1, pages=pages, **common)
            for i in range(pages)]


def render(json_path, out_dir=None):
    data = json.loads(Path(json_path).read_text())
    out = Path(out_dir or ROOT / "out"); out.mkdir(parents=True, exist_ok=True)
    stem = Path(json_path).stem
    files = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(build_pages(data), 1):
            page.set_content(html, wait_until="load")
            f = out / (f"{stem}.png" if i == 1 and data["kind"] == "match" else f"{stem}_{i}.png")
            page.screenshot(path=str(f), clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            files.append(str(f))
        browser.close()
    return files


if __name__ == "__main__":
    for f in render(*sys.argv[1:3]):
        print(f)
