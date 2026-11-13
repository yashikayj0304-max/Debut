"""Swap generic emoji in page text for a consistent line-icon set (CSS masks), so the UI stops looking auto-generated."""
import re
from urllib.parse import quote

P = {
 "cal": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
 "img": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
 "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
 "flame": '<path d="M12 2c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-6 1-9z"/>',
 "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 1-1 1.7M12 17h.01"/>',
 "rocket": '<path d="M14 4c3-1 6-1 7-1 0 1 0 4-1 7l-7 7-5-5zM9 14l-4 1-2 6 6-2 1-4M10 8L6 9l-3 3 4 1"/>',
 "bulb": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10c1 1 1 2 1 3h6c0-1 0-2 1-3a6 6 0 0 0-4-10z"/>',
 "chart": '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
 "bot": '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 14h.01M15 14h.01"/>',
 "chat": '<path d="M21 12a8 8 0 0 1-11.5 7.2L3 21l1.8-5.5A8 8 0 1 1 21 12z"/>',
 "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
 "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.5 0 2-1 1.5-2s0-2 1.5-2h2a4 4 0 0 0 4-4c0-5-4-10-9-10z"/><circle cx="8" cy="11" r="1"/><circle cx="12" cy="7.5" r="1"/><circle cx="16" cy="11" r="1"/>',
 "home": '<path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10"/>',
 "camera": '<rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="12" cy="13.5" r="3.5"/><path d="M8 7l1.5-3h5L16 7"/>',
 "radar": '<circle cx="12" cy="12" r="2"/><path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2"/>',
 "plug": '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
 "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/>',
 "event": '<path d="M3 21h18M5 21L12 4l7 17M12 21v-6"/>',
 "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
 "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1"/>',
 "note": '<path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4"/>',
 "magnet": '<path d="M5 3v9a7 7 0 0 0 14 0V3h-4v9a3 3 0 0 1-6 0V3zM5 7h4M15 7h4"/>',
 "mega": '<path d="M3 11v3l12 5V6zM15 9a3 3 0 0 1 0 6M6 15l1 5h3l-1-4"/>',
 "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
 "refresh": '<path d="M21 12a9 9 0 0 0-15-6.7L3 8M3 3v5h5M3 12a9 9 0 0 0 15 6.7L21 16M21 21v-5h-5"/>',
 "book": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M8 7h7"/>',
 "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
 "doc": '<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7"/>',
 "phone": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
 "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2 21a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M18 21a6 6 0 0 0-3-5"/>',
 "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 21h4"/>',
 "card": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
 "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
 "building": '<path d="M4 21V4h10v17M14 9h6v12M8 8h2M8 12h2M8 16h2M3 21h18"/>',
 "crown": '<path d="M3 8l4 4 5-7 5 7 4-4-2 11H5z"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
 "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
 "heart": '<path d="M12 21s-8-5-8-11a4.5 4.5 0 0 1 8-2.5A4.5 4.5 0 0 1 20 10c0 6-8 11-8 11z"/>',
 "sparkle": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
 "warn": '<path d="M12 3l10 18H2zM12 10v5M12 18h.01"/>',
 "upload": '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
 "download": '<path d="M12 4v12M7 11l5 5 5-5M4 20h16"/>',
 "folder": '<path d="M3 6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
 "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
 "bag": '<path d="M5 8h14l-1 12H6zM9 8V6a3 3 0 0 1 6 0v2"/>',
 "coin": '<circle cx="12" cy="12" r="9"/><path d="M14.5 9c-.5-1-1.500-1.500-2.500-1.500-1.500 0-2.500.8-2.500 2s1 1.700 2.500 2 2.500.8 2.500 2-1 2-2.500 2c-1 0-2-.5-2.500-1.500M12 6v1.500M12 16.500V18"/>',
 "trophy": '<path d="M8 4h8v6a4 4 0 0 1-8 0zM8 6H4v1a3 3 0 0 0 4 3M16 6h4v1a3 3 0 0 1-4 3M12 14v4M8 21h8"/>',
 "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
 "plus": '<path d="M12 5v14M5 12h14"/>',
 "pin": '<path d="M12 17v5M8 3h8l-1 7 3 3H6l3-3z"/>',
 "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10"/>',
 "hand": '<path d="M8 12V5a1.500 1.500 0 0 1 3 0v6M11 11V3.500a1.500 1.500 0 0 1 3 0V11M14 11V5a1.500 1.500 0 0 1 3 0v8c0 5-3 8-6 8-3 0-4-2-6-5l-1-2a1.500 1.500 0 0 1 3-1z"/>',
 "smile": '<circle cx="12" cy="12" r="9"/><path d="M8 14c1 1.500 2.500 2.500 4 2.500s3-1 4-2.500M9 9.500h.01M15 9.500h.01"/>',
 "leaf": '<path d="M5 19C5 9 11 4 20 4c0 9-5 15-15 15zM5 19l8-8"/>',
 "star": '<path d="M12 3l2.700 5.600 6.100.8-4.500 4.200 1.100 6.100L12 16.800 6.600 19.700l1.100-6.100L3.200 9.400l6.100-.8z"/>',
 "key": '<circle cx="8" cy="14" r="4"/><path d="M11 11l9-9M16 6l3 3"/>',
 "unlock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7-2.500"/>',
 "moon": '<path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/>',
 "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.500 1.500M17.500 17.500L19 19M19 5l-1.500 1.500M6.500 17.500L5 19"/>',
 "vol": '<path d="M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6M18.500 6.500a8 8 0 0 1 0 11"/>',
 "mute": '<path d="M4 9v6h4l5 4V5L8 9zM17 9l5 6M22 9l-5 6"/>',
}
EMO = {
 "📅": "cal", "🖼": "img", "✅": "check", "🔥": "flame", "❓": "help", "🚀": "rocket", "💡": "bulb", "📈": "chart", "🤖": "bot",
 "💬": "chat", "🔗": "link", "🎨": "palette", "🏠": "home", "🤳": "camera", "📡": "radar", "🔌": "plug", "🔎": "search", "🎪": "event",
 "🧭": "compass", "🏷": "tag", "📝": "note", "✍": "note", "✎": "note", "🧲": "magnet", "📣": "mega", "🔐": "lock", "🔒": "lock", "🔄": "refresh",
 "📖": "book", "📘": "book", "⚙": "gear", "🛠": "gear", "📑": "doc", "📋": "doc", "📱": "phone", "👥": "users", "👤": "users", "🔔": "bell",
 "💳": "card", "⚡": "bolt", "🏢": "building", "👑": "crown", "🕘": "clock", "✉": "mail", "👁": "eye", "🩺": "heart", "✨": "sparkle", "⚠": "warn",
 "📤": "upload", "⬆": "upload", "📲": "download", "⬇": "download", "📥": "download", "📁": "folder", "🗂": "folder", "🗑": "trash", "🛍": "bag", "💰": "coin", "💸": "coin",
 "🏆": "trophy", "🌐": "globe", "➕": "plus", "📌": "pin", "📦": "box", "✋": "hand", "🫠": "smile", "🌱": "leaf", "🌟": "star", "⭐": "star", "🔑": "key", "🔓": "unlock",
 "📊": "chart", "🚨": "warn", "🤝": "users", "🗓": "cal", "📧": "mail", "📬": "mail", "✏": "note", "🖨": "doc", "📜": "doc", "❤": "heart", "👀": "eye", "👏": "heart", "🙌": "heart", "👋": "hand",
 "🧹": "refresh", "🎬": "camera", "🔭": "search", "📚": "book", "📗": "book", "🗺": "compass",
}
NAME = {"cal": "Calendar", "img": "Image", "check": "Done", "help": "Help", "search": "Search", "bell": "Notifications", "gear": "Settings", "trash": "Delete", "plus": "Add", "download": "Download", "upload": "Upload", "lock": "Locked", "link": "Link", "note": "Edit", "chat": "Chat", "star": "Star", "home": "Home", "heart": "Like", "warn": "Warning", "bot": "AI", "doc": "Document", "eye": "View", "refresh": "Refresh", "mail": "Email"}
_VS = "\ufe0f"
_RX = re.compile("(" + "|".join(map(re.escape, EMO)) + ")" + _VS + "?")
_SPLIT = re.compile(r"""(<(?:"[^"]*"|'[^']*'|[^'">])*>)""")
_SKIP = ("script", "style", "textarea", "title", "option", "svg")


def css():
    out = [".ic{display:inline-block;width:1.15em;height:1.15em;vertical-align:-.2em;background:currentColor;-webkit-mask:var(--i) center/contain no-repeat;mask:var(--i) center/contain no-repeat;flex:none}"]
    for k, d in P.items():
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + d.replace('"', "'") + "</svg>")
        out.append(".ic-%s{--i:url(\"data:image/svg+xml,%s\")}" % (k, quote(svg, safe="/:=' ,.-")))
    return "\n".join(out)


def swap(html):
    parts = _SPLIT.split(html)
    skip = None
    for i, p in enumerate(parts):
        if i % 2:
            m = re.match(r"<(/?)\s*([a-zA-Z0-9]+)", p)
            if m:
                tag = m.group(2).lower()
                if skip:
                    if m.group(1) and tag == skip:
                        skip = None
                elif not m.group(1) and tag in _SKIP:
                    skip = tag
                elif m.group(1) and tag in _SKIP:
                    skip = None
            continue
        if skip or not p:
            continue
        alone = not _RX.sub("", p).strip()
        parts[i] = _RX.sub(lambda m: ('<i class="ic ic-%s" role="img" aria-label="%s"></i>' % (EMO[m.group(1)], NAME.get(EMO[m.group(1)], EMO[m.group(1)])) if alone else '<i class="ic ic-%s" aria-hidden="true"></i>' % EMO[m.group(1)]), p)
    return "".join(parts)
