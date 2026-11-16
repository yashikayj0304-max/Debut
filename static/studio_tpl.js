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

    ["coupon", "Coupon", "post", function (t, B, d) { return { slides: [S("coupon", "20% OFF", t.code + "; " + (d ? "Valid till " + d : "Valid this week") + "; On your " + t.n + " order"), S("cta", t.cta, B)], hook: t.e + " 20% off for " + t.n, body: "Use code " + t.code + (d ? " till " + d : " this week") + ". Our " + t.w + " is waiting.", cta: t.cta + " and use the code." }; }],
    ["menu-card", "Price list", "post", function (t, B) { return { slides: [S("menu", t.n + " price list", t.menu), S("cta", t.cta, B)], hook: t.e + " " + t.n + " price list", body: t.menu.split(";").slice(0, 3).join(". ") + ".", cta: t.cta + "." }; }],
    ["event-invite", "Event invite", "post", function (t, B, d) { return { slides: [S("event", "Join us for " + t.n, (d ? d.split(" ").reverse().join(" ") : "Sat 25") + "; 6 PM onwards; Add your venue here"), S("cta", "Save your spot", t.cta)], hook: t.e + " You are invited: " + t.n, body: "Join us" + (d ? " on " + d : "") + ". Add your venue and time in the image.", cta: t.cta + " to save your spot." }; }],
    ["launch-ribbon", "New ribbon", "post", function (t, B) { return { slides: [S("ribbon", t.prod + " is here", "Made for " + t.n + "; NEW"), S("cta", t.cta, B)], hook: t.e + " New: " + t.prod, body: "Meet our " + t.prod.toLowerCase() + " for " + t.n + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["stat-trio", "3 numbers", "post", function (t, B) { return { slides: [S("stat3", "Why " + B, t.nums), S("cta", t.cta, B)], hook: t.e + " " + t.nums.split(";")[0], body: t.nums.replace(/;/g, ". ") + ".", cta: t.cta + "." }; }],
    ["magazine-cover", "Magazine cover", "post", function (t, B) { return { slides: [S("magazine", "The " + t.n + " edit", "Our picks, stories and offers; Issue " + t.n.split(" ")[0]), S("cta", t.cta, B)], hook: t.e + " The " + t.n + " edit", body: "Our picks, our stories and one special offer for " + t.n + ".", cta: t.cta + "." }; }],
    ["picks-collage", "Picks collage", "post", function (t, B) { return { slides: [S("collage", "Our " + t.n + " picks", t.feats + "; " + t.prod), S("cta", t.cta, B)], hook: t.e + " Our " + t.n + " picks", body: t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["this-vs-that", "Versus", "post", function (t, B) { return { slides: [S("versus", "Which one are you?", "Last-minute rush; Planned with " + B), S("cta", "Be option B", t.cta)], hook: t.e + " Which one are you?", body: "Last-minute rush, or planned ahead for " + t.n + "?", cta: "Comment A or B." }; }],
    ["how-it-works", "How it works", "carousel", function (t, B) { return { slides: [S("cover", "How it works", B + " · " + t.n + " " + t.e), S("timeline", "4 easy steps", t.steps), S("cta", t.cta, B)], hook: "How it works " + t.e, body: t.steps.split(";").map(function (x, i) { return (i + 1) + ") " + x; }).join(" "), cta: t.cta + "." }; }],
    ["coupon-story", "Coupon story", "story", function (t, B, d) { return { slides: [S("ribbon", "A gift for " + t.n, "Swipe up for your code; NEW"), S("coupon", "20% OFF", t.code + "; " + (d ? "Valid till " + d : "Valid this week") + "; On your " + t.n + " order"), S("cta", t.cta, B)], hook: t.e + " A gift for " + t.n, body: "Use code " + t.code + ".", cta: t.cta + "." }; }],
    ["event-story", "Event story", "story", function (t, B, d) { return { slides: [S("bold", "You are invited"), S("event", t.n + " at " + B, (d ? d.split(" ").reverse().join(" ") : "Sat 25") + "; 6 PM onwards; Add your venue here"), S("cta", "Save your spot", t.cta)], hook: t.e + " You are invited", body: "Join us for " + t.n + ".", cta: t.cta + "." }; }],
    ["spotlight", "Product spotlight", "post", function (t, B) { return { slides: [S("spotlight", t.prod + " for " + t.n, t.feats, { emoji: t.e }), S("cta", t.cta, B)], hook: t.e + " " + t.prod + " for " + t.n, body: "Meet our " + t.prod.toLowerCase() + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + ". Link in bio." }; }],
    ["stop-scroll", "Stop scrolling reel", "reel", function (t, B) { return { slides: [S("bold", "Stop scrolling", t.n + " " + t.e), S("bold", "Your " + t.w + " is here"), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: "Stop scrolling " + t.e, body: "Your " + t.w + " for " + t.n + " is here. " + t.price[2] + ".", cta: t.cta + "." }; }],
    ["three-reasons", "3 reasons", "carousel", function (t, B) { return { slides: [S("cover", "3 reasons to choose " + B, t.n + " " + t.e), S("split", t.tips[0], "Why it matters for " + t.n + ".", { emoji: "1️⃣" }), S("split", t.tips[1], "Small things, big difference.", { emoji: "2️⃣" }), S("split", t.tips[2], "Ask us and we will help.", { emoji: "3️⃣" }), S("cta", t.cta, B)], hook: "3 reasons " + t.e, body: t.tips.join(". ") + ".", cta: t.cta + "." }; }],
    ["offer-ends", "Offer ends soon", "story", function (t, B, d) { return { slides: [S("countdown", "3", "days left for " + t.n), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: "Offer ends soon " + t.e, body: t.prod + " at " + t.price[0] + " for " + t.n + ".", cta: t.cta + "." }; }],
    ["price-drop", "Price tag", "post", function (t, B, d) { return { slides: [S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2], { emoji: t.e }), S("cta", t.cta, d ? "Offer till " + d : "Limited time only")], hook: t.e + " " + t.prod + " now " + t.price[0], body: "Was " + t.price[1] + ", now " + t.price[0] + ". " + t.price[2] + ".", cta: t.cta + " before " + (d || "it ends") + "." }; }],
    ["new-arrival", "New arrival reel", "reel", function (t, B) { return { slides: [S("bold", "New in", B), S("spotlight", t.prod, t.feats, { emoji: t.e }), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, "Link in bio")], hook: "New in " + t.e, body: "Say hello to our " + t.prod.toLowerCase() + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["review-card", "Review card", "post", function (t, B) { return { slides: [S("review", t.rev, "Happy customer"), S("cta", "Join " + t.proof.split(" ")[0] + " others", t.cta)], hook: "★★★★★ " + t.e + " What our customers say", body: "“" + t.rev + "” Shared with permission.", cta: t.cta + "." }; }],
    ["vote-story", "Vote story", "story", function (t, B) { return { slides: [S("poll", "Which one for " + t.n + "?", t.prod + "; Something new"), S("cta", "Thanks for voting", "Follow " + B)], hook: "You decide " + t.e, body: "Vote in the poll sticker.", cta: "We will share the winner." }; }],
    ["photo-story", "Photo story", "story", function (t, B) { return { slides: [S("photo", t.n + " at " + B, "Add your photo here", { emoji: t.e }), S("photo", t.prod, "Swap in a close-up of the " + t.prod.toLowerCase(), { emoji: "✨" }), S("cta", t.cta, B)], hook: t.e + " " + t.n + " at " + B, body: "A little peek for you.", cta: t.cta + "." }; }],
    ["pro-tips", "3 pro tips", "carousel", function (t, B) { return { slides: [S("cover", "3 tips before " + t.n, "From people who do this every day"), S("tip", t.tips[0], "", { num: 1 }), S("tip", t.tips[1], "", { num: 2 }), S("tip", t.tips[2], "", { num: 3 }), S("cta", t.cta, B)], hook: "3 tips before " + t.n + " " + t.e, body: t.tips.join(". ") + ".", cta: t.cta + "." }; }],
    ["proof-reel", "Proof reel", "reel", function (t, B) { return { slides: [S("bold", "Why people trust us"), S("stat", t.proof.split(" ")[0], t.proof.split(" ").slice(1).join(" ")), S("review", t.rev, "Happy customer"), S("cta", t.cta, B)], hook: t.proof + " " + t.e, body: "“" + t.rev + "”", cta: t.cta + "." }; }],
    ["countdown-reel", "Countdown reel", "reel", function (t, B) { return { slides: [S("countdown", "3", "days to " + t.n), S("countdown", "2", "days to " + t.n), S("countdown", "1", "day to " + t.n), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: t.e + " " + t.n + " is almost here", body: t.prod + " at " + t.price[0] + ". " + t.price[2] + ".", cta: t.cta + "." }; }],
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


  // ---- Looks: every template gets colours that belong to its moment (event) or, failing that, its industry. Never the app's own theme. ----
  // a, b gradient stops; fg text; ac accent (buttons, numbers); ac2 second accent; m motif drawn behind the words
  var LOOK = {
    diwali:   { a: "#b91c1c", b: "#d97706", fg: "#fff7e6", ac: "#fde047", ac2: "#fb923c", m: "sparks" },
    dhanteras:{ a: "#1e1b4b", b: "#7c2d12", fg: "#fff7e6", ac: "#facc15", ac2: "#f59e0b", m: "sparks" },
    holi:     { a: "#7c3aed", b: "#ec4899", fg: "#ffffff", ac: "#fde047", ac2: "#22d3ee", m: "splash" },
    rakhi:    { a: "#be123c", b: "#f97316", fg: "#fff7ed", ac: "#fde68a", ac2: "#fecdd3", m: "rings" },
    eid:      { a: "#064e3b", b: "#0f766e", fg: "#f0fdf4", ac: "#fcd34d", ac2: "#a7f3d0", m: "stars" },
    navratri: { a: "#9d174d", b: "#ea580c", fg: "#fffbeb", ac: "#fde047", ac2: "#f472b6", m: "rings" },
    dussehra: { a: "#7c2d12", b: "#dc2626", fg: "#fffbeb", ac: "#fbbf24", ac2: "#fb923c", m: "rays" },
    ganesh:   { a: "#c2410c", b: "#f59e0b", fg: "#fffbeb", ac: "#7f1d1d", ac2: "#fef3c7", m: "rings" },
    harvest:  { a: "#15803d", b: "#facc15", fg: "#052e16", ac: "#b45309", ac2: "#ffffff", m: "rays" },
    winterfest:{ a: "#7c2d12", b: "#f97316", fg: "#fffbeb", ac: "#fde047", ac2: "#fecaca", m: "sparks" },
    christmas:{ a: "#7f1d1d", b: "#166534", fg: "#ffffff", ac: "#fde047", ac2: "#fecaca", m: "snow" },
    newyear:  { a: "#0f172a", b: "#6d28d9", fg: "#ffffff", ac: "#fbbf24", ac2: "#22d3ee", m: "confetti" },
    love:     { a: "#be123c", b: "#f472b6", fg: "#fff1f2", ac: "#ffffff", ac2: "#fecdd3", m: "hearts" },
    tricolour:{ a: "#ea580c", b: "#16a34a", fg: "#ffffff", ac: "#1d4ed8", ac2: "#ffffff", m: "bands" },
    women:    { a: "#86198f", b: "#e11d48", fg: "#fff1f2", ac: "#fde68a", ac2: "#f5d0fe", m: "rings" },
    family:   { a: "#0ea5e9", b: "#f472b6", fg: "#ffffff", ac: "#fef08a", ac2: "#ffffff", m: "confetti" },
    kids:     { a: "#06b6d4", b: "#a855f7", fg: "#ffffff", ac: "#fde047", ac2: "#fb7185", m: "confetti" },
    school:   { a: "#1d4ed8", b: "#0ea5e9", fg: "#ffffff", ac: "#fde047", ac2: "#bfdbfe", m: "grid" },
    sale:     { a: "#111827", b: "#dc2626", fg: "#ffffff", ac: "#fde047", ac2: "#ffffff", m: "bands" },
    flash:    { a: "#4c1d95", b: "#db2777", fg: "#ffffff", ac: "#fde047", ac2: "#22d3ee", m: "bolts" },
    bundle:   { a: "#0f766e", b: "#2563eb", fg: "#ffffff", ac: "#fde047", ac2: "#a7f3d0", m: "confetti" },
    wedding:  { a: "#831843", b: "#c2410c", fg: "#fff7ed", ac: "#fcd34d", ac2: "#fbcfe8", m: "rings" },
    summer:   { a: "#f97316", b: "#facc15", fg: "#431407", ac: "#0369a1", ac2: "#ffffff", m: "rays" },
    monsoon:  { a: "#0c4a6e", b: "#0d9488", fg: "#f0f9ff", ac: "#a5f3fc", ac2: "#e0f2fe", m: "drops" },
    winter:   { a: "#1e3a8a", b: "#0ea5e9", fg: "#ffffff", ac: "#e0f2fe", ac2: "#fde68a", m: "snow" },
    exam:     { a: "#312e81", b: "#2563eb", fg: "#ffffff", ac: "#fde047", ac2: "#c7d2fe", m: "grid" },
    launch:   { a: "#4338ca", b: "#06b6d4", fg: "#ffffff", ac: "#fde047", ac2: "#fb7185", m: "bolts" },
    giveaway: { a: "#c026d3", b: "#f97316", fg: "#ffffff", ac: "#fde047", ac2: "#ffffff", m: "confetti" },
    trust:    { a: "#0f172a", b: "#0e7490", fg: "#ffffff", ac: "#34d399", ac2: "#a5f3fc", m: "grid" },
    people:   { a: "#7c3aed", b: "#f43f5e", fg: "#ffffff", ac: "#fde047", ac2: "#fecdd3", m: "rings" },
    learn:    { a: "#0b3b5c", b: "#0d9488", fg: "#ffffff", ac: "#fde047", ac2: "#99f6e4", m: "grid" },
    celebrate:{ a: "#be185d", b: "#7c3aed", fg: "#ffffff", ac: "#fde047", ac2: "#67e8f9", m: "confetti" }
  };
  var TOPIC_LOOK = { "Diwali": "diwali", "Dhanteras": "dhanteras", "Holi": "holi", "Raksha Bandhan": "rakhi", "Eid": "eid", "Navratri": "navratri", "Dussehra": "dussehra", "Ganesh Chaturthi": "ganesh",
    "Onam": "harvest", "Pongal": "harvest", "Lohri": "winterfest", "Makar Sankranti": "harvest", "Christmas": "christmas", "New Year": "newyear", "Valentine's Day": "love", "Republic Day": "tricolour",
    "Independence Day": "tricolour", "Women's Day": "women", "Mother's Day": "women", "Father's Day": "trust", "Teachers' Day": "school", "Children's Day": "kids", "Friendship Day": "family", "Karwa Chauth": "rakhi",
    "Bhai Dooj": "rakhi", "Durga Puja": "navratri", "Baisakhi": "harvest", "Ugadi": "harvest", "Black Friday": "sale", "End-of-season sale": "sale", "Flash sale": "flash", "Payday sale": "flash", "Buy 1 Get 1": "bundle",
    "Free shipping weekend": "bundle", "Wedding season": "wedding", "Summer": "summer", "Monsoon": "monsoon", "Winter": "winter", "Back to school": "school", "Exam season": "exam", "New launch": "launch", "Restock": "launch",
    "Pre-order": "launch", "Giveaway": "giveaway", "Referral offer": "giveaway", "Loyalty reward": "celebrate", "Bundle deal": "bundle", "Early-bird offer": "flash", "Limited edition": "flash", "Collab drop": "launch",
    "Anniversary": "celebrate", "Customer story": "trust", "Behind the scenes": "people", "Meet the team": "people", "FAQ": "learn", "Myth busting": "learn", "Quick tips": "learn", "Milestone": "celebrate", "How it's made": "people" };
  // Industry flavour: the looks an industry leans towards when a moment has no colours of its own, plus what that industry really sells
  var IND = {
    general:   { w: "special offer", looks: ["launch", "celebrate", "people"], tags: "#smallbusiness #shoplocal", cta: "Message us", prod: "Bestseller", proof: "500+ happy customers", tips: "Plan early;Keep it simple;Ask us anything", price: "₹499;₹799;Free delivery", rev: "Quick, friendly and exactly what I wanted.", feats: "Made with care;Fast delivery;Easy returns", menu: "Starter pack - ₹499;Family pack - ₹899;Gift box - ₹1,299", steps: "Tell us what you need;We suggest the best fit;Confirm and pay;Delivered to you", nums: "500+ happy customers;4.9★ average rating;48h delivery", code: "FESTIVE20" },
    d2c:       { w: "bestseller bundle", looks: ["bundle", "flash", "celebrate"], tags: "#d2cindia #shoponline #madeinindia", cta: "Shop now", prod: "Bestseller bundle", proof: "10,000+ orders shipped", tips: "Check the ingredients;Start with the mini pack;Pair it with a routine", price: "₹799;₹1,199;Free shipping", rev: "Arrived in 2 days and the quality is unreal.", feats: "Free shipping;COD available;7-day returns", menu: "Starter kit - ₹799;Bestseller bundle - ₹1,499;Gift set - ₹1,999", steps: "Pick your product;Place the order;We pack and ship;Unbox in 2 days", nums: "10,000+ orders shipped;4.8★ rating;7-day returns", code: "SHIP20" },
    hospitality:{ w: "festive menu and stays", looks: ["summer", "wedding", "diwali"], tags: "#foodiesofindia #staycation #restaurantindia", cta: "Book a table", prod: "Chef's special", proof: "2,000+ guests this month", tips: "Book ahead for weekends;Ask for the chef's special;Come hungry", price: "₹599;₹899;Includes a drink", rev: "Best meal we have had in months. Staff were lovely.", feats: "Fresh ingredients;Family friendly;Pure veg options", menu: "Butter chicken - ₹399;Dal makhani - ₹299;Paneer tikka - ₹349;Gulab jamun - ₹149", steps: "Reserve your table;Choose from the menu;Enjoy fresh food;Tell us how it was", nums: "2,000+ guests a month;4.7★ on Google;15 min avg wait", code: "TABLE20" },
    fmcg:      { w: "festive family pack", looks: ["flash", "harvest", "bundle"], tags: "#fmcg #madeinindia #familypack", cta: "Find it near you", prod: "Family pack", proof: "1 lakh+ packs sold", tips: "Check the label;Store it cool and dry;Buy the family pack to save", price: "₹149;₹199;Pack of 3", rev: "Our whole family loves it. Always in the kitchen.", feats: "No added colours;Value pack;Available nearby", menu: "Single pack - ₹49;Family pack - ₹149;Value pack of 3 - ₹399", steps: "Find it at your store;Pick your pack;Enjoy with family;Share your review", nums: "1 lakh+ packs sold;4.6★ rated;Available in 500 stores", code: "FAMILY10" },
    saas:      { w: "free trial", looks: ["launch", "trust", "learn"], tags: "#saas #startupindia #productivity", cta: "Start free trial", prod: "Pro plan", proof: "1,200+ teams onboard", tips: "Automate the boring bits;Track one metric daily;Invite your team early", price: "₹999;₹1,499;14-day free trial", rev: "Saved us 6 hours every week from day one.", feats: "No credit card;Setup in 5 min;Cancel anytime", menu: "Starter - ₹499;Pro - ₹999;Team - ₹2,499", steps: "Sign up free;Connect your tools;Invite your team;See results in a week", nums: "1,200+ teams;4.8★ on G2;Setup in 5 min", code: "START14" },
    realestate:{ w: "site visit slot", looks: ["trust", "winterfest", "wedding"], tags: "#realestateindia #dreamhome #propertyinvestment", cta: "Book a site visit", prod: "3 BHK sample flat", proof: "300+ families moved in", tips: "Visit at different times of day;Check the RERA number;Ask about maintenance cost", price: "₹68 L;₹75 L;Limited units", rev: "Honest advice and a smooth registration.", feats: "RERA approved;Ready to move;Bank loan help", menu: "2 BHK - ₹45 L;3 BHK - ₹68 L;4 BHK - ₹92 L", steps: "Book a site visit;See the flat;Check paperwork and loan;Move in", nums: "300+ families;RERA approved;Ready to move", code: "VISIT10" },
    education: { w: "admissions window", looks: ["school", "exam", "learn"], tags: "#education #admissionsopen #learnwithus", cta: "Enrol now", prod: "Weekend batch", proof: "5,000+ students taught", tips: "Revise a little every day;Practise past papers;Sleep before the exam", price: "₹4,999;₹7,999;Free demo class", rev: "My marks went up in just two months.", feats: "Small batches;Doubt sessions;Free demo", menu: "Weekend batch - ₹4,999;Weekday batch - ₹6,999;Crash course - ₹2,999", steps: "Book a free demo;Pick your batch;Learn and practise;Track your progress", nums: "5,000+ students;92% pass rate;Doubt help daily", code: "LEARN15" },
    healthcare:{ w: "health check-up", looks: ["trust", "monsoon", "learn"], tags: "#healthcare #wellness #stayhealthy", cta: "Book an appointment", prod: "Full health check-up", proof: "10,000+ patients served", tips: "Drink enough water;Get a yearly check-up;Do not ignore small symptoms", price: "₹1,499;₹2,499;Reports in 24 hrs", rev: "Caring doctors and zero waiting time.", feats: "Trusted doctors;Same-day reports;Home sample pickup", menu: "Basic check-up - ₹999;Full body - ₹1,999;Senior plan - ₹2,499", steps: "Book a slot;Visit or home pickup;Get reports in 24 hrs;Talk to a doctor", nums: "10,000+ patients;4.8★ rated;Reports in 24 hrs", code: "CARE15" },
    fashion:   { w: "new collection", looks: ["wedding", "love", "celebrate"], tags: "#ootd #fashionindia #styleinspo", cta: "Shop the look", prod: "New collection", proof: "Loved by 8,000+ customers", tips: "Start with one hero piece;Mix prints with solids;Check the fit before the colour", price: "₹1,299;₹1,999;Easy exchange", rev: "The fit is perfect and the fabric feels premium.", feats: "Easy exchange;Real photos;Ships in 48 hrs", menu: "Kurta set - ₹1,499;Co-ord set - ₹1,999;Festive saree - ₹2,799", steps: "Pick your style;Choose your size;Order in 2 taps;Easy exchange", nums: "8,000+ happy customers;4.8★ rated;48h shipping", code: "STYLE20" },
    fintech:   { w: "zero-fee plan", looks: ["trust", "launch", "learn"], tags: "#fintech #moneymatters #investsmart", cta: "Get started", prod: "Zero-fee plan", proof: "50,000+ users trust us", tips: "Automate your savings;Track every expense;Start a small SIP", price: "₹0;₹499;Zero fees", rev: "Simple, safe and super quick to set up.", feats: "Bank-grade security;Zero hidden fees;Instant setup", menu: "Basic - ₹0;Plus - ₹199;Pro - ₹499", steps: "Download the app;Verify in minutes;Add money;Start saving", nums: "50,000+ users;Zero hidden fees;Bank-grade security", code: "SAVE50" },
    agency:    { w: "free marketing audit", looks: ["launch", "trust", "people"], tags: "#digitalmarketing #marketingagency #growthmarketing", cta: "Book a free audit", prod: "Growth package", proof: "40+ brands grown", tips: "Post at one fixed time;Reuse your best post;Measure what you post", price: "₹24,999;₹39,999;Per month", rev: "Our leads doubled in 90 days.", feats: "Content plan;Monthly report;Dedicated manager", menu: "Starter - ₹14,999;Growth - ₹24,999;Scale - ₹39,999", steps: "Free audit;Strategy plan;Content and ads live;Monthly report", nums: "40+ brands grown;3x average reach;Reports every month", code: "AUDIT0" },
    personal_brand:{ w: "free 1:1 session", looks: ["people", "celebrate", "learn"], tags: "#personalbrand #creatoreconomy #contentcreator", cta: "Book a free call", prod: "1:1 session", proof: "300+ people coached", tips: "Show up weekly;Share one real story;Reply to every comment", price: "₹1,999;₹2,999;60 minutes", rev: "One session gave me more clarity than a year of guessing.", feats: "1:1 attention;Action plan;Follow-up notes", menu: "Intro call - ₹0;1:1 session - ₹1,999;Monthly mentoring - ₹7,999", steps: "Book a free call;Share your goal;Get your plan;Check in weekly", nums: "300+ people coached;4.9★ rated;Plans in 48h", code: "CALL1" },
    b2b:       { w: "free consultation", looks: ["trust", "learn", "launch"], tags: "#b2b #manufacturingindia #businessgrowth", cta: "Request a quote", prod: "Bulk order", proof: "150+ businesses supplied", tips: "Ask for samples first;Compare total cost;Check delivery timelines", price: "₹95;₹120;Per unit, 500+", rev: "On-time delivery, every single time.", feats: "GST invoice;Bulk pricing;Pan-India delivery", menu: "100 units - ₹120;500 units - ₹105;1000 units - ₹95", steps: "Share your need;Get a quote;Approve a sample;Bulk delivery", nums: "150+ businesses;On-time delivery;GST invoice", code: "BULK5" },
    retail:    { w: "in-store offer", looks: ["sale", "flash", "bundle"], tags: "#retail #shoplocal #storeoffer", cta: "Visit the store", prod: "Store special", proof: "Serving this area since 2015", tips: "Visit on weekdays for peace;Ask about combo offers;Check the warranty", price: "₹999;₹1,499;In-store only", rev: "Great range and the staff helped me choose.", feats: "In-store offers;Easy exchange;Free parking", menu: "Combo 1 - ₹999;Combo 2 - ₹1,499;Gift hamper - ₹1,999", steps: "Visit the store;Try before you buy;Pick your combo;Carry it home", nums: "Serving since 2015;4.7★ rated;Free parking", code: "STORE10" },
    startup:   { w: "early access", looks: ["launch", "flash", "celebrate"], tags: "#startupindia #buildinpublic #founderlife", cta: "Join the waitlist", prod: "Early access", proof: "2,000+ on the waitlist", tips: "Talk to users weekly;Ship small, ship often;Share what you learn", price: "₹0;₹999;Early-bird", rev: "Finally a tool that gets what we actually need.", feats: "Early-bird price;Founder support;Shape the product", menu: "Early access - ₹0;Founding plan - ₹499;Team - ₹1,999", steps: "Join the waitlist;Get your invite;Try the beta;Tell us what to build", nums: "2,000+ on the waitlist;Beta this month;Founder replies daily", code: "EARLY" }
  };
  function lookFor(t, ind, si) {
    var k = TOPIC_LOOK[t[0]], I = IND[ind] || IND.general;
    if (k && (t[1] === "Festival" || t[1] === "Season" || t[1] === "Sale")) return k;
    var l = I.looks; return l[(si || 0) % l.length] || k || "launch";
  }

  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function nice(iso) { if (!iso) return ""; var p = iso.split("-"); return p.length === 3 ? (+p[2]) + " " + MON[+p[1] - 1] : ""; }

  function tagsFor(pl, t) { var n = PL[pl].tags; if (!n) return []; return (t[3] || "").split(/\s+/).filter(Boolean).slice(0, n); }
  var BUL = ["✔", "✨", "👉", "🎯", "💛", "🔥"];
  function cap(pl, x, t, ind) {
    var I = IND[ind] || IND.general, tags = tagsFor(pl, t), extra = PL[pl].tags ? (I.tags || "").split(/\s+/).filter(Boolean).slice(0, 2) : [], all = tags.concat(extra).join(" ");
    var lines = String(x.body || "").split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 3), cat = t[1];
    if (lines.length < 3) lines.push(cat === "Brand" ? "Built with care, and shared with honesty." : "Made for " + t[5] + ", so every detail counts.");
    if (lines.length < 3) lines.push(cat === "Sale" || cat === "Promo" ? "Limited time, so do not wait till the last minute." : cat === "Festival" ? "Order early so it reaches you in time." : "Tell us what you would love to see next.");
    var bullets = lines.map(function (l, i) { return BUL[i % 3] + " " + l; }).join("\n");
    if (pl === "LinkedIn") return x.hook + "\n\n" + lines.join("\n\n") + "\n\nWhat has your experience been? I would love to hear it in the comments.\n\n" + x.cta + (all ? "\n\n" + all : "");
    if (pl === "X / Twitter") { var s = x.hook + " " + x.body + " " + x.cta; return s.length > 240 ? s.slice(0, 237) + "..." : s; }
    if (pl === "YouTube") return x.hook + "\n\n" + x.body + "\n\n⏱️ In this video: the quick version.\n👍 Like, 💬 comment and 🔔 subscribe for more.\n\n" + x.cta + (all ? "\n\n" + all : "");
    if (pl === "WhatsApp") return "Hi! 👋\n\n" + x.hook + "\n\n" + bullets + "\n\nReply *YES* and we will share the details. 🙌";
    if (pl === "Email") return "Subject: " + x.hook + "\n\nHi there,\n\n" + x.body + "\n\n" + x.cta + "\n\nWarmly,\nThe team";
    if (pl === "Facebook") return x.hook + "\n\n" + bullets + "\n\n👉 " + x.cta + (all ? "\n\n" + all : "");
    return x.hook + "\n\n" + bullets + "\n\n👉 " + x.cta + "\n💾 Save this for later  ·  📤 Share it with someone who needs it" + (all ? "\n\n" + all : "");
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
  TPL.build = function (pl, ti, si, B, dateIso, ind) {
    var t = Array.isArray(ti) ? ti : T[ti], s = ST[si], I = IND[ind] || IND.general, w = (t[1] === "Brand") ? t[4] : (ind && ind !== "general" ? I.w : t[4]);
    var tt = { n: t[0], c: t[1], e: t[2], t: t[3], w: w, g: t[5], I: I, cta: I.cta, prod: I.prod, proof: I.proof, tips: I.tips.split(";"), price: I.price.split(";"), rev: I.rev, feats: I.feats, menu: I.menu, steps: I.steps, nums: I.nums, code: I.code }; tt[3] = t[3]; tt[0] = t[0];
    if (Array.isArray(ti)) { tt.prod = t[4]; tt.w = t[4]; }
    var x = s[3](tt, B, nice(dateIso)), k = kindFor(pl, s[2]), look = lookFor(t, ind, si);
    x.slides.forEach(function (sl, i) { if (ind && ind !== "general" && sl.layout === "cta" && /^(Order now|Be next|Find out more|Want one\?|Want the after\?|Join them|Easy|Be this person)$/.test(sl.headline)) sl.headline = I.cta; sl.look = look; if (!sl.emoji && (sl.layout === "cover" || sl.layout === "offer")) sl.emoji = t[2]; });
    return { kind: k, slides: x.slides, caption: cap(pl, x, t, ind), tags: tagsFor(pl, t), title: t[0] + ": " + s[1], channel: pl, look: look };
  };
  TPL.LOOK = LOOK;
  TPL.siOf = function (key) { for (var i = 0; i < ST.length; i++) if (ST[i][0] === key) return i; return -1; };
  var ALT = [["deepavali", "Diwali"], ["diwali", "Diwali"], ["dhanteras", "Dhanteras"], ["holi", "Holi"], ["raksha", "Raksha Bandhan"], ["rakhi", "Raksha Bandhan"], ["eid", "Eid"], ["navratri", "Navratri"], ["navaratri", "Navratri"], ["dussehra", "Dussehra"], ["vijayadashami", "Dussehra"], ["ganesh", "Ganesh Chaturthi"], ["onam", "Onam"], ["pongal", "Pongal"], ["lohri", "Lohri"], ["sankranti", "Makar Sankranti"], ["christmas", "Christmas"], ["new year", "New Year"], ["valentine", "Valentine's Day"], ["republic", "Republic Day"], ["independence", "Independence Day"], ["women", "Women's Day"], ["mother", "Mother's Day"], ["father", "Father's Day"], ["teacher", "Teachers' Day"], ["children", "Children's Day"], ["friendship", "Friendship Day"], ["karwa", "Karwa Chauth"], ["bhai dooj", "Bhai Dooj"], ["durga", "Durga Puja"], ["baisakhi", "Baisakhi"], ["ugadi", "Ugadi"], ["black friday", "Black Friday"], ["sale", "Flash sale"], ["launch", "New launch"], ["giveaway", "Giveaway"]];
  TPL.topicFor = function (name) {
    var n = (name || "").toLowerCase();
    for (var i = 0; i < ALT.length; i++) if (n.indexOf(ALT[i][0]) > -1) for (var j = 0; j < T.length; j++) if (T[j][0] === ALT[i][1]) return j;
    return -1;
  };
  window.TPL = TPL;
})();
