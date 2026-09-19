from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1536, 864
TEXT = (245, 241, 231)
MUTED = (194, 187, 174)
GOLD = (226, 187, 103)
TEMPLATE = Path(__file__).resolve().parent / "assets" / "top_template.png"

def font(n, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, n)
        except OSError:
            pass
    return ImageFont.load_default()

def text(d, xy, value, size, fill=TEXT, bold=False, anchor=None):
    d.text(xy, str(value), font=font(size, bold), fill=fill, anchor=anchor)

def remaining(sec, compact=False):
    days, rem = divmod(max(0, int(sec)), 86400)
    hours = rem // 3600
    return f"{days}j {hours}h" if compact else f"{days} JOURS {hours} HEURES"

def avatar(im, d, cx, cy, r, player, border):
    raw = player.get("avatar")
    if raw:
        try:
            src = Image.open(BytesIO(raw)).convert("RGB")
            src = ImageOps.fit(src, (r * 2, r * 2), Image.Resampling.LANCZOS)
            mask = Image.new("L", (r * 2, r * 2), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, r * 2 - 1, r * 2 - 1), fill=255)
            im.paste(src, (cx-r, cy-r), mask)
            d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=border, width=3)
            return
        except Exception:
            pass
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(31, 29, 25), outline=border, width=3)
    text(d, (cx, cy), (player.get("name") or "?")[:1].upper(), r, TEXT, True, "mm")

def panel(d, box, fill=(15, 13, 10, 238), outline=(125, 96, 48, 220), radius=12, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def render_top(group_title, season_number, month_label, players, total_players, top10_xp, remaining_seconds, group_avatar=None):
    # The approved artwork is the source of truth. Pillow only overlays live Telegram data.
    try:
        src = Image.open(TEMPLATE).convert("RGB")
        im = ImageOps.fit(src, (W, H), Image.Resampling.LANCZOS).convert("RGBA")
    except Exception:
        im = Image.new("RGBA", (W, H), (10, 9, 7, 255))
    d = ImageDraw.Draw(im, "RGBA")

    # Mask only variable-data zones; keep the template's borders, glow, texture and decoration.
    panel(d, (174, 34, 850, 137), fill=(13, 12, 10, 244), outline=(0,0,0,0), width=0)
    panel(d, (1160, 31, 1485, 133), fill=(13, 12, 10, 244), outline=(0,0,0,0), width=0)
    text(d, (184, 38), "C L A S S E M E N T   G R O U P E", 20, MUTED, True)
    text(d, (184, 67), (group_title or "GROUPE").upper()[:22], 43, TEXT, True)
    text(d, (184, 113), "Top des membres de ce groupe", 20, MUTED)
    text(d, (1472, 38), f"SAISON {season_number}", 25, GOLD, True, "ra")
    text(d, (1472, 72), month_label.upper(), 18, MUTED, False, "ra")
    text(d, (1472, 112), "◷  Fin dans " + remaining(remaining_seconds, True), 19, MUTED, False, "ra")

    # Live podium. The template remains visible around these compact content surfaces.
    cards = [
        (55, 165, 522, 355, 1, (185, 88, 108, 255)),
        (548, 126, 988, 355, 0, (229, 184, 72, 255)),
        (1014, 165, 1481, 355, 2, (150, 132, 190, 255)),
    ]
    for x1, y1, x2, y2, idx, accent in cards:
        panel(d, (x1+8, y1+8, x2-8, y2-8), fill=(15, 13, 11, 226), outline=accent, radius=13, width=2)
        cx = (x1+x2)//2
        text(d, (cx, y1+22), f"#{idx+1}", 21, accent, True, "ma")
        if idx < len(players):
            p = players[idx]
            avatar(im, d, cx, y1+75, 39, p, accent)
            text(d, (cx, y1+123), p["name"][:18], 23, TEXT, True, "ma")
            text(d, (cx, y1+151), p["rank"].upper(), 19, accent, True, "ma")
            text(d, (cx, y1+177), f'{p["xp"]:,} XP'.replace(",", " "), 19, TEXT, True, "ma")

    y = 375
    for idx in range(3, 7):
        panel(d, (55, y, 1481, y+58), fill=(14, 13, 11, 235), outline=(116, 88, 43, 210), radius=10, width=1)
        text(d, (78, y+29), f"#{idx+1}", 23, MUTED, True, "lm")
        if idx < len(players):
            p = players[idx]
            avatar(im, d, 184, y+29, 22, p, (181, 172, 153, 255))
            text(d, (235, y+29), p["name"][:24], 23, TEXT, True, "lm")
            text(d, (1450, y+29), f'{p["rank"]}   {p["xp"]:,} XP'.replace(",", " "), 21, TEXT, True, "rm")
        y += 64

    panel(d, (55, 644, 1481, 754), fill=(14, 13, 11, 235), outline=(125, 96, 48, 220), radius=16, width=2)
    values = [
        ("MEMBRES DU GROUPE", str(total_players)),
        ("TOP 10", f'{top10_xp:,} XP'.replace(",", " ")),
        ("FIN DE SAISON DANS", remaining(remaining_seconds)),
    ]
    for cx, (label, value) in zip((275, 768, 1260), values):
        text(d, (cx, 670), label, 17, MUTED, False, "ma")
        text(d, (cx, 714), value, 27, GOLD, True, "ma")

    out = BytesIO()
    im.convert("RGB").save(out, "PNG", optimize=True)
    out.seek(0)
    return out
