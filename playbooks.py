"""Campaign templates that actually build something.

The Templates page used to be six cards that linked to the sign-up form and nothing else: it promised
"it opens ready to edit" and then opened nothing. A template here is a real plan - a campaign, a set of
dated posts and the tasks around them - that lands on the calendar in one tap, counted in days from the
date the person picks (Diwali, the sale weekend, launch day).

Each item is (day_offset, kind, title, channel, format). A negative offset is before the big day, 0 is
the day itself, positive is after. Kinds: "post" becomes a content item, "task" becomes a to-do.
"""

PLAYBOOKS = [
    dict(
        key="diwali", icon="🪔", title="Diwali campaign", tag="Festive",
        desc="Three weeks of gifting, offers and a countdown, ending on the day itself.",
        anchor="The date of Diwali",
        items=[
            (-21, "task", "Decide the Diwali offer and the last order date", "", ""),
            (-18, "post", "Diwali is coming: here is what we are making", "Instagram", "Reel / Short"),
            (-14, "post", "The gift box, unwrapped", "Instagram", "Carousel"),
            (-12, "task", "Shoot the gifting photos", "", ""),
            (-10, "post", "Gifting guide: what to pick for whom", "Instagram", "Carousel"),
            (-7, "post", "Early-bird price ends this week", "WhatsApp", "Post"),
            (-5, "post", "Behind the scenes: packing the orders", "Instagram", "Story"),
            (-3, "post", "Last day to order for Diwali delivery", "Instagram", "Post"),
            (-1, "post", "Final reminder: orders close tonight", "WhatsApp", "Post"),
            (0, "post", "Happy Diwali from all of us", "Instagram", "Post"),
            (3, "task", "Count what sold, and what people asked for", "", ""),
        ],
    ),
    dict(
        key="launch", icon="🚀", title="Product launch in 30 days", tag="Launch",
        desc="Teasers, launch day, the follow-up push and an honest results check.",
        anchor="Launch day",
        items=[
            (-30, "task", "Write the one sentence that says what this is", "", ""),
            (-21, "post", "Something is coming: the problem we kept hearing", "Instagram", "Reel / Short"),
            (-14, "post", "A first look, without the full reveal", "Instagram", "Carousel"),
            (-10, "task", "Line up three people to try it early", "", ""),
            (-7, "post", "How we made it, and what we changed twice", "Instagram", "Reel / Short"),
            (-3, "post", "Launching on Friday. Here is what to expect", "Instagram", "Story"),
            (0, "post", "It's live", "Instagram", "Post"),
            (0, "post", "It's live: the longer story", "LinkedIn", "Post"),
            (2, "post", "The first people to try it, in their words", "Instagram", "Carousel"),
            (7, "post", "The three questions everyone asked in week one", "Instagram", "Carousel"),
            (14, "task", "Check the numbers: what worked, what to fix", "", ""),
        ],
    ),
    dict(
        key="sale", icon="🛍️", title="Sale weekend", tag="Sales",
        desc="A short, sharp push: tease, open, remind, last call.",
        anchor="The first day of the sale",
        items=[
            (-10, "task", "Set the discount, the rules and the end time", "", ""),
            (-7, "post", "Save the date: the sale starts Friday", "Instagram", "Story"),
            (-3, "post", "What's going on sale, and what isn't", "Instagram", "Carousel"),
            (-1, "post", "Tomorrow. Set an alarm", "WhatsApp", "Post"),
            (0, "post", "The sale is open", "Instagram", "Post"),
            (1, "post", "What people are picking up most", "Instagram", "Story"),
            (2, "post", "Last few hours", "Instagram", "Reel / Short"),
            (2, "post", "Last call: ends at midnight", "WhatsApp", "Post"),
            (4, "task", "Log the sales numbers and the best seller", "", ""),
        ],
    ),
    dict(
        key="reels", icon="🎬", title="Reels batch week", tag="Content",
        desc="Plan, shoot and schedule ten reels in one go, then post two a week.",
        anchor="The day you shoot",
        items=[
            (-3, "task", "Pick ten hooks and write them on one page", "", ""),
            (-1, "task", "Set up the light and charge everything", "", ""),
            (0, "task", "Shoot all ten in one sitting", "", ""),
            (2, "post", "Reel 1: the mistake everyone makes", "Instagram", "Reel / Short"),
            (5, "post", "Reel 2: how it's actually made", "Instagram", "Reel / Short"),
            (9, "post", "Reel 3: answering your most-asked question", "Instagram", "Reel / Short"),
            (12, "post", "Reel 4: a day here, start to finish", "Instagram", "Reel / Short"),
            (16, "post", "Reel 5: before and after", "Instagram", "Reel / Short"),
            (19, "post", "Reel 6: three things worth knowing", "Instagram", "Reel / Short"),
            (23, "post", "Reel 7: a customer tells it", "Instagram", "Reel / Short"),
            (26, "post", "Reel 8: what we refuse to compromise on", "Instagram", "Reel / Short"),
        ],
    ),
    dict(
        key="collab", icon="🤝", title="Creator collaboration", tag="Creators",
        desc="Brief, agree, post and measure, with the chasing built in.",
        anchor="The day their post goes up",
        items=[
            (-21, "task", "Shortlist five creators and check their real engagement", "", ""),
            (-18, "task", "Send the brief: deliverables, dates, usage rights, fee", "", ""),
            (-12, "task", "Ship the product or book the shoot", "", ""),
            (-7, "task", "Approve their draft", "", ""),
            (-2, "post", "Tease the collab without naming them", "Instagram", "Story"),
            (0, "post", "Our collab with them is live", "Instagram", "Post"),
            (1, "post", "Reshare their reel to our story", "Instagram", "Story"),
            (7, "task", "Pay the invoice", "", ""),
            (10, "task", "Log reach, saves and sales, and decide about next time", "", ""),
        ],
    ),
    dict(
        key="newsletter", icon="📬", title="Newsletter launch", tag="Email",
        desc="Name it, line up the first four issues, and get people to sign up.",
        anchor="The day the first issue goes out",
        items=[
            (-14, "task", "Name it and write what each issue will promise", "", ""),
            (-10, "task", "Put the sign-up form on your link page", "", ""),
            (-7, "post", "Starting a newsletter: here is what will be in it", "Instagram", "Post"),
            (-3, "post", "Last chance to be on the first issue's list", "Instagram", "Story"),
            (0, "post", "Issue 1", "Email", "Newsletter"),
            (7, "post", "Issue 2", "Email", "Newsletter"),
            (14, "post", "Issue 3", "Email", "Newsletter"),
            (21, "post", "Issue 4", "Email", "Newsletter"),
            (24, "task", "Check open rates and cut whatever nobody reads", "", ""),
        ],
    ),
    dict(
        key="openweek", icon="🎉", title="New shop or branch opening", tag="Launch",
        desc="Build the queue before the doors open, then keep them coming back.",
        anchor="Opening day",
        items=[
            (-21, "task", "Confirm the date, the hours and the opening offer", "", ""),
            (-14, "post", "We are opening here. The address and the date", "Instagram", "Post"),
            (-10, "post", "Watch the place come together", "Instagram", "Reel / Short"),
            (-7, "task", "Tell the neighbours and nearby businesses", "", ""),
            (-3, "post", "Opening on Saturday. First fifty get something", "WhatsApp", "Post"),
            (0, "post", "We're open", "Instagram", "Post"),
            (1, "post", "Day one, in pictures", "Instagram", "Carousel"),
            (7, "post", "A reason to come back this week", "WhatsApp", "Post"),
            (10, "task", "Ask the first customers for a review", "", ""),
        ],
    ),
    dict(
        key="winback", icon="💌", title="Win back quiet customers", tag="Sales",
        desc="A short, polite sequence for people who bought once and went quiet.",
        anchor="The day you send the first message",
        items=[
            (-5, "task", "Pull the list: bought once, nothing in 90 days", "", ""),
            (0, "post", "We missed you. Here is what's new since you were last here", "Email", "Newsletter"),
            (0, "task", "Message the top twenty personally, not as a blast", "", ""),
            (5, "post", "A small thank-you, just for you", "WhatsApp", "Post"),
            (12, "post", "Last nudge, then we'll leave you alone", "Email", "Newsletter"),
            (15, "task", "Count who came back, and ask two of them why", "", ""),
        ],
    ),
]

BY_KEY = {p["key"]: p for p in PLAYBOOKS}


def summary(p):
    """How many posts and tasks a template will create, and how long it runs."""
    posts = sum(1 for i in p["items"] if i[1] == "post")
    tasks = sum(1 for i in p["items"] if i[1] == "task")
    span = max(i[0] for i in p["items"]) - min(i[0] for i in p["items"])
    return posts, tasks, span
