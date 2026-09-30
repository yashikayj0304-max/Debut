# Run Debut on your own computer and test it

This is the shortest path to actually clicking through the real app yourself. It runs entirely on your own machine — nothing to deploy, nothing to pay for, no accounts needed except the ones you choose to test.

---

## 1. Get it running (5 minutes)

### Windows
1. Unzip `Debut-App.zip`.
2. Double-click **`Launch Debut.bat`** inside the `debut` folder.
   - First run: it installs everything automatically (needs Python 3.10+ — if you don't have it, install it from python.org first and tick "Add to PATH" during setup, then run the .bat again).
   - It opens your browser to `http://127.0.0.1:8001` automatically.
3. Leave the black command window open while you test — closing it stops the app.

### Mac / Linux
```bash
unzip Debut-App.zip && cd debut
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:8001` in your browser.

**That's it.** No database to install — it creates a local file (`gtm.db`) automatically. No payment setup, no email server — both run in a safe "demo" mode so you can test everything without any real accounts.

---

## 2. What "demo mode" means while you're testing

- **Billing:** clicking a paid plan switches it instantly with no real payment. This lets you test what Team or Agency plan features look like without a Razorpay account.
- **Email:** since no real mail server is connected, verification links, password resets, and team invites are **printed directly on the screen** as a purple "DEV" banner instead of being emailed. Click that link to continue the flow.
- **AI Studio and Market Pulse (live news):** these need real API keys (Anthropic, optionally a news/YouTube key) to actually generate text or fetch live headlines. Without them, you'll see a clear "not configured" message instead of a crash — that's expected, not a bug. If you want to test these for real, add your own key to a `.env` file (copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY=...`).

---

## 3. If it didn't work the first time

I found and fixed one real bug that likely explains this: the setup was trying to install a database driver (`psycopg2-binary`) that isn't actually needed for local testing and can fail to install on some Windows/Python combinations without extra developer tools — silently breaking the whole setup. It's fixed in this zip; **please re-download and try again from a fresh unzip** before anything below.

If it still doesn't work:

| What you saw | Likely cause / fix |
|---|---|
| Double-clicking the .bat does nothing, or a window flashes and disappears | Right-click the file → "Run as administrator", or open a Command Prompt, `cd` into the `debut` folder, and type `"Launch Debut.bat"` so you can read the error instead of it closing instantly. |
| "Python was not found" | Install Python from [python.org/downloads](https://python.org/downloads) — on the **very first screen** of the installer, tick **"Add python.exe to PATH"** before clicking Install. This is the single most common miss. Restart the .bat afterwards. |
| Typing `python` opens the Microsoft Store instead of running anything | This means Windows has a stub alias instead of a real Python install. Install Python properly from python.org (not the Store), ticking "Add to PATH", then try again. |
| An error mentioning "Microsoft Visual C++" or "Build Tools" during install | A package needed compiling and couldn't. Try again — this update should have removed the one package that caused this. If you still see it, tell me the exact package name in the error. |
| The browser opens but shows "This site can't be reached" | The app is still starting — wait 5 seconds and refresh. If it still fails, check the black window for a red error message. |
| Everything installs, but the app window closes immediately when it tries to start | There's a real error printed just before it closes — scroll up in that window (or reopen via Command Prompt as above so it doesn't auto-close) and copy the error text back to me. |

**The fastest way to get this fixed:** open a Command Prompt, `cd` to the unzipped `debut` folder, and run:
```
"Launch Debut.bat"
```
Running it this way (instead of double-clicking) means the window won't vanish if something fails — copy whatever text appears and send it to me. That's the single most useful thing you can give me to fix this quickly.

---

## 4. A 20-minute tour to bug-test against

Work through this as one person first, then repeat parts of it as a second signup to check the roles properly.

1. **Sign up.** Pick an industry (try "Hospitality" or "Personal brand"). Notice the checklist, key dates, and Idea Bank content are already tailored to it.
2. **Verify your email** using the DEV link shown on screen.
3. **Add a few real things:** a GTM plan, a content item scheduled for a date this week, a mood board with a note and an image, a task assigned to your own name.
4. **Drag things around:** move the content item to a different day on the Calendar. Open the mood board and drag a card, resize it by its corner, then reload the page — did it stay where you put it?
5. **Invite a second person.** Use a second real email address (or a "+" alias like `you+test@gmail.com` if your provider supports it) and invite them as "Lead". Accept the invite in an incognito window using the DEV link. Confirm they land in the same workspace with a different menu than you see.
6. **Try a locked feature.** On the Free plan, try opening something like Influencers or the Client Portal — you should see a clear upgrade message, not a broken page. Then switch to the Team plan (demo mode, instant) and confirm it unlocks.
7. **Try the AI Studio and Market Pulse pages** even without a key configured — confirm you get a friendly message, not an error page.
8. **Try to break things on purpose** — this is the most useful thing you can do:
   - Log out, then try to open a page directly by typing its URL — you should be sent to login, not shown data.
   - As the second person (Lead role), try to reach the Billing page — it should be blocked.
   - Leave required fields empty on a form and submit — check the error message makes sense.
   - Upload a non-image file where an image is expected on a mood board.
   - Try the same email twice on signup.

---

## 5. How to tell me what you found

For anything that looks wrong, tell me:
- What page you were on and what you clicked.
- What you expected to happen.
- What actually happened (a screenshot helps a lot if you can share one).

I'll fix it directly in the app and give you an updated zip — I can't watch you test in real time, so this is the fastest way for me to reproduce and fix whatever you find.

---

## 6. If you want to go further

- **`DEVELOPER_GUIDE.md`** (in the same zip) covers everything needed to put this on a real domain for other people to use — that's a separate, bigger step for later, not needed just to test it yourself.
- The `docs/` folder has PDF guides for personal-brand users and for agencies/teams, plus a visual tour of every screen if you'd rather look before you click.
