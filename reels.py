"""Everything a reel needs that a slide deck does not.

A reel is not slides. It is a sequence of shots with seconds attached, a cover frame that decides
whether anyone taps it, and a hook that has about three seconds to work. The Create studio was
producing carousel-shaped output for reels - headlines with no timing and no instruction to film
anything - so this module adds the parts that were missing:

  shot_list()  the thing you take to the shoot: each shot, its seconds, what to point the camera at,
               the words on screen and the line you say
  hooks()      several openings to choose from, because the first three seconds carry the reel
  cover()      the three-to-five words that sit on the cover frame in your grid
  checks()     the reel-specific mistakes worth catching before it goes out
  repurpose()  one piece of work, placed four times

Nothing here needs an AI key or the internet: it is structure, not generated prose. When the AI
draft is available the studio fills these in with better words; without it, the structure still holds.
"""
import re

# The first three seconds decide whether anyone watches the rest. These are shapes, not scripts:
# each one takes the subject and makes a different promise.
HOOK_SHAPES = [
    ("Problem", "Still {pain}? Watch this."),
    ("Mistake", "Most people get {subject} wrong. Here's why."),
    ("Promise", "{subject}, in under a minute."),
    ("Curiosity", "Nobody tells you this about {subject}."),
    ("Proof", "This is what {subject} actually looks like."),
    ("Direct", "If you want {subject}, start here."),
    ("Contrast", "{subject}: what we used to do, and what we do now."),
    ("Question", "What would you pick for {subject}?"),
]

# What to film, by the job each shot is doing. Deliberately concrete: "hands opening the box" is a
# thing a person can point a phone at; "engaging visual" is not.
SHOT_IDEAS = {
    "hook": ["the most striking thing you have, close up", "your face, talking straight to camera",
             "the end result first, before showing how"],
    "context": ["a wide shot of the place or the product", "the problem happening in real life",
                "hands getting started"],
    "detail": ["a slow close-up of the part people ask about", "the step everyone gets wrong",
               "the texture, the finish, the ingredient"],
    "proof": ["a customer using it, or saying one line", "the before and after, side by side",
              "the thing working, uncut"],
    "cta": ["you, looking at camera, saying the ask", "the product with your handle on screen",
            "the offer written large, held in frame"],
}

# A reel's shape at three common lengths: (job, seconds, what the shot is for).
PLANS = {
    15: [("hook", 3, "Stop the scroll"), ("detail", 5, "Show the one thing"),
         ("proof", 4, "Make it believable"), ("cta", 3, "Ask for the action")],
    30: [("hook", 3, "Stop the scroll"), ("context", 5, "Say what this is"),
         ("detail", 8, "Show the one thing"), ("proof", 8, "Make it believable"),
         ("cta", 6, "Ask for the action")],
    60: [("hook", 3, "Stop the scroll"), ("context", 7, "Say what this is"),
         ("detail", 12, "Show how it works"), ("detail", 12, "Show the part people ask about"),
         ("proof", 16, "Make it believable"), ("cta", 10, "Ask for the action")],
}

STOPWORDS = {"the", "a", "an", "and", "or", "for", "with", "your", "our", "this", "that", "to", "of", "in", "on", "is", "are"}


def _subject(title):
    t = re.sub(r"^[^:]{0,24}:\s*", "", (title or "").strip())        # drop "Diwali: " style prefixes
    return (t[:1].lower() + t[1:])[:60] if t else "this"


def _beats(copy, n):
    """Split the caption into n sayable lines. Sentences first, then whatever is there."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", copy or "") if p.strip()]
    parts = [p for p in parts if not p.startswith("#")]
    out = parts[:n]
    while len(out) < n:
        out.append("")
    return out


def hooks(title, pain=""):
    """Several openings for the same reel, so the first three seconds can be chosen, not accepted."""
    subj = _subject(title)
    pain = (pain or "guessing what to post").strip()
    return [(name, shape.format(subject=subj, pain=pain)) for name, shape in HOOK_SHAPES[:5]]


def cover(title):
    """Three to five words for the cover frame: this is what people read in the grid, not the caption.
    Splits on spaces, not on every non-letter, so "make/deliver" and "hand-packed" survive whole."""
    words = [w.strip(".,:;!?\"'()") for w in (title or "").split()]
    words = [w for w in words if w]
    big = [w for w in words if w.lower() not in STOPWORDS] or words
    text = " ".join(big[:5]) or "Watch this"
    return text[:38].upper().rstrip("/-")


def shot_list(title, copy="", seconds=30):
    """The sheet you shoot from: every shot, its seconds, what to film, the on-screen words and the line
    you say. Returned as plain data so it renders on a page, copies to a phone, or prints."""
    seconds = min(PLANS, key=lambda s: abs(s - (seconds or 30)))
    plan = PLANS[seconds]
    said = _beats(copy, len(plan))
    subj = _subject(title)
    shots, clock = [], 0
    for i, (job, dur, purpose) in enumerate(plan):
        line = said[i] or {
            "hook": hooks(title)[0][1],
            "context": title.strip() or f"A quick look at {subj}.",
            "detail": "Show the part people always ask about.",
            "proof": "Say the one result you can honestly claim.",
            "cta": "Message us, or tap the link in our bio.",
        }[job]
        on_screen = cover(title) if job == "hook" else " ".join(line.split()[:4])
        shots.append(dict(n=i + 1, job=job, purpose=purpose, start=clock, end=clock + dur, secs=dur,
                          film=SHOT_IDEAS[job][i % len(SHOT_IDEAS[job])],
                          on_screen=on_screen.strip(" .,"), say=line.strip()))
        clock += dur
    return dict(seconds=clock, shots=shots, cover=cover(title))


def as_text(title, plan):
    """The same shot list as something you can paste into notes or read off a phone on set."""
    lines = [f"🎬 {title} — {plan['seconds']}s", f"Cover frame: {plan['cover']}", ""]
    for s in plan["shots"]:
        lines += [f"{s['start']}-{s['end']}s · {s['purpose']}",
                  f"   Film: {s['film']}",
                  f"   On screen: {s['on_screen']}",
                  f"   Say: {s['say']}", ""]
    return "\n".join(lines)


# The reel-specific mistakes. Each one is (ok?, what to do about it) - phrased as a fix, not a scolding.
def checks(item):
    fmt = (item["format"] or "") if "format" in item.keys() else ""
    copy = (item["copy"] or "") if "copy" in item.keys() else ""
    tags = (item["hashtags"] or "") if "hashtags" in item.keys() else ""
    cta = (item["cta"] or "") if "cta" in item.keys() else ""
    asset = (item["asset_url"] or "") if "asset_url" in item.keys() else ""
    first = copy.strip().split("\n")[0]
    out = [
        (bool(copy.strip()), "Write the caption", "A reel with no caption loses every viewer who watches on mute."),
        (len(first) <= 120 or len(copy) <= 120, "Put the hook in the first 120 characters",
         "Instagram cuts the caption at about 120 characters. Right now the first line is "
         f"{len(first)} characters, so the rest hides behind “more”."),
        (bool(cta.strip()) or bool(re.search(r"\b(dm|message|link|book|order|call|save|share|follow)\b", copy, re.I)),
         "End with one clear ask", "Say exactly what to do next: message us, book, save this."),
        (len([t for t in re.split(r"[,\s]+", tags) if t.strip()]) <= 5 or not tags.strip(),
         "Keep it to five hashtags", "Long hashtag walls read as spam and do not help reach any more."),
        (bool(asset.strip()), "Add the video or the cover picture",
         "Without a file there is nothing to post, and nothing for Instagram to download when Debut publishes it."),
    ]
    if fmt in ("Reel / Short", "Story"):
        out.append((True, "Shoot it 9:16, full screen",
                    "Keep faces and words away from the top and bottom - Instagram's own buttons sit there."))
    return [dict(ok=bool(ok), title=t, why=why) for ok, t, why in out]


# One piece of work, placed four times. Each target says what to change, not just where to send it.
REPURPOSE = {
    "Carousel": ("Carousel", "Instagram", "Split the script into slides: hook, three points, the ask."),
    "Story": ("Story", "Instagram", "Cut to three frames with a poll or a question sticker in the middle."),
    "Post": ("Post", "LinkedIn", "Rewrite as a short piece of writing: what happened, what you learned, the ask."),
    "Newsletter": ("Newsletter", "Email", "Open with the same hook, add the detail that did not fit, then the ask."),
}


def repurpose_plan(item):
    """What this piece could become next, and what to change for each."""
    fmt = (item["format"] or "") if "format" in item.keys() else ""
    return [(name, f, ch, how) for name, (f, ch, how) in REPURPOSE.items() if f != fmt]
