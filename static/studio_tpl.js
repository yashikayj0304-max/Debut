/* Template library for the Create studio: platform -> format -> starting point.
   Every template is a moment (Diwali, flash sale, customer story...) crossed with a proven post structure,
   so each platform has well over a thousand different starting points. They are built on the fly, so nothing is stored. */
(function () {
  var PL = {
    "Instagram": { ico: "📸", kinds: ["post", "carousel", "reel", "story"], tags: 5 },
    "LinkedIn": { ico: "💼", kinds: ["post", "carousel", "reel"], tags: 3 },
    "Facebook": { ico: "👍", kinds: ["post", "reel", "story"], tags: 2 },
    "X / Twitter": { ico: "🐦", kinds: ["post", "carousel"], tags: 2 },
    "YouTube": { ico: "▶️", kinds: ["reel", "post"], tags: 5 },
    "WhatsApp": { ico: "💬", kinds: ["story", "post"], tags: 0 },
    "Email": { ico: "✉️", kinds: ["post", "carousel"], tags: 0 }
  };
  var KIND_LABEL = {
    "Instagram": { post: "Post", carousel: "Carousel", reel: "Reel", story: "Story" },
    "LinkedIn": { post: "Post", carousel: "Document carousel", reel: "Video" },
    "Facebook": { post: "Post", reel: "Reel", story: "Story" },
    "X / Twitter": { post: "Tweet", carousel: "Thread" },
    "YouTube": { reel: "Short", post: "Community post" },
    "WhatsApp": { story: "Status", post: "Broadcast card" },
    "Email": { post: "Email banner", carousel: "Newsletter sections" }
  };
  var KIND_ICO = { post: "🖼️", carousel: "🎠", reel: "🎬", story: "📱" };

  // n name, c category, e emoji, t hashtags (what people actually search), w what you offer in that moment, g the feeling
  var T = [
    ["Diwali", "Festival", "🪔", "#diwali #diwaligifts #festiveseason #diwalisale", "festive gift box", "light and joy"],
    ["Dhanteras", "Festival", "✨", "#dhanteras #dhanteras2026 #goldandsilver #shubhmuhurat", "lucky buy", "good fortune"],
    ["Holi", "Festival", "🎨", "#holi #holihai #festivalofcolours #holisale", "colourful combo", "colour and fun"],
    ["Raksha Bandhan", "Festival", "🧿", "#rakshabandhan #rakhigifts #brothersister #rakhi", "rakhi gift set", "a sibling bond"],
    ["Eid", "Festival", "🌙", "#eid #eidmubarak #eidgifts #eidcollection", "Eid special", "togetherness"],
    ["Navratri", "Festival", "💃", "#navratri #garba #navratrispecial #garbanight", "nine-day special", "nine nights of garba"],
    ["Dussehra", "Festival", "🏹", "#dussehra #vijayadashami #festiveoffer #dussehraspecial", "festival offer", "a fresh start"],
    ["Ganesh Chaturthi", "Festival", "🐘", "#ganeshchaturthi #ganpatibappamorya #bappa #ganeshfestival", "festival special", "blessings"],
    ["Onam", "Festival", "🌼", "#onam #onamsadya #onamcelebration #happyonam", "Onam special", "harvest and home"],
    ["Pongal", "Festival", "🌾", "#pongal #happypongal #harvestfestival #pongalspecial", "harvest special", "a good harvest"],
    ["Lohri", "Festival", "🔥", "#lohri #lohricelebration #lohri2027 #winterfestival", "winter warmer", "warmth and bonfires"],
    ["Makar Sankranti", "Festival", "🪁", "#makarsankranti #uttarayan #kiteflying #tilgul", "til-gud special", "kites and sweetness"],
    ["Christmas", "Festival", "🎄", "#christmas #christmasgifts #giftideasindia #secretsanta", "gift box", "giving and cosy evenings"],
    ["New Year", "Festival", "🎆", "#newyear #newyear2027 #newyearnewme #newbeginnings", "new-year offer", "a fresh start"],
    ["Valentine's Day", "Festival", "❤️", "#valentinesday #valentinesgift #loveisintheair #giftforhim", "gift for two", "love"],
    ["Republic Day", "Festival", "🇮🇳", "#republicday #26january #proudindian #madeinindia", "Made-in-India special", "pride"],
    ["Independence Day", "Festival", "🇮🇳", "#independenceday #15august #azadi #madeinindia", "freedom sale", "pride and freedom"],
    ["Women's Day", "Festival", "👩", "#womensday #womenwhoinspire #womenentrepreneurs #iwd", "tribute offer", "celebrating women"],
    ["Mother's Day", "Festival", "💐", "#mothersday #giftsformom #thankyoumom #mothersdaygift", "thank-you gift", "gratitude"],
    ["Father's Day", "Festival", "👔", "#fathersday #giftsfordad #superdad #fathersdaygift", "dad gift", "gratitude"],
    ["Teachers' Day", "Festival", "📚", "#teachersday #thankyouteacher #gururbrahma #teachersdaygift", "thank-you gift", "gratitude"],
    ["Children's Day", "Festival", "🧸", "#childrensday #kidsfun #bachchaparty #childrensdayspecial", "kids special", "playfulness"],
    ["Friendship Day", "Festival", "🤝", "#friendshipday #bestfriends #friendsforever #friendshipgoals", "bestie bundle", "friendship"],
    ["Karwa Chauth", "Festival", "🌕", "#karwachauth #karwachauthgifts #moonrise #karwachauthspecial", "gift set", "love and devotion"],
    ["Bhai Dooj", "Festival", "🪔", "#bhaidooj #bhaidoojgifts #siblinglove #bhaidoojspecial", "gift for bhai", "a sibling bond"],
    ["Durga Puja", "Festival", "🌺", "#durgapuja #pujo #durgapuja2026 #pujovibes", "puja special", "celebration"],
    ["Baisakhi", "Festival", "🌾", "#baisakhi #vaisakhi #punjabifestival #newharvest", "harvest offer", "new harvest"],
    ["Ugadi", "Festival", "🌿", "#ugadi #gudipadwa #newyear #ugadispecial", "new-year special", "new beginnings"],
    ["Black Friday", "Sale", "🖤", "#blackfriday #blackfridaysale #bigsale #blackfridayindia", "biggest deals", "the biggest deals"],
    ["End-of-season sale", "Sale", "🏷️", "#eoss #endofseasonsale #sale #bigsale", "season-end sale", "clearing the shelves"],
    ["Flash sale", "Sale", "⚡", "#flashsale #limitedtime #shopnow #hurry", "24-hour deal", "speed"],
    ["Payday sale", "Sale", "💸", "#payday #paydaysale #treatyourself #shopnow", "payday treat", "treating yourself"],
    ["Buy 1 Get 1", "Sale", "🎁", "#bogo #buy1get1 #offer #shoplocal", "buy one get one", "double the value"],
    ["Free shipping weekend", "Sale", "📦", "#freeshipping #freedelivery #shoponline #weekendsale", "free delivery weekend", "no delivery charge"],
    ["Wedding season", "Season", "💍", "#weddingseason #shaadi #indianwedding #weddingshopping", "wedding edit", "big celebrations"],
    ["Summer", "Season", "☀️", "#summer #summervibes #staycool", "summer special", "beating the heat"],
    ["Monsoon", "Season", "🌧️", "#monsoon #monsoonmagic #rainydays #chai", "monsoon special", "rain and comfort"],
    ["Winter", "Season", "🧣", "#winter #winterspecial #cosyseason #winteroffer", "winter special", "staying cosy"],
    ["Back to school", "Season", "🎒", "#backtoschool #schoolessentials #newsession #parentsofinstagram", "school-ready bundle", "a fresh term"],
    ["Exam season", "Season", "📝", "#examseason #studymotivation #boardexams #allthebest", "study-time special", "focus"],
    ["New launch", "Promo", "🚀", "#newlaunch #justlaunched #comingsoon #introducing", "new launch", "something new"],
    ["Restock", "Promo", "📣", "#backinstock #restock #limitedstock #shopnow", "back in stock", "the wait is over"],
    ["Pre-order", "Promo", "⏳", "#preorder #comingsoon #earlyaccess #bethefirst", "pre-order spot", "being first"],
    ["Giveaway", "Promo", "🎉", "#giveaway #giveawayindia #contest #win", "giveaway", "winning"],
    ["Referral offer", "Promo", "🫶", "#referral #refernearn #friendsandfamily #sharethelove", "refer-a-friend reward", "sharing the love"],
    ["Loyalty reward", "Promo", "🏅", "#loyalty #thankyou #regularcustomers #rewards", "loyalty reward", "thanking regulars"],
    ["Bundle deal", "Promo", "🧺", "#bundle #combo #valuedeal #savemore", "bundle", "more for less"],
    ["Early-bird offer", "Promo", "🐦", "#earlybird #earlyaccess #limitedtime #offer", "early-bird price", "being early"],
    ["Limited edition", "Promo", "💎", "#limitededition #exclusive #onlyfew #dropalert", "limited drop", "being exclusive"],
    ["Collab drop", "Promo", "🤝", "#collab #collaboration #newdrop #teamup", "collab drop", "a team-up"],
    ["Anniversary", "Promo", "🎂", "#anniversary #thankyou #celebrating #birthdayoffer", "anniversary offer", "thanking you"],
    ["Customer story", "Brand", "💬", "#customerlove #happycustomers #testimonial #review", "customer story", "trust"],
    ["Behind the scenes", "Brand", "🎥", "#behindthescenes #bts #madewithlove #smallbusiness", "behind-the-scenes look", "honesty"],
    ["Meet the team", "Brand", "👋", "#meettheteam #teamwork #smallbusinessindia #ourstory", "team intro", "the people"],
    ["FAQ", "Brand", "❓", "#faq #askus #questionsanswered #helpful", "answers to your questions", "clarity"],
    ["Myth busting", "Brand", "🧠", "#mythbusting #didyouknow #knowledge #factsnotmyths", "myth buster", "the truth"],
    ["Quick tips", "Brand", "💡", "#tips #howto #learnwithus", "quick tips", "being helpful"],
    ["Milestone", "Brand", "🏆", "#milestone #thankyou #grateful #community", "milestone celebration", "gratitude"],
    ["How it's made", "Brand", "🛠️", "#howitsmade #handmade #process #madeinindia", "process reveal", "craft"]
  ];

  // Structures. Each returns slides + hook + body + cta; the platform decides the caption shape.
  function S(layout, headline, sub, extra) { var o = { layout: layout, headline: headline, sub: sub || "" }; if (extra) for (var k in extra) o[k] = extra[k]; return o; }
  var ST = [
    ["hook-tips", "3 tips", "carousel", function (t, B) { return { slides: [S("cover", t.n + "? Read this first.", "3 quick things before you buy"), S("tip", "Start early", "The best " + t.w + " goes first.", { num: 1 }), S("tip", "Know what you want", "Pick one thing you will really use.", { num: 2 }), S("tip", "Ask us", "Message " + B + " and we will help you pick.", { num: 3 }), S("cta", "Need help choosing?", "Message " + B)], hook: t.n + "? Read this first.", body: "Three quick things before you buy your " + t.w + ".", cta: "Save this and send it to someone who needs it." }; }],
    ["problem-proof", "Problem, 3 points, proof", "carousel", function (t, B) { return { slides: [S("cover", "Struggling with " + t.n + " shopping?", "Here is the easy way"), S("step", "Skip the rush", "Order your " + t.w + " ahead.", { num: 1 }), S("step", "Keep it simple", "One choice, no stress.", { num: 2 }), S("step", "We handle the rest", "Packed and sent with care.", { num: 3 }), S("quote", "Exactly what I needed.", "A happy customer"), S("cta", "Your turn", "Message " + B + " to order")], hook: "Struggling with " + t.n + " shopping?", body: "Three ways " + B + " makes it easy, plus what a customer said.", cta: "Message us to order." }; }],
    ["offer", "Offer", "post", function (t, B, d) { return { slides: [S("offer", t.w.charAt(0).toUpperCase() + t.w.slice(1), "Now at " + B + (d ? " · till " + d : "")), S("cta", "Order now", "Message " + B + " to claim it")], hook: t.e + " " + t.n + ": " + t.w, body: "Our " + t.w + " is here. Limited stock, so grab yours early.", cta: "Message us to order." }; }],
    ["countdown", "Countdown", "story", function (t, B) { return { slides: [S("cover", "3 days to " + t.n, "Get ready " + t.e), S("cover", "2 days to " + t.n, "Your " + t.w + " is waiting"), S("cover", "Tomorrow!", t.n + " is almost here"), S("offer", "It's here", t.w + " is live now")], hook: "Counting down to " + t.n + " " + t.e, body: "Turn on notifications so you do not miss our " + t.w + ".", cta: "Tap the link in bio." }; }],
    ["before-after", "Before and after", "reel", function (t, B) { return { slides: [S("cover", "Before vs after " + t.n, "Which one are you?"), S("compare", "Before vs after", "Last-minute panic; A calm " + t.n + " with " + B), S("cta", "Want the after?", "Message " + B)], hook: "Before vs after " + t.n, body: "From last-minute panic to a calm " + t.n + ".", cta: "Which one are you? Tell us below." }; }],
    ["pov", "POV", "reel", function (t, B) { return { slides: [S("cover", "POV: it's " + t.n + " and you planned ahead", t.e), S("quote", "I found the perfect " + t.w + " in two minutes.", "You, with " + B), S("cta", "Be this person", "Follow " + B)], hook: "POV: it's " + t.n + " and you planned ahead " + t.e, body: "Be the person who sorted it early.", cta: "Follow us for more." }; }],
    ["big-number", "Big number", "post", function (t, B) { return { slides: [S("stat", "500+", "happy customers this " + t.n), S("cta", "Be next", "Message " + B)], hook: "500+ happy customers this " + t.n, body: "Thank you for trusting " + B + " with your " + t.w + ".", cta: "Be our next happy customer." }; }],
    ["testimonial", "Testimonial", "post", function (t, B) { return { slides: [S("quote", "Paste a real customer review here", "Customer name"), S("cta", "Join them", "Message " + B)], hook: "What our customers say " + t.e, body: "Real words from real customers (shared with permission).", cta: "Want the same? Message us." }; }],
    ["bts", "Behind the scenes", "reel", function (t, B) { return { slides: [S("cover", "Behind the scenes: " + t.n, B), S("step", "How it starts", "Add a photo of the first step.", { num: 1 }), S("step", "How it is made", "Add a photo of the work.", { num: 2 }), S("cta", "See more", "Follow " + B)], hook: "A peek behind the scenes " + t.e, body: "How we get ready for " + t.n + ".", cta: "What should we show next?" }; }],
    ["myth", "Myth vs fact", "carousel", function (t, B) { return { slides: [S("cover", "Myths about " + t.n, "Let's clear them up"), S("compare", "Myth vs fact", "You need to spend a lot; A small budget works if you plan"), S("tip", "The fact", "Simple and early wins every time.", { num: 1 }), S("cta", "Questions?", "Ask " + B)], hook: "3 myths about " + t.n, body: "Let's clear them up, one by one.", cta: "Which one surprised you?" }; }],
    ["faq", "FAQ", "carousel", function (t, B) { return { slides: [S("cover", t.n + " questions, answered", "Quick answers"), S("step", "How do I order?", "Message " + B + " or tap the link in bio.", { num: 1 }), S("step", "How long does it take?", "Add your delivery time here.", { num: 2 }), S("step", "Can I customise it?", "Yes. Tell us what you need.", { num: 3 }), S("cta", "Still unsure?", "Ask " + B)], hook: "Your " + t.n + " questions, answered", body: "The three things people ask us most.", cta: "Ask us anything in the comments." }; }],
    ["picks", "3 picks", "carousel", function (t, B) { return { slides: [S("cover", "3 picks for " + t.n, B), S("list", "Our top picks", "Pick one; Pick two; Pick three"), S("cta", "Want one?", "Message " + B)], hook: "Our 3 picks for " + t.n + " " + t.e, body: "If you are not sure what to choose, start here.", cta: "Which one is your favourite?" }; }],
    ["poll", "Poll", "story", function (t, B) { return { slides: [S("cover", "Help us choose", t.n + " " + t.e), S("list", "Which one?", "Option A; Option B; Surprise me"), S("cta", "Vote in the poll", "Reply and tell " + B)], hook: "Help us choose for " + t.n, body: "Vote in the poll sticker.", cta: "We will share the winner." }; }],
    ["teaser", "Teaser", "reel", function (t, B) { return { slides: [S("cover", "Something is coming for " + t.n, "Can you guess?"), S("quote", "It is worth the wait.", B), S("cta", "Be the first to know", "Follow " + B)], hook: "Something is coming for " + t.n + " " + t.e, body: "A small hint, a big reveal soon.", cta: "Turn on notifications." }; }],
    ["quote", "Quote", "post", function (t, B) { return { slides: [S("quote", "The best part of " + t.n + " is " + t.g + ".", B), S("cta", "Celebrate with us", "Follow " + B)], hook: "The best part of " + t.n + " " + t.e, body: "It is all about " + t.g + ".", cta: "Tag someone you are celebrating with." }; }],
    ["checklist", "Checklist", "carousel", function (t, B) { return { slides: [S("cover", t.n + " checklist", "Save this"), S("list", "Before " + t.n, "Plan your budget; Pick your " + t.w + "; Order early; Share with friends"), S("cta", "Done?", "Message " + B)], hook: "Your " + t.n + " checklist " + t.e, body: "Four steps, so nothing slips.", cta: "Save this for later." }; }],
    ["story-time", "Story time", "reel", function (t, B) { return { slides: [S("cover", "Our " + t.n + " story", t.e), S("quote", "It started with one order and a lot of " + t.g + ".", "The " + B + " team"), S("cta", "Be part of it", "Follow " + B)], hook: "Our " + t.n + " story " + t.e, body: "How a small idea grew with your support.", cta: "Share your story in the comments." }; }],
    ["giveaway", "Giveaway", "post", function (t, B) { return { slides: [S("offer", "Win a " + t.w, "Follow " + B + ", like and tag a friend"), S("cta", "How to enter", "Follow, like, tag")], hook: "GIVEAWAY " + t.e, body: "Win our " + t.w + " for " + t.n + ". Follow, like and tag a friend to enter.", cta: "Winner announced soon." }; }],
    ["thank-you", "Thank you", "post", function (t, B) { return { slides: [S("cover", "Thank you for " + t.n, "From all of us at " + B), S("cta", "See you soon", "Follow " + B)], hook: "Thank you " + t.e, body: "You made " + t.n + " special for us.", cta: "Tell us your favourite moment." }; }],
    ["last-call", "Last call", "story", function (t, B, d) { return { slides: [S("cover", "Last call", t.n + " " + t.e), S("offer", t.w.charAt(0).toUpperCase() + t.w.slice(1), d ? "Ends " + d : "Ends tonight"), S("cta", "Order now", "Message " + B)], hook: "Last call for " + t.n, body: "Our " + t.w + " ends soon.", cta: "Message us now." }; }],
    ["lesson", "Lesson learned", "post", function (t, B) { return { slides: [S("cover", "What " + t.n + " taught us", B), S("quote", "Plan early and keep it simple.", "The " + B + " team"), S("cta", "What did you learn?", "Tell us below")], hook: "What " + t.n + " taught us about running a small brand.", body: "Plan early, keep it simple, and talk to your customers.", cta: "What is your biggest lesson?" }; }],
    ["announce", "Announcement", "post", function (t, B) { return { slides: [S("cover", "Big news for " + t.n, t.e), S("cta", "Find out more", "Message " + B)], hook: "Big news " + t.e, body: "We are getting ready for " + t.n + " with our " + t.w + ".", cta: "Message us for details." }; }],
    ["how-to", "How to", "reel", function (t, B) { return { slides: [S("cover", "How to nail " + t.n, "In 3 steps"), S("step", "Plan", "Decide your budget.", { num: 1 }), S("step", "Pick", "Choose your " + t.w + ".", { num: 2 }), S("step", "Order", "Message " + B + ".", { num: 3 }), S("cta", "Easy", "Follow " + B)], hook: "How to nail " + t.n + " in 3 steps", body: "Plan, pick, order. That is it.", cta: "Save this for later." }; }],
    ["compare", "This or that", "post", function (t, B) { return { slides: [S("compare", "This or that?", "Rushing at the last minute; Ordering early from " + B), S("cta", "Choose early", "Message " + B)], hook: "This or that? " + t.e, body: "Rushing, or ordering early for " + t.n + "?", cta: "Comment this or that." }; }]
  ];

  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function nice(iso) { if (!iso) return ""; var p = iso.split("-"); return p.length === 3 ? (+p[2]) + " " + MON[+p[1] - 1] : ""; }

  function tagsFor(pl, t) { var n = PL[pl].tags; if (!n) return []; return (t[3] || "").split(/\s+/).filter(Boolean).slice(0, n); }
  function cap(pl, x, t) {
    var tags = tagsFor(pl, t).join(" ");
    if (pl === "LinkedIn") return x.hook + "\n\n" + x.body + "\n\nWe have been thinking about this a lot while getting ready for " + t[0] + ".\n\n" + x.cta + (tags ? "\n\n" + tags : "");
    if (pl === "X / Twitter") { var s = x.hook + " " + x.body + " " + x.cta; return s.length > 240 ? s.slice(0, 237) + "..." : s; }
    if (pl === "YouTube") return x.hook + "\n\n" + x.body + "\n\n" + x.cta + "\nSubscribe for more." + (tags ? "\n\n" + tags : "");
    if (pl === "WhatsApp") return "Hi! 👋 " + x.hook + "\n\n" + x.body + "\n\nReply YES and we will share the details.";
    if (pl === "Email") return "Subject: " + x.hook + "\n\nHi there,\n\n" + x.body + "\n\n" + x.cta + "\n\nWarmly,\nThe team";
    if (pl === "Facebook") return x.hook + "\n\n" + x.body + " " + x.cta + (tags ? "\n\n" + tags : "");
    return x.hook + "\n\n" + x.body + "\n\n" + x.cta + (tags ? "\n\n" + tags : "");
  }
  function kindFor(pl, k) {
    var ok = PL[pl].kinds; if (ok.indexOf(k) > -1) return k;
    if (k === "reel") return ok.indexOf("carousel") > -1 ? "carousel" : ok[0];
    if (k === "story") return ok.indexOf("post") > -1 ? "post" : ok[0];
    if (k === "carousel") return ok.indexOf("post") > -1 ? "post" : ok[0];
    return ok[0];
  }

  var TPL = { platforms: Object.keys(PL), PL: PL, KIND_LABEL: KIND_LABEL, KIND_ICO: KIND_ICO, topics: T, cats: ["Festival", "Sale", "Season", "Promo", "Brand"] };
  TPL.total = function (pl) { return T.length * ST.length; };
  TPL.kindsOf = function (pl) { return PL[pl].kinds; };
  TPL.count = function (pl, kind) { var c = 0; ST.forEach(function (s) { if (kindFor(pl, s[2]) === kind) c += T.length; }); return c; };
  // list: filters {kind, cat, q, topic}; returns [{id, ti, si, label, topic, cat, kind}]
  TPL.list = function (pl, f) {
    f = f || []; var out = [], q = (f.q || "").toLowerCase();
    T.forEach(function (t, ti) {
      if (f.cat && t[1] !== f.cat) return; if (f.topic != null && f.topic !== ti) return;
      ST.forEach(function (s, si) {
        var k = kindFor(pl, s[2]); if (f.kind && k !== f.kind) return;
        if (q && (t[0] + " " + s[1] + " " + t[1]).toLowerCase().indexOf(q) < 0) return;
        out.push({ ti: ti, si: si, kind: k, label: s[1], topic: t[0], cat: t[1], emoji: t[2] });
      });
    });
    return out;
  };
  TPL.build = function (pl, ti, si, B, dateIso) {
    var t = T[ti], s = ST[si], tt = { n: t[0], c: t[1], e: t[2], t: t[3], w: t[4], g: t[5] }; tt[3] = t[3]; tt[0] = t[0];
    var x = s[3](tt, B, nice(dateIso)), k = kindFor(pl, s[2]);
    return { kind: k, slides: x.slides, caption: cap(pl, x, t), tags: tagsFor(pl, t), title: t[0] + ": " + s[1], channel: pl };
  };
  var ALT = [["deepavali", "Diwali"], ["diwali", "Diwali"], ["dhanteras", "Dhanteras"], ["holi", "Holi"], ["raksha", "Raksha Bandhan"], ["rakhi", "Raksha Bandhan"], ["eid", "Eid"], ["navratri", "Navratri"], ["navaratri", "Navratri"], ["dussehra", "Dussehra"], ["vijayadashami", "Dussehra"], ["ganesh", "Ganesh Chaturthi"], ["onam", "Onam"], ["pongal", "Pongal"], ["lohri", "Lohri"], ["sankranti", "Makar Sankranti"], ["christmas", "Christmas"], ["new year", "New Year"], ["valentine", "Valentine's Day"], ["republic", "Republic Day"], ["independence", "Independence Day"], ["women", "Women's Day"], ["mother", "Mother's Day"], ["father", "Father's Day"], ["teacher", "Teachers' Day"], ["children", "Children's Day"], ["friendship", "Friendship Day"], ["karwa", "Karwa Chauth"], ["bhai dooj", "Bhai Dooj"], ["durga", "Durga Puja"], ["baisakhi", "Baisakhi"], ["ugadi", "Ugadi"], ["black friday", "Black Friday"], ["sale", "Flash sale"], ["launch", "New launch"], ["giveaway", "Giveaway"]];
  TPL.topicFor = function (name) {
    var n = (name || "").toLowerCase();
    for (var i = 0; i < ALT.length; i++) if (n.indexOf(ALT[i][0]) > -1) for (var j = 0; j < T.length; j++) if (T[j][0] === ALT[i][1]) return j;
    return -1;
  };
  window.TPL = TPL;
})();
