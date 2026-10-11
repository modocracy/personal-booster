"""Draw assets/icon.png: a booster-style yellow hexagon with a blocky gift box.

Coordinates are in a 225-unit grid matching the game's booster icon; the image is
drawn 8x larger and scaled down for smooth edges.
"""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "icon.png")
SIZE = 512
GRID = 225
SCALE = 8
YELLOW = (255, 223, 33, 255)
DARK = (41, 44, 41, 255)

HEXAGON = [(59, 23), (165, 23), (217, 112), (165, 201), (59, 201), (7, 112)]


def main():
    big = GRID * SCALE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def s(points):
        return [(x * SCALE, y * SCALE) for x, y in points]

    dx, dy = -5, -3  # centres the drawing in the hexagon

    def rect(x0, y0, x1, y1, fill):
        draw.rectangle([(x0 + dx) * SCALE, (y0 + dy) * SCALE,
                        (x1 + dx) * SCALE - 1, (y1 + dy) * SCALE - 1], fill=fill)

    draw.polygon(s(HEXAGON), fill=YELLOW)

    # Layered bracket behind the box, as on the game's icon.
    rect(64, 98, 70, 166, DARK)
    rect(64, 98, 71, 104, DARK)

    # Lid and body, split by the ribbon.
    rect(74, 90, 160, 108, DARK)
    rect(80, 112, 154, 166, DARK)
    rect(112, 90, 122, 166, YELLOW)
    rect(114, 90, 120, 166, DARK)

    # Bow: two square loops and a knot above the lid.
    rect(89, 62, 114, 87, DARK)
    rect(96, 69, 107, 80, YELLOW)
    rect(120, 62, 145, 87, DARK)
    rect(127, 69, 138, 80, YELLOW)
    rect(112, 72, 122, 90, DARK)

    # Plus, cut out of the box corner by a yellow margin.
    rect(136, 136, 172, 172, YELLOW)
    rect(141, 151, 167, 157, DARK)
    rect(151, 141, 157, 167, DARK)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    image.resize((SIZE, SIZE), Image.LANCZOS).save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
