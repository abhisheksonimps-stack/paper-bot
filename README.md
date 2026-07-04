# Dual Paper-Trading Bot — runs itself in the cloud, forever

This runs both strategies (ORIGINAL = the YouTuber's method, MODIFIED = the
trending-COC version) automatically every hour on GitHub's free servers.
Your PC/phone can be off — it doesn't matter. You just open a web page to
check results whenever you like.

It **backfills**: even if a scheduled run is skipped or delayed, the next run
catches every signal it missed. So gaps (PC off, GitHub delays) don't lose data.

────────────────────────────────────────────────────────────────────────────
ONE-TIME SETUP (~15 min, can be done from phone or PC)
────────────────────────────────────────────────────────────────────────────

1. Make a free GitHub account at github.com (skip if you have one).

2. Create a new repository:
   - Click the "+" (top right) → "New repository"
   - Name it e.g. "paper-bot"
   - Set it to **Private** (your ledgers stay yours)
   - Tick "Add a README file"
   - Click "Create repository"

3. Upload these files into the repo:
   - Click "Add file" → "Upload files"
   - Drag in:  paper_dual.py   and   requirements.txt
   - For the workflow file, it must sit in a folder. Easiest way:
     Click "Add file" → "Create new file", and in the filename box type exactly:
         .github/workflows/paper.yml
     (typing the slashes creates the folders automatically)
     Then paste the contents of paper.yml into the editor.
   - Commit / "Save" each.

4. Turn write-permission on for the bot (so it can save ledgers):
   - Repo → "Settings" → "Actions" → "General"
   - Scroll to "Workflow permissions"
   - Select "Read and write permissions" → Save

5. Enable and run it:
   - Go to the "Actions" tab
   - If prompted, click the green button to enable workflows
   - Click "paper-trade-bot" on the left → "Run workflow" → "Run workflow"
   - Wait ~1 min, refresh. A green tick = it ran.

Done. It now runs automatically every hour, forever.

────────────────────────────────────────────────────────────────────────────
HOW TO CHECK RESULTS (from anywhere, phone or PC)
────────────────────────────────────────────────────────────────────────────

Open your repo in a browser and click on **STATUS.txt**. It shows the latest
scoreboard, e.g.:

    === DUAL PAPER BOT — 2026-07-05 14:05 UTC ===
    ORIGINAL: 23 closed | win 43% | PF 1.19 | exp +0.31% | 4 open | equity $10,180 (+1.8%)
    MODIFIED: 6 closed  | win 50% | PF 1.92 | exp +1.80% | 2 open | equity $10,410 (+4.1%)

- ledger_original.json / ledger_modified.json hold every trade in full detail.
- STATUS.txt is the quick human-readable summary.

Bookmark the STATUS.txt page on your phone. That's your dashboard.

────────────────────────────────────────────────────────────────────────────
RULES (the whole point of a forward test)
────────────────────────────────────────────────────────────────────────────

1. DO NOT change any settings while it runs. No tweaking symbols, filters, or
   R:R. The value is that it's untouched, out-of-sample data.
2. Judge nothing until each strategy has ~30+ CLOSED trades (roughly 2-3 months).
3. Then compare against the backtest benchmark:
      MODIFIED should show PF ~1.3-2.3 and positive expectancy.
      If live matches backtest → the edge is real.
      If it degrades → the backtest was optimistic; you risked nothing learning that.
4. Both start at a paper $10,000, so the equity lines are directly comparable.

No real money is involved anywhere in this. It's a scoreboard.

────────────────────────────────────────────────────────────────────────────
NOTES
────────────────────────────────────────────────────────────────────────────
- GitHub's free scheduled runs can be delayed 5-30 min or occasionally skipped
  under heavy load. The backfill handles this — nothing is lost.
- If the repo goes 60 days with zero commits, GitHub pauses schedules. Since the
  bot commits every hour, that won't happen while it's active.
- Binance's public API needs no key and works fine from GitHub's servers.
