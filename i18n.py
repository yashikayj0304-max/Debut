"""Hindi for the screens people actually live in.

Two decisions worth stating plainly, because they shape everything here:

1. **The English string is the key.** `t("Calendar")` looks up "Calendar" and falls back to "Calendar"
   when there is no translation. Templates stay readable, nothing breaks when a string is missing, and
   a half-finished translation degrades to English rather than to "nav.calendar.title".

2. **This is a real but partial translation.** The navigation, the dashboard, the buttons and the main
   actions are translated - the parts someone touches every day. Deeper screens are still English.
   A machine-translated interface is worse than an English one, so the dictionary below is written by
   hand, in the Hindi that Indian apps and Indian users actually use: Devanagari, with the English
   loanwords people say out loud (पोस्ट, कैलेंडर, रील) rather than textbook Sanskrit equivalents
   nobody uses in a shop.

To add a language: copy the "hi" block, translate the right-hand side, add it to LANGUAGES. Anything
you leave out simply shows in English.
"""

LANGUAGES = [("en", "English"), ("hi", "हिन्दी")]

HI = {
    # --- the sections down the side
    "Content & Calendar": "कंटेंट और कैलेंडर",
    "Tasks & Campaigns": "काम और कैम्पेन",
    "Brand & Ideas": "ब्रांड और आइडिया",
    "Launch playbook": "लॉन्च प्लेबुक",
    "Influencers & PR": "इन्फ़्लुएंसर और पीआर",
    "Leads & Clients": "लीड्स और क्लाइंट",
    "Freelancers & Payments": "फ़्रीलांसर और पेमेंट",
    "Results & Insights": "रिज़ल्ट और इनसाइट",
    "AI & Market News": "एआई और मार्केट न्यूज़",
    "Team": "टीम",
    "More tools": "और टूल्स",
    "Your essentials": "आपकी ज़रूरी चीज़ें",
    "Workspace": "वर्कस्पेस",
    "Recent": "हाल ही में",

    # --- the bar at the bottom of a phone
    "Home": "होम",
    "Plan": "प्लान",
    "Tasks": "काम",
    "Menu": "मेन्यू",
    "More": "और",

    # --- the bar at the top
    "Search": "खोजें",
    "Search…": "खोजें…",
    "Create": "बनाएँ",
    "Notifications": "नोटिफ़िकेशन",
    "Approvals": "अप्रूवल",
    "Chat": "चैट",
    "Help & guides": "मदद और गाइड",
    "Send feedback": "फ़ीडबैक भेजें",
    "Log out": "लॉग आउट",
    "Account": "अकाउंट",
    "Dark / light": "डार्क / लाइट",

    # --- buttons and words that appear on nearly every screen
    "Save": "सेव करें",
    "Save changes": "बदलाव सेव करें",
    "Cancel": "रद्द करें",
    "Delete": "डिलीट करें",
    "Edit": "एडिट करें",
    "New": "नया",
    "+ New": "+ नया",
    "Back": "वापस",
    "Close": "बंद करें",
    "Copy": "कॉपी करें",
    "Done": "हो गया",
    "Open": "खोलें",
    "Share": "शेयर करें",
    "Filter": "फ़िल्टर",
    "Sort": "क्रम",
    "Today": "आज",
    "Yesterday": "कल",
    "Tomorrow": "कल",
    "This week": "इस हफ़्ते",
    "This month": "इस महीने",
    "Overdue": "देर हो चुकी",
    "Upgrade": "अपग्रेड करें",
    "Settings": "सेटिंग",
    "Import / export": "इम्पोर्ट / एक्सपोर्ट",
    "Board view": "बोर्ड व्यू",
    "List": "लिस्ट",
    "Nothing here yet": "अभी यहाँ कुछ नहीं है",

    # --- the words for the things themselves
    "Post": "पोस्ट",
    "Posts": "पोस्ट",
    "Reel / Short": "रील / शॉर्ट",
    "Carousel": "कैरोसेल",
    "Story": "स्टोरी",
    "Campaign": "कैम्पेन",
    "Campaigns": "कैम्पेन",
    "Task": "काम",
    "Lead": "लीड",
    "Leads": "लीड्स",
    "Client": "क्लाइंट",
    "Calendar": "कैलेंडर",
    "Content calendar": "कंटेंट कैलेंडर",
    "Key dates": "ख़ास तारीख़ें",
    "Library": "लाइब्रेरी",
    "Ideas": "आइडिया",
    "Templates": "टेम्पलेट",
    "Mood boards": "मूड बोर्ड",
    "Brand kit": "ब्रांड किट",
    "Numbers": "नंबर",
    "Reviews": "रिव्यू",
    "Publishing": "पब्लिशिंग",
    "Status": "स्टेटस",
    "Planned": "प्लान किया",
    "Published": "पब्लिश हो गया",
    "To do": "करना है",
    "In progress": "चल रहा है",
    "Idea": "आइडिया",

    # --- the dashboard
    "Good morning": "सुप्रभात",
    "Good afternoon": "नमस्कार",
    "Good evening": "शुभ संध्या",
    "What needs you today": "आज आपकी ज़रूरत कहाँ है",
    "Nothing is due today": "आज कुछ बाकी नहीं है",
    "Open tasks": "बचे हुए काम",
    "Awaiting approval": "अप्रूवल बाकी",
    "day streak": "दिन का सिलसिला",

    # --- the things this app does that are worth saying clearly
    "Post to Instagram": "इंस्टाग्राम पर पोस्ट करें",
    "Schedule it": "शेड्यूल करें",
    "Post it now": "अभी पोस्ट करें",
    "Do this again": "इसे दोबारा करें",
    "Next week": "अगले हफ़्ते",
    "Next month": "अगले महीने",
    "Next year": "अगले साल",
    "Fill my calendar": "मेरा कैलेंडर भरें",
    "Use this": "इसे चुनें",
    "Shoot sheet": "शूट शीट",
    "Cover frame": "कवर फ़्रेम",
    "Before you post": "पोस्ट करने से पहले",
    "How did it do?": "यह कैसा चला?",
    "Use this again somewhere else": "इसे कहीं और दोबारा इस्तेमाल करें",
    "Print the month": "महीना प्रिंट करें",
    "Ask for reviews": "रिव्यू माँगें",
    "Ask Deb": "Deb से पूछें",
    "Language": "भाषा",
    "Customise menu": "मेन्यू बदलें",
}

STRINGS = {"hi": HI}


def t(text, lang="en"):
    """Translate one interface string. Unknown strings come back as they are, in English."""
    if not text or lang == "en":
        return text
    return STRINGS.get(lang, {}).get(text, text)


def coverage(lang):
    """How much of the interface this language covers, so the setting can be honest about it."""
    return len(STRINGS.get(lang) or {})
