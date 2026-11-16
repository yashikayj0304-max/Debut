/* Complete Launch Deck: builds a dated run of designed posts, carousels, reels and stories with captions, then saves it all to the calendar. */
(function () {
  var C = window.STUDIO, $ = function (id) { return document.getElementById(id); }, TP = window.TPL, SD = window.StudioDeck, DECK = [], FREE_SHOWN = 3;
  var PLAN = [  // [day offset from launch, phase, structure, label]
    [-7, "Tease", "teaser", "Something is coming"], [-6, "Tease", "vote-story", "You decide"], [-5, "Build-up", "pro-tips", "Before you buy"],
    [-3, "Build-up", "countdown", "3 days to go"], [-3, "Build-up", "bts", "Behind the scenes"], [-2, "Build-up", "countdown-reel", "Countdown"],
    [-1, "Build-up", "event-story", "Tomorrow"], [0, "Launch day", "stop-scroll", "It is live"], [0, "Launch day", "launch-ribbon", "Meet it"],
    [0, "Launch day", "coupon-story", "Launch gift"], [1, "Keep going", "review-card", "First reviews"], [2, "Keep going", "three-reasons", "3 reasons"],
    [3, "Keep going", "proof-reel", "Why people trust us"], [5, "Keep going", "price-drop", "Launch price"], [7, "Keep going", "thank-you", "Thank you"]];
  var ICON = { post: "🖼️", carousel: "🎠", reel: "🎬", story: "📱" }, DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function addDays(iso, d) { var t = new Date(iso + "T00:00:00Z"); t.setUTCDate(t.getUTCDate() + d); return t.toISOString().slice(0, 10); }
  function nice(iso) { var t = new Date(iso + "T00:00:00Z"); return DOW[t.getUTCDay()] + " " + t.getUTCDate() + " " + MON[t.getUTCMonth()]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function tomorrow() { return addDays(C.today, 1); }
  $("ld-date").value = addDays(C.today, 10); $("ld-date").min = tomorrow();

  function build() {
    var name = $("ld-name").value.trim(), prod = $("ld-prod").value.trim() || name, day = $("ld-date").value, pl = $("ld-plat").value, look = $("ld-look").value;
    if (!name) { $("ld-msg").textContent = "Type what you are launching first."; $("ld-name").focus(); return; }
    if (!day || day < tomorrow()) { $("ld-msg").textContent = "Pick a launch day from tomorrow onwards."; return; }
    $("ld-msg").textContent = ""; var topic = [name, "Brand", "🚀", "#launch #newlaunch #comingsoon", prod, "excitement"], clamped = 0;
    DECK = PLAN.map(function (p, i) {
      var si = TP.siOf(p[2]), b = TP.build(pl, topic, si, C.brand, "", C.ind), date = addDays(day, p[0]);
      if (date < tomorrow()) { date = tomorrow(); clamped++; }
      b.slides.forEach(function (sl) { sl.look = look === "brand" ? sl.look : look; });
      return { n: i, off: p[0], phase: p[1], date: date, kind: b.kind, channel: pl, title: p[3] + ": " + name, caption: b.caption, hashtags: b.tags, slides: b.slides, theme: look === "brand" ? "brand" : "auto", size: "", trans: i % 3 ? "push" : "zoom" };
    });
    show(clamped, name, day);
  }
  function counts() { var c = { reel: 0, carousel: 0, post: 0, story: 0 }; DECK.forEach(function (d) { c[d.kind]++; }); return c; }
  function show(clamped, name, day) {
    var c = counts(), paid = C.paid;
    $("ld-sum").innerHTML = "<b>" + DECK.length + " pieces, " + nice(DECK[0].date) + " to " + nice(DECK[DECK.length - 1].date) + "</b><br><span class='muted'>" + [c.reel && c.reel + " reels", c.carousel && c.carousel + " carousels", c.post && c.post + " posts", c.story && c.story + " stories"].filter(Boolean).join(" · ") + " · " + DECK.length + " captions with hashtags · launch day " + nice(day) + "</span>" + (clamped ? "<br><span class='muted'>Some pre-launch pieces are set for tomorrow because the launch is close. Pick a later launch day for the full run.</span>" : "");
    var html = "", last = "";
    DECK.forEach(function (d, i) {
      if (d.phase !== last) { html += "<h2 class='ld-ph'>" + d.phase + "</h2>"; last = d.phase; }
      var locked = !paid && i >= FREE_SHOWN;
      html += "<article class='card ld-card" + (locked ? " ld-locked" : "") + "' data-i='" + i + "'><div class='ld-vis'><canvas class='ld-main' aria-label='Design preview'></canvas><div class='ld-strip'></div>" + (d.kind === "reel" || d.kind === "story" ? "<button type='button' class='btn ghost sm ld-play'>▶ Play</button>" : "") + "</div>" +
        "<div class='ld-txt'><div class='ld-meta'><b>" + nice(d.date) + "</b> <span class='tag'>" + ICON[d.kind] + " " + d.kind + "</span> <span class='tag'>" + d.channel + "</span></div><label class='ld-t'>Title<input class='ld-ti' value='" + esc(d.title) + "' maxlength='140'></label>" +
        "<label>Caption<textarea class='ld-cap' rows='7'>" + esc(d.caption) + "</textarea></label><label>Hashtags<input class='ld-tags' value='" + esc(d.hashtags.join(" ")) + "'></label>" + (locked ? "<div class='ld-lockbar'>🔒 <a href='/billing'>Unlock the full deck</a></div>" : "") + "</div></article>";
    });
    $("ld-list").innerHTML = html; $("ld-out").hidden = false; $("ld-done").hidden = true;
    var add = $("ld-add"); if (!paid) { add.textContent = "🔒 Unlock to add the whole deck to my calendar"; }
    Array.prototype.forEach.call(document.querySelectorAll(".ld-card"), function (el) {
      var d = DECK[+el.dataset.i], cv = el.querySelector(".ld-main"), strip = el.querySelector(".ld-strip");
      SD.draw(cv, d, 0, 300); d.slides.forEach(function (s, k) { if (k > 7) return; var b = document.createElement("canvas"); b.className = "ld-mini"; strip.appendChild(b); SD.draw(b, d, k, 70); b.onclick = function () { SD.draw(cv, d, k, 300); }; });
      var pb = el.querySelector(".ld-play"); if (pb) pb.onclick = function () { pb.disabled = true; SD.play(cv, d, 300, function () { pb.disabled = false; SD.draw(cv, d, 0, 300); }); };
      el.querySelector(".ld-ti").oninput = function () { d.title = this.value; }; el.querySelector(".ld-cap").oninput = function () { d.caption = this.value; }; el.querySelector(".ld-tags").oninput = function () { d.hashtags = this.value.match(/#\w+/g) || []; };
    });
    $("ld-out").scrollIntoView({ behavior: "smooth" });
  }
  function addAll() {
    if (!C.paid) { location.href = "/billing"; return; }
    var body = { campaign: ($("ld-name").value.trim() || "Launch") + " launch", items: DECK.map(function (d) { return { title: d.title, kind: d.kind, channel: d.channel, date: d.date, caption: d.caption, hashtags: d.hashtags, cta: "", thumb: SD.thumb(null, d), board: { slides: d.slides, theme: d.theme, size: d.size, trans: d.trans } }; }) };
    $("ld-add").disabled = true; $("ld-add").textContent = "Adding…";
    fetch("/launch-deck/create", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": window.CSRF }, body: JSON.stringify(body) }).then(function (r) { return r.json(); }).then(function (j) {
      $("ld-add").disabled = false; $("ld-add").textContent = "📅 Add the whole deck to my calendar";
      if (!j.ok) { $("ld-msg").textContent = j.error || "Could not save. Try again."; return; }
      $("ld-done").hidden = false; $("ld-done").innerHTML = "<b>🎉 " + j.items.length + " pieces added to your calendar.</b> <a class='btn sm' href='" + j.calendar + "'>Open calendar</a><div class='ld-links'>" + j.items.map(function (x) { return "<a href='" + x.url + "'>" + esc(nice(x.date)) + " · " + ICON[x.kind] + " Edit design</a>"; }).join("") + "</div>"; $("ld-done").scrollIntoView({ behavior: "smooth" });
    }).catch(function () { $("ld-add").disabled = false; $("ld-add").textContent = "📅 Add the whole deck to my calendar"; $("ld-msg").textContent = "Could not save. Try again."; });
  }
  function dl() {
    var t = DECK.map(function (d) { return nice(d.date) + "  |  " + d.kind.toUpperCase() + "  |  " + d.channel + "\n" + d.title + "\n\n" + d.caption + "\n" + d.hashtags.join(" ") + "\n"; }).join("\n----------------------------------------\n\n");
    var a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([t], { type: "text/plain" })); a.download = "launch-deck-captions.txt"; document.body.appendChild(a); a.click(); a.remove();
  }
  $("ld-build").onclick = build; $("ld-add").onclick = addAll; $("ld-txt").onclick = function () { if (!C.paid) { location.href = "/billing"; return; } dl(); };
})();
