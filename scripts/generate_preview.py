#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 640
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def rr(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], r: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill, bold: bool = False, mono: bool = False) -> None:
    draw.text(xy, value, font=font(FONT_MONO if mono else FONT_BOLD if bold else FONT_REG, size), fill=fill)


def glow_background(base: tuple[int, int, int], glow_points: list[tuple[int, int, tuple[int, int, int], float]]) -> Image.Image:
    img = Image.new("RGB", (W, H), base)
    px = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b = base
            for gx, gy, color, radius in glow_points:
                dist = math.sqrt((x - gx) ** 2 + (y - gy) ** 2)
                strength = max(0.0, 1.0 - dist / radius) ** 1.8
                r += int(color[0] * strength)
                g += int(color[1] * strength)
                b += int(color[2] * strength)
            px[x, y] = (min(r, 255), min(g, 255), min(b, 255))
    return img


def add_noise_grid(img: Image.Image, line=(255, 255, 255, 14), step: int = 44) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=line, width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=line, width=1)


def save(img: Image.Image, filename: str) -> None:
    out = ROOT / filename
    img.save(out, "PNG", optimize=True)
    print(out)


def variant_linear() -> Image.Image:
    img = glow_background((2, 3, 6), [(210, 100, (70, 55, 160), 650), (1110, 520, (28, 60, 125), 520)])
    add_noise_grid(img, (255, 255, 255, 9), 40)
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(9):
        d.arc((700 - i * 26, 70 - i * 14, 1230 + i * 18, 590 + i * 14), 195, 18, fill=(114, 112, 255, 38 - i * 3), width=2)
    rr(d, (70, 70, 822, 560), 28, (15, 16, 20, 232), (255, 255, 255, 24), 1)
    rr(d, (110, 110, 308, 146), 18, (94, 106, 210, 70), (130, 143, 255, 90), 1)
    text(d, (130, 118), "AI INTELLIGENCE", 16, (210, 214, 255), bold=True)
    text(d, (110, 188), "AI", 108, (247, 248, 248), bold=True)
    text(d, (110, 292), "Yesterday", 92, (247, 248, 248), bold=True)
    text(d, (114, 426), "Daily AI developments translated", 31, (208, 214, 224))
    text(d, (114, 468), "for busy humans.", 31, (208, 214, 224))
    rr(d, (110, 516, 364, 546), 15, (255, 255, 255, 12), (255, 255, 255, 35), 1)
    text(d, (128, 523), "sahirvhora.github.io/ai-yesterday", 14, (138, 143, 152), mono=True)
    # Right-side decorative feature list
    features = ["Plain-English summaries", "Impact flags", "Source links", "Searchable history"]
    for idx, feat in enumerate(features):
        y = 154 + idx * 88
        rr(d, (878, y, 1188, y + 60), 10, (255, 255, 255, 10), (255, 255, 255, 22), 1)
        d.ellipse((900, y + 20, 912, y + 32), fill=(114, 112, 255, 180))
        text(d, (930, y + 16), feat, 19, (208, 214, 224))
    return img.convert("RGB")


def variant_vercel() -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(0, W, 64):
        d.line([(i, 0), (i, H)], fill=(0, 0, 0, 10), width=1)
    for i in range(0, H, 64):
        d.line([(0, i), (W, i)], fill=(0, 0, 0, 10), width=1)
    d.polygon([(878, 88), (1184, 570), (574, 570)], fill=(0, 0, 0, 14))
    rr(d, (74, 72, 1186, 560), 24, (255, 255, 255, 248), (0, 0, 0, 22), 1)
    text(d, (116, 114), "AI YESTERDAY", 18, (23, 23, 23), bold=True, mono=True)
    text(d, (116, 178), "Daily AI news,", 74, (23, 23, 23), bold=True)
    text(d, (116, 264), "without the noise.", 74, (23, 23, 23), bold=True)
    text(d, (120, 390), "Plain-English summaries, impact flags, source links", 28, (77, 77, 77))
    text(d, (120, 430), "and a searchable history of AI developments.", 28, (77, 77, 77))
    pills = [("Critical", (255, 91, 79)), ("Models", (10, 114, 239)), ("Policy", (222, 29, 141))]
    x = 118
    for label, color in pills:
        rr(d, (x, 500, x + 128, 536), 18, (255, 255, 255, 255), (0, 0, 0, 26), 1)
        d.ellipse((x + 16, 512, x + 28, 524), fill=color)
        text(d, (x + 38, 507), label, 16, (23, 23, 23), bold=True)
        x += 146
    features = ["Plain-English summaries", "Impact & importance flags", "Source links included"]
    for idx, feat in enumerate(features):
        y = 174 + idx * 88
        rr(d, (870, y, 1130, y + 60), 10, (255, 255, 255, 255), (0, 0, 0, 28), 1)
        d.ellipse((892, y + 20, 904, y + 32), fill=(10, 114, 239))
        text(d, (922, y + 17), feat, 16, (23, 23, 23), bold=True)
    text(d, (874, 496), "sahirvhora.github.io/ai-yesterday", 16, (77, 77, 77), mono=True)
    return img

def variant_superhuman() -> Image.Image:
    img = glow_background((27, 25, 56), [(250, 120, (94, 65, 160), 600), (1060, 80, (104, 54, 130), 520), (980, 560, (36, 38, 80), 520)])
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(8):
        d.ellipse((780 - i * 20, 50 - i * 18, 1210 + i * 18, 500 + i * 18), outline=(203, 183, 251, 42 - i * 4), width=2)
    rr(d, (76, 76, 1184, 560), 34, (255, 255, 255, 20), (255, 255, 255, 46), 1)
    text(d, (118, 118), "AI YESTERDAY", 18, (203, 183, 251), bold=True)
    text(d, (118, 178), "Read AI", 86, (255, 255, 255, 242), bold=True)
    text(d, (118, 266), "like a human.", 86, (255, 255, 255, 242), bold=True)
    text(d, (122, 410), "A calm premium briefing for yesterday's AI developments", 29, (255, 255, 255, 205))
    rr(d, (122, 488, 344, 536), 8, (233, 229, 221, 245), None, 1)
    text(d, (148, 501), "Open daily briefing", 18, (41, 40, 39), bold=True)
    rr(d, (816, 130, 1128, 444), 24, (255, 255, 255, 232), (220, 215, 211, 255), 1)
    text(d, (846, 158), "Yesterday", 22, (41, 40, 39), bold=True)
    rows = [("Critical", "Governance", (255, 93, 115)), ("High", "Agents", (113, 76, 182)), ("Medium", "Research", (80, 209, 141)), ("Source", "Open links", (203, 183, 251))]
    for idx, (left, right, color) in enumerate(rows):
        y = 208 + idx * 54
        d.ellipse((850, y + 6, 862, y + 18), fill=color)
        text(d, (878, y), left, 18, (41, 40, 39), bold=True)
        text(d, (1000, y), right, 17, (102, 100, 98))
    text(d, (816, 506), "sahirvhora.github.io/ai-yesterday", 16, (255, 255, 255, 190), mono=True)
    return img.convert("RGB")


def main() -> None:
    variants = {
        "preview-linear.png": variant_linear(),
        "preview-vercel.png": variant_vercel(),
        "preview-superhuman.png": variant_superhuman(),
    }
    for name, image in variants.items():
        save(image, name)
    variants["preview-linear.png"].save(ROOT / "preview.png", "PNG", optimize=True)
    print(ROOT / "preview.png")


if __name__ == "__main__":
    main()
