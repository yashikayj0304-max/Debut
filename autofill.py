"""Fill in whatever a post is missing, so it can go out without anyone opening another app.

Publishing used to send exactly what was typed. A planned post with no caption went out with an
empty one, and a planned post with no picture could not go to Instagram at all - which left the
owner downloading a file, writing a caption somewhere else and uploading it by hand, the one job
Debut exists to remove.

So before anything is sent:

  caption_for()  uses the caption that is already written. If there isn't one, Claude writes it
                 when a key is configured, and a plain template writes it when there isn't. The
                 template never invents a claim - it works from the title the owner typed.
  image_for()    uses the picture that is already there. If there isn't one, Debut draws a
                 branded card at the right size for the platform.

Both write what they produced back onto the post, so the owner can see exactly what went out and
edit it before next time. Neither ever overwrites something the owner wrote.
"""
import logging
import re

import config as C
import postcard
import services as S
from db import ex, q

log = logging.getLogger("gtm")

SYSTEM = ("You write social captions for small Indian businesses. Plain, warm, specific. "
          "Never invent prices, discounts, dates or claims that are not given to you. "
          "No emoji spam, no hashtag walls.")


def _tags_for(ws, n=4):
    import industries as IND
    ind = IND.get(ws["industry"] if "industry" in ws.keys() else "general")
    base = re.sub(r"[^a-z0-9]+", "", (ind.get("label") or "").split("/")[0].split("(")[0].lower())
    base = "business" if base in ("", "general", "other") else base
    return " ".join([f"#{base}", "#india", "#smallbusiness", "#supportlocal"][:n])


def _template_caption(item, ws):
    """A caption built only from what the owner already typed. Dull beats wrong."""
    title = (item["title"] or "").strip()
    brand = (ws["name"] or "").replace(" (demo)", "").strip()
    cta = (item["cta"] or "").strip() if "cta" in item.keys() else ""
    bits = [title or f"Something new from {brand}"]
    if cta:
        bits.append(cta)
    else:
        bits.append("Message us to order, or drop a comment and we'll reply.")
    bits.append("Save this for later 📌")
    return "\n\n".join(bits)


def _ai_caption(item, ws):
    """Claude writes it when a key is set. Returns "" on any problem - a caption is never worth
    failing a post over, and the template below is always there."""
    if not C.ANTHROPIC_API_KEY:
        return ""
    try:
        import industries as IND
        import views as V
        ind = IND.get(ws["industry"] if "industry" in ws.keys() else "general")
        brand = (ws["name"] or "").replace(" (demo)", "")
        voice = (ws["ai_voice"] or "") if "ai_voice" in ws.keys() else ""
        lang = (ws["ai_lang"] or "English") if "ai_lang" in ws.keys() else "English"
        prompt = (f"Brand: {brand}. Industry: {ind['label']}. Write in: {lang}. "
                  f"Brand voice: {voice or 'friendly and clear'}.\n"
                  f"Channel: {item['channel'] or 'Instagram'}. Format: {item['format'] or 'Post'}.\n"
                  f"This post is about: {item['title']}\n"
                  f"{('Notes from the owner: ' + item['notes']) if ('notes' in item.keys() and item['notes']) else ''}\n"
                  "Write the caption only - no preamble, no quotes around it. Put the hook in the "
                  "first 120 characters. End with one clear ask. Do not invent prices, discounts "
                  "or dates. Keep it under 90 words.")
        text, _ = V.claude_call(SYSTEM, prompt, 500)
        return (text or "").strip().strip('"')[:900]
    except Exception:
        log.exception("auto caption failed; using the template instead")
        return ""


def caption_for(item, ws, allow_ai=True):
    """(body, hashtags, how it was made). Anything the owner wrote always wins.

    The three parts come back separately so they can be stored in the fields they belong to -
    the caption in `copy`, the tags in `hashtags`. Returning one joined string meant that reading
    the post back a moment later looked like the owner had written it with no tags, and the tags
    were then dropped from the post that actually went out.
    """
    written = (item["copy"] or "").strip()
    tags = (item["hashtags"] or "").strip() if "hashtags" in item.keys() else ""
    if written:
        return (written, tags, "yours")
    ai = _ai_caption(item, ws) if allow_ai else ""
    body = ai or _template_caption(item, ws)
    return (body, tags or _tags_for(ws), "ai" if ai else "template")


def image_for(item, ws):
    """(url, how it was made). Draws a branded card only when there is no picture at all."""
    have = (item["asset_url"] or "").strip() if "asset_url" in item.keys() else ""
    if have:
        return (have, "yours")
    logo = None
    url = (ws["logo_url"] or "") if "logo_url" in ws.keys() else ""
    if url.startswith("/media/"):
        try:
            import os
            with open(os.path.join(C.UPLOAD_DIR, str(ws["id"]), os.path.basename(url)), "rb") as f:
                logo = f.read()
        except Exception:
            logo = None
    try:
        data = postcard.card(item["title"] or "", (ws["name"] or "").replace(" (demo)", ""),
                             (ws["brand_color"] or "") if "brand_color" in ws.keys() else "",
                             (ws["secondary_color"] or "") if "secondary_color" in ws.keys() else "",
                             postcard.shape_for(item["format"] or ""), logo,
                             kicker=(item["channel"] or "") if "channel" in item.keys() else "")
        return (S.store_file(ws["id"], "jpg", data), "made")
    except Exception:
        log.exception("could not draw a card for the post")
        return ("", "none")


def prepare(item, ws, allow_ai=True, save=True):
    """Everything a post needs to go out, written back so the owner can see what was used.

    Returns {caption, image, caption_from, image_from, filled} where `filled` lists what Debut
    had to supply. Never touches a caption or a picture the owner already put there.
    """
    body, tags, cfrom = caption_for(item, ws, allow_ai)
    caption = "\n\n".join(x for x in (body, tags) if x)
    image, ifrom = image_for(item, ws)
    filled = [n for n, src in (("caption", cfrom), ("picture", ifrom)) if src not in ("yours", "none")]
    if save and filled:
        sets, vals = [], []
        if cfrom != "yours":
            sets += ["copy=?", "hashtags=?"]
            vals += [body[:4000], tags[:300]]
        if ifrom == "made":
            sets.append("asset_url=?")
            vals.append(image)
        if sets:
            try:
                ex(f"UPDATE content_items SET {','.join(sets)} WHERE workspace_id=? AND id=?",
                   tuple(vals) + (ws["id"], item["id"]))
            except Exception:
                log.exception("could not save what was auto-filled")
    return dict(caption=caption, image=image, caption_from=cfrom, image_from=ifrom, filled=filled)


def fresh(ws_id, cid):
    rows = q("SELECT * FROM content_items WHERE workspace_id=? AND id=?", (ws_id, cid))
    return rows[0] if rows else None
