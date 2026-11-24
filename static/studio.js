/* Create studio: designs posts, carousels and reels on a canvas in the browser, so the server stays light. */
(function () {
  var C = window.STUDIO, $ = function (id) { return document.getElementById(id); };
  var SIZES = { "4:5": [1080, 1350], "1:1": [1080, 1080], "9:16": [1080, 1920], "16:9": [1200, 675] };
  var DEF_SIZE = { post: "4:5", carousel: "4:5", reel: "9:16", story: "9:16" };
  var ANIMS = ["pop", "slide", "type", "zoom", "wipe"];
  var S = { kind: C.kind || "carousel", slides: [], caption: C.caption || "", tags: [], cta: "", theme: "auto", size: "", cur: 0, noLogo: false, guides: false, rid: C.rid || 0 };
  var logo = null;
  if (C.logo) { logo = new Image(); logo.crossOrigin = "anonymous"; logo.onload = redraw; logo.onerror = function () { logo = null; }; logo.src = C.logo; }

  /* ---------- colour helpers ---------- */
  function rgb(h) { h = (h || "#6a3df0").replace("#", ""); if (h.length === 3) h = h.replace(/./g, "$&$&"); var n = parseInt(h, 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
  function hex(a) { return "#" + a.map(function (v) { return ("0" + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2); }).join(""); }
  function mix(a, b, t) { var x = rgb(a), y = rgb(b); return hex([0, 1, 2].map(function (i) { return x[i] + (y[i] - x[i]) * t; })); }
  function lum(h) { var c = rgb(h).map(function (v) { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]; }
  function lookOf(sl) { var L = window.TPL && TPL.LOOK; return (L && sl && L[sl.look]) || null; }
  function palette(sl) {
    var pri = C.pri || "#6a3df0", sec = C.sec || "#ff4f9a", K = lookOf(sl);
    if (S.theme === "auto" && K) { var P0 = { bg: K.a, bg2: K.b, fg: K.fg, accent: K.ac, accent2: K.ac2, soft: mix(K.a, "#000000", .25), on: lum(K.ac) > .5 ? "#1a1033" : "#ffffff", motif: K.m };
      if (S.cust && S.cust.bg) { P0.bg = S.cust.bg; P0.bg2 = mix(S.cust.bg, S.cust.ac || K.b, .55); P0.fg = lum(S.cust.bg) > .55 ? "#1a1033" : "#ffffff"; P0.soft = mix(S.cust.bg, "#000000", .25); }
      if (S.cust && S.cust.ac) { P0.accent = S.cust.ac; P0.on = lum(S.cust.ac) > .5 ? "#1a1033" : "#ffffff"; }
      return P0; }
    if (S.theme === "sunset") return { bg: "#2a0f2e", fg: "#fff4ea", accent: "#ff9f43", soft: "#4a1a45", on: "#2a0f2e" };
    if (S.theme === "mint") return { bg: "#e8fbf2", fg: "#0b3d2e", accent: "#12b886", soft: "#c9f3e0", on: "#ffffff" };
    if (S.theme === "mono") return { bg: "#0a0a0a", fg: "#ffffff", accent: "#c6ff3d", soft: "#1c1c1c", on: "#0a0a0a" };
    if (S.theme === "light") return { bg: mix(pri, "#ffffff", .92), fg: mix(pri, "#000000", .72), accent: pri, soft: mix(pri, "#ffffff", .8), on: lum(pri) > .5 ? "#111" : "#fff" };
    if (S.theme === "brand") return { bg: pri, fg: lum(pri) > .5 ? "#111" : "#ffffff", accent: "#ffe14a", soft: mix(pri, "#000000", .2), on: "#111" };
    var bg = mix(pri, "#000000", .82), ac = lum(sec) > .12 ? sec : "#ffe14a";
    return { bg: bg, fg: "#ffffff", accent: ac, soft: mix(pri, "#000000", .6), on: lum(ac) > .5 ? "#111" : "#fff" };
  }

  /* ---------- drawing ---------- */
  var FONT = '"Bricolage Grotesque", Inter, "Segoe UI", system-ui, sans-serif';
  function wrap(ctx, text, maxW) {
    var words = String(text || "").split(/\s+/), lines = [], line = "";
    words.forEach(function (w) { var t = line ? line + " " + w : w; if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t; });
    if (line) lines.push(line); return lines;
  }
  function fit(ctx, text, maxW, maxH, max, min, weight) {
    for (var f = max; f >= min; f -= 4) { ctx.font = weight + " " + f + "px " + FONT; var l = wrap(ctx, text, maxW); if (l.length * f * 1.12 <= maxH) return { f: f, lines: l }; }
    ctx.font = weight + " " + min + "px " + FONT; return { f: min, lines: wrap(ctx, text, maxW).slice(0, Math.floor(maxH / (min * 1.12))) };
  }
  function drawText(ctx, lines, x, y, f, color, reveal) {
    ctx.fillStyle = color; ctx.textBaseline = "top"; var left = reveal == null ? 1e9 : Math.floor(reveal * lines.join("").length);
    lines.forEach(function (ln, i) { var s = ln; if (left < s.length) s = s.slice(0, Math.max(0, left)); left -= ln.length; ctx.fillText(s, x, y + i * f * 1.12); });
    return y + lines.length * f * 1.12;
  }
  function imgOf(s) { if (!s.img) return null; if (!s._im) { var i = new Image(); i.onload = function () { redraw(); }; i.src = s.img; s._im = i; } return s._im; }
  /* decorative layer drawn behind the words: it is what makes each event look different */
  function seeded(n) { var x = Math.sin(n * 9301 + 49297) * 233280; return x - Math.floor(x); }
  function motif(ctx, w, h, P, idx) {
    var a = P.accent, b = P.accent2 || P.accent, k = P.motif, i, n, x, y, r; ctx.save();
    function disc(x, y, r, c, al) { ctx.globalAlpha = al; ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); }
    if (k === "splash") { for (i = 0; i < 9; i++) disc(seeded(i + 1) * w, seeded(i + 40) * h, w * (.06 + seeded(i + 7) * .16), [a, b, "#ffffff", "#fb7185", "#34d399"][i % 5], .28); }
    else if (k === "sparks" || k === "stars") { for (i = 0; i < 34; i++) { x = seeded(i + 3) * w; y = seeded(i + 90) * h; r = 3 + seeded(i + 5) * 9; disc(x, y, r, i % 3 ? a : b, .35 + seeded(i) * .5); } disc(w * .86, h * .12, w * .24, a, .12); disc(w * .1, h * .92, w * .3, b, .14); }
    else if (k === "confetti") { for (i = 0; i < 46; i++) { x = seeded(i + 11) * w; y = seeded(i + 51) * h; ctx.save(); ctx.translate(x, y); ctx.rotate(seeded(i) * 6); ctx.globalAlpha = .55; ctx.fillStyle = [a, b, "#ffffff", "#22d3ee", "#fb7185"][i % 5]; ctx.fillRect(-9, -4, 18, 8); ctx.restore(); } }
    else if (k === "rings") { for (i = 0; i < 4; i++) { ctx.globalAlpha = .22 - i * .03; ctx.strokeStyle = i % 2 ? b : a; ctx.lineWidth = 10; ctx.beginPath(); ctx.arc(w * .92, h * .1, w * (.16 + i * .12), 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(w * .05, h * .95, w * (.12 + i * .1), 0, 7); ctx.stroke(); } }
    else if (k === "rays") { ctx.translate(w * .5, h * .02); for (i = 0; i < 18; i++) { ctx.rotate(Math.PI / 9); ctx.globalAlpha = i % 2 ? .12 : .05; ctx.fillStyle = a; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(w * 1.3, -40); ctx.lineTo(w * 1.3, 40); ctx.fill(); } }
    else if (k === "snow") { for (i = 0; i < 40; i++) disc(seeded(i + 2) * w, seeded(i + 70) * h, 3 + seeded(i + 9) * 9, "#ffffff", .3 + seeded(i) * .4); }
    else if (k === "hearts") { ctx.font = Math.round(w * .06) + "px sans-serif"; for (i = 0; i < 16; i++) { ctx.globalAlpha = .25 + seeded(i) * .35; ctx.fillText("♥", seeded(i + 4) * w, seeded(i + 60) * h); } disc(w * .9, h * .08, w * .22, "#ffffff", .1); }
    else if (k === "bands") { for (i = 0; i < 5; i++) { ctx.globalAlpha = .18; ctx.fillStyle = i % 2 ? a : b; ctx.save(); ctx.translate(w * (.1 + i * .22), 0); ctx.rotate(.45); ctx.fillRect(0, -h * .2, w * .07, h * 1.5); ctx.restore(); } }
    else if (k === "bolts") { ctx.globalAlpha = .2; ctx.fillStyle = a; for (i = 0; i < 3; i++) { x = w * (.12 + i * .34); ctx.beginPath(); ctx.moveTo(x, h * .06); ctx.lineTo(x + w * .08, h * .06); ctx.lineTo(x + w * .02, h * .2); ctx.lineTo(x + w * .1, h * .2); ctx.lineTo(x - w * .02, h * .36); ctx.lineTo(x + w * .01, h * .24); ctx.lineTo(x - w * .05, h * .24); ctx.closePath(); ctx.fill(); } disc(w * .85, h * .85, w * .3, b, .18); }
    else if (k === "drops") { for (i = 0; i < 26; i++) { x = seeded(i + 8) * w; y = seeded(i + 33) * h; ctx.globalAlpha = .3; ctx.strokeStyle = a; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 10, y + 34); ctx.stroke(); } }
    else if (k === "grid") { ctx.globalAlpha = .1; ctx.strokeStyle = a; ctx.lineWidth = 2; for (i = 1; i < 12; i++) { ctx.beginPath(); ctx.moveTo(w * i / 12, 0); ctx.lineTo(w * i / 12, h); ctx.stroke(); } for (i = 1; i < 16; i++) { ctx.beginPath(); ctx.moveTo(0, h * i / 16); ctx.lineTo(w, h * i / 16); ctx.stroke(); } disc(w * .9, h * .1, w * .2, a, .15); }
    ctx.restore();
  }

  /* ---------- extra layouts (all editable: headline + supporting line; use ";" to separate parts) ---------- */
  function clamp01(v) { return Math.max(0, Math.min(1, v)); }
  function partsOf(s) { return String(s.items && s.items.length ? s.items.join(";") : s.sub || "").split(/[;|\n]/).map(function (x) { return x.trim(); }).filter(Boolean); }
  function countTo(txt, p, live) { if (!live) return txt; var m = String(txt).match(/^(\D*)(\d[\d,]*)(.*)$/); if (!m) return txt; var v = parseInt(m[2].replace(/,/g, ""), 10), e = 1 - Math.pow(1 - clamp01(p * 1.3), 3), n = Math.round(v * e); return m[1] + (m[2].indexOf(",") > -1 ? n.toLocaleString("en-IN") : n) + m[3]; }
  function grad2(ctx, x, y, w, h, a, b) { var g = ctx.createLinearGradient(x, y, x + w, y + h); g.addColorStop(0, a); g.addColorStop(1, b); return g; }
  var NEWL = {
    photo: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, hasImg = !!(s.img && s._im && s._im.complete), py = h * .54, ph = h * .32;
      if (!hasImg) { ctx.fillStyle = P.accent + "33"; ctx.beginPath(); ctx.arc(w / 2, h * .34, w * .27, 0, 7); ctx.fill(); ctx.font = Math.round(w * .34) + "px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff"; ctx.fillText(s.emoji || "📸", w / 2, h * .34 + 6); ctx.textAlign = "left"; ctx.textBaseline = "top"; }
      ctx.fillStyle = hasImg ? "rgba(10,8,24,.72)" : P.soft + "ee"; roundRect(ctx, m * .6, py, w - m * 1.2, ph, 36); ctx.fill();
      ctx.fillStyle = P.accent; roundRect(ctx, m, py + 30, w * .1, 8, 4); ctx.fill();
      var t = fit(ctx, s.headline || "", mw, ph * .5, Math.round(w * .085), 34, 800); ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, py + 56, t.f, "#ffffff", c.rev);
      if (s.sub) { ctx.font = "500 " + Math.round(w * .037) + "px " + FONT; drawText(ctx, wrap(ctx, s.sub, mw), m, y + 14, w * .037, "#ffffffdd", null); }
    },
    split: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, ty = c.zoneTop - h * .02, th = h * .27, hasImg = !!(s.img && s._im && s._im.complete);
      ctx.fillStyle = grad2(ctx, m, ty, mw, th, P.accent, P.accent2 || P.accent); roundRect(ctx, m, ty, mw, th, 44); ctx.fill();
      ctx.font = Math.round(th * .62) + "px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff"; ctx.fillText(s.emoji || "✨", w / 2, ty + th / 2 + 6); ctx.textAlign = "left"; ctx.textBaseline = "top";
      var t = fit(ctx, s.headline || "", mw, h * .2, Math.round(w * .095), 38, 800); ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, ty + th + 36, t.f, P.fg, c.rev);
      if (s.sub) { ctx.font = "500 " + Math.round(w * .04) + "px " + FONT; y = drawText(ctx, wrap(ctx, s.sub, mw), m, y + 14, w * .04, P.fg + "dd", null); }
      ctx.fillStyle = P.fg + "22"; roundRect(ctx, m, y + 22, w * .36, w * .08, w * .04); ctx.fill(); ctx.font = "700 " + Math.round(w * .03) + "px " + FONT; ctx.fillStyle = P.fg; ctx.fillText("Tap for details  →", m + 24, y + 22 + w * .022);
    },
    price: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), name = pa[0] || "", old = pa[1] || "", note = pa[2] || "", bh = h * .5, by = h * .5 - bh / 2 + h * .01;
      ctx.fillStyle = grad2(ctx, m, by, mw, bh, P.accent, P.accent2 || P.accent); roundRect(ctx, m, by, mw, bh, 48); ctx.fill();
            ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = P.on; ctx.font = "700 " + Math.round(w * .042) + "px " + FONT; ctx.fillText(name.slice(0, 34), w / 2, by + bh * .1);
      var price = countTo(s.headline || "₹499", c.p, c.live), t = fit(ctx, price, mw - 140, bh * .38, Math.round(w * .24), 60, 800); ctx.font = "800 " + t.f + "px " + FONT; ctx.fillText(price, w / 2, by + bh * .26);
      if (old) { ctx.font = "600 " + Math.round(w * .06) + "px " + FONT; var ow = ctx.measureText(old).width, oy = by + bh * .26 + t.f * 1.12 + 6; ctx.globalAlpha = .75; ctx.fillText(old, w / 2, oy); ctx.fillRect(w / 2 - ow / 2, oy + w * .032, ow, 5); ctx.globalAlpha = 1;
        var a = parseFloat(old.replace(/[^\d.]/g, "")), b = parseFloat(String(s.headline || "").replace(/[^\d.]/g, "")); if (a > b && b > 0) { var pc = Math.round(100 * (a - b) / a); ctx.save(); ctx.translate(w - m - 30, by + 10); ctx.rotate(.22); ctx.fillStyle = "#ffffff"; ctx.beginPath(); ctx.arc(0, 0, w * .09, 0, 7); ctx.fill(); ctx.fillStyle = "#111"; ctx.textBaseline = "middle"; ctx.font = "800 " + Math.round(w * .042) + "px " + FONT; ctx.fillText(pc + "%", 0, -8); ctx.font = "700 " + Math.round(w * .024) + "px " + FONT; ctx.fillText("OFF", 0, w * .03); ctx.restore(); ctx.textBaseline = "top"; } }
      if (note) { ctx.font = "700 " + Math.round(w * .036) + "px " + FONT; var nw = ctx.measureText(note).width + 56; ctx.fillStyle = P.bg; roundRect(ctx, w / 2 - nw / 2, by + bh - bh * .17, nw, w * .075, w * .037); ctx.fill(); ctx.fillStyle = P.fg; ctx.fillText(note, w / 2, by + bh - bh * .17 + w * .017); }
      ctx.textAlign = "left";
    },
    countdown: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, cx = w / 2, cy = h * .4, r = w * .27, sweep = c.live ? clamp01(c.p * 1.2) : 1;
      ctx.lineWidth = w * .035; ctx.strokeStyle = P.fg + "22"; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke();
      ctx.strokeStyle = P.accent; ctx.lineCap = "round"; ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * .78 * sweep); ctx.stroke(); ctx.lineCap = "butt";
      var n = String(s.headline || "3"), t = fit(ctx, n, r * 1.5, r * 1.3, Math.round(w * .34), 70, 800); ctx.font = "800 " + t.f + "px " + FONT; ctx.fillStyle = P.fg; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(n, cx, cy + 6);
      ctx.textBaseline = "top"; var sub = s.sub || "days to go", sf = fit(ctx, sub, mw, h * .15, Math.round(w * .075), 34, 800); ctx.font = "800 " + sf.f + "px " + FONT; ctx.fillStyle = P.accent; var y = cy + r + 60;
      sf.lines.forEach(function (ln, i) { ctx.fillText(ln, cx, y + i * sf.f * 1.15); }); ctx.textAlign = "left";
    },
    review: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, cy = h * .5, ch = h * .4, cyy = cy - ch / 2;
      ctx.save(); ctx.shadowColor = "rgba(0,0,0,.35)"; ctx.shadowBlur = 40; ctx.shadowOffsetY = 18; ctx.fillStyle = "#ffffff"; roundRect(ctx, m * .8, cyy, w - m * 1.6, ch, 44); ctx.fill(); ctx.restore();
      ctx.font = Math.round(w * .075) + "px sans-serif"; ctx.fillStyle = "#f59e0b"; ctx.textBaseline = "top"; ctx.fillText("★★★★★", m * 1.4, cyy + 40);
      var t = fit(ctx, s.headline || "", mw - 40, ch * .5, Math.round(w * .078), 30, 700); ctx.font = "700 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m * 1.4, cyy + 40 + w * .11, t.f, "#1a1033", c.rev);
      var nm = s.sub || "Happy customer"; ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(m * 1.4 + 28, cyy + ch - 64, 28, 0, 7); ctx.fill(); ctx.fillStyle = P.on; ctx.font = "800 " + Math.round(w * .036) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(nm.charAt(0).toUpperCase(), m * 1.4 + 28, cyy + ch - 62); ctx.textAlign = "left";
      ctx.fillStyle = "#1a1033"; ctx.font = "700 " + Math.round(w * .036) + "px " + FONT; ctx.fillText(nm, m * 1.4 + 76, cyy + ch - 92); ctx.fillStyle = "#16a34a"; ctx.font = "600 " + Math.round(w * .028) + "px " + FONT; ctx.fillText("✔ Verified customer", m * 1.4 + 76, cyy + ch - 50);
    },
    spotlight: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, cx = w / 2, cy = h * .34, r = w * .27, hasImg = !!(s.img && s._im && s._im.complete), pa = partsOf(s);
      ctx.fillStyle = P.accent + "33"; ctx.beginPath(); ctx.arc(cx, cy, r * 1.22, 0, 7); ctx.fill();
      ctx.fillStyle = grad2(ctx, cx - r, cy - r, r * 2, r * 2, P.accent, P.accent2 || P.accent); ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
      ctx.font = Math.round(r * 1.1) + "px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff"; ctx.fillText(s.emoji || "🎁", cx, cy + 6);
      ctx.textBaseline = "top"; var t = fit(ctx, s.headline || "", mw, h * .16, Math.round(w * .09), 36, 800); ctx.font = "800 " + t.f + "px " + FONT; ctx.fillStyle = P.fg; var y = cy + r * 1.22 + 36; t.lines.forEach(function (ln, i) { ctx.fillText(ln, cx, y + i * t.f * 1.12); }); y += t.lines.length * t.f * 1.12 + 22;
      ctx.font = "700 " + Math.round(w * .036) + "px " + FONT; var chips = pa.slice(0, 4), tot = chips.reduce(function (a, x) { return a + ctx.measureText(x).width + 56; }, 0) + (chips.length - 1) * 14, x = cx - Math.min(tot, mw) / 2, row = 0;
      chips.forEach(function (ch) { var cw = ctx.measureText(ch).width + 56; if (x + cw > w - m + 4) { x = m; row++; } ctx.fillStyle = P.fg + "24"; roundRect(ctx, x, y + row * w * .1, cw, w * .08, w * .04); ctx.fill(); ctx.fillStyle = P.fg; ctx.textAlign = "left"; ctx.fillText("✓ " + ch, x + 24, y + row * w * .1 + w * .02); x += cw + 14; });
      ctx.textAlign = "left";
    },
    poll: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), t = fit(ctx, s.headline || "Which one?", mw, h * .2, Math.round(w * .1), 38, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop, t.f, P.fg, c.rev) + 34, bh = h * .105;
      [pa[0] || "Option A", pa[1] || "Option B"].forEach(function (o, i) { var yy = y + i * (bh + 22); ctx.fillStyle = i ? P.fg + "1f" : P.accent; roundRect(ctx, m, yy, mw, bh, bh / 2); ctx.fill(); ctx.fillStyle = i ? P.fg : P.on; ctx.font = "800 " + Math.round(w * .05) + "px " + FONT; ctx.textBaseline = "middle"; ctx.fillText((i ? "B  " : "A  ") + o.slice(0, 26), m + 44, yy + bh / 2 + 3); ctx.textBaseline = "top"; });
      ctx.font = "700 " + Math.round(w * .034) + "px " + FONT; ctx.fillStyle = P.fg + "cc"; ctx.textAlign = "center"; ctx.fillText("Tap to vote 👆", w / 2, y + 2 * (bh + 22) + 14); ctx.textAlign = "left";
    },
    bold: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, words = String(s.headline || "").toUpperCase().split(/\s+/).filter(Boolean).slice(0, 6), n = words.length || 1, y = h * .5 - (Math.min(w * .26, h / (n + 1.5)) * n * 1.02) / 2 - h * .02;
      var fs = Math.min(Math.round(w * .26), Math.round(h / (n + 2)));
      words.forEach(function (wd, i) { var f = fs; ctx.font = "800 " + f + "px " + FONT; while (ctx.measureText(wd).width > mw && f > 40) { f -= 4; ctx.font = "800 " + f + "px " + FONT; }
        var a = c.live ? clamp01(c.p * (n + 1) - i) : 1; ctx.save(); ctx.globalAlpha = a; ctx.translate((1 - a) * -w * .08, 0); ctx.fillStyle = i % 2 ? P.accent : P.fg; ctx.textBaseline = "top"; ctx.fillText(wd, m, y + i * fs * 1.0); ctx.restore(); });
      if (s.sub) { ctx.font = "600 " + Math.round(w * .04) + "px " + FONT; drawText(ctx, wrap(ctx, s.sub, mw), m, y + n * fs + 24, w * .04, P.fg + "dd", null); }
    }
  };
  function progressBar(ctx, w, h, idx, total, frac) { if (total < 2) return; var m = Math.round(w * .085), bw = (w - m * 2 - (total - 1) * 8) / total, by = Math.round(h * .028); for (var bi = 0; bi < total; bi++) { var f = bi < idx ? 1 : bi === idx ? clamp01(frac) : 0; ctx.fillStyle = "rgba(255,255,255,.28)"; roundRect(ctx, m + bi * (bw + 8), by, bw, 7, 3.5); ctx.fill(); if (f > 0) { ctx.fillStyle = "#ffffff"; roundRect(ctx, m + bi * (bw + 8), by, Math.max(7, bw * f), 7, 3.5); ctx.fill(); } } }

  function kv(str) { var m = String(str).split(/\s+[-–|]\s+|\s{2,}/); return m.length > 1 ? [m.slice(0, -1).join(" "), m[m.length - 1]] : [str, ""]; }
  var NEWL2 = {
    coupon: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), bh = h * .46, by = h * .5 - bh / 2, r = 40, nx = m + mw * .66;
      ctx.fillStyle = grad2(ctx, m, by, mw, bh, P.accent, P.accent2 || P.accent); roundRect(ctx, m, by, mw, bh, r); ctx.fill();
      ctx.fillStyle = P.bg; [by + bh * .5].forEach(function (yy) { ctx.beginPath(); ctx.arc(m, yy, 34, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(m + mw, yy, 34, 0, 7); ctx.fill(); });
      ctx.setLineDash([14, 12]); ctx.strokeStyle = P.on + "88"; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(m + 60, by + bh * .5); ctx.lineTo(m + mw - 60, by + bh * .5); ctx.stroke(); ctx.setLineDash([]);
      ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = P.on; var hd = countTo(s.headline || "20% OFF", c.p, c.live), t = fit(ctx, hd, mw - 100, bh * .3, Math.round(w * .2), 50, 800); ctx.font = "800 " + t.f + "px " + FONT; ctx.fillText(hd, w / 2, by + bh * .1);
      ctx.font = "600 " + Math.round(w * .04) + "px " + FONT; ctx.fillText((pa[2] || "On your first order").slice(0, 40), w / 2, by + bh * .1 + t.f * 1.15 + 6);
      var code = pa[0] || "CODE20", cw = Math.min(mw - 120, w * .5); ctx.setLineDash([12, 8]); ctx.strokeStyle = P.on; ctx.lineWidth = 5; roundRect(ctx, w / 2 - cw / 2, by + bh * .58, cw, bh * .2, 22); ctx.stroke(); ctx.setLineDash([]);
      ctx.font = "800 " + Math.round(w * .06) + "px " + FONT; ctx.fillText(code.replace(/^code:\s*/i, "").toUpperCase(), w / 2, by + bh * .58 + bh * .2 / 2 - w * .03); ctx.font = "600 " + Math.round(w * .032) + "px " + FONT; ctx.fillText(pa[1] || "Valid this week", w / 2, by + bh * .84); ctx.textAlign = "left";
    },
    menu: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, rows = partsOf(s).slice(0, 6), t = fit(ctx, s.headline || "Menu", mw, h * .16, Math.round(w * .1), 38, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop - h * .02, t.f, P.fg, c.rev) + 8; ctx.fillStyle = P.accent; ctx.fillRect(m, y, w * .14, 8); y += 44;
      var fs = Math.round(w * .054), step = Math.min(w * .15, (h * .62 - (y - c.zoneTop)) / Math.max(rows.length, 1));
      rows.forEach(function (r, i) { var a = kv(r), yy = y + i * step; ctx.font = "700 " + fs + "px " + FONT; ctx.fillStyle = P.fg; ctx.textBaseline = "top"; ctx.fillText(a[0].slice(0, 28), m, yy); var pw = 0; if (a[1]) { ctx.fillStyle = P.accent; ctx.textAlign = "right"; ctx.fillText(a[1], m + mw, yy); pw = ctx.measureText(a[1]).width; ctx.textAlign = "left"; ctx.font = "700 " + fs + "px " + FONT; }
        var nw = ctx.measureText(a[0].slice(0, 28)).width; ctx.setLineDash([3, 9]); ctx.strokeStyle = P.fg + "66"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(m + nw + 16, yy + fs * .85); ctx.lineTo(m + mw - pw - 16, yy + fs * .85); ctx.stroke(); ctx.setLineDash([]); });
    },
    timeline: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, rows = partsOf(s).slice(0, 5), t = fit(ctx, s.headline || "How it works", mw, h * .14, Math.round(w * .09), 36, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop - h * .02, t.f, P.fg, c.rev) + 36, step = Math.min(w * .17, (h * .66 - (y - c.zoneTop)) / Math.max(rows.length, 1)), x = m + 36;
      ctx.strokeStyle = P.accent + "88"; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x, y + 30); ctx.lineTo(x, y + step * (rows.length - 1) + 30); ctx.stroke();
      rows.forEach(function (r, i) { var yy = y + i * step; ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(x, yy + 30, 34, 0, 7); ctx.fill(); ctx.fillStyle = P.on; ctx.font = "800 " + Math.round(w * .045) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(String(i + 1), x, yy + 33); ctx.textAlign = "left"; ctx.textBaseline = "top";
        ctx.fillStyle = P.fg; ctx.font = "700 " + Math.round(w * .046) + "px " + FONT; drawText(ctx, wrap(ctx, r, mw - 120).slice(0, 2), x + 62, yy + 8, w * .046, P.fg, null); });
    },
    stat3: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, rows = partsOf(s).slice(0, 3), t = fit(ctx, s.headline || "In numbers", mw, h * .14, Math.round(w * .085), 36, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop - h * .02, t.f, P.fg, c.rev) + 28, bh = Math.min(h * .17, (h * .62 - (y - c.zoneTop)) / Math.max(rows.length, 1) - 18);
      rows.forEach(function (r, i) { var sp = r.split(/\s+/), val = countTo(sp[0], c.p, c.live), lab = sp.slice(1).join(" "), yy = y + i * (bh + 18); ctx.fillStyle = i % 2 ? P.fg + "1c" : P.accent; roundRect(ctx, m, yy, mw, bh, 34); ctx.fill();
        ctx.fillStyle = i % 2 ? P.accent : P.on; ctx.font = "800 " + Math.round(bh * .56) + "px " + FONT; ctx.textBaseline = "middle"; ctx.fillText(val, m + 36, yy + bh / 2 + 3); var vw = ctx.measureText(val).width;
        ctx.fillStyle = i % 2 ? P.fg : P.on; ctx.font = "600 " + Math.round(w * .04) + "px " + FONT; ctx.fillText(lab.slice(0, 22), m + 36 + vw + 28, yy + bh / 2 + 3); ctx.textBaseline = "top"; });
    },
    event: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), bs = w * .36, by = c.zoneTop - h * .01;
      ctx.fillStyle = "#ffffff"; roundRect(ctx, m, by, bs, bs, 40); ctx.fill(); ctx.fillStyle = P.accent; ctx.save(); ctx.beginPath(); roundRect(ctx, m, by, bs, bs * .3, 40); ctx.clip(); ctx.fillRect(m, by, bs, bs * .3); ctx.restore();
      var dt = (pa[0] || "Sat 25").split(/\s+/); ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = P.on; ctx.font = "800 " + Math.round(bs * .15) + "px " + FONT; ctx.fillText((dt.slice(0, -1).join(" ") || "SAT").toUpperCase(), m + bs / 2, by + bs * .15); ctx.fillStyle = "#1a1033"; ctx.font = "800 " + Math.round(bs * .44) + "px " + FONT; ctx.fillText(dt[dt.length - 1] || "25", m + bs / 2, by + bs * .64); ctx.textAlign = "left"; ctx.textBaseline = "top";
      var t = fit(ctx, s.headline || "You are invited", mw, h * .26, Math.round(w * .11), 40, 800); ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, by + bs + 44, t.f, P.fg, c.rev) + 26;
      [["🕒", pa[1] || "7 PM onwards"], ["📍", pa[2] || "Your venue here"]].forEach(function (r, i) { ctx.fillStyle = P.fg + "22"; roundRect(ctx, m, y + i * w * .125, mw, w * .1, w * .05); ctx.fill(); ctx.fillStyle = P.fg; ctx.font = "600 " + Math.round(w * .042) + "px " + FONT; ctx.fillText(r[0] + "  " + r[1].slice(0, 34), m + 30, y + i * w * .125 + w * .027); });
    },
    ribbon: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), tag = (pa[1] || "NEW").toUpperCase().slice(0, 12);
      var t = fit(ctx, s.headline || "", mw, h * .36, Math.round(w * .15), 46, 800); ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, h * .5 - (t.lines.length * t.f * 1.12) / 2 + h * .03, t.f, P.fg, c.rev);
      if (pa[0]) { ctx.font = "500 " + Math.round(w * .042) + "px " + FONT; drawText(ctx, wrap(ctx, pa[0], mw), m, y + 22, w * .042, P.fg + "dd", null); }
      ctx.save(); ctx.translate(w * .78, h * .15); ctx.rotate(Math.PI / 4); ctx.fillStyle = P.accent; ctx.shadowColor = "rgba(0,0,0,.3)"; ctx.shadowBlur = 20; ctx.fillRect(-w * .36, -w * .06, w * .72, w * .12); ctx.shadowBlur = 0; ctx.fillStyle = P.on; ctx.font = "800 " + Math.round(w * .06) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(tag, 0, 3); ctx.restore(); ctx.textAlign = "left"; ctx.textBaseline = "top";
    },
    collage: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, rows = partsOf(s).slice(0, 4), em = ["✨", "🔥", "💛", "🎁"], t = fit(ctx, s.headline || "Our picks", mw, h * .14, Math.round(w * .09), 36, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop - h * .02, t.f, P.fg, c.rev) + 30, g = 22, tw = (mw - g) / 2, th = Math.min(tw * 1.05, (h * .64 - (y - c.zoneTop) - g) / 2);
      for (var i = 0; i < 4; i++) { var x = m + (i % 2) * (tw + g), yy = y + Math.floor(i / 2) * (th + g); ctx.fillStyle = i === 0 || i === 3 ? P.accent : P.fg + "1f"; roundRect(ctx, x, yy, tw, th, 36); ctx.fill();
        ctx.font = Math.round(th * .42) + "px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff"; ctx.fillText(em[i], x + tw / 2, yy + th * .4);
        ctx.font = "700 " + Math.round(w * .036) + "px " + FONT; ctx.fillStyle = i === 0 || i === 3 ? P.on : P.fg; ctx.fillText((rows[i] || "").slice(0, 18), x + tw / 2, yy + th * .82); ctx.textAlign = "left"; ctx.textBaseline = "top"; }
    },
    magazine: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), words = String(s.headline || "").split(/\s+/), last = words.pop() || "", head = words.join(" ");
      ctx.fillStyle = P.fg; ctx.fillRect(m, c.zoneTop - h * .02, mw, 4); ctx.font = "700 " + Math.round(w * .03) + "px " + FONT; ctx.fillText((C.brand || "").toUpperCase() + "  ·  THE EDIT", m, c.zoneTop + 14);
      var t = fit(ctx, head, mw, h * .28, Math.round(w * .16), 50, 800); ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop + h * .06, t.f, P.fg, c.rev);
      var f2 = Math.round(w * .26); ctx.font = "italic 800 " + f2 + "px " + FONT; while (ctx.measureText(last).width > mw && f2 > 50) { f2 -= 6; ctx.font = "italic 800 " + f2 + "px " + FONT; } ctx.fillStyle = P.accent; ctx.fillText(last, m, y - 6);
      ctx.fillStyle = P.fg; ctx.fillRect(m, y + f2 * 1.15, mw, 4); if (pa[0]) { ctx.font = "500 " + Math.round(w * .04) + "px " + FONT; drawText(ctx, wrap(ctx, pa[0], mw * .62), m, y + f2 * 1.15 + 26, w * .04, P.fg + "dd", null); }
      if (pa[1]) { ctx.save(); ctx.translate(w - m - w * .1, y + f2 * 1.15 + w * .12); ctx.rotate(-.2); ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(0, 0, w * .11, 0, 7); ctx.fill(); ctx.fillStyle = P.on; ctx.font = "800 " + Math.round(w * .036) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; wrap(ctx, pa[1], w * .17).slice(0, 3).forEach(function (ln, i, a) { ctx.fillText(ln, 0, (i - (a.length - 1) / 2) * w * .042); }); ctx.restore(); ctx.textAlign = "left"; ctx.textBaseline = "top"; }
    },
    versus: function (c) {
      var ctx = c.ctx, s = c.s, P = c.P, w = c.w, h = c.h, m = c.m, mw = c.mw, pa = partsOf(s), t = fit(ctx, s.headline || "This vs that", mw, h * .14, Math.round(w * .085), 36, 800);
      ctx.font = "800 " + t.f + "px " + FONT; var y = drawText(ctx, t.lines, m, c.zoneTop - h * .02, t.f, P.fg, c.rev) + 30, bh = h * .46, cw = (mw - 20) / 2;
      [[pa[0] || "Option A", P.fg + "1f", P.fg, "A"], [pa[1] || "Option B", P.accent, P.on, "B"]].forEach(function (col, i) { var x = m + i * (cw + 20); ctx.fillStyle = col[1]; roundRect(ctx, x, y, cw, bh, 40); ctx.fill(); ctx.fillStyle = col[2]; ctx.globalAlpha = .22; ctx.font = "800 " + Math.round(cw * .8) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(col[3], x + cw / 2, y + bh * .42); ctx.globalAlpha = 1;
        ctx.font = "800 " + Math.round(w * .052) + "px " + FONT; var ls = wrap(ctx, col[0], cw - 50).slice(0, 4); ctx.textBaseline = "top"; ls.forEach(function (ln, k) { ctx.fillText(ln, x + cw / 2, y + bh * .62 + k * w * .06 - (ls.length > 2 ? w * .05 : 0)); }); ctx.textAlign = "left"; });
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(w / 2, y + bh / 2, 46, 0, 7); ctx.fill(); ctx.fillStyle = "#1a1033"; ctx.font = "800 " + Math.round(w * .044) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("VS", w / 2, y + bh / 2 + 2); ctx.textAlign = "left"; ctx.textBaseline = "top";
    }
  };
  for (var k2 in NEWL2) NEWL[k2] = NEWL2[k2];
  function render(ctx, s, w, h, o) {
    o = o || {}; var P = palette(s), m = Math.round(w * .085), mw = w - m * 2, p = o.p == null ? 1 : o.p, anim = o.anim || "pop", idx = o.idx || 0, total = o.total || 1;
    ctx.save(); ctx.clearRect(0, 0, w, h);
    if (P.bg2) { var bgG = ctx.createLinearGradient(0, 0, w * .7, h); bgG.addColorStop(0, P.bg); bgG.addColorStop(1, P.bg2); ctx.fillStyle = bgG; } else ctx.fillStyle = P.bg;
    var live = o.t != null, kb = live ? 1 + .07 * clamp01(o.t / (o.T || 3)) : 1;
    if (live) { ctx.save(); ctx.translate(w / 2, h / 2); ctx.scale(kb, kb); ctx.translate(-w / 2, -h / 2); ctx.fillRect(-w * .1, -h * .1, w * 1.2, h * 1.2); } else ctx.fillRect(0, 0, w, h);
    if (P.motif) { if (live) { ctx.save(); ctx.translate(Math.sin(o.t * .9 + idx) * w * .015, Math.cos(o.t * .7 + idx) * h * .012 - o.t * h * .006); } motif(ctx, w, h, P, idx); if (live) ctx.restore(); }
    if (live) ctx.restore();
    var g = ctx.createRadialGradient(w * .85, h * .12, 10, w * .85, h * .12, w * .8); g.addColorStop(0, P.accent + "55"); g.addColorStop(1, P.accent + "00"); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = P.soft; ctx.beginPath(); ctx.arc(w * .08, h * .96, w * .32, 0, 7); ctx.fill();
    var im = imgOf(s);
    if (im && im.complete && im.naturalWidth) { var k = Math.max(w / im.naturalWidth, h / im.naturalHeight), iw = im.naturalWidth * k, ih = im.naturalHeight * k; ctx.drawImage(im, (w - iw) / 2, (h - ih) / 2, iw, ih); ctx.fillStyle = "rgba(0,0,0,.52)"; ctx.fillRect(0, 0, w, h); P = { bg: P.bg, fg: "#ffffff", accent: P.accent, soft: P.soft, on: P.on }; }
    /* brand bar */
    ctx.font = "700 " + Math.round(w * .033) + "px " + FONT; ctx.textBaseline = "top"; ctx.fillStyle = P.fg;
    var bx = m, by = Math.round(h * (o.safe ? .09 : .05));
    if (logo && !S.noLogo && logo.complete && logo.naturalWidth) { var lh = Math.round(w * .06); try { ctx.drawImage(logo, bx, by - 6, lh * logo.naturalWidth / logo.naturalHeight, lh); bx += lh * logo.naturalWidth / logo.naturalHeight + 14; } catch (e) { S.noLogo = true; } }
    else { ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(bx + 12, by + Math.round(w * .017), 12, 0, 7); ctx.fill(); bx += 34; }
    ctx.fillStyle = P.fg; ctx.fillText(C.brand, bx, by);
    if (total > 1) { ctx.textAlign = "right"; ctx.globalAlpha = .7; ctx.fillText((idx + 1) + " / " + total, w - m, by); ctx.globalAlpha = 1; ctx.textAlign = "left"; }
    /* animated content block */
    var e = 1 - Math.pow(1 - Math.min(1, p), 3), ob = e + (anim === "pop" ? .0 : 0);
    ctx.save(); ctx.globalAlpha = Math.min(1, p * 2.2);
    var cy = h * .5; ctx.translate(w / 2, cy);
    if (anim === "pop") { var sc = .82 + .18 * (1 + 1.6 * Math.pow(e - 1, 3) + 1.6 * Math.pow(e - 1, 2)); ctx.scale(Math.min(1.04, sc), Math.min(1.04, sc)); }
    if (anim === "slide") ctx.translate(0, (1 - e) * h * .08);
    if (anim === "zoom") ctx.scale(1.18 - .18 * e, 1.18 - .18 * e);
    if (live) ctx.translate(0, Math.sin(o.t * 2.1) * h * .0035);
    ctx.translate(-w / 2, -cy);
    if (anim === "wipe") { ctx.beginPath(); ctx.rect(0, 0, w * Math.min(1, e * 1.05), h); ctx.clip(); }
    var rev = anim === "type" ? Math.min(1, p * 1.25) : null, top = Math.round(h * .24), L = s.layout || "step", head = s.headline || "", sub = s.sub || "";
    var zoneTop = o.safe ? h * .2 : h * .17, zoneH = h * (o.safe ? .5 : .62);
    if (L === "cover") {
      var t = fit(ctx, head, mw, zoneH * .62, Math.round(w * .13), 44, 800); ctx.font = "800 " + t.f + "px " + FONT;
      var y = drawText(ctx, t.lines, m, h * .5 - (t.lines.length * t.f * 1.12) / 2 - h * .04, t.f, P.fg, rev);
      ctx.fillStyle = P.accent; ctx.fillRect(m, y + 24, w * .16, 10);
      if (sub) { ctx.font = "500 " + Math.round(w * .036) + "px " + FONT; drawText(ctx, wrap(ctx, sub, mw), m, y + 56, w * .036, P.fg + "cc", null); }
    } else if (L === "step" || L === "tip") {
      var nm = s.num != null ? String(s.num) : (L === "tip" ? "★" : "✓"), d = Math.round(w * .17);
      ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(m + d / 2, zoneTop + d / 2, d / 2, 0, 7); ctx.fill();
      ctx.font = "800 " + Math.round(d * .55) + "px " + FONT; ctx.fillStyle = P.on; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(nm, m + d / 2, zoneTop + d / 2 + 4); ctx.textAlign = "left";
      var t2 = fit(ctx, head, mw, zoneH * .36, Math.round(w * .095), 40, 800); ctx.font = "800 " + t2.f + "px " + FONT; var y2 = drawText(ctx, t2.lines, m, zoneTop + d + 40, t2.f, P.fg, rev);
      if (sub) { ctx.font = "500 " + Math.round(w * .04) + "px " + FONT; drawText(ctx, wrap(ctx, sub, mw), m, y2 + 26, w * .04, P.fg + "dd", null); }
    } else if (L === "quote") {
      ctx.font = "800 " + Math.round(w * .3) + "px " + FONT; ctx.fillStyle = P.accent; ctx.textBaseline = "top"; ctx.fillText("“", m - 10, zoneTop - w * .06);
      var t3 = fit(ctx, head, mw, zoneH * .5, Math.round(w * .082), 38, 700); ctx.font = "700 " + t3.f + "px " + FONT; var y3 = drawText(ctx, t3.lines, m, zoneTop + w * .2, t3.f, P.fg, rev);
      if (sub) { ctx.font = "600 " + Math.round(w * .035) + "px " + FONT; ctx.fillStyle = P.accent; ctx.fillText("— " + sub, m, y3 + 30); }
    } else if (L === "list") {
      var t4 = fit(ctx, head, mw, zoneH * .22, Math.round(w * .085), 38, 800); ctx.font = "800 " + t4.f + "px " + FONT; var y4 = drawText(ctx, t4.lines, m, zoneTop, t4.f, P.fg, rev) + 30;
      var items = (s.items && s.items.length ? s.items : String(sub).split(/[;|\n]/)).filter(Boolean).slice(0, 5);
      ctx.font = "600 " + Math.round(w * .042) + "px " + FONT;
      items.forEach(function (it) { ctx.fillStyle = P.accent; ctx.beginPath(); ctx.arc(m + 14, y4 + w * .02, 14, 0, 7); ctx.fill(); ctx.fillStyle = P.fg; var ls = wrap(ctx, it, mw - 60); y4 = drawText(ctx, ls, m + 50, y4, w * .042, P.fg, null) + 22; });
    } else if (L === "stat") {
      head = countTo(head, p, live); var t7 = fit(ctx, head, mw, zoneH * .5, Math.round(w * .32), 70, 800); while (t7.lines.length === 1 && t7.f > 40 && (ctx.font = "800 " + t7.f + "px " + FONT, ctx.measureText(t7.lines[0]).width > mw)) t7.f -= 6; ctx.font = "800 " + t7.f + "px " + FONT; ctx.fillStyle = P.accent;
      var y7 = drawText(ctx, t7.lines, m, h * .5 - (t7.lines.length * t7.f * 1.12) / 2 - h * .05, t7.f, P.accent, rev);
      ctx.fillStyle = P.fg; ctx.fillRect(m, y7 + 18, w * .12, 8);
      if (sub) { ctx.font = "600 " + Math.round(w * .05) + "px " + FONT; drawText(ctx, wrap(ctx, sub, mw), m, y7 + 56, w * .05, P.fg, null); }
    } else if (L === "compare") {
      var parts = (s.items && s.items.length ? s.items : String(sub).split(/[;|\n]/)).filter(Boolean), bh3 = zoneH * .3;
      var t8 = fit(ctx, head, mw, zoneH * .2, Math.round(w * .08), 36, 800); ctx.font = "800 " + t8.f + "px " + FONT; var y8 = drawText(ctx, t8.lines, m, zoneTop - h * .02, t8.f, P.fg, rev) + 24;
      [["Before", parts[0] || "", P.fg + "22", P.fg], ["After", parts[1] || "", P.accent, P.on]].forEach(function (c, i) {
        var yy2 = y8 + i * (bh3 + 20); ctx.fillStyle = c[2]; roundRect(ctx, m, yy2, mw, bh3, 28); ctx.fill();
        ctx.fillStyle = c[3]; ctx.font = "700 " + Math.round(w * .03) + "px " + FONT; ctx.fillText(c[0], m + 28, yy2 + 24);
        ctx.font = "700 " + Math.round(w * .05) + "px " + FONT; drawText(ctx, wrap(ctx, c[1], mw - 56), m + 28, yy2 + 24 + w * .05, w * .05, c[3], null);
      });
    } else if (L === "offer") {
      ctx.fillStyle = P.accent; var bh = zoneH * .5; roundRect(ctx, m, h * .5 - bh / 2, mw, bh, 36); ctx.fill();
      var t5 = fit(ctx, head, mw - 80, bh * .6, Math.round(w * .12), 40, 800); ctx.font = "800 " + t5.f + "px " + FONT; ctx.textAlign = "center";
      var yy = h * .5 - (t5.lines.length * t5.f * 1.12) / 2 - 10; ctx.fillStyle = P.on; t5.lines.forEach(function (ln, i) { ctx.textBaseline = "top"; ctx.fillText(rev == null ? ln : ln.slice(0, Math.floor(rev * ln.length)), w / 2, yy + i * t5.f * 1.12); });
      if (sub) { ctx.font = "600 " + Math.round(w * .038) + "px " + FONT; ctx.fillText(sub, w / 2, yy + t5.lines.length * t5.f * 1.12 + 20); } ctx.textAlign = "left";
    } else if (NEWL[L]) { NEWL[L]({ ctx: ctx, s: s, P: P, w: w, h: h, m: m, mw: mw, zoneTop: zoneTop, zoneH: zoneH, rev: rev, p: p, live: o.t != null, o: o });
    } else { /* cta */
      var t6 = fit(ctx, head, mw, zoneH * .4, Math.round(w * .11), 40, 800); ctx.font = "800 " + t6.f + "px " + FONT; var y6 = drawText(ctx, t6.lines, m, h * .38, t6.f, P.fg, rev) + 30;
      if (sub) { ctx.font = "600 " + Math.round(w * .04) + "px " + FONT; var sl = wrap(ctx, sub, mw - 170), bh2 = Math.max(sl.length * w * .045 + 56, 110); ctx.fillStyle = P.accent; var rr = bh2 / 2 > 60 ? 40 : bh2 / 2; roundRect(ctx, m, y6, mw, bh2, rr); ctx.fill(); drawText(ctx, wrap(ctx, sub, mw - 170), m + 40, y6 + 28, w * .045, P.on, null); ctx.fillStyle = P.on; ctx.beginPath(); ctx.arc(m + mw - 62, y6 + bh2 / 2, 36, 0, 7); ctx.fill(); ctx.fillStyle = P.accent; ctx.font = "800 " + Math.round(w * .05) + "px " + FONT; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("→", m + mw - 62, y6 + bh2 / 2 + 3); ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.font = "600 " + Math.round(w * .032) + "px " + FONT; ctx.fillStyle = P.fg + "cc"; ctx.fillText("💾 Save   📤 Share   💬 Comment", m, y6 + bh2 + 36); }
    }
    if (s.emoji && !{ spotlight: 1, split: 1, photo: 1, price: 1, review: 1, poll: 1, countdown: 1, bold: 1, coupon: 1, menu: 1, timeline: 1, stat3: 1, event: 1, ribbon: 1, collage: 1, magazine: 1, versus: 1 }[L]) { ctx.font = Math.round(w * .17) + "px sans-serif"; ctx.textAlign = "right"; ctx.textBaseline = "top"; ctx.fillText(s.emoji, w - m, h * .17); ctx.textAlign = "left"; }
    ctx.restore();
    if (live && o.t < .22 && o.flash) { ctx.fillStyle = "rgba(255,255,255," + (.35 * (1 - o.t / .22)).toFixed(3) + ")"; ctx.fillRect(0, 0, w, h); }
    ctx.font = "500 " + Math.round(w * .026) + "px " + FONT; 
    if (o.guides) { ctx.strokeStyle = "#ff3b6b"; ctx.lineWidth = 4; ctx.setLineDash([16, 12]); ctx.strokeRect(24, h * .1, w - 48, h * .68); ctx.setLineDash([]); ctx.fillStyle = "#ff3b6bcc"; ctx.font = "600 28px " + FONT; ctx.fillText("Keep text inside the box", 40, h * .1 + 10); }
    ctx.restore();
  }
  function roundRect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

  /* ---------- UI ---------- */
  try { document.fonts.load("800 40px \"Bricolage Grotesque\"").then(function(){ redraw(); }); document.fonts.load("500 20px Inter"); } catch (e) {}
  var cv = $("st-canvas"), ctx = cv ? cv.getContext("2d") : null;
  function dims() { return SIZES[S.size || DEF_SIZE[S.kind]] || SIZES["4:5"]; }
  function safeOn() { return S.kind === "reel" || S.kind === "story" || (S.size || DEF_SIZE[S.kind]) === "9:16"; }
  function redraw() { if (!cv) return;
    var d = dims(); if (cv.width !== d[0] || cv.height !== d[1]) { cv.width = d[0]; cv.height = d[1]; }
    if (!S.slides.length) { $("st-empty").hidden = false; cv.hidden = true; } else { $("st-empty").hidden = true; cv.hidden = false; render(ctx, S.slides[S.cur] || S.slides[0], d[0], d[1], { idx: S.cur, total: S.slides.length, guides: S.guides && safeOn(), safe: safeOn() && S.guides }); }
    thumbs(); runChecks();
  }
  function thumbs() {
    var box = $("st-strip"); box.innerHTML = ""; var d = dims();
    S.slides.forEach(function (s, i) {
      var c = document.createElement("canvas"), tw = 90, th = Math.round(90 * d[1] / d[0]); c.width = d[0]; c.height = d[1]; c.style.width = tw + "px"; c.style.height = th + "px"; c.className = "st-th" + (i === S.cur ? " on" : ""); c.title = "Slide " + (i + 1); c.tabIndex = 0;
      render(c.getContext("2d"), s, d[0], d[1], { idx: i, total: S.slides.length }); c.onclick = function () { S.cur = i; redraw(); editor(); }; c.onkeydown = function (e) { if (e.key === "Enter") c.onclick(); }; box.appendChild(c);
    });
  }
  var LABELS = { cover: "Cover", step: "Step", tip: "Tip", quote: "Quote", list: "List", stat: "Big number", compare: "Before / after", offer: "Offer", cta: "Call to action", photo: "Photo + caption", split: "Split card", price: "Price tag", countdown: "Countdown", review: "Review card", spotlight: "Product spotlight", poll: "Poll", bold: "Big words", coupon: "Coupon", menu: "Menu / price list", timeline: "Timeline", stat3: "3 numbers", event: "Event card", ribbon: "New ribbon", collage: "Collage tiles", magazine: "Magazine", versus: "Versus" };
  function editor() {
    var box = $("st-edit"); box.innerHTML = ""; var s = S.slides[S.cur]; if (!s) return;
    var h = '<label>Layout<select id="e-lay">' + Object.keys(LABELS).map(function (k) { return '<option value="' + k + '"' + (k === s.layout ? " selected" : "") + ">" + LABELS[k] + "</option>"; }).join("") + "</select></label>" +
      '<label>Headline<input id="e-head" maxlength="90" value=""></label><label>Supporting line<textarea id="e-sub" rows="2" maxlength="180"></textarea></label>' +
      '<div class="st-row"><button type="button" class="btn ghost sm" id="e-up" aria-label="Move slide earlier">←</button><button type="button" class="btn ghost sm" id="e-dn" aria-label="Move slide later">→</button><button type="button" class="btn ghost sm" id="e-dup">Duplicate</button><button type="button" class="btn ghost sm" id="e-del">Delete</button><button type="button" class="btn ghost sm" id="e-add">＋ Slide</button></div><label>Sticker emoji <input id="e-emoji" maxlength="4" placeholder="🔥" style="width:90px"></label>' + (S.kind === "reel" || S.kind === "story" ? '<div class="st-2"><label>Seconds on screen<input type="range" id="e-dur" min="1" max="6" step=".5"></label><label>Movement<select id="e-anim"><option value="">Auto</option>' + ANIMS.map(function (a) { return '<option value="' + a + '">' + a + "</option>"; }).join("") + "</select></label></div>" : "") + '<div class="st-row"><label class="btn ghost sm" style="margin:0;cursor:pointer">📷 Photo background<input type="file" id="e-photo" accept="image/*" hidden></label>' + (s.img ? '<button type="button" class="btn ghost sm" id="e-nophoto">Remove photo</button>' : "") + "</div>";
    box.innerHTML = h; $("e-head").value = s.headline || ""; $("e-sub").value = s.sub || "";
    $("e-lay").onchange = function () { s.layout = this.value; redraw(); };
    $("e-head").oninput = function () { s.headline = this.value; redraw(); }; $("e-sub").oninput = function () { s.sub = this.value; redraw(); };
    $("e-up").onclick = function () { mv(-1); }; $("e-dn").onclick = function () { mv(1); };
    $("e-dup").onclick = function () { S.slides.splice(S.cur + 1, 0, JSON.parse(JSON.stringify(s))); S.cur++; redraw(); editor(); };
    $("e-del").onclick = function () { if (S.slides.length > 1) { S.slides.splice(S.cur, 1); S.cur = Math.max(0, S.cur - 1); redraw(); editor(); } };
    $("e-emoji").value = s.emoji || ""; $("e-emoji").oninput = function () { s.emoji = this.value; redraw(); };
    if ($("e-dur")) { $("e-dur").value = s.dur || 2.4; $("e-dur").oninput = function () { s.dur = +this.value; runChecks(); }; $("e-anim").value = s.anim || ""; $("e-anim").onchange = function () { s.anim = this.value; }; }
    $("e-photo").onchange = function () { var f = this.files[0]; if (f) shrink(f, function (u) { s.img = u; s._im = null; redraw(); editor(); }); };
    if ($("e-nophoto")) $("e-nophoto").onclick = function () { delete s.img; s._im = null; redraw(); editor(); };
    $("e-add").onclick = function () { S.slides.splice(S.cur + 1, 0, { layout: "step", headline: "New point", sub: "Say it in one line" }); S.cur++; redraw(); editor(); };
  }
  function shrink(file, cb) { var r = new FileReader(); r.onload = function () { var i = new Image(); i.onload = function () { var k = Math.min(1, 720 / Math.max(i.width, i.height)), c = document.createElement("canvas"); c.width = Math.round(i.width * k); c.height = Math.round(i.height * k); c.getContext("2d").drawImage(i, 0, 0, c.width, c.height); cb(c.toDataURL("image/jpeg", .66)); }; i.src = r.result; }; r.readAsDataURL(file); }
  function strip(k, v) { return k.charAt(0) === "_" ? undefined : v; }
  function mv(dx) { var j = S.cur + dx; if (j < 0 || j >= S.slides.length) return; var t = S.slides[S.cur]; S.slides[S.cur] = S.slides[j]; S.slides[j] = t; S.cur = j; redraw(); editor(); }

  /* ---------- checks ---------- */
  var SEASON = { monsoon: [6, 7, 8, 9], rainy: [6, 7, 8, 9], summer: [3, 4, 5, 6], winter: [11, 12, 1, 2], christmas: [12], "new year": [12, 1], valentine: [2], "independence day": [8], "republic day": [1] };
  function checks() {
    var out = [], cap = ($("st-cap").value || ""), ch = $("st-chan").value, date = $("st-date").value, text = (cap + " " + S.slides.map(function (s) { return (s.headline || "") + " " + (s.sub || ""); }).join(" ")).toLowerCase();
    var hook = cap.slice(0, 125);
    if (!cap.trim()) out.push(["warn", "Write a caption. The first 125 characters are what people see before “more”."]);
    else if (hook.length < 30 || !/[?0-9]|\byou\b|\byour\b|\bpov\b|\bstop\b|don't|never|secret|new/i.test(hook)) out.push(["warn", "The hook is weak. Open with a question, a number, or “you”, within the first 125 characters."]);
    else out.push(["ok", "Hook looks good."]);
    var tags = ($("st-tags").value.match(/#\w+/g) || []).length, lim = ch === "LinkedIn" ? 3 : ch === "Instagram" ? 5 : 8;
    out.push([tags > lim ? "warn" : "ok", tags > lim ? tags + " hashtags. " + ch + " works best with " + lim + " or fewer." : tags + " hashtag" + (tags === 1 ? "" : "s") + ", fine."]);
    var cl = { Instagram: 2200, LinkedIn: 3000, "X / Twitter": 280, WhatsApp: 700 }[ch]; if (cl && cap.length > cl) out.push(["warn", "Caption is " + cap.length + " characters; " + ch + " allows about " + cl + "."]);
    var per = S.kind === "reel" || S.kind === "story" ? 2.2 : 0;
    S.slides.forEach(function (s, i) { var wds = ((s.headline || "") + " " + (s.sub || "")).trim().split(/\s+/).filter(Boolean).length; if (per && wds > per * 3.2) out.push(["warn", "Slide " + (i + 1) + " has " + wds + " words; viewers can read about " + Math.round(per * 3) + " in " + per + " seconds."]); else if (!per && wds > 34) out.push(["warn", "Slide " + (i + 1) + " has " + wds + " words. Shorter reads better."]); });
    if (S.kind === "reel" && S.slides.length < 3) out.push(["warn", "A reel works better with 4 to 6 scenes."]);
    if (date) {
      var mth = +date.slice(5, 7); Object.keys(SEASON).forEach(function (k) { if (text.indexOf(k) > -1 && SEASON[k].indexOf(mth) < 0) out.push(["warn", "This mentions “" + k + "” but is scheduled for " + new Date(date + "T00:00").toLocaleString("en-IN", { month: "long" }) + "."]); });
      (C.kd || []).forEach(function (k) { var key = (k.name || "").toLowerCase().replace(/\(.*?\)/g, "").trim().split(/\s+/)[0]; if (key.length > 3 && text.indexOf(key) > -1 && date > k.date) out.push(["warn", k.name + " is on " + k.date + ", before this post goes out."]); });
    }
    if (/\b(best|no\.? ?1|number one|guaranteed|100%|cure|lowest price|risk[- ]free)\b|\d+\s?% ?off/i.test(text)) out.push(["warn", "Claims check: discounts, prices or “best / No.1” wording may need approval or proof."]);
    if (!out.some(function (o) { return o[0] === "warn"; })) out.unshift(["ok", "Ready to go. Nothing to fix."]);
    return out;
  }
  /* hook rating: scores the first line out of 100 and offers sharper openers */
  var RZ_LABEL = C.rizz || "Rizz score";
  function rizzScore(t) {
    t = (t || "").trim(); if (!t) return 0; var w = t.split(/\s+/).length, sc = 40;
    if (w >= 3 && w <= 9) sc += 20; else if (w > 14) sc -= 15;
    if (/\d/.test(t)) sc += 12; if (/\?$/.test(t)) sc += 8; if (/\b(you|your|pov|stop|secret|nobody|mistake|free|new|last|only)\b/i.test(t)) sc += 14;
    if (/^(introducing|welcome|we are|our)\b/i.test(t)) sc -= 14; if (t.length > 70) sc -= 10; if (/[!]{2,}/.test(t)) sc -= 6;
    return Math.max(5, Math.min(98, sc));
  }
  function renderRizz() {
    var box = $("st-rizz"); if (!box) return; var s0 = S.slides[0]; if (!s0) { box.innerHTML = ""; return; }
    var head = (s0.headline || "").trim(), sc = rizzScore(head), topic = head.replace(/[?!.:]+$/g, "").split(/\s+/).slice(0, 6).join(" ").toLowerCase() || "this";
    var opts = [topic.charAt(0).toUpperCase() + topic.slice(1) + "? Read this first.", "3 things nobody tells you about " + topic, "POV: you finally sorted " + topic, "Stop scrolling: " + topic].filter(function (o) { return o !== head; }).slice(0, 3);
    box.innerHTML = '<div class="rz"><b>' + esc(RZ_LABEL) + ': ' + sc + '/100</b> <span class="muted">' + (sc >= 75 ? "Strong first line." : sc >= 55 ? "Decent. Try one below." : "Weak opener. Try one below.") + "</span></div>" +
      (sc < 85 ? '<div class="st-chips">' + opts.map(function (o, i) { return '<button type="button" class="st-chip sm" data-rz="' + i + '">' + esc(o) + "</button>"; }).join("") + "</div>" : "");
    box.querySelectorAll("[data-rz]").forEach(function (b) { b.onclick = function () { s0.headline = opts[+b.dataset.rz]; redraw(); editor(); }; });
  }
  function runChecks() { renderRizz(); versions(); var el = $("st-checks"); el.innerHTML = checks().map(function (o) { return '<li class="' + o[0] + '"><span aria-hidden="true">' + (o[0] === "ok" ? "✅" : "⚠️") + "</span> " + esc(o[1]) + "</li>"; }).join(""); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------- export ---------- */
  function blobOf(c) { return new Promise(function (res, rej) { try { c.toBlob(function (b) { b ? res(b) : rej(new Error("blank")); }, "image/png"); } catch (e) { rej(e); } }); }
  function frame(s, i, size) { var c = document.createElement("canvas"); c.width = size[0]; c.height = size[1]; render(c.getContext("2d"), s, size[0], size[1], { idx: i, total: S.slides.length, safe: false }); return c; }
  function thumb() { try { var d = dims(), c = document.createElement("canvas"); c.width = 160; c.height = Math.round(160 * d[1] / d[0]); var big = frame(S.slides[0], 0, d); c.getContext("2d").drawImage(big, 0, 0, c.width, c.height); return c.toDataURL("image/jpeg", .6); } catch (e) { return ""; } }
  function slug() { return (($("st-title").value || "post").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "post").slice(0, 40); }
  function save(blob, name) { var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500); }
  function safely(fn) { return fn().catch(function (e) { if (!S.noLogo && logo) { S.noLogo = true; return fn(); } throw e; }); }
  function crcTable() { var t = [], c, n, k; for (n = 0; n < 256; n++) { c = n; for (k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; }
  var CT = null; function crc(u) { CT = CT || crcTable(); var c = 0xFFFFFFFF; for (var i = 0; i < u.length; i++) c = CT[(c ^ u[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function zip(files) {
    var parts = [], cen = [], off = 0, enc = new TextEncoder();
    files.forEach(function (f) {
      var nm = enc.encode(f.name), cr = crc(f.data), h = new DataView(new ArrayBuffer(30)); h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint32(14, cr, true); h.setUint32(18, f.data.length, true); h.setUint32(22, f.data.length, true); h.setUint16(26, nm.length, true);
      parts.push(h.buffer, nm, f.data);
      var c = new DataView(new ArrayBuffer(46)); c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true); c.setUint32(16, cr, true); c.setUint32(20, f.data.length, true); c.setUint32(24, f.data.length, true); c.setUint16(28, nm.length, true); c.setUint32(42, off, true);
      cen.push(c.buffer, nm); off += 30 + nm.length + f.data.length;
    });
    var csz = cen.reduce(function (a, b) { return a + (b.byteLength || b.length); }, 0), e = new DataView(new ArrayBuffer(22)); e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true); e.setUint32(12, csz, true); e.setUint32(16, off, true);
    return new Blob(parts.concat(cen, [e.buffer]), { type: "application/zip" });
  }
  function exportOne() { return safely(function () { var d = dims(); return blobOf(frame(S.slides[S.cur], S.cur, d)); }).then(function (b) { save(b, slug() + "-" + (S.cur + 1) + ".png"); }); }
  function exportAll(allSizes) {
    var sizes = allSizes ? Object.keys(SIZES) : [S.size || DEF_SIZE[S.kind]];
    return safely(function () {
      var jobs = []; sizes.forEach(function (k) { S.slides.forEach(function (s, i) { jobs.push(blobOf(frame(s, i, SIZES[k])).then(function (b) { return b.arrayBuffer(); }).then(function (ab) { return { name: (allSizes ? k.replace(":", "x") + "/" : "") + slug() + "-" + (i + 1) + ".png", data: new Uint8Array(ab) }; })); }); });
      return Promise.all(jobs);
    }).then(function (files) {
      files.push({ name: "caption.txt", data: new TextEncoder().encode(($("st-cap").value || "") + "\n\n" + ($("st-tags").value || "")) }); save(zip(files), slug() + (allSizes ? "-all-sizes" : "") + ".zip");
    });
  }

  /* ---------- reel ---------- */
  var play = { on: false, raf: 0 };
  function sceneDur(s, i) { return s.dur || (i === 0 ? 2.2 : 2.6); }
  function total() { return S.slides.reduce(function (a, s, i) { return a + sceneDur(s, i); }, 0); }
  var TRANS = ["push", "fade", "zoom"], bufA, bufB;
  function buf(k) { var c = k ? (bufB = bufB || document.createElement("canvas")) : (bufA = bufA || document.createElement("canvas")); c.width = 1080; c.height = 1920; return c; }
  function frameAt(c2, t) {
    var acc = 0, d = SIZES["9:16"], n = S.slides.length, W = d[0], H = d[1], mode = S.trans || "push";
    for (var i = 0; i < n; i++) {
      var du = sceneDur(S.slides[i], i);
      if (t < acc + du || i === n - 1) {
        var lt = t - acc, sl = S.slides[i], opt = { p: Math.min(1, lt / .55), anim: sl.anim || ANIMS[i % ANIMS.length], idx: i, total: n, safe: false, t: lt, T: du, flash: mode === "flash" }, TR = .42, md = mode === "auto" ? TRANS[i % 3] : mode;
        if (i > 0 && lt < TR && md !== "none") {
          var pd = sceneDur(S.slides[i - 1], i - 1), A = buf(0), B = buf(1), pa = S.slides[i - 1];
          render(A.getContext("2d"), pa, W, H, { p: 1, anim: pa.anim || ANIMS[(i - 1) % ANIMS.length], idx: i - 1, total: n, safe: false, t: pd, T: pd });
          render(B.getContext("2d"), sl, W, H, opt);
          var e = lt / TR; e = 1 - Math.pow(1 - e, 3); c2.clearRect(0, 0, W, H);
          if (md === "push") { c2.drawImage(A, -W * e * .9, 0); c2.drawImage(B, W * (1 - e) * .9 + 0, 0); c2.save(); c2.fillStyle = "rgba(0,0,0," + (.35 * (1 - e)).toFixed(3) + ")"; c2.fillRect(0, 0, W * (1 - e) * .9, H); c2.restore(); }
          else if (md === "zoom") { c2.drawImage(A, 0, 0); c2.save(); c2.globalAlpha = e; var z = 1.35 - .35 * e; c2.translate(W / 2, H / 2); c2.scale(z, z); c2.translate(-W / 2, -H / 2); c2.drawImage(B, 0, 0); c2.restore(); }
          else if (md === "flash") { c2.drawImage(e < .45 ? A : B, 0, 0); c2.fillStyle = "rgba(255,255,255," + (.8 * (1 - Math.abs(e - .45) / .55)).toFixed(3) + ")"; c2.fillRect(0, 0, W, H); }
          else { c2.drawImage(A, 0, 0); c2.save(); c2.globalAlpha = e; c2.drawImage(B, 0, 0); c2.restore(); }
        } else render(c2, sl, W, H, opt);
        progressBar(c2, W, H, i, n, lt / du); return;
      }
      acc += du;
    }
  }
  function playReel(onEnd) {
    var c = $("st-reel"), c2 = c.getContext("2d"); c.width = 1080; c.height = 1920; c.hidden = false; cv.hidden = true; var t0 = performance.now(), T = total();
    play.on = true; (function loop(now) { var t = (now - t0) / 1000; if (!play.on) return; frameAt(c2, Math.min(t, T - .001)); if (t >= T) { play.on = false; c.hidden = true; redraw(); if (onEnd) onEnd(); return; } play.raf = requestAnimationFrame(loop); })(t0);
  }
  function mime() { var l = ["video/mp4;codecs=avc1", "video/mp4", "video/webm;codecs=vp9", "video/webm"]; for (var i = 0; i < l.length; i++) if (window.MediaRecorder && MediaRecorder.isTypeSupported(l[i])) return l[i]; return ""; }
  function recordReel() {
    var m = mime(), msg = $("st-msg"); if (!m || !HTMLCanvasElement.prototype.captureStream) { msg.textContent = "This browser can't record video. Try Chrome or Edge, or use Play to screen-record."; return; }
    var c = $("st-reel"); c.width = 1080; c.height = 1920; var stream = c.captureStream(30), rec = new MediaRecorder(stream, { mimeType: m, videoBitsPerSecond: 6e6 }), chunks = [];
    rec.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); }; rec.onstop = function () { var ext = /mp4/.test(m) ? "mp4" : "webm"; save(new Blob(chunks, { type: m.split(";")[0] }), slug() + "-reel." + ext); msg.textContent = "Reel saved as ." + ext + (ext === "webm" ? " (this browser records WebM; Instagram accepts it after a quick convert, or use Chrome for MP4)." : ". Add trending audio inside Instagram for the best reach."); $("st-rec").disabled = false; };
    $("st-rec").disabled = true; msg.textContent = "Recording " + Math.round(total()) + " seconds… keep this tab open."; rec.start(); playReel(function () { setTimeout(function () { rec.stop(); }, 150); });
  }

  /* ---------- ready-made formats ---------- */
  function fmt(k) {
    var g = ($("st-goal").value || "").trim() || "Your idea", o = ($("st-offer").value || "").trim(), B = C.brand, cta = { layout: "cta", headline: "Your turn", sub: "Message " + B + " to get started" };
    var F = {
      tips: { kind: "carousel", slides: [{ layout: "cover", headline: "3 tips: " + g, sub: "Save this for later" }, { layout: "tip", num: 1, headline: "Tip one", sub: "Say the first thing people should do" }, { layout: "tip", num: 2, headline: "Tip two", sub: "Add a detail that is specific to you" }, { layout: "tip", num: 3, headline: "Tip three", sub: "End with the one that saves the most time" }, cta], cap: "3 things to know about " + g.toLowerCase() + ". Save this for later and send it to someone who needs it." },
      ba: { kind: "reel", slides: [{ layout: "cover", headline: "Before vs after", sub: g }, { layout: "compare", headline: "Before vs after", sub: "The problem people recognise; The result in one line" }, { layout: "cta", headline: "Want this too?", sub: "Message " + B }], cap: "Before vs after: " + g + ". Which one are you?" },
      pov: { kind: "reel", slides: [{ layout: "cover", headline: "POV: " + g, sub: "" }, { layout: "quote", headline: "Say what they are thinking, in their words", sub: "a real customer" }, { layout: "cta", headline: "Sound like you?", sub: "Follow " + B + " for more" }], cap: "POV: " + g + ". Tell us if this is you." },
      count: { kind: "story", slides: [{ layout: "cover", headline: "3 days to go", sub: g }, { layout: "cover", headline: "2 days to go", sub: g }, { layout: "cover", headline: "Tomorrow", sub: g }, { layout: "offer", headline: o || "It is live", sub: "Today only" }], cap: "Counting down to " + g + ". Turn on notifications so you do not miss it." },
      offer: { kind: "post", slides: [{ layout: "offer", headline: o || "Your offer here", sub: g }, { layout: "cta", headline: "Order now", sub: "Message " + B + " to claim it" }], cap: (o || "A special offer") + ": " + g + ". Message us to claim it before it ends." },
      testi: { kind: "post", slides: [{ layout: "quote", headline: "Paste a real customer review here", sub: "Customer name" }, { layout: "cta", headline: "Join them", sub: "Message " + B }], cap: "What our customers say. Only real reviews, shared with permission." },
      stat: { kind: "post", slides: [{ layout: "stat", headline: "500+", sub: "happy customers, and counting" }, { layout: "cta", headline: "Be next", sub: "Message " + B }], cap: "A number we are proud of: " + g + ". Thank you for being part of it." },
      bts: { kind: "reel", slides: [{ layout: "cover", headline: "Behind the scenes", sub: B }, { layout: "step", num: 1, headline: "How it starts", sub: "Add a photo of the first step" }, { layout: "step", num: 2, headline: "How it is made", sub: "Add a photo of the work" }, { layout: "cta", headline: "See more", sub: "Follow " + B }], cap: "A peek behind the scenes at " + B + ". What do you want to see next?" }
    }[k];
    if (!F) return; S.kind = F.kind; S.size = ""; S.slides = F.slides; S.cur = 0; $("st-cap").value = F.cap; $("st-tags").value = ""; if (!$("st-title").value) $("st-title").value = g.slice(0, 80); kindBtns(); redraw(); editor();
    $("st-msg").textContent = "Template ready. Replace the grey prompts with your own words, or press Write it for me to have it filled in.";
  }
  document.querySelectorAll("[data-fmt]").forEach(function (b) { b.onclick = function () { fmt(b.dataset.fmt); }; });

  /* ---------- one idea, every channel ---------- */
  function versions() {
    var cap = $("st-cap").value || "", tags = ($("st-tags").value.match(/#\w+/g) || []), box = $("st-vers"); if (!box) return;
    var lines = cap.split(/\n+/).filter(Boolean), hook = lines[0] || "", body = lines.slice(1).join("\n\n"), V = [];
    V.push(["Instagram", [cap, tags.slice(0, 5).join(" ")].filter(Boolean).join("\n\n")]);
    V.push(["LinkedIn", [hook, "", body || "", "", tags.slice(0, 3).join(" ")].join("\n").replace(/\n{3,}/g, "\n\n").trim()]);
    V.push(["X / Twitter", (hook + (body ? " " + body.split(/\n/)[0] : "")).slice(0, 250).trim() + (tags[0] ? " " + tags[0] : "")]);
    V.push(["WhatsApp", "*" + hook + "*\n" + (body.split(/\n/)[0] || "") + "\n\nReply to this message to order 👇"]);
    V.push(["Email", "Subject: " + hook.slice(0, 60) + "\nPreview: " + (body.split(/\n/)[0] || hook).slice(0, 90) + "\n\n" + cap]);
    box.innerHTML = V.map(function (v, i) { return '<details><summary>' + esc(v[0]) + '</summary><textarea rows="5" readonly aria-label="' + esc(v[0]) + ' draft" id="ver' + i + '">' + esc(v[1]) + '</textarea><button type="button" class="btn ghost sm" data-copy="ver' + i + '">Copy</button></details>'; }).join("");
    box.querySelectorAll("[data-copy]").forEach(function (b) { b.onclick = function () { var t = $(b.dataset.copy); t.select(); if (window.copyTxt) return copyTxt(t.value, b); try { navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); } b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = "Copy"; }, 1500); }; });
  }

  /* ---------- post it now ---------- */
  var LINKS = { Instagram: "https://www.instagram.com/", LinkedIn: "https://www.linkedin.com/feed/", "X / Twitter": "https://x.com/compose/post", Facebook: "https://www.facebook.com/", YouTube: "https://studio.youtube.com/", WhatsApp: "https://web.whatsapp.com/" };
  function copyText(t, btn) { if (window.copyTxt) return copyTxt(t, btn); try { navigator.clipboard.writeText(t); } catch (e) {} if (btn) { var o = btn.textContent; btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = o; }, 1500); } }
  function postMode() {
    var box = $("st-post"); if (!box || !C.post) return; box.hidden = false; var ch = C.channel || $("st-chan").value;
    $("pm-img").onclick = function () { exportAll(false); }; $("pm-cap").onclick = function () { copyText($("st-cap").value, this); }; $("pm-tags").onclick = function () { copyText($("st-tags").value, this); };
    var a = $("pm-open"); if (LINKS[ch]) { a.href = LINKS[ch]; a.textContent = "Open " + ch + " ↗"; } else a.hidden = true;
    if ($("pm-share")) $("pm-share").onclick = shareIt;
    $("pm-done").onclick = function () { $("pm-nums").hidden = false; this.hidden = true; };
    $("pm-save").onclick = function () { var b = this; b.disabled = true; post("/studio/done", { rid: S.rid, reach: $("pm-reach").value, likes: $("pm-likes").value, saves: $("pm-saves").value }).then(function (j) { b.disabled = false; if (j.error || j._s >= 400) { $("pm-msg").textContent = "Couldn't save that. Try again."; return; } if (window.confetti) window.confetti(); $("pm-msg").innerHTML = "🎉 Posted! " + (j.streak ? "🔥 " + j.streak + "-day streak. " : "") + (j.logged ? "Numbers saved to Results. " : "") + '<a href="/app">Back to Today</a> · <a href="/studio">Make the next one</a>'; $("pm-nums").hidden = true; }); };
  }

  /* ---------- best time, hooks, saved hashtags ---------- */
  var BEST = { Instagram: "Tue to Thu, 7 to 9 pm", LinkedIn: "Tue to Thu, 8 to 10 am", "X / Twitter": "weekdays, 12 to 3 pm", WhatsApp: "10 am to 12 noon, or 7 to 9 pm", Email: "Tue or Thu, around 10 am", Facebook: "Wed to Fri, 1 to 4 pm", YouTube: "Thu to Sat, 3 to 6 pm" };
  function bestTime() { var el = $("st-best"); if (el) el.textContent = BEST[$("st-chan").value] ? "General guidance for " + $("st-chan").value + " (IST): " + BEST[$("st-chan").value] + ". Your own results are the real answer." : ""; }
  var HOOKS = ["POV: you finally…", "Stop scrolling if you…", "Nobody tells you this about…", "3 mistakes we made with…", "Here is what we would do differently…", "You do not need more followers, you need…", "We tried … for 30 days. Here is what happened.", "The one thing that changed our…"];
  var hb = $("st-hooks"); if (hb) { hb.innerHTML = HOOKS.map(function (h) { return '<button type="button" class="linkbtn" data-hook="' + esc(h) + '">' + esc(h) + "</button>"; }).join(" "); hb.querySelectorAll("[data-hook]").forEach(function (b) { b.onclick = function () { var c = $("st-cap"); c.value = b.dataset.hook + " " + c.value.replace(/^[^\n]*?\n+/, ""); c.focus(); runChecks(); }; }); }
  function loadSets() { var sel = $("st-sets"); if (!sel) return; fetch("/studio/sets", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (j) { sel.innerHTML = '<option value="">My hashtag sets</option>' + (j.sets || []).map(function (s) { return '<option value="' + esc(s.body) + '">' + esc(s.title) + "</option>"; }).join(""); }).catch(function () {}); sel.onchange = function () { if (this.value) { $("st-tags").value = this.value; runChecks(); } }; }
  function saveSet() { var tags = $("st-tags").value.trim(); if (!tags) { $("st-msg").textContent = "Type some hashtags first."; return; } var n = prompt("Name this set (for example: Diwali gifting)"); if (!n) return; post("/studio/sets", { title: n, body: tags }).then(function (j) { if (j._s === 403) { $("st-msg").textContent = C.demo ? "Saving is switched off in the demo." : "You can look but not save with your role."; return; } $("st-msg").textContent = j.error || "Saved. Pick it from My hashtag sets next time."; loadSets(); }); }
  function shareIt() {
    var msg = $("pm-msg"); if (!navigator.canShare || !navigator.share) { msg.textContent = "Sharing to apps works on your phone. Here, use Download the images."; return; }
    safely(function () { var d = dims(); return Promise.all(S.slides.map(function (s, i) { return blobOf(frame(s, i, d)).then(function (b) { return new File([b], slug() + "-" + (i + 1) + ".png", { type: "image/png" }); }); })); }).then(function (files) {
      if (!navigator.canShare({ files: files })) { msg.textContent = "This browser can't share images straight to apps. Use Download the images."; return; }
      return navigator.share({ files: files, text: $("st-cap").value + "\n\n" + $("st-tags").value }).catch(function () {});
    }).catch(function () { msg.textContent = "Couldn't open the share sheet. Use Download the images."; });
  }

  /* ---------- this week's pack ---------- */
  function preload(slides) { return Promise.all(slides.map(function (s) { return new Promise(function (res) { if (!s.img) return res(); var i = new Image(); i.onload = i.onerror = function () { s._im = i; res(); }; i.src = s.img; }); })); }
  function weekPack() {
    var msg = $("st-msg"); msg.textContent = "Building your pack…";
    fetch("/studio/pack.json", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j.items.length) { msg.textContent = "No designed posts in the next 7 days yet. Design one and save it to the calendar."; return; }
      var keep = { kind: S.kind, theme: S.theme, size: S.size, slides: S.slides, cur: S.cur }, files = [], idx = 0, lines = ["Posting order for the next 7 days:", ""];
      return j.items.reduce(function (p, it) {
        return p.then(function () {
          var b = it.board || {}; S.kind = b.kind || "post"; S.theme = b.theme || "bold"; S.size = b.size || ""; S.slides = b.slides || []; idx++;
          var folder = ("0" + idx).slice(-2) + "-" + it.date + "-" + it.channel.replace(/[^A-Za-z0-9]+/g, "") + "-" + (it.title || "post").toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 28) + "/", d = dims();
          lines.push(idx + ". " + it.date + " · " + it.channel + " · " + it.title);
          return preload(S.slides).then(function () { return Promise.all(S.slides.map(function (s, i) { return blobOf(frame(s, i, d)).then(function (bl) { return bl.arrayBuffer(); }).then(function (ab) { files.push({ name: folder + "slide-" + (i + 1) + ".png", data: new Uint8Array(ab) }); }); })); })
            .then(function () { files.push({ name: folder + "caption.txt", data: new TextEncoder().encode((it.caption || "") + "\n\n" + (it.hashtags || "")) }); });
        });
      }, Promise.resolve()).then(function () {
        S.kind = keep.kind; S.theme = keep.theme; S.size = keep.size; S.slides = keep.slides; S.cur = keep.cur;
        files.unshift({ name: "00-posting-order.txt", data: new TextEncoder().encode(lines.join("\n")) }); save(zip(files), "debut-week-pack.zip"); msg.textContent = "Pack downloaded: " + j.items.length + " post" + (j.items.length === 1 ? "" : "s") + ", in posting order."; redraw();
      });
    }).catch(function () { msg.textContent = "Couldn't build the pack. Try again."; });
  }

  /* ---------- wiring ---------- */
  function setBoard(b) { S.slides = b.slides; S.trans = b.trans || S.trans || "push"; if ($("st-trans")) $("st-trans").value = S.trans; S.cur = 0; if (b.caption != null) $("st-cap").value = b.caption; if (b.hashtags) $("st-tags").value = b.hashtags.join(" "); S.cta = b.cta || ""; redraw(); editor(); }
  function post(url, body) { return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": window.CSRF }, body: JSON.stringify(body, strip), credentials: "same-origin" }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j._s = r.status; return j; }); }); }
  function kindBtns() { document.querySelectorAll("[data-kind]").forEach(function (b) { b.classList.toggle("on", b.dataset.kind === S.kind); b.setAttribute("aria-pressed", b.dataset.kind === S.kind); }); $("st-size").value = S.size || DEF_SIZE[S.kind]; $("st-play").hidden = $("st-rec").hidden = !(S.kind === "reel" || S.kind === "story"); }

  /* ---------- platform first, then format, then a template ---------- */
  var G = { pl: "", kind: "", cat: "", q: "", n: 12 }, TP = window.TPL;
  function lsGet(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function fmtN(n) { return n.toLocaleString("en-IN"); }
  function nice(iso) { var p = (iso || "").split("-"); return p.length === 3 ? (+p[2]) + " " + ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+p[1] - 1] : ""; }
  function addDays(iso, d) { var t = new Date(iso + "T00:00:00Z"); t.setUTCDate(t.getUTCDate() + d); return t.toISOString().slice(0, 10); }
  function postDate(ev) { var d = addDays(ev, -2), min = addDays(C.today, 1); return d < min ? (ev >= C.today ? ev : min) : d; }
  function loadTpl(ti, si, ev) {
    var t = TP.build(G.pl, ti, si, C.brand, ev || "", C.ind);
    S.kind = t.kind; S.size = ""; S.slides = t.slides; S.cur = 0; S.cta = ""; S.rid = C.rid && S.rid ? S.rid : 0;
    $("st-cap").value = t.caption; $("st-tags").value = t.tags.join(" "); $("st-title").value = t.title; setChan(G.pl);
    if (ev) $("st-date").value = postDate(ev);
    kindBtns(); redraw(); editor(); bestTime(); markKinds();
    $("st-msg").textContent = "Loaded. Change any words, then save it to your calendar.";
    var st = document.querySelector(".st-mid"); if (st && window.innerWidth < 1100 && st.scrollIntoView) st.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function setChan(p) { var o = $("st-chan"); for (var i = 0; i < o.options.length; i++) if (o.options[i].text === p) { o.selectedIndex = i; break; } }
  function upcoming() {
    var seen = {}, out = [];
    (C.kd || []).forEach(function (k) { if (k.date < C.today) return; var ti = TP.topicFor(k.name); if (ti < 0 || seen[ti]) return; seen[ti] = 1; out.push({ ti: ti, date: k.date, name: TP.topics[ti][0], emoji: TP.topics[ti][2] }); });
    return out.slice(0, 4);
  }
  function firstFor(kind, ti) { var l = TP.list(G.pl, { kind: kind, topic: ti }); return l.length ? l[0].si : 0; }
  function renderPlats() {
    var box = $("st-plats"); box.innerHTML = TP.platforms.map(function (p) { return '<button type="button" class="st-chip' + (p === G.pl ? " on" : "") + '" data-pl="' + esc(p) + '" aria-pressed="' + (p === G.pl) + '">' + TP.PL[p].ico + " " + esc(p) + "</button>"; }).join("");
    box.querySelectorAll("[data-pl]").forEach(function (b) { b.onclick = function () { pickPlat(b.dataset.pl, true); }; });
  }
  function markKinds() { document.querySelectorAll("#st-kinds [data-kind]").forEach(function (b) { var on = b.dataset.kind === G.kind; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); }); }
  function renderKinds() {
    var box = $("st-kinds"), ks = TP.kindsOf(G.pl);
    box.innerHTML = '<button type="button" class="st-chip' + (G.kind ? "" : " on") + '" data-kind="">All · ' + fmtN(TP.total(G.pl)) + "</button>" + ks.map(function (k) { return '<button type="button" class="st-chip" data-kind="' + k + '" aria-pressed="false">' + TP.KIND_ICO[k] + " " + TP.KIND_LABEL[G.pl][k] + "</button>"; }).join("");
    box.querySelectorAll("[data-kind]").forEach(function (b) { b.onclick = function () {
      G.kind = b.dataset.kind; G.n = 12; markKinds(); box.querySelector('[data-kind=""]').classList.toggle("on", !G.kind); renderGal();
      if (G.kind) { var up = upcoming()[0], ti = up ? up.ti : TP.topics.findIndex(function (t) { return t[0] === "New launch"; }); loadTpl(ti, firstFor(G.kind, ti), up ? up.date : ""); }
    }; });
  }
  function renderUp() {
    var u = upcoming(), w = $("st-up-wrap"); w.hidden = !u.length; if (!u.length) return;
    $("st-up").innerHTML = u.map(function (x, i) { return '<div class="st-upc"><b>' + x.emoji + " " + esc(x.name) + '</b><span class="muted">' + esc(nice(x.date)) + "</span><span class=\"st-upb\">" + TP.kindsOf(G.pl).map(function (k) { return '<button type="button" class="btn ghost sm" data-u="' + i + '" data-k="' + k + '">' + TP.KIND_ICO[k] + " " + TP.KIND_LABEL[G.pl][k].split(" ")[0] + "</button>"; }).join("") + "</span></div>"; }).join("");
    $("st-up").querySelectorAll("[data-u]").forEach(function (b) { b.onclick = function () { var x = u[+b.dataset.u]; G.kind = b.dataset.k; renderKinds(); markKinds(); renderGal(); loadTpl(x.ti, firstFor(G.kind, x.ti), x.date); }; });
  }
  function renderCats() {
    var cs = ["All"].concat(TP.cats); $("st-cats").innerHTML = cs.map(function (c) { return '<button type="button" class="st-chip sm' + ((c === "All" && !G.cat) || c === G.cat ? " on" : "") + '" data-c="' + (c === "All" ? "" : c) + '">' + c + "</button>"; }).join("");
    $("st-cats").querySelectorAll("[data-c]").forEach(function (b) { b.onclick = function () { G.cat = b.dataset.c; G.n = 12; renderCats(); renderGal(); }; });
  }
  function thumbOf(sl, kind) { var d = SIZES[DEF_SIZE[kind]] || SIZES["4:5"], c = document.createElement("canvas"), k = 150 / d[0]; c.width = 150; c.height = Math.round(d[1] * k); var x = c.getContext("2d"); x.scale(k, k); try { render(x, sl, d[0], d[1], { idx: 0, total: 1 }); } catch (e) {} return c; }
  function renderGal() {
    var l = TP.list(G.pl, { kind: G.kind, cat: G.cat, q: G.q }), box = $("st-gal"), shown = l.slice(0, G.n);
    $("st-cnt").textContent = fmtN(l.length) + " to choose from";
    box.innerHTML = "";
    if (!l.length) { box.innerHTML = '<p class="muted">Nothing matches. Try another word.</p>'; $("st-more").hidden = true; return; }
    shown.forEach(function (it) {
      var t = TP.build(G.pl, it.ti, it.si, C.brand, "", C.ind), b = document.createElement("button"); b.type = "button"; b.className = "st-card"; b.setAttribute("aria-label", it.topic + ": " + it.label);
      b.appendChild(thumbOf(t.slides[0], t.kind)); var m = document.createElement("span"); m.innerHTML = "<b>" + esc(it.emoji + " " + it.topic) + "</b><i>" + esc(it.label) + " · " + esc(TP.KIND_LABEL[G.pl][it.kind]) + "</i>"; b.appendChild(m);
      b.onclick = function () { var up = upcoming().filter(function (x) { return x.ti === it.ti; })[0]; loadTpl(it.ti, it.si, up ? up.date : ""); }; box.appendChild(b);
    });
    $("st-more").hidden = l.length <= G.n;
  }
  function pickPlat(p, load) {
    if (!TP.PL[p]) return; G.pl = p; G.kind = ""; G.cat = ""; G.q = ""; G.n = 12; $("st-q").value = ""; lsSet("debut_plat", p);
    renderPlats(); $("st-after").hidden = false; renderKinds(); renderUp(); renderCats(); renderGal(); setChan(p); runChecks();
    if (load) { var ks = TP.kindsOf(p); G.kind = ks[0]; renderKinds(); markKinds(); renderGal(); var up = upcoming()[0], ti = up ? up.ti : TP.topics.findIndex(function (t) { return t[0] === "New launch"; }); loadTpl(ti, firstFor(G.kind, ti), up ? up.date : ""); }
  }
  if (!$("st-canvas")) {      /* another page (the Launch Deck) borrows the renderer */
    window.StudioDeck = {
      draw: function (cv, it, i, w) { S.kind = it.kind; S.theme = it.theme || "auto"; S.cust = null; var d = SIZES[it.size || DEF_SIZE[it.kind]] || SIZES["4:5"], k = w / d[0]; cv.width = w; cv.height = Math.round(d[1] * k); var c = cv.getContext("2d"); c.save(); c.scale(k, k); render(c, it.slides[i], d[0], d[1], { idx: i, total: it.slides.length, safe: false }); c.restore(); },
      play: function (cv, it, w, done) { S.kind = it.kind; S.theme = it.theme || "auto"; S.cust = null; S.slides = it.slides; S.trans = it.trans || "push"; var off = document.createElement("canvas"); off.width = 1080; off.height = 1920; var oc = off.getContext("2d"), k = w / 1080; cv.width = w; cv.height = Math.round(1920 * k); var c = cv.getContext("2d"), T = total(), t0 = performance.now(); (function loop(now) { var t = (now - t0) / 1000; frameAt(oc, Math.min(t, T - .001)); c.clearRect(0, 0, cv.width, cv.height); c.drawImage(off, 0, 0, cv.width, cv.height); if (t < T) requestAnimationFrame(loop); else if (done) done(); })(t0); },
      thumb: function (cv, it) { S.kind = it.kind; S.theme = it.theme || "auto"; S.cust = null; var d = SIZES[it.size || DEF_SIZE[it.kind]] || SIZES["4:5"], c = document.createElement("canvas"); c.width = 160; c.height = Math.round(160 * d[1] / d[0]); var x = c.getContext("2d"); x.scale(160 / d[0], 160 / d[0]); render(x, it.slides[0], d[0], d[1], { idx: 0, total: it.slides.length }); try { return c.toDataURL("image/jpeg", .6); } catch (e) { return ""; } }
    };
    return;
  }
  $("st-more").onclick = function () { G.n += 24; renderGal(); };
  var qt = 0; $("st-q").oninput = function () { clearTimeout(qt); var v = this.value; qt = setTimeout(function () { G.q = v.trim(); G.n = 12; renderGal(); }, 200); };
  $("st-size").onchange = function () { S.size = this.value; redraw(); };
  $("st-theme").onchange = function () { S.theme = this.value; redraw(); };
  if ($("st-trans")) { $("st-trans").value = S.trans || "push"; $("st-trans").onchange = function () { S.trans = this.value; }; }
  function custom(k, v) { S.cust = S.cust || {}; S.cust[k] = v; if (S.theme !== "auto") { S.theme = "auto"; $("st-theme").value = "auto"; } redraw(); }
  $("st-c1").oninput = function () { custom("bg", this.value); }; $("st-c2").oninput = function () { custom("ac", this.value); };
  $("st-c0").onclick = function () { S.cust = null; S.theme = "auto"; $("st-theme").value = "auto"; redraw(); };
  $("st-guides").onchange = function () { S.guides = this.checked; redraw(); };
  ["st-cap", "st-tags", "st-chan", "st-date"].forEach(function (id) { $(id).oninput = $(id).onchange = function () { runChecks(); bestTime(); }; });
  if ($("st-saveset")) $("st-saveset").onclick = saveSet;
  if ($("st-pack")) $("st-pack").onclick = weekPack;
  $("st-make").onclick = function () {
    var goal = $("st-goal").value.trim(); if (!goal) { $("st-msg").textContent = "Say what this is for first, for example: Diwali gift box, 20% off till Sunday."; $("st-goal").focus(); return; }
    var b = this; b.disabled = true; $("st-msg").textContent = "Writing…";
    post("/studio/draft", { goal: goal, offer: $("st-offer").value, kind: S.kind, channel: $("st-chan").value }).then(function (j) { b.disabled = false; if (j.error) { $("st-msg").textContent = j.error; return; } setBoard(j); $("st-msg").textContent = j.note || (j.source === "ai" ? "Written in your brand voice. Edit anything." : "Built from a template. Edit anything, then save."); if (!$("st-title").value) $("st-title").value = goal.slice(0, 80); }).catch(function () { b.disabled = false; $("st-msg").textContent = "Couldn't reach the server. Try again."; });
  };
  $("st-png").onclick = function () { if (S.slides.length) exportOne().catch(function () { $("st-msg").textContent = "Couldn't export. Try again."; }); };
  $("st-zip").onclick = function () { if (S.slides.length) exportAll(false).catch(function () { $("st-msg").textContent = "Couldn't export. Try again."; }); };
  $("st-all").onclick = function () { if (S.slides.length) exportAll(true).catch(function () { $("st-msg").textContent = "Couldn't export. Try again."; }); };
  $("st-play").onclick = function () { if (S.slides.length) { if (play.on) { play.on = false; $("st-reel").hidden = true; redraw(); } else playReel(); } };
  $("st-rec").onclick = function () { if (S.slides.length) recordReel(); };
  $("st-save").onclick = function () {
    if (!S.slides.length) { $("st-msg").textContent = "Make something first."; return; }
    var b = this; b.disabled = true;
    post("/studio/save", { rid: S.rid, title: $("st-title").value || $("st-goal").value, channel: $("st-chan").value, kind: S.kind, date: $("st-date").value, caption: $("st-cap").value, hashtags: ($("st-tags").value.match(/#\w+/g) || []), cta: S.cta, campaign: "", repeat: S.rid ? 0 : +($("st-rep") ? $("st-rep").value : 0), thumb: thumb(), board: { slides: S.slides, theme: S.theme, size: S.size, trans: S.trans || "" } })
      .then(function (j) { b.disabled = false; if (j._s === 403) { $("st-msg").innerHTML = C.demo ? 'This is the demo, so saving is switched off. <a href="/signup">Make your own free</a> to save to your calendar.' : "You can look but not save with your role."; return; } if (j.error) { $("st-msg").textContent = j.error; return; } S.rid = j.id; if (window.confetti) window.confetti(); $("st-msg").innerHTML = '🎉 Saved to your calendar. <a href="' + j.url + '">Open calendar</a> · <a href="/studio">Make another</a>'; });
  };
  var exBox = document.querySelector(".st-ex"); if (exBox && C.ideas && C.ideas.length) { exBox.innerHTML = "Ideas for you: " + C.ideas.map(function (t) { return '<button type="button" class="linkbtn" data-ex="' + esc(t) + '">' + esc(t) + "</button>"; }).join(" "); }
  document.querySelectorAll("[data-ex]").forEach(function (b) { b.onclick = function () { $("st-goal").value = b.dataset.ex; $("st-goal").focus(); }; });
  if (C.saved && C.saved.slides && C.saved.slides.length) { S.kind = C.saved.kind || S.kind; S.theme = C.saved.theme || "bold"; S.size = C.saved.size || ""; $("st-theme").value = S.theme; S.slides = C.saved.slides; $("st-title").value = C.title || ""; }
  else if (C.goal) { $("st-goal").value = C.goal; $("st-offer").value = C.offer || ""; }
  if (C.channel) $("st-chan").value = C.channel;
  $("st-date").value = C.date || new Date(Date.now() + 2 * 864e5).toISOString().slice(0, 10);
  if (C.rid && C.caption != null) { $("st-cap").value = C.caption; $("st-tags").value = C.hashtags || ""; }
  kindBtns(); redraw(); editor(); postMode(); bestTime(); loadSets();
  renderPlats();
  (function () {
    var p0 = (C.channel && TP.PL[C.channel] && C.channel) || lsGet("debut_plat"); if (!p0 || !TP.PL[p0]) p0 = "Instagram";
    var has = (C.saved && C.saved.slides && C.saved.slides.length) || C.goal;
    pickPlat(p0, !has); if (C.saved && C.saved.slides) { G.kind = ""; }
    if (has && S.kind) { G.kind = S.kind; renderKinds(); markKinds(); }
  })();
  if (!S.slides.length && C.goal) { $("st-own").open = true; if (!G.pl) pickPlat("Instagram", false); $("st-make").click(); }
  window.addEventListener("beforeunload", function () { play.on = false; });
})();
