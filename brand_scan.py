"""Automatic (no-AI) brand-deck scanning: pull the dominant colours, the most-used font and a logo image
straight out of an uploaded .pptx or .pdf brand deck, so a small-business owner doesn't have to type in
hex codes or font names by hand after a designer hands them a deck. Heuristic, not perfect - it looks at
what actually recurs across the deck (a picture repeated on several slides is almost certainly the logo;
a colour used in solid shape fills or a big title is more likely "the brand colour" than incidental text)
rather than calling any external AI service, so it's free and works the moment a file is uploaded.
"""
import io
import hashlib
from collections import Counter

RASTER_EXTS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
MAX_SLIDES_OR_PAGES = 12


def _is_extreme(hexv):
    """True for near-white or near-black - almost never the deliberate brand colour, just backgrounds/text."""
    try:
        r, g, b = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)
    except ValueError:
        return True
    return (r > 245 and g > 245 and b > 245) or (r < 12 and g < 12 and b < 12)


def _pick_logo(images):
    """images: list of (blob, ext, area, page_or_slide_index). A picture repeated on several
    slides/pages is almost certainly a logo (brands stamp it on every slide); failing that, fall back
    to the largest picture found."""
    if not images:
        return None, None
    by_hash = {}
    for blob, ext, area, idx in images:
        if ext not in RASTER_EXTS:
            continue
        h = hashlib.md5(blob).hexdigest()
        entry = by_hash.setdefault(h, {"blob": blob, "ext": ext, "pages": set(), "area": 0})
        entry["pages"].add(idx)
        entry["area"] = max(entry["area"], area)
    if not by_hash:
        return None, None
    repeats = [v for v in by_hash.values() if len(v["pages"]) >= 2]
    best = max(repeats, key=lambda v: len(v["pages"])) if repeats else max(by_hash.values(), key=lambda v: v["area"])
    return best["blob"], ("jpg" if best["ext"] == "jpeg" else best["ext"])


def _scan_pptx(data):
    from pptx import Presentation

    prs = Presentation(io.BytesIO(data))
    color_counts, font_counts = Counter(), Counter()
    images = []
    for si, slide in enumerate(list(prs.slides)[:MAX_SLIDES_OR_PAGES]):
        cover_weight = 3 if si == 0 else 1  # the cover/title slide's choices are the most deliberate
        for shape in slide.shapes:
            try:
                if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        for run in para.runs:
                            if run.font.name:
                                big = bool(run.font.size and run.font.size.pt >= 24)
                                font_counts[run.font.name] += (3 if big else 1) * cover_weight
                            try:
                                if run.font.color and run.font.color.type is not None:
                                    hexv = str(run.font.color.rgb).upper()
                                    if not _is_extreme(hexv):
                                        color_counts[hexv] += cover_weight
                            except (AttributeError, TypeError, KeyError):
                                pass
            except Exception:
                pass
            try:
                if shape.fill is not None and shape.fill.type == 1:  # MSO_FILL_TYPE.SOLID
                    hexv = str(shape.fill.fore_color.rgb).upper()
                    if not _is_extreme(hexv):
                        color_counts[hexv] += 4 * cover_weight  # a deliberate shape fill outweighs stray text colour
            except (AttributeError, TypeError, KeyError):
                pass
            try:
                if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                    img = shape.image
                    if shape.width > 274320 and shape.height > 274320:  # skip tiny bullet/icon images (~0.3in)
                        images.append((img.blob, img.ext, shape.width * shape.height, si))
            except Exception:
                pass
    logo_bytes, logo_ext = _pick_logo(images)
    return dict(
        colors=[c for c, _ in color_counts.most_common(4)],
        fonts=[f for f, _ in font_counts.most_common(3)],
        logo_bytes=logo_bytes, logo_ext=logo_ext or "png",
    )


def _scan_pdf(data):
    import fitz
    from PIL import Image

    doc = fitz.open(stream=data, filetype="pdf")
    font_counts, images = Counter(), []
    pages = list(doc)[:MAX_SLIDES_OR_PAGES]
    for pi, page in enumerate(pages):
        try:
            for f in page.get_fonts(full=True):
                basefont = (f[3] or f[4] or "").split("+")[-1]  # strip a subset prefix like "ABCDEF+Calibri"
                if basefont:
                    font_counts[basefont] += (2 if pi == 0 else 1)
        except Exception:
            pass
        try:
            for img in page.get_images(full=True):
                try:
                    base = doc.extract_image(img[0])
                except Exception:
                    continue
                ext, w, h = base.get("ext"), base.get("width", 0), base.get("height", 0)
                if ext in RASTER_EXTS and w >= 60 and h >= 60:
                    images.append((base["image"], ext, w * h, pi))
        except Exception:
            pass
    logo_bytes, logo_ext = _pick_logo(images)
    colors = []
    try:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        quant = img.resize((80, 80)).convert("P", palette=Image.ADAPTIVE, colors=8).convert("RGB")
        for (r, g, b), _ in Counter(quant.getdata()).most_common(8):
            hexv = "%02X%02X%02X" % (r, g, b)
            if not _is_extreme(hexv):
                colors.append(hexv)
            if len(colors) >= 4:
                break
    except Exception:
        pass
    return dict(colors=colors, fonts=[f for f, _ in font_counts.most_common(3)], logo_bytes=logo_bytes, logo_ext=logo_ext or "png")


def scan_deck(data, filename):
    """Entry point. Returns {"colors": [hex,...] (no '#'), "fonts": [name,...], "logo_bytes": bytes|None,
    "logo_ext": "png"|"jpg"|...}. Raises ValueError for anything unreadable, so callers can show one
    friendly message instead of a stack trace."""
    name = (filename or "").lower()
    try:
        if name.endswith(".pptx"):
            return _scan_pptx(data)
        if name.endswith(".pdf"):
            return _scan_pdf(data)
    except Exception as e:
        raise ValueError("Could not read that file.") from e
    raise ValueError("Unsupported file type - upload a .pptx or .pdf.")
