"""Tone of voice: the same message in three registers. Chill is the default; agencies and older users can switch to Corporate."""
TONES = ("chill", "normal", "corporate")
V = {
    "overdue": ("Lowkey overdue 👀", "Overdue", "Overdue"),
    "empty_today": ("No thoughts, just vibes 🌱", "All clear today", "Nothing is due today"),
    "win": ("You ate that 🔥", "Nice work, it's published", "Published"),
    "launch_day": ("Main character energy ✨", "It's launch day", "Launch day"),
    "rizz": ("Rizz score", "Hook score", "Hook strength"),
    "err": ("Oops, the internet ate it. Try again?", "Something went wrong. Try again.", "An error occurred. Please retry."),
    "saved": ("Locked in 🔒", "Saved", "Saved"),
    "wrapped": ("Your week, wrapped 🎁", "Your week in marketing", "Weekly summary"),
    "radar": ("What's hot right now", "Coming up", "Upcoming moments"),
    "ask": ("Ask Deb", "Ask Deb", "Ask the assistant"),
}


def tone_of(user):
    try:
        t = (user["tone"] or "chill") if user else "chill"
    except (KeyError, IndexError, TypeError):
        t = "chill"
    return t if t in TONES else "chill"


def tn(key, user=None):
    from flask import g
    u = user if user is not None else g.get("user")
    return V[key][TONES.index(tone_of(u))]
