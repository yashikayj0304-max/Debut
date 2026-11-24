"""Make the picture when there isn't one.

Instagram will not accept a post without an image, and the whole point of publishing from Debut
is that nobody has to download a file, open a design tool and upload it again. So when a planned
post has no picture of its own, this draws one: the headline in the workspace's own brand colours,
its logo if it has one, at the size the platform wants.

It is deliberately plain. A generated card competes with nothing - it is a readable, on-brand
holding image so a post can go out on time, and it is obvious enough to look at that anyone can
see it is not a photograph and swap in something better.

Two things it refuses to do: invent claims (only the title and the brand name appear, never made-up
copy), and depend on a font that might not exist on the server. The font ships with the code.
"""
import io
import os
import re

SIZES = {                     # what each platform actually wants
    "square": (1080, 1080),   # the safe default: a feed post
    "portrait": (1080, 1350),  # taller feed post, more of the screen
    "story": (1080, 1920),    # story and reel cover
}
FOR_FORMAT = {"Story": "story", "Reel / Short": "story", "Carousel": "square", "Post": "square"}

_HERE = os.path.dirname(os.path.abspath(__file__))
# Bundled first, on purpose: a server without these system fonts would otherwise fall back to a
# bitmap face that looks broken at 1080px, and we would only find out from a customer's feed.
FONTS = [os.path.join(_HERE, "static", "fonts", "DejaVuSans-Bold.ttf"),
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]
FONTS_REG = [os.path.join(_HERE, "static", "fonts", "DejaVuSans.ttf"),
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def _font(size, bold=True):
    from PIL import ImageFont
    for path in (FONTS if bold else FONTS_REG):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)       # Pillow 10+: scalable, plain, still legible
    except Exception:
        return ImageFont.load_default()


def _rgb(hexish, fallback=(106, 61, 240)):
    s = re.sub(r"[^0-9a-fA-F]", "", hexish or "")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return fallback
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _ink_for(bg):
    """White or near-black, whichever can actually be read on this background."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    L = 0.2126 * lin(bg[0]) + 0.7152 * lin(bg[1]) + 0.0722 * lin(bg[2])
    return (255, 255, 255) if (1.05 / (L + 0.05)) >= ((L + 0.05) / 0.05) else (18, 16, 28)


def _wrap(draw, text, font, width):
    words, lines, line = (text or "").split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def card(title, brand_name="", c1="", c2="", shape="square", logo_bytes=None, kicker=""):
    """A JPEG of the headline on a brand-coloured background. Returns bytes."""
    from PIL import Image, ImageDraw
    w, h = SIZES.get(shape, SIZES["square"])
    a, b = _rgb(c1), _rgb(c2 or c1, _rgb(c1))
    im = Image.new("RGB", (w, h), a)
    px = im.load()
    for y in range(h):                                  # a soft diagonal, so it is not a flat slab
        for x in range(0, w, 4):
            t = (x / w + y / h) / 2
            v = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = v
    dr = ImageDraw.Draw(im, "RGBA")
    dr.ellipse((w * .58, -h * .12, w * 1.25, h * .5), fill=(255, 255, 255, 28))
    dr.ellipse((-w * .2, h * .62, w * .45, h * 1.2), fill=(0, 0, 0, 30))

    ink = _ink_for(tuple(int((a[i] + b[i]) / 2) for i in range(3)))
    pad = int(w * 0.09)
    box = w - pad * 2

    if kicker:
        kf = _font(int(w * 0.034), bold=False)
        dr.text((pad, int(h * 0.11)), kicker[:40].upper(), font=kf, fill=ink + (210,))

    size = int(w * 0.105)
    while size > int(w * 0.045):
        f = _font(size)
        lines = _wrap(dr, title or brand_name or "", f, box)
        if len(lines) <= (4 if shape != "story" else 6):
            break
        size = int(size * 0.9)
    f = _font(size)
    lines = _wrap(dr, title or brand_name or "", f, box)[:6]
    lh = int(size * 1.22)
    y = int(h * (0.30 if shape == "story" else 0.26))
    for ln in lines:
        dr.text((pad + 3, y + 3), ln, font=f, fill=(0, 0, 0, 55))     # a shadow, so it reads on any mix
        dr.text((pad, y), ln, font=f, fill=ink)
        y += lh

    if brand_name:
        bf = _font(int(w * 0.038), bold=False)
        dr.text((pad, h - pad - int(w * 0.05)), brand_name[:40], font=bf, fill=ink + (235,))

    if logo_bytes:
        try:
            lg = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            side = int(w * 0.11)
            lg.thumbnail((side, side))
            im.paste(lg, (w - pad - lg.width, h - pad - lg.height), lg)
        except Exception:
            pass                                       # a missing logo is not worth failing a post over

    out = io.BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=88, optimize=True)
    return out.getvalue()


def shape_for(fmt):
    return FOR_FORMAT.get((fmt or "").strip(), "square")
