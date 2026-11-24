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

    ["coupon", "Coupon", "post", function (t, B, d) { return { slides: [S("coupon", t.off, t.code + "; " + (d ? "Valid till " + d : "Valid this week") + "; On your " + t.n + " order"), S("cta", t.cta, B)], hook: t.e + " 20% off for " + t.n, body: "Use code " + t.code + (d ? " till " + d : " this week") + ". Our " + t.w + " is waiting.", cta: t.cta + " and use the code." }; }],
    ["menu-card", "Price list", "post", function (t, B) { return { slides: [S("menu", t.n + " price list", t.menu), S("cta", t.cta, B)], hook: t.e + " " + t.n + " price list", body: t.menu.split(";").slice(0, 3).join(". ") + ".", cta: t.cta + "." }; }],
    ["event-invite", "Event invite", "post", function (t, B, d) { return { slides: [S("event", "Join us for " + t.n, (d ? d.split(" ").reverse().join(" ") : "Sat 25") + "; 6 PM onwards; Add your venue here"), S("cta", "Save your spot", t.cta)], hook: t.e + " You are invited: " + t.n, body: "Join us" + (d ? " on " + d : "") + ". Add your venue and time in the image.", cta: t.cta + " to save your spot." }; }],
    ["launch-ribbon", "New ribbon", "post", function (t, B) { return { slides: [S("ribbon", t.prod + " is here", "Made for " + t.n + "; NEW"), S("cta", t.cta, B)], hook: t.e + " New: " + t.prod, body: "Meet our " + t.prod.toLowerCase() + " for " + t.n + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["stat-trio", "3 numbers", "post", function (t, B) { return { slides: [S("stat3", "Why " + B, t.nums), S("cta", t.cta, B)], hook: t.e + " " + t.nums.split(";")[0], body: t.nums.replace(/;/g, ". ") + ".", cta: t.cta + "." }; }],
    ["magazine-cover", "Magazine cover", "post", function (t, B) { return { slides: [S("magazine", "The " + t.n + " edit", "Our picks, stories and offers; Issue " + t.n.split(" ")[0]), S("cta", t.cta, B)], hook: t.e + " The " + t.n + " edit", body: "Our picks, our stories and one special offer for " + t.n + ".", cta: t.cta + "." }; }],
    ["picks-collage", "Picks collage", "post", function (t, B) { return { slides: [S("collage", "Our " + t.n + " picks", t.feats + "; " + t.prod), S("cta", t.cta, B)], hook: t.e + " Our " + t.n + " picks", body: t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["this-vs-that", "Versus", "post", function (t, B) { return { slides: [S("versus", "Which one are you?", "Last-minute rush; Planned with " + B), S("cta", "Be option B", t.cta)], hook: t.e + " Which one are you?", body: "Last-minute rush, or planned ahead for " + t.n + "?", cta: "Comment A or B." }; }],
    ["how-it-works", "How it works", "carousel", function (t, B) { return { slides: [S("cover", "How it works", B + " · " + t.n + " " + t.e), S("timeline", "4 easy steps", t.steps), S("cta", t.cta, B)], hook: "How it works " + t.e, body: t.steps.split(";").map(function (x, i) { return (i + 1) + ") " + x; }).join(" "), cta: t.cta + "." }; }],
    ["coupon-story", "Coupon story", "story", function (t, B, d) { return { slides: [S("ribbon", "A gift for " + t.n, "Swipe up for your code; NEW"), S("coupon", t.off, t.code + "; " + (d ? "Valid till " + d : "Valid this week") + "; On your " + t.n + " order"), S("cta", t.cta, B)], hook: t.e + " A gift for " + t.n, body: "Use code " + t.code + ".", cta: t.cta + "." }; }],
    ["event-story", "Event story", "story", function (t, B, d) { return { slides: [S("bold", "You are invited"), S("event", t.n + " at " + B, (d ? d.split(" ").reverse().join(" ") : "Sat 25") + "; 6 PM onwards; Add your venue here"), S("cta", "Save your spot", t.cta)], hook: t.e + " You are invited", body: "Join us for " + t.n + ".", cta: t.cta + "." }; }],
    ["spotlight", "Product spotlight", "post", function (t, B) { return { slides: [S("spotlight", t.prod + " for " + t.n, t.feats, { emoji: t.e }), S("cta", t.cta, B)], hook: t.e + " " + t.prod + " for " + t.n, body: "Meet our " + t.prod.toLowerCase() + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + ". Link in bio." }; }],
    ["stop-scroll", "Stop scrolling reel", "reel", function (t, B) { return { slides: [S("bold", "Stop scrolling", t.n + " " + t.e), S("bold", t.prod && t.prod.charAt(0) !== "[" ? t.prod + " is here" : "It is here"), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: "Stop scrolling " + t.e, body: t.n + " is here." + (t.price[2] ? " " + t.price[2] + "." : ""), cta: t.cta + "." }; }],
    ["three-reasons", "3 reasons", "carousel", function (t, B) { return { slides: [S("cover", "3 reasons to choose " + B, t.n + " " + t.e), S("split", t.tips[0], "Why it matters for " + t.n + ".", { emoji: "1️⃣" }), S("split", t.tips[1], "Small things, big difference.", { emoji: "2️⃣" }), S("split", t.tips[2], "Ask us and we will help.", { emoji: "3️⃣" }), S("cta", t.cta, B)], hook: "3 reasons " + t.e, body: t.tips.join(". ") + ".", cta: t.cta + "." }; }],
    ["offer-ends", "Offer ends soon", "story", function (t, B, d) { return { slides: [S("countdown", "3", "days left for " + t.n), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: "Offer ends soon " + t.e, body: t.prod + " at " + t.price[0] + " for " + t.n + ".", cta: t.cta + "." }; }],
    ["price-drop", "Price tag", "post", function (t, B, d) { return { slides: [S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2], { emoji: t.e }), S("cta", t.cta, d ? "Offer till " + d : "Limited time only")], hook: t.e + " " + t.prod + " now " + t.price[0], body: "Was " + t.price[1] + ", now " + t.price[0] + ". " + t.price[2] + ".", cta: t.cta + " before " + (d || "it ends") + "." }; }],
    ["new-arrival", "New arrival reel", "reel", function (t, B) { return { slides: [S("bold", "New in", B), S("spotlight", t.prod, t.feats, { emoji: t.e }), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, "Link in bio")], hook: "New in " + t.e, body: "Say hello to our " + t.prod.toLowerCase() + ". " + t.feats.replace(/;/g, ", ") + ".", cta: t.cta + "." }; }],
    ["review-card", "Review card", "post", function (t, B) { return { slides: [S("review", t.rev, t.revwho || "[who said it]"), S("cta", "Join " + t.proof, t.cta)], hook: "★★★★★ " + t.e + " What our customers say", body: "“" + t.rev + "”", cta: t.cta + "." }; }],
    ["vote-story", "Vote story", "story", function (t, B) { return { slides: [S("poll", "Which one for " + t.n + "?", t.prod + "; Something new"), S("cta", "Thanks for voting", "Follow " + B)], hook: "You decide " + t.e, body: "Vote in the poll sticker.", cta: "We will share the winner." }; }],
    ["photo-story", "Photo story", "story", function (t, B) { return { slides: [S("photo", t.n + " at " + B, "Add your photo here", { emoji: t.e }), S("photo", t.prod, "Swap in a close-up of the " + t.prod.toLowerCase(), { emoji: "✨" }), S("cta", t.cta, B)], hook: t.e + " " + t.n + " at " + B, body: "A little peek for you.", cta: t.cta + "." }; }],
    ["pro-tips", "3 pro tips", "carousel", function (t, B) { return { slides: [S("cover", "3 tips before " + t.n, "From people who do this every day"), S("tip", t.tips[0], "", { num: 1 }), S("tip", t.tips[1], "", { num: 2 }), S("tip", t.tips[2], "", { num: 3 }), S("cta", t.cta, B)], hook: "3 tips before " + t.n + " " + t.e, body: t.tips.join(". ") + ".", cta: t.cta + "." }; }],
    ["proof-reel", "Proof reel", "reel", function (t, B) { return { slides: [S("bold", "Why people trust us"), S("stat", t.proof, ""), S("review", t.rev, t.revwho), S("cta", t.cta, B)], hook: t.proof + " " + t.e, body: "“" + t.rev + "”", cta: t.cta + "." }; }],
    ["countdown-reel", "Countdown reel", "reel", function (t, B) { return { slides: [S("countdown", "3", "days to " + t.n), S("countdown", "2", "days to " + t.n), S("countdown", "1", "day to " + t.n), S("price", t.price[0], t.prod + "; " + t.price[1] + "; " + t.price[2]), S("cta", t.cta, B)], hook: t.e + " " + t.n + " is almost here", body: t.prod + " at " + t.price[0] + ". " + t.price[2] + ".", cta: t.cta + "." }; }],
    ["hook-tips", "3 tips", "carousel", function (t, B) { return { slides: [S("cover", t.n + "? Read this first.", "3 quick things before you buy"), S("tip", "Start early", "The best " + t.w + " goes first.", { num: 1 }), S("tip", "Know what you want", "Pick one thing you will really use.", { num: 2 }), S("tip", "Ask us", "Message " + B + " and we will help you pick.", { num: 3 }), S("cta", "Need help choosing?", "Message " + B)], hook: t.n + "? Read this first.", body: "Three quick things before you buy your " + t.w + ".", cta: "Save this and send it to someone who needs it." }; }],
    ["problem-proof", "Problem, 3 points, proof", "carousel", function (t, B) { return { slides: [S("cover", "Struggling with " + t.n + " shopping?", "Here is the easy way"), S("step", "Skip the rush", "Order your " + t.w + " ahead.", { num: 1 }), S("step", "Keep it simple", "One choice, no stress.", { num: 2 }), S("step", "We handle the rest", "Packed and sent with care.", { num: 3 }), S("quote", "Exactly what I needed.", "A happy customer"), S("cta", "Your turn", "Message " + B + " to order")], hook: "Struggling with " + t.n + " shopping?", body: "Three ways " + B + " makes it easy, plus what a customer said.", cta: "Message us to order." }; }],
    ["offer", "Offer", "post", function (t, B, d) { return { slides: [S("offer", t.w.charAt(0).toUpperCase() + t.w.slice(1), "Now at " + B + (d ? " · till " + d : "")), S("cta", "Order now", "Message " + B + " to claim it")], hook: t.e + " " + t.n + ": " + t.w, body: "Our " + t.w + " is here. Limited stock, so grab yours early.", cta: "Message us to order." }; }],
    ["countdown", "Countdown", "story", function (t, B) { return { slides: [S("cover", "3 days to " + t.n, "Get ready " + t.e), S("cover", "2 days to " + t.n, "Your " + t.w + " is waiting"), S("cover", "Tomorrow!", t.n + " is almost here"), S("offer", "It's here", t.w + " is live now")], hook: "Counting down to " + t.n + " " + t.e, body: "Turn on notifications so you do not miss our " + t.w + ".", cta: "Tap the link in bio." }; }],
    ["before-after", "Before and after", "reel", function (t, B) { return { slides: [S("cover", "Before vs after " + t.n, "Which one are you?"), S("compare", "Before vs after", "Last-minute panic; A calm " + t.n + " with " + B), S("cta", "Want the after?", "Message " + B)], hook: "Before vs after " + t.n, body: "From last-minute panic to a calm " + t.n + ".", cta: "Which one are you? Tell us below." }; }],
    ["pov", "POV", "reel", function (t, B) { return { slides: [S("cover", "POV: it's " + t.n + " and you planned ahead", t.e), S("quote", "I found the perfect " + t.w + " in two minutes.", "You, with " + B), S("cta", "Be this person", "Follow " + B)], hook: "POV: it's " + t.n + " and you planned ahead " + t.e, body: "Be the person who sorted it early.", cta: "Follow us for more." }; }],
    ["big-number", "Big number", "post", function (t, B) { return { slides: [S("stat", t.proof, t.n), S("cta", "Be next", "Message " + B)], hook: t.proof + " this " + t.n, body: "Thank you for trusting " + B + " with your " + t.w + ".", cta: "Be our next happy customer." }; }],
    ["testimonial", "Testimonial", "post", function (t, B) { return { slides: [S("quote", t.rev, t.revwho), S("cta", "Join them", "Message " + B)], hook: "What our customers say " + t.e, body: "In their own words - paste only reviews you really received.", cta: "Want the same? Message us." }; }],
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
  // What is true of an INDUSTRY: the kind of offer it runs, the looks that suit it, what its
  // call to action says. Nothing here is a claim about a particular business. Prices, sales
  // figures, reviews and discount codes used to live here too, as plausible-looking samples,
  // and they went out on real posts as though they were real. They are gone; see FACTS below.
  var IND = {
    general:     { w: "special offer", looks: ["launch", "celebrate", "people"], cta: "Message us", tags: "#smallbusiness #shoplocal" },
    d2c:         { w: "bestseller bundle", looks: ["bundle", "flash", "celebrate"], cta: "Shop now", tags: "#d2cindia #shoponline #madeinindia" },
    hospitality: { w: "festive menu and stays", looks: ["summer", "wedding", "diwali"], cta: "Book a table", tags: "#foodiesofindia #staycation #restaurantindia" },
    fmcg:        { w: "festive family pack", looks: ["flash", "harvest", "bundle"], cta: "Find it near you", tags: "#fmcg #madeinindia #familypack" },
    saas:        { w: "free trial", looks: ["launch", "trust", "learn"], cta: "Start free trial", tags: "#saas #startupindia #productivity" },
    realestate:  { w: "site visit slot", looks: ["trust", "winterfest", "wedding"], cta: "Book a site visit", tags: "#realestateindia #dreamhome #propertyinvestment" },
    education:   { w: "admissions window", looks: ["school", "exam", "learn"], cta: "Enrol now", tags: "#education #admissionsopen #learnwithus" },
    healthcare:  { w: "health check-up", looks: ["trust", "monsoon", "learn"], cta: "Book an appointment", tags: "#healthcare #wellness #stayhealthy" },
    fashion:     { w: "new collection", looks: ["wedding", "love", "celebrate"], cta: "Shop the look", tags: "#ootd #fashionindia #styleinspo" },
    fintech:     { w: "zero-fee plan", looks: ["trust", "launch", "learn"], cta: "Get started", tags: "#fintech #moneymatters #investsmart" },
    agency:      { w: "free marketing audit", looks: ["launch", "trust", "people"], cta: "Book a free audit", tags: "#digitalmarketing #marketingagency #growthmarketing" },
    personal_brand: { w: "free 1:1 session", looks: ["people", "celebrate", "learn"], cta: "Book a free call", tags: "#personalbrand #creatoreconomy #contentcreator" },
    b2b:         { w: "free consultation", looks: ["trust", "learn", "launch"], cta: "Request a quote", tags: "#b2b #manufacturingindia #businessgrowth" },
    retail:      { w: "in-store offer", looks: ["sale", "flash", "bundle"], cta: "Visit the store", tags: "#retail #shoplocal #storeoffer" },
    startup:     { w: "early access", looks: ["launch", "flash", "celebrate"], cta: "Join the waitlist", tags: "#startupindia #buildinpublic #founderlife" }
  };

  // Facts belong to the BUSINESS, and Debut only knows the ones it has been told. Anything
  // missing comes back as an obvious placeholder in square brackets, never as a plausible
  // sample: a price, a sales figure, a review or a discount code that was invented would go out
  // on a real post as though it were real, and in India that is an advertising and consumer-
  // protection problem as well as a trust one.
  var ASK = {
    price:  ["[your price]", "[was ₹…, if there is an old price]", "[what is included]"],
    prod:   "[what you are selling]",
    proof:  "[your real number] customers",
    nums:   "[a real number];[a real rating];[a real promise]",
    rev:    "[paste a real review from a real customer]",
    feats:  "[something true about it];[another true thing];[a third]",
    menu:   "[item] – [price];[item] – [price];[item] – [price]",
    steps:  "[what happens first];[then this];[then this];[and finally]",
    tips:   "[a tip you would actually give];[another one];[a third]",
    code:   "[YOURCODE]",
    off:    "[your offer]"
  };
  // Is this piece still carrying something Debut made up for the person to replace?
  TPLNEEDS = /\[[^\]]+\]/;
  function factsOf(f) {
    f = f || {};
    function pick(k, d) { var v = (f[k] || "").toString().trim(); return v ? v : d; }
    var price = pick("price", "");
    return {
      prod:  pick("prod", ASK.prod),
      price: (function () { var a = price ? price.split(";") : ASK.price.slice();
                            while (a.length < 3) a.push(""); return a; })(),
      proof: pick("proof", ASK.proof),
      nums:  pick("nums", ASK.nums),
      rev:   pick("rev", ASK.rev),
      feats: pick("feats", ASK.feats),
      menu:  pick("menu", ASK.menu),
      steps: pick("steps", ASK.steps),
      tips:  pick("tips", ASK.tips).split(";"),
      code:  pick("code", ASK.code),
      revwho: pick("revwho", "[who said it]"),
      off:   pick("off", ASK.off)
    };
  }

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
  // Fifteen captions with one skeleton read as a bot, which is what they were: hook, three
  // ticked bullets, the same closing couplet, every single time. These are five different
  // shapes, picked by the piece's own index so a run of them varies, and the closing line is
  // only added where it earns its place rather than on all of them.
  var CLOSERS = ["", "", "💾 Save this one for later.", "📤 Send this to whoever is planning.", ""];
  function shape(n, hook, lines, cta, closer) {
    var b = lines.map(function (l, i) { return BUL[i % 3] + " " + l; }).join("\n");
    var tail = (closer ? "\n" + closer : "");
    switch (n % 5) {
      case 0: return hook + "\n\n" + b + "\n\n👉 " + cta + tail;
      case 1: return hook + "\n\n" + lines.join("\n\n") + "\n\n" + cta + tail;
      case 2: return lines[0] + "\n\n" + hook + "\n\n" + lines.slice(1).map(function (l) { return "— " + l; }).join("\n") + "\n\n" + cta + tail;
      case 3: return hook + "\n" + lines[0] + "\n\n" + cta + tail;
      default: return hook + "\n\n" + lines.join(" ") + "\n\n👉 " + cta + tail;
    }
  }
  function cap(pl, x, t, ind, vi) {
    vi = vi || 0;
    var I = IND[ind] || IND.general, tags = tagsFor(pl, t), extra = PL[pl].tags ? (I.tags || "").split(/\s+/).filter(Boolean).slice(0, 2) : [], all = tags.concat(extra).join(" ");
    var lines = String(x.body || "").split(/(?<=[.!?])\s+/)
      .map(function (l) { return l.trim(); })
      .filter(function (l) { return l && l !== "." && /[\p{L}\p{N}]/u.test(l); })   // a blank entry in a list left "— ."
      .slice(0, 3), cat = t[1];
    // The filler used to be one fixed sentence per category, so it repeated down the whole deck.
    var FILL_BRAND = ["Made slowly, and honestly.", "Small batch, made to last.", "The details are the point.",
                      "Made by people, not a machine.", "Nothing in it we would not use ourselves."];
    var FILL_END = ["Tell us what you would love to see next.", "Ask us anything in the comments.",
                    "Tell us who you are buying for.", "Questions? We answer every message.",
                    "What would you want us to make next?"];
    if (lines.length < 2) lines.push(cat === "Brand" ? FILL_BRAND[vi % FILL_BRAND.length] : "Made for " + t[5] + ", so every detail counts.");
    if (lines.length < 3) lines.push(cat === "Sale" || cat === "Promo" ? "Limited time, so do not leave it to the last minute."
      : cat === "Festival" ? "Order early so it reaches you in time." : FILL_END[vi % FILL_END.length]);
    var bullets = lines.map(function (l, i) { return BUL[i % 3] + " " + l; }).join("\n");
    if (pl === "LinkedIn") return x.hook + "\n\n" + lines.join("\n\n") + "\n\nWhat has your experience been? I would love to hear it in the comments.\n\n" + x.cta + (all ? "\n\n" + all : "");
    if (pl === "X / Twitter") { var s = x.hook + " " + x.body + " " + x.cta; return s.length > 240 ? s.slice(0, 237) + "..." : s; }
    if (pl === "YouTube") return x.hook + "\n\n" + x.body + "\n\n⏱️ In this video: the quick version.\n👍 Like, 💬 comment and 🔔 subscribe for more.\n\n" + x.cta + (all ? "\n\n" + all : "");
    if (pl === "WhatsApp") return "Hi! 👋\n\n" + x.hook + "\n\n" + bullets + "\n\nReply *YES* and we will share the details. 🙌";
    if (pl === "Email") return "Subject: " + x.hook + "\n\nHi there,\n\n" + x.body + "\n\n" + x.cta + "\n\nWarmly,\nThe team";
    if (pl === "Facebook") return x.hook + "\n\n" + bullets + "\n\n👉 " + x.cta + (all ? "\n\n" + all : "");
    return shape(vi, x.hook, lines, x.cta, CLOSERS[vi % CLOSERS.length]) + (all ? "\n\n" + all : "");
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
  TPL.build = function (pl, ti, si, B, dateIso, ind, facts) {
    var t = Array.isArray(ti) ? ti : T[ti], s = ST[si], I = IND[ind] || IND.general, w = (t[1] === "Brand") ? t[4] : (ind && ind !== "general" ? I.w : t[4]);
    var F = factsOf(facts);
    var tt = { n: t[0], c: t[1], e: t[2], t: t[3], w: w, g: t[5], I: I, cta: I.cta, prod: F.prod, proof: F.proof, tips: F.tips, price: F.price, rev: F.rev, revwho: F.revwho, feats: F.feats, menu: F.menu, steps: F.steps, nums: F.nums, code: F.code, off: F.off }; tt[3] = t[3]; tt[0] = t[0];
    if (Array.isArray(ti)) { tt.prod = t[4]; tt.w = t[4]; }
    var x = s[3](tt, B, nice(dateIso)), k = kindFor(pl, s[2]), look = lookFor(t, ind, si);
    x.slides.forEach(function (sl, i) { if (ind && ind !== "general" && sl.layout === "cta" && /^(Order now|Be next|Find out more|Want one\?|Want the after\?|Join them|Easy|Be this person)$/.test(sl.headline)) sl.headline = I.cta; sl.look = look; if (!sl.emoji && (sl.layout === "cover" || sl.layout === "offer")) sl.emoji = t[2]; });
    return { kind: k, slides: x.slides, caption: cap(pl, x, t, ind, si), tags: tagsFor(pl, t), title: t[0] + ": " + s[1], channel: pl, look: look };
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
