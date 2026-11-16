"""Ready-made mood boards. Each one is a palette, a mood line, a shot list, a tone note and a 'never' note,
plus two generated picture tiles in the palette. Everything lands on the canvas as normal items, so every piece is editable."""
import base64

CATS = ["Festival", "Launch", "Industry", "Style", "Content", "Brand"]
ROLES = ["Base", "Accent", "Highlight", "Soft tint", "Ink"]

# key, category, emoji, name, palette (base accent highlight soft ink), mood, shots, tone, never
B = [
 # ---- Festival
 ("diwali", "Festival", "🪔", "Diwali glow", "#1B1033 #FF8C1A #FFD166 #FFF1D6 #8B1E3F", "Warm, gifting-led, golden-hour light. Home getting ready together.", "Diya close-ups, hands exchanging gifts, rangoli from above, family at the table.", "Warm, a little funny, one emoji max.", "Guilt-trip copy, harsh white backgrounds, heavy discount banners."),
 ("holi", "Festival", "🎨", "Holi colour burst", "#FFFFFF #FF3D7F #FFC83D #33C7A5 #3B2A6B", "Playful, loud, joyful colour against clean white.", "Powder in the air, laughing faces, colour on palms, before and after the splash.", "Fun, energetic, short lines.", "Muddy colours, posed stiff shots, anything slippery or unsafe."),
 ("eid", "Festival", "🌙", "Eid elegance", "#0F3D3E #D4AF37 #F5E6C8 #E8F3EE #1A1A1A", "Calm, generous, crescent and lantern light.", "Lanterns at dusk, dates and sweets on a platter, mehendi hands, family spread.", "Gracious, warm, community-first.", "Loud sale banners, stereotyped imagery."),
 ("christmas", "Festival", "🎄", "Cosy Christmas", "#12372A #C1272D #F2C94C #FDF3E7 #2B2B2B", "Cosy lights, wrapped gifts, warm kitchens.", "Fairy lights, wrapped boxes, steam from a mug, a decorated corner.", "Cheerful, gift-led, kind.", "Snow clichés that do not fit your city, hard sell."),
 ("rakhi", "Festival", "🧿", "Rakhi and siblings", "#7A1F3D #F4A261 #FFD6A5 #FFF4E6 #2B1B17", "Teasing, tender sibling bond, thoughtful gifts.", "Rakhi on a wrist, sibling candids, thali, gift being opened.", "Warm and a little cheeky.", "Gender stereotypes, expensive-gift pressure."),
 ("navratri", "Festival", "💃", "Navratri nine nights", "#2A0E3D #E63946 #F7B801 #FFE8D1 #1D3557", "Garba energy, nine-colour days, twirling fabric.", "Dandiya sticks, twirls, chaniya choli details, night lights, one colour per day.", "Energetic, rhythmic, community.", "Mixing the day colours, blurry low-light shots."),
 ("onam", "Festival", "🌼", "Onam pookalam", "#FFFDF5 #F4B400 #2E8B57 #FCE9C8 #4A2C0A", "Fresh, floral, banana-leaf sadya feel.", "Pookalam from above, sadya on leaf, kasavu saree borders, boat race wide shots.", "Gentle, proud, regional.", "Generic South-Indian clichés, wrong dishes."),
 ("pongal", "Festival", "🌾", "Pongal and Sankranti", "#FFF6E0 #E67E22 #7BB661 #FDE9B8 #5B3A1A", "Harvest, kites, sweet pots overflowing.", "Pot boiling over, kites in sky, sugarcane, til-gud, kolam.", "Earthy, thankful, simple.", "Mixing festivals, stock farmer photos."),
 ("newyear", "Festival", "🎆", "New Year reset", "#0B1026 #7C5CFF #FF5DA2 #E8EAFF #FFFFFF", "Fresh start, midnight sparkle, goal-setting.", "Planner flat lays, countdown clocks, sparklers, clinking glasses.", "Hopeful, bold, short.", "Over-promising results, tired resolutions."),
 ("valentine", "Festival", "❤️", "Valentine's soft", "#FFF0F3 #E63B5B #FF9BB0 #FFD9E0 #4A1525", "Soft, playful, love in small gestures.", "Handwritten notes, shared dessert, two cups, gift wrap.", "Sweet, witty, inclusive of every kind of love.", "Pressure to spend, only couples."),
 ("independence", "Festival", "🇮🇳", "Made in India pride", "#FFFFFF #FF9933 #138808 #EAF2FF #000080", "Pride, nostalgia, made-in-India craft.", "Tricolour details, hands at work, local craft, family waving flags.", "Proud and grounded, never preachy.", "Misusing the flag, discount-first copy."),
 ("wedding", "Festival", "💍", "Wedding season", "#FFF8EE #C9184A #D4A373 #FDE2E4 #3A1C23", "Big celebrations, couture, family joy.", "Mehendi, jewellery close-ups, venue wide, getting-ready candids.", "Romantic, luxurious, warm.", "Stock couples, cluttered collages."),
 ("durga", "Festival", "🌺", "Durga Puja pandal", "#FFF9F0 #D62828 #F77F00 #FCE5CD #1C1C1C", "Dhak beats, red and white sarees, pandal lights.", "Pandal hopping, sindoor khela, bhog, dhunuchi dance.", "Emotional, communal.", "Disrespecting rituals, loud ads."),
 # ---- Launch
 ("product", "Launch", "🚀", "Product launch", "#F1ECFF #6A3DF0 #FF4F9A #FFFFFF #2B2442", "One hero, one promise, lots of white space.", "Hero on a textured surface, in-hand, flat lay, packaging reveal.", "Confident and clear.", "Feature lists on the cover, clutter."),
 ("collection", "Launch", "🛍️", "New collection drop", "#111111 #FF5A36 #F5F0E6 #E7E2D8 #FFFFFF", "Editorial, drop-day hype.", "Lookbook portraits, texture close-ups, hanger and flat lay, detail shots.", "Short, teasing, scarcity-honest.", "Fake scarcity, inconsistent edits."),
 ("shopopen", "Launch", "🏪", "Shop grand opening", "#FFF4E6 #E8590C #1C7C54 #FFE0B2 #2B1B0E", "Welcoming, local, ribbon-cutting energy.", "Storefront wide, ribbon cutting, shelves, owner portrait, first customers.", "Friendly neighbour.", "Dark empty-shop photos, missing address."),
 ("cafeopen", "Launch", "☕", "Cafe opening", "#2E1F14 #D68C45 #F3E5D0 #FFF8EE #7A4B2A", "Cosy, steamy, first-sip feeling.", "Latte art, window light, menu board, hands around a mug.", "Warm, inviting.", "Blue-white lighting, stocky food shots."),
 ("salonopen", "Launch", "💇", "Salon or clinic opening", "#FFFFFF #C084FC #F6D6E6 #F4EEFB #2B1D3D", "Fresh, clean, transformation.", "Before and after, tools, calm interior, team portraits.", "Reassuring, professional, friendly.", "Unproven medical claims, harsh filters."),
 ("gymopen", "Launch", "🏋️", "Gym or studio launch", "#0D0D0D #C6FF3D #FF3D3D #1E1E1E #FFFFFF", "High contrast, sweat, momentum.", "Equipment close-ups, trainer in action, community class, transformations.", "Direct, motivating.", "Body shaming, miracle claims."),
 ("event", "Launch", "🎟️", "Event or pop-up", "#14213D #FCA311 #E5E5E5 #FFF3D1 #000000", "Save-the-date, crowd, countdown.", "Venue wide, speaker portraits, crowd, ticket mock-up, map pin.", "Urgent but clear: date, place, price.", "Hiding the venue, tiny dates."),
 ("course", "Launch", "🎓", "Course or coaching launch", "#F8FAFC #2563EB #F59E0B #DBEAFE #0F172A", "Trust, clarity, transformation.", "Face to camera, screen recordings, student wins, curriculum card.", "Helpful, honest, specific.", "Income claims, vague promises."),
 ("app", "Launch", "📱", "App or SaaS launch", "#0B1020 #5B8CFF #22D3A5 #E6ECFF #FFFFFF", "Clean product UI on a dark stage.", "Screen mock-ups, one-feature clips, founder note, waitlist card.", "Plain and precise.", "Jargon, ten features at once."),
 ("relaunch", "Launch", "🔁", "Relaunch or rebrand", "#FAFAFA #FF6B35 #004E64 #FFE5D9 #1A1A1A", "Old to new, the glow-up story.", "Old vs new split, process sketches, new packaging, team reveal.", "Proud, grateful.", "Trashing the old look."),
 ("sale", "Launch", "🔥", "Sale day", "#FFF200 #E10600 #111111 #FFFBD1 #FFFFFF", "Loud, urgent, honest.", "Price tags, product grids, countdown clocks, packed parcels.", "Short, direct, deadline-clear.", "Fake discounts, tiny fine print."),
 # ---- Industry
 ("bakery", "Industry", "🧁", "Bakery and desserts", "#FFF3E8 #E58F65 #8D5A97 #FFD9C0 #4B2E2B", "Soft pastels, flour dust, fresh from the oven.", "Cross-sections, piping, hands dusting sugar, box unboxing.", "Sweet, personal.", "Plastic-looking icing, dim light."),
 ("sweets", "Industry", "🍬", "Mithai and gifting", "#FFF7E0 #E6A100 #B5179E #FFE9A8 #4A2511", "Festive, shiny, boxes of joy.", "Overhead thali, silver warq, box opening, hands sharing.", "Warm, family-first.", "Cluttered backdrops."),
 ("restaurant", "Industry", "🍛", "Restaurant and cloud kitchen", "#1D1A16 #E85D04 #FFBA08 #F6EFE4 #FFFFFF", "Steam, sizzle, close-up appetite.", "Pour shots, pulls, steam, plating from 45 degrees, chef at work.", "Craving-led, short.", "Flat flash, lacklustre menus."),
 ("skincare", "Industry", "🧴", "Skincare and beauty", "#FDF6F0 #E8A598 #9AB7A0 #F6E6DE #3E2C2C", "Dewy, clean, ingredient-led.", "Texture swatches, shelfie, glowing skin close-ups, ingredient flat lay.", "Gentle, honest, no miracle claims.", "Heavy retouching, before-and-after claims."),
 ("fashion", "Industry", "👗", "Ethnic and fashion wear", "#FAF3EB #B83280 #D69E2E #F6E4D2 #2D1B2E", "Fabric in motion, handcrafted detail.", "Twirl shots, embroidery close-up, flat lay, street style.", "Elegant and proud.", "Wrong lighting that shifts colours."),
 ("jewellery", "Industry", "💎", "Jewellery", "#101010 #D4AF37 #F2E7D0 #1F1F1F #FFFFFF", "Sparkle on dark, macro detail.", "Macro shots, on-skin, box reveal, light rotating.", "Quiet luxury.", "Busy backgrounds, fingerprints."),
 ("fitness", "Industry", "💪", "Fitness and wellness", "#F5FFF8 #00B37E #FF7A59 #D6F5E6 #0B2B20", "Energy, routines, small wins.", "Workout clips, meal prep, progress, outdoors.", "Encouraging, never shaming.", "Extreme claims."),
 ("homedecor", "Industry", "🛋️", "Home decor", "#F4EFE6 #A67C52 #6B8F71 #E8DCC8 #2F2A24", "Calm corners, natural textures.", "Room wide, texture close-up, styled shelf, before and after.", "Calm, aspirational.", "Cramped photos."),
 ("kids", "Industry", "🧸", "Kids and toys", "#FFFDF0 #FF6B6B #4D96FF #FFD93D #2B2D42", "Primary colours, play, laughter.", "Hands playing, parents' point of view, product in use, gift wrap.", "Cheerful, parent-trust.", "Unsafe settings, pushy ads to children."),
 ("pets", "Industry", "🐶", "Pet brand", "#FFF9F2 #FF8C42 #4EA699 #FFE5CC #2B2118", "Goofy, loving, eye-level.", "Pet reactions, tail wags, unboxing, owner and pet.", "Playful.", "Stressed animals."),
 ("tech", "Industry", "💻", "Tech and B2B", "#0F172A #38BDF8 #A78BFA #E2E8F0 #FFFFFF", "Clean grids, data, human faces.", "Product UI, customer quotes, team portraits, charts.", "Plain, proof-led.", "Jargon walls."),
 ("realestate", "Industry", "🏡", "Real estate", "#FFFFFF #0B6E4F #C9A227 #E8F3EE #1B1B1B", "Light-filled rooms, trust.", "Wide rooms at golden hour, walkthrough, neighbourhood, keys handover.", "Honest and clear.", "Wide-angle distortion."),
 ("travel", "Industry", "🧳", "Travel and stays", "#06283D #1363DF #47B5FF #DFF6FF #FFFFFF", "Wanderlust, wide skies.", "Views, window seats, local food, hands with map.", "Dreamy but practical.", "Unreal edits."),
 ("education", "Industry", "📚", "Education and tutoring", "#FFFDF5 #F4A261 #264653 #FDEBD0 #1F2D3D", "Friendly, achievable.", "Notebooks, whiteboards, student smiles, results cards.", "Encouraging.", "Pressure on parents."),
 ("craft", "Industry", "🧶", "Handmade and craft", "#FBF5EC #C97B63 #7A9E7E #F0E0CE #3B2F2F", "Real hands, imperfect and proud.", "Hands at work, tools, material swatches, packaging with a handwritten note.", "Personal, proud.", "Factory-look mockups."),
 ("florist", "Industry", "💐", "Florist", "#FFF5F7 #E75480 #7BAE7F #FFD6E0 #3B2A2F", "Fresh, soft, seasonal.", "Bouquet from above, hands wrapping, delivery, close-up petals.", "Soft and sweet.", "Wilted stock."),
 # ---- Style
 ("minimal", "Style", "◻️", "Minimal clean", "#FFFFFF #111111 #8E8E93 #F2F2F2 #000000", "Space, one idea per frame, quiet type.", "Centred products, flat backgrounds, one prop.", "Few words, plain.", "Decoration for its own sake."),
 ("retro", "Style", "📼", "Retro 70s", "#F6E7C1 #D1495B #EDAE49 #00798C #30638E", "Warm sunsets, curved type, film grain.", "Film-look portraits, vintage props, sunburst.", "Fun, nostalgic.", "Over-filtered mud."),
 ("y2k", "Style", "💿", "Y2K pop", "#F0E7FF #FF4FD8 #38E8FF #FFFFFF #2A1B4D", "Chrome, gloss, butterfly clips.", "Chrome type, flip-phone, glitter, collage cut-outs.", "Chaotic, cheeky.", "Muddy contrast."),
 ("desibold", "Style", "🌈", "Desi bold", "#FF4D6D #FFB703 #023E8A #FFF1E6 #1B1B1B", "Truck-art colours, thick type, humour.", "Flower garlands, chai glass, auto-rickshaw, signboard type.", "Loud, funny, local.", "Faking regional slang."),
 ("pastel", "Style", "🍡", "Pastel dream", "#FFF5FA #F7A8C4 #A8D8EA #FFE6F1 #5B4B6B", "Soft, airy, dreamy.", "Light gradients, balloons, fluffy props.", "Gentle, kind.", "Heavy black text."),
 ("darkluxe", "Style", "🖤", "Dark luxe", "#0B0B0F #C8A45C #8A8A93 #1C1C24 #FFFFFF", "Moody, glossy, gold on black.", "Low-key lighting, reflections, slow-motion pours.", "Quiet, exact.", "Cheap-looking gold."),
 ("earthy", "Style", "🌿", "Earthy organic", "#F3EEE3 #6B705C #CB997E #DDBEA9 #3A3A2E", "Linen, clay, plants, slow living.", "Natural light, hands in clay, wooden props, green corners.", "Calm, honest.", "Plastic packaging shots."),
 ("neon", "Style", "🌃", "Neon night", "#07070D #00F5D4 #F15BB5 #1A1A2E #FFFFFF", "City night, glow and reflections.", "Neon signs, wet streets, long-exposure trails.", "Bold, short.", "Overexposed glow."),
 ("vintagefilm", "Style", "🎞️", "Vintage film", "#EFE3CD #B5651D #5C7A6B #D9C5A0 #2E2A25", "Grain, soft colour, candid.", "Disposable-camera frames, light leaks, candid moments.", "Nostalgic.", "Digital-looking sharpness."),
 ("cottage", "Style", "🫖", "Cottagecore", "#FBF6EE #8DAA91 #E3B7A0 #EBD9C3 #4B3F35", "Gardens, baskets, soft linens.", "Picnic spreads, wildflowers, window light.", "Soft, storybook.", "Plastic props."),
 ("maximal", "Style", "🎪", "Maximalist", "#FF006E #FFBE0B #3A86FF #FB5607 #1B1B1B", "More is more, clashing colours.", "Pattern on pattern, collage, sticker layers.", "Loud, joyful.", "Low-energy neutral frames."),
 ("mono", "Style", "⬛", "Monochrome editorial", "#F2F2F2 #1A1A1A #6B6B6B #D9D9D9 #000000", "Black, white, big type, contrast.", "High-contrast portraits, architecture lines, big headlines.", "Sharp.", "Random colour."),
 # ---- Content
 ("reels", "Content", "🎬", "Reel look and feel", "#0F0A1F #7C5CFF #FF5DA2 #EDE9FF #FFFFFF", "Fast hook, big captions, one idea.", "Hook in 3 seconds, B-roll, text on screen, beat-synced cuts.", "Snappy.", "Long intros, tiny text."),
 ("grid", "Content", "🧩", "Instagram grid plan", "#FFFFFF #6A3DF0 #FF4F9A #F4F0FF #1B1433", "Alternating post types, one colour rhythm.", "Cover, quote, photo, carousel repeating in threes.", "Consistent.", "Random order."),
 ("stories", "Content", "📲", "Story templates", "#121212 #FFE14A #FF5D8F #F5F5F5 #FFFFFF", "Stickers, polls, quick wins.", "Poll, quiz, countdown, link sticker, behind-the-scenes.", "Chatty.", "Stories without a reason to tap."),
 ("ugc", "Content", "🤳", "UGC and testimonials", "#FFFBF3 #FF7A59 #2D9CDB #FFE7D6 #1D2B36", "Real faces, real words.", "Selfie reviews, unboxing, screenshots, voice notes.", "Real and unpolished.", "Scripted reviews."),
 ("influencer", "Content", "🌟", "Influencer brief", "#FFF4E6 #E8590C #1C7C54 #FFE0B2 #2B1B0E", "Show real use. Their voice, your look.", "Real use in 3 seconds, product in hand, tagged handle.", "Do's and don'ts, clear.", "Reading a script word for word."),
 ("shoot", "Content", "📷", "Shoot day plan", "#F7F7F7 #2D6A4F #F4A261 #E9F5EC #1B1B1B", "Props list, shot list, light.", "Hero, detail, in-use, lifestyle, flat lay.", "Organised.", "No backup battery."),
 ("ads", "Content", "📣", "Ad creative", "#FFFFFF #FF3B30 #007AFF #F2F2F7 #1C1C1E", "One message, big proof, clear button.", "Hook frame, product proof, offer card.", "Direct.", "Too much text."),
 ("website", "Content", "🌐", "Website look", "#FFFFFF #0066FF #00C2A8 #F3F6FB #0B1B33", "Clean sections, big hero, trust.", "Hero photo, icon row, testimonials, footer.", "Plain, fast.", "Autoplay clutter."),
 ("email", "Content", "✉️", "Email newsletter look", "#FFFFFF #7C3AED #F59E0B #F5F3FF #1F2937", "One hero, one button.", "Hero image, 3 blocks, offer strip.", "Warm, short.", "Walls of text."),
 ("packaging", "Content", "📦", "Packaging", "#FFF8F0 #E85D04 #264653 #FFE8D6 #1B1B1B", "Unboxing delight, thank-you note.", "Box open, tissue, sticker, handwritten card.", "Delightful.", "Over-packaging."),
 # ---- Brand
 ("brand", "Brand", "🎨", "Brand identity", "#F1ECFF #6A3DF0 #E8590C #FFFFFF #2B2442", "Colours, voice and visual rules at a glance.", "Natural light, real people, uncluttered backgrounds.", "Friendly, plain-spoken, confident.", "Stock smiles, ALL-CAPS shouting."),
 ("voice", "Brand", "💬", "Brand voice", "#FFFDF5 #FF6B6B #4ECDC4 #FFF0D6 #2D3436", "How we sound in captions and replies.", "Sample captions, reply examples, words we love.", "Warm and direct.", "Jargon and filler."),
 ("logo", "Brand", "✒️", "Logo direction", "#FFFFFF #111111 #FF4F9A #F2F2F2 #6A3DF0", "Shapes, type, spacing and where it can go.", "Logo on light, dark, photo, and small sizes.", "Clear.", "Thin lines that vanish at small size."),
 ("photo", "Brand", "🖼️", "Photography style", "#F6F2EC #8A6F5A #D4B483 #E8DFD2 #2D2620", "Light, angle and edit consistency.", "Same window light, 45 degree angle, soft shadows.", "Natural.", "Mixed filters."),
 ("founder", "Brand", "🙋", "Founder story", "#FFF9F0 #E85D04 #264653 #FFE5CC #1B1B1B", "A real person, real beginnings.", "Portrait, workspace, first product, thank you.", "Honest.", "Hero-worship."),
]


def svg(label, c1, c2, emoji):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
         f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/>'
         f'<circle cx="400" cy="70" r="90" fill="#fff" opacity=".12"/><circle cx="60" cy="330" r="110" fill="#000" opacity=".1"/>'
         f'<text x="40" y="190" font-size="64">{emoji}</text>'
         f'<text x="40" y="250" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#fff">{label}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()


def _q(t): return t.lower().replace(" ", "%20")


def build(row):
    key, cat, emoji, name, pal, mood, shots, tone, never = row
    c = pal.split()
    nm = _q(name)
    tag = "".join(ch for ch in name.lower() if ch.isalnum())
    items = [("image", svg("Hero look", c[1], c[0] if c[0] != "#FFFFFF" else c[4], emoji), "Hero look: replace with your best photo"),
             ("image", svg("Texture and detail", c[2], c[4], "✨"), "Texture and detail"),
             ("image", svg("Flat lay / props", c[3], c[1], "🧺"), "Flat lay or props: drop your photo here")]
    items += [("color", hx, role) for hx, role in zip(c, ROLES)]
    items += [("note", mood, "Mood")]
    for n, shot in enumerate([x.strip() for x in shots.replace(" and ", ", ").split(",") if x.strip()][:5], 1):
        items.append(("note", shot[0].upper() + shot[1:], f"Shot {n}"))
    items += [("note", tone, "Tone of voice"), ("note", "Never: " + never, "Avoid"),
              ("note", f"Post ideas: 1) {name}: behind the scenes. 2) Before and after. 3) One tip in 3 slides. 4) Customer moment. 5) Reel: 3 quick cuts with big text.", "Content ideas"),
              ("note", f"Caption starters: \"The part nobody sees...\", \"Made for {name.lower()} moments\", \"Save this for later\"", "Caption starters"),
              ("note", f"#{tag} #smallbusinessindia #madeinindia #reelsindia #supportlocal", "Hashtags to try"),
              ("link", "https://www.pinterest.com/search/pins/?q=" + nm + "%20aesthetic", "Pinterest: " + name + " ideas"),
              ("link", "https://www.instagram.com/explore/search/keyword/?q=%23" + tag, "Instagram: see #" + tag),
              ("link", "https://www.behance.net/search/projects?search=" + nm, "Behance: designer work"),
              ("link", "https://www.google.com/search?tbm=isch&q=" + nm + "%20photography%20reference", "Google Images: photo reference"),
              ("link", "https://unsplash.com/s/photos/" + nm.replace("%20", "-"), "Unsplash: free photos"),
              ("link", "https://coolors.co/" + "-".join(h.lstrip("#").lower() for h in c), "Open this palette in Coolors"),
              ("link", "https://www.youtube.com/results?search_query=" + nm + "%20reel%20ideas", "YouTube: video ideas")]
    return name, mood, items


LIB = {r[0]: r for r in B}
