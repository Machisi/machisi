"""Keep GitHub's contribution days visible under the animated snake."""

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
calendar_style = (
    '<style>:root{--c1:#0e4429;--c2:#006d32;--c3:#26a641;--c4:#39d353}'
    'rect.c{animation:none!important}</style>'
)
svg = svg[: opening.end()] + background + svg[opening.end() :]
style_end = svg.find("</style>", opening.end())
if style_end < 0:
    raise ValueError("Snake SVG has no animation styles")
style_end += len("</style>")
svg = svg[:style_end] + calendar_style + svg[style_end:]
path.write_text(svg, encoding="utf-8")
