#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview.png"
W, H = 1280, 640

BG = (9, 13, 20)
CARD = (17, 22, 32)
CARD2 = (23, 28, 40)
GOLD = (200, 168, 78)
GOLD2 = (240, 207, 106)
TEXT = (230, 233, 240)
MUTED = (155, 163, 178)
BLUE = (105, 167, 255)
RED = (255, 93, 115)
GREEN = (80, 209, 141)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def font(path, size):
    return ImageFont.truetype(path, size)

def rounded(draw, xy, r, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def gradient_bg():
    img = Image.new("RGB", (W, H), BG)
    px = img.load()
    for y in range(H):
        for x in range(W):
            dx = x - 160
            dy = y - 80
            glow = max(0, 1 - math.sqrt(dx*dx + dy*dy) / 650)
            dx2 = x - 1080
            dy2 = y - 520
            glow2 = max(0, 1 - math.sqrt(dx2*dx2 + dy2*dy2) / 520)
            r = int(BG[0] + glow * 42 + glow2 * 20)
            g = int(BG[1] + glow * 34 + glow2 * 35)
            b = int(BG[2] + glow * 10 + glow2 * 68)
            px[x, y] = (min(r,255), min(g,255), min(b,255))
    return img

img = gradient_bg()
d = ImageDraw.Draw(img)

# grid
for x in range(0, W, 48):
    d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=1)
for y in range(0, H, 48):
    d.line([(0, y), (W, y)], fill=(255, 255, 255, 10), width=1)

# orbital rings
for i, color in enumerate([(200,168,78,70), (105,167,255,45), (255,255,255,24)]):
    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((745-i*24, 92-i*24, 1215+i*24, 562+i*24), outline=color, width=2)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

# main glass card
shadow = Image.new("RGBA", (W,H), (0,0,0,0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle((72, 72, 790, 558), radius=34, fill=(0,0,0,110))
shadow = shadow.filter(ImageFilter.GaussianBlur(22))
img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
d = ImageDraw.Draw(img)
rounded(d, (72, 72, 790, 558), 34, CARD, (45, 51, 65), 2)

# badge
d.rounded_rectangle((112, 112, 334, 152), radius=20, fill=(200,168,78,26), outline=GOLD)
d.text((132, 122), "DAILY AI BRIEFING", font=font(FONT_BOLD, 18), fill=GOLD2)

# title
d.text((112, 188), "AI", font=font(FONT_BOLD, 112), fill=TEXT)
d.text((112, 296), "Yesterday", font=font(FONT_BOLD, 94), fill=TEXT)
d.rectangle((116, 405, 468, 413), fill=GOLD)

# subtitle
d.text((112, 438), "Yesterday's AI developments", font=font(FONT_REG, 31), fill=(205, 210, 220))
d.text((112, 478), "translated into plain English.", font=font(FONT_REG, 31), fill=(205, 210, 220))

# right dashboard cards
cards = [
    (850, 136, 1158, 214, "11", "curated signals", RED),
    (850, 238, 1158, 316, "9", "sources monitored", BLUE),
    (850, 340, 1158, 418, "2332", "items scanned", GOLD2),
]
for x1,y1,x2,y2,num,label,color in cards:
    rounded(d, (x1,y1,x2,y2), 18, CARD2, (48,56,72), 1)
    d.ellipse((x1+20, y1+24, x1+34, y1+38), fill=color)
    d.text((x1+52, y1+14), num, font=font(FONT_MONO, 31), fill=color)
    d.text((x1+52, y1+51), label, font=font(FONT_REG, 18), fill=MUTED)

# mini news stack
for i, (label, color) in enumerate([("Critical", RED), ("High", GOLD2), ("Plain English", GREEN)]):
    y = 462 + i*42
    d.rounded_rectangle((850, y, 1160, y+28), radius=14, fill=(255,255,255,18), outline=(255,255,255,35))
    d.ellipse((866, y+9, 876, y+19), fill=color)
    d.text((890, y+5), label, font=font(FONT_BOLD, 16), fill=(218,224,235))

# footer
d.text((72, 594), "sahirvhora.github.io/ai-yesterday", font=font(FONT_MONO, 20), fill=GOLD2)
d.text((806, 594), "Searchable history - source links - impact flags", font=font(FONT_REG, 18), fill=MUTED)

img.save(OUT, "PNG")
print(OUT)
