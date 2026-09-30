# Put Debut online for free and test it from any browser

This gets you a real `https://something.onrender.com` link — no local install, no command line, no credit card. Two accounts, both free: **GitHub** (to hold the code) and **Render** (to run it).

I found and fixed two real bugs in the app while preparing this — see the note at the bottom. This zip already has both fixes.

---

## What "free" actually means here (read this first)

Render's free plan (checked today, no card required) gives you:
- A free web service — but it **falls asleep after 15 minutes** with no visitors, and takes 30–60 seconds to wake up on the next click. That first slow load after a break is normal, not broken.
- A free database — but it **expires 30 days after you create it**. Fine for testing; don't treat it as permanent storage.
- Anything uploaded (like a mood board image) lives only as long as the app hasn't restarted — it's fine for a click-through test, just don't rely on it surviving long-term.

None of this costs anything or asks for a card. It's just not meant for a real, permanent business — which is exactly right for testing.

---

## Step 1: Get the code onto GitHub (no command line)

1. Go to [github.com](https://github.com) and sign up free, if you don't have an account.
2. Click the **+** in the top right → **New repository**. Name it `debut` (private or public, either works). Don't tick any of the "initialize with README" boxes. Click **Create repository**.
3. Unzip `Debut-App.zip` on your computer — you'll get a folder called `debut` full of files.
4. On the new empty repository's page, click **"uploading an existing file"** (a link right there on the page).
5. Drag the **contents** of the unzipped `debut` folder into the upload box — all the files and subfolders at once, not the outer `debut` folder itself. This can take a minute for ~100 files.
6. Scroll down, click **Commit changes**.

You now have the code on GitHub with no Git commands typed.

---

## Step 2: Deploy it on Render

1. Go to [render.com](https://render.com) and sign up free (you can use your GitHub account to sign in — no card asked).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account if prompted, then select the `debut` repository you just created.
4. Render reads the `render.yaml` file already in the code and shows you two services it's about to create: a **web service** and a **database**. **Confirm both say "Free" as the plan** — that file is already set to free, but double-check before clicking apply, since plans can be changed in the Render UI.
5. Click **Apply** / **Create**. Render will build and deploy — this takes a few minutes the first time. You'll see build logs scrolling; that's normal.
6. Once it says "Live", Render shows you a URL like `https://debut-xxxx.onrender.com`. Click it.

## Step 3: Two settings to fill in after first deploy

Go to the web service in Render → **Environment** tab, and fill in:

| Variable | What to put |
|---|---|
| `APP_URL` | The exact `https://debut-xxxx.onrender.com` URL Render just gave you |
| `ADMIN_EMAILS` | Your own email address, so you get the admin dashboard at `/admin` |

Leave everything else blank for now (AI Studio, live email, and real payments all need their own API keys — the app is specifically built to work fine without them, showing a clear message instead of breaking). Click **Save Changes** — Render redeploys automatically, takes about a minute.

---

## Step 4: Use it

Open your URL. Sign up like a real user would, pick an industry, and go through the [bug-testing tour I gave you earlier](Debut-How-To-Test-It-Yourself.md) — all of it applies here too, it's the same app. Since there's no real email sending configured, verification and invite links show up as a purple "DEV" banner on screen instead of arriving by email — click those to continue.

**Anyone you send the link to can test it too**, from their own phone or computer, with no setup on their end. That's the actual point of putting it online.

---

## Two bugs I found and fixed while setting this up

I didn't just hand you a config file — I actually ran the app the way Render would run it before giving this to you, and found two real problems:

1. **The subscription/billing page would have been broken.** Render requires the app to run in "production" mode for technical reasons (correct HTTPS detection behind Render's proxy). The app's billing code had an unrelated rule that turned off its safe "demo billing" mode whenever production mode was on — meaning clicking any paid plan on your free test deployment would have tried to contact a real payment provider with no keys configured, and failed. Demo billing and production mode are now correctly independent, and I verified subscribing to a plan actually works under the exact conditions Render uses.
2. **The included `render.yaml` was set to paid plans by default** (a $7/month web service and a paid database) — the opposite of what "free" means. It's now set to Render's actual free plans, with a note about the 15-minute sleep and 30-day database expiry so neither surprises you.

Both are re-tested: 70 automated tests passing, plus a direct simulation of Render's exact environment (production mode, no payment keys) confirming sign-up and subscribing both work end to end.
