"""Give the generated snake the dark background seen in the reference video."""

import re
from pathlib import Path


path = Path("assets/contribution-snake.svg")
svg = path.read_text(encoding="utf-8")
opening = re.match(r'<svg\b[^>]*>', svg)
if opening is None:
    raise ValueError("Snake generator did not produce an SVG")
view_box = re.search(r'\bviewBox="([^"]+)"', opening.group())
if view_box is None:
    raise ValueError("Snake SVG has no viewBox")
x, y, width, height = view_box.group(1).split()
background = (
    f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
    'fill="#0d1117"/>'
)
svg = svg[: opening.end()] + background + svg[opening.end() :]
path.write_text(svg, encoding="utf-8")
