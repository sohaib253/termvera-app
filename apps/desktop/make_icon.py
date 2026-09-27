"""Draw the Termvera icon as multi-size .ico files.

Same geometry as the web mark (apps/web/components/brand/logo.tsx): a T and
V monogram on an indigo tile, the white bar the T, the teal stroke both the
V and a check mark. Drawn at 1024px and downsampled so the small sizes
(16/24/32px, taskbar and tab) stay clean.

Usage: python make_icon.py <out.ico> [<another.ico> ...]
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
U = S / 32  # the web mark's 32-unit grid


def p(x: float, y: float) -> tuple[float, float]:
    return (x * U, y * U)


def draw() -> Image.Image:
    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Tile: diagonal indigo gradient, rounded square.
    gradient = Image.new("RGBA", (S, S))
    top, bottom = (91, 91, 240), (46, 42, 156)
    shade = ImageDraw.Draw(gradient)
    for y in range(S):
        t = y / (S - 1)
        colour = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        shade.line([(0, y), (S, y)], fill=colour)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(8.5 * U), fill=255)
    image.paste(gradient, (0, 0), mask)

    d = ImageDraw.Draw(image)
    # The T: a white bar with round ends.
    d.rounded_rectangle([*p(7, 7.2), *p(25, 11.4)], radius=int(2.1 * U), fill=(255, 255, 255, 255))
    # The V / check.
    teal = (45, 212, 191, 255)
    points = [p(13.9, 11.2), p(16.2, 23.2), p(23.6, 13.8)]
    d.line(points, fill=teal, width=int(3.8 * U), joint="curve")
    r = 1.9 * U
    for x, y in (points[0], points[2]):  # round caps
        d.ellipse([x - r, y - r, x + r, y + r], fill=teal)
    return image


if __name__ == "__main__":
    targets = [Path(a) for a in sys.argv[1:]] or [Path(__file__).with_name("termvera.ico")]
    icon = draw()
    for target in targets:
        icon.save(target, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"Wrote {target}")
