/* Create studio: designs posts, carousels and reels on a canvas in the browser, so the server stays light. */
(function () {
  var C = window.STUDIO, $ = function (id) { return document.getElementById(id); };
  var SIZES = { "4:5": [1080, 1350], "1:1": [1080, 1080], "9:16": [1080, 1920], "16:9": [1200, 675] };
  var DEF_SIZE = { post: "4:5", carousel: "4:5", reel: "9:16", story: "9:16" };
  var ANIMS = ["pop", "slide", "type", "zoom", "wipe"];
  var S = { kind: C.kind || "carousel", slides: [], caption: C.caption || "", tags: [], cta: "", theme: "bold", size: "", cur: 0, noLogo: false, guides: false, rid: C.rid || 0 };
  var logo = null;
  if (C.logo) { logo = new Image(); logo.crossOrigin = "anonymous"; logo.onload = redraw; logo.onerror = function () { logo = null; }; logo.src = C.logo; }

  /* ---------- colour helpers ---------- */
  function rgb(h) { h = (h || "#6a3df0").replace("#", ""); if (h.length === 3) h = h.replace(/./g, "$&$&"); var n = parseInt(h, 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
  function hex(a) { return "#" + a.map(function (v) { return ("0" + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2); }).join(""); }
  function mix(a, b, t) { var x = rgb(a), y = rgb(b); return hex([0, 1, 2].map(function (i) { return x[i] + (y[i] - x[i]) * t; })); }
  function lum(h) { var c = rgb(h).map(function (v) { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]; }
  function palette() {
    var pri = C.pri || "#6a3df0", sec = C.sec || "#ff4f9a";
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
  function render(ctx, s, w, h, o) {
    o = o || {}; var P = palette(), m = Math.round(w * .085), mw = w - m * 2, p = o.p == null ? 1 : o.p, anim = o.anim || "pop", idx = o.idx || 0, total = o.total || 1;
    ctx.save(); ctx.clearRect(0, 0, w, h); ctx.fillStyle = P.bg; ctx.fillRect(0, 0, w, h);
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
      var t7 = fit(ctx, head, mw, zoneH * .5, Math.round(w * .32), 70, 800); ctx.font = "800 " + t7.f + "px " + FONT; ctx.fillStyle = P.accent;
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
    } else { /* cta */
      var t6 = fit(ctx, head, mw, zoneH * .4, Math.round(w * .11), 40, 800); ctx.font = "800 " + t6.f + "px " + FONT; var y6 = drawText(ctx, t6.lines, m, h * .38, t6.f, P.fg, rev) + 30;
      if (sub) { ctx.font = "600 " + Math.round(w * .04) + "px " + FONT; var sl = wrap(ctx, sub, mw - 80), bh2 = sl.length * w * .045 + 56; ctx.fillStyle = P.accent; roundRect(ctx, m, y6, mw, bh2, bh2 / 2 > 60 ? 40 : bh2 / 2); ctx.fill(); drawText(ctx, sl, m + 40, y6 + 28, w * .045, P.on, null); }
    }
    if (s.emoji) { ctx.font = Math.round(w * .17) + "px sans-serif"; ctx.textAlign = "right"; ctx.textBaseline = "top"; ctx.fillText(s.emoji, w - m, h * .17); ctx.textAlign = "left"; }
    ctx.restore();
    ctx.font = "500 " + Math.round(w * .026) + "px " + FONT; 
    if (o.guides) { ctx.strokeStyle = "#ff3b6b"; ctx.lineWidth = 4; ctx.setLineDash([16, 12]); ctx.strokeRect(24, h * .1, w - 48, h * .68); ctx.setLineDash([]); ctx.fillStyle = "#ff3b6bcc"; ctx.font = "600 28px " + FONT; ctx.fillText("Keep text inside the box", 40, h * .1 + 10); }
    ctx.restore();
  }
  function roundRect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

  /* ---------- UI ---------- */
  try { document.fonts.load("800 40px \"Bricolage Grotesque\"").then(function(){ redraw(); }); document.fonts.load("500 20px Inter"); } catch (e) {}
  var cv = $("st-canvas"), ctx = cv.getContext("2d");
  function dims() { return SIZES[S.size || DEF_SIZE[S.kind]] || SIZES["4:5"]; }
  function safeOn() { return S.kind === "reel" || S.kind === "story" || (S.size || DEF_SIZE[S.kind]) === "9:16"; }
  function redraw() {
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
  var LABELS = { cover: "Cover", step: "Step", tip: "Tip", quote: "Quote", list: "List", stat: "Big number", compare: "Before / after", offer: "Offer", cta: "Call to action" };
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
  function frameAt(c2, t) {
    var acc = 0, d = SIZES["9:16"]; for (var i = 0; i < S.slides.length; i++) { var du = sceneDur(S.slides[i], i); if (t < acc + du || i === S.slides.length - 1) { render(c2, S.slides[i], d[0], d[1], { p: Math.min(1, (t - acc) / .55), anim: S.slides[i].anim || ANIMS[i % ANIMS.length], idx: i, total: S.slides.length, safe: false }); return; } acc += du; }
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
    box.innerHTML = V.map(function (v, i) { return '<details><summary>' + esc(v[0]) + '</summary><textarea rows="5" readonly id="ver' + i + '">' + esc(v[1]) + '</textarea><button type="button" class="btn ghost sm" data-copy="ver' + i + '">Copy</button></details>'; }).join("");
    box.querySelectorAll("[data-copy]").forEach(function (b) { b.onclick = function () { var t = $(b.dataset.copy); t.select(); try { navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); } b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = "Copy"; }, 1500); }; });
  }

  /* ---------- post it now ---------- */
  var LINKS = { Instagram: "https://www.instagram.com/", LinkedIn: "https://www.linkedin.com/feed/", "X / Twitter": "https://x.com/compose/post", Facebook: "https://www.facebook.com/", YouTube: "https://studio.youtube.com/", WhatsApp: "https://web.whatsapp.com/" };
  function copyText(t, btn) { try { navigator.clipboard.writeText(t); } catch (e) {} if (btn) { var o = btn.textContent; btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = o; }, 1500); } }
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
  function setBoard(b) { S.slides = b.slides; S.cur = 0; if (b.caption != null) $("st-cap").value = b.caption; if (b.hashtags) $("st-tags").value = b.hashtags.join(" "); S.cta = b.cta || ""; redraw(); editor(); }
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
    var t = TP.build(G.pl, ti, si, C.brand, ev || "");
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
      var t = TP.build(G.pl, it.ti, it.si, C.brand, ""), b = document.createElement("button"); b.type = "button"; b.className = "st-card"; b.setAttribute("aria-label", it.topic + ": " + it.label);
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
  $("st-more").onclick = function () { G.n += 24; renderGal(); };
  var qt = 0; $("st-q").oninput = function () { clearTimeout(qt); var v = this.value; qt = setTimeout(function () { G.q = v.trim(); G.n = 12; renderGal(); }, 200); };
  $("st-size").onchange = function () { S.size = this.value; redraw(); };
  $("st-theme").onchange = function () { S.theme = this.value; redraw(); };
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
    post("/studio/save", { rid: S.rid, title: $("st-title").value || $("st-goal").value, channel: $("st-chan").value, kind: S.kind, date: $("st-date").value, caption: $("st-cap").value, hashtags: ($("st-tags").value.match(/#\w+/g) || []), cta: S.cta, campaign: "", repeat: S.rid ? 0 : +($("st-rep") ? $("st-rep").value : 0), thumb: thumb(), board: { slides: S.slides, theme: S.theme, size: S.size } })
      .then(function (j) { b.disabled = false; if (j._s === 403) { $("st-msg").innerHTML = C.demo ? 'This is the demo, so saving is switched off. <a href="/signup">Make your own free</a> to save to your calendar.' : "You can look but not save with your role."; return; } if (j.error) { $("st-msg").textContent = j.error; return; } S.rid = j.id; if (window.confetti) window.confetti(); $("st-msg").innerHTML = '🎉 Saved to your calendar. <a href="' + j.url + '">Open calendar</a> · <a href="/studio">Make another</a>'; });
  };
  var exBox = document.querySelector(".st-ex"); if (exBox && C.ideas && C.ideas.length) { exBox.innerHTML = "Ideas for you: " + C.ideas.map(function (t) { return '<button type="button" class="linkbtn" data-ex="' + esc(t) + '">' + esc(t) + "</button>"; }).join(" "); }
  document.querySelectorAll("[data-ex]").forEach(function (b) { b.onclick = function () { $("st-goal").value = b.dataset.ex; $("st-goal").focus(); }; });
  if (C.saved && C.saved.slides && C.saved.slides.length) { S.kind = C.saved.kind || S.kind; S.theme = C.saved.theme || S.theme; S.size = C.saved.size || ""; $("st-theme").value = S.theme; S.slides = C.saved.slides; $("st-title").value = C.title || ""; }
  else if (C.goal) { $("st-goal").value = C.goal; $("st-offer").value = C.offer || ""; }
  if (C.channel) $("st-chan").value = C.channel;
  $("st-date").value = C.date || new Date(Date.now() + 2 * 864e5).toISOString().slice(0, 10);
  if (C.rid && C.caption != null) { $("st-cap").value = C.caption; $("st-tags").value = C.hashtags || ""; }
  kindBtns(); redraw(); editor(); postMode(); bestTime(); loadSets();
  renderPlats();
  (function () { var p0 = (C.channel && TP.PL[C.channel] && C.channel) || lsGet("debut_plat"); if (p0 && TP.PL[p0]) { pickPlat(p0, false); if (C.saved && C.saved.slides) G.kind = ""; } })();
  if (!S.slides.length && C.goal) { $("st-own").open = true; if (!G.pl) pickPlat("Instagram", false); $("st-make").click(); }
  window.addEventListener("beforeunload", function () { play.on = false; });
})();
