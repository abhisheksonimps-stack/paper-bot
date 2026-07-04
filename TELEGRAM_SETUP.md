# Adding Telegram notifications

You'll get a push message on your phone whenever a new signal fires (not every
idle hour — only when something happens). Setup is ~5 minutes.

────────────────────────────────────────────────────────────────────────────
STEP 1 — Create your Telegram bot (get the TOKEN)
────────────────────────────────────────────────────────────────────────────
1. In Telegram, search for  @BotFather  (the official one, blue tick).
2. Send:  /newbot
3. Give it a name (anything, e.g. "my paper bot") and a username ending in
   "bot" (e.g. "abhishek_paper_bot").
4. BotFather replies with a line like:
       Use this token to access the HTTP API:
       8123456789:AAExampleTokenStringHere....
   Copy that whole token. That is your TELEGRAM_TOKEN.

────────────────────────────────────────────────────────────────────────────
STEP 2 — Get your chat ID (TELEGRAM_CHAT)
────────────────────────────────────────────────────────────────────────────
1. In Telegram, search for the bot you just made and press START (send it any
   message, e.g. "hi"). This is required — bots can't message you first.
2. Search for  @userinfobot  and send it  /start  — it replies with your
   numeric "Id" (e.g. 512345678). That number is your TELEGRAM_CHAT.
   (Alternative: open this URL in a browser, replacing <TOKEN>:
    https://api.telegram.org/bot<TOKEN>/getUpdates
    and look for  "chat":{"id":  512345678  ... )

────────────────────────────────────────────────────────────────────────────
STEP 3 — Put them in GitHub Secrets (safe, never shown in code)
────────────────────────────────────────────────────────────────────────────
In your repo:
1. Settings → Secrets and variables → Actions → "New repository secret"
2. Add two secrets (names must match EXACTLY):
      Name: TELEGRAM_TOKEN   Value: (the token from BotFather)
      Name: TELEGRAM_CHAT    Value: (your numeric id)
3. Save each.

────────────────────────────────────────────────────────────────────────────
STEP 4 — Update the two files in your repo
────────────────────────────────────────────────────────────────────────────
Replace these with the new versions (Edit → paste → commit):
   - paper_dual.py                  (now has Telegram sending built in)
   - .github/workflows/paper.yml    (now passes the secrets to the script)

Then go to Actions → paper-trade-bot → "Run workflow" to test.
If a signal fires, you'll get a Telegram message. If not, no message (normal).

To force a test message regardless of signals, you can temporarily send yourself
one by opening this URL in a browser (replace both placeholders):
   https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHATID>&text=hello
If "hello" arrives in Telegram, your token + chat id are correct.

────────────────────────────────────────────────────────────────────────────
NOTES
────────────────────────────────────────────────────────────────────────────
- You'll only be pinged when a NEW signal is logged, with the entry/target/stop
  and the current scoreboard. Idle hours stay silent.
- If you never set the secrets, the bot still runs fine — it just won't send.
- Keep your TOKEN private. Anyone with it can control your bot (though it can
  only message people who started it). If it leaks, /revoke in BotFather.
