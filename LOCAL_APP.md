# Morning Stock Picks on your own computer

This app runs on your laptop and emails you every weekday morning. One email covers:
- **today's picks**, each with a Buy, Hold or Sell call, its odds and source links;
- **every stock it is tracking**: the price since the pick, news, and changes to the call;
- **a calendar** of upcoming events.

## How it works

Each weekday at the time you choose (6:30 a.m. by default), your computer's scheduler starts `scripts/morning_app.py run`. It then:

1. **Skips the day** if both the US and Canadian markets are closed (weekends and shared holidays).
2. **Updates the tracker:** prices, returns, and new news and SEC filings for every tracked stock.
3. **Starts Claude Code** on your machine, using your Claude plan, for the research. It reads the news, checks filings, re-rates stocks, looks for new short-term ideas, and writes the report and the top of the email. It is locked down:
   - it can run only the project's research tool and web search;
   - it can edit only the `reports/` folder;
   - it cannot read your settings folder, run other commands, send email or use git.
4. **Builds and sends the email** through your Gmail. If the research step failed, the email still arrives with tracking and the calendar, plus a note about what went wrong.
5. **Saves everything to git:** it commits locally, and pushes to GitHub if you turned that on.

Your Gmail app password is stored only in `~/.precatalyst/config.json`, which only you can read. It never goes into the repository.

## Setup (about 15 minutes, once)

1. **Python 3.11 or newer.** Run `python3 --version` (on Windows, `python --version`). If it prints a version older than 3.11, or nothing, install Python from <https://www.python.org/downloads/>.
2. **Git.**
   - Mac: run `xcode-select --install`.
   - Windows: install [Git for Windows](https://git-scm.com/downloads/win). Claude Code also uses it.
3. **Claude Code**, which needs a Pro or Max plan.
   - Mac: `curl -fsSL https://claude.ai/install.sh | bash`
   - Windows (PowerShell): `irm https://claude.ai/install.ps1 | iex`

   Open a new terminal, run `claude`, log in in the browser, then type `/exit`.
4. **Get the app.**
   - On a Mac, put it in your home folder, not Documents or Desktop: macOS blocks background jobs from those two.

   ```bash
   git clone -b claude/serene-meitner-u5aw38 https://github.com/noahp179/financial-reports.git ~/precatalyst
   cd ~/precatalyst
   ```

   If GitHub asks you to sign in, the easiest route is to install the GitHub CLI, run `gh auth login`, then clone again.
5. **Create a Gmail app password.** Go to <https://myaccount.google.com/apppasswords>; it needs 2-Step Verification turned on. Name it "Morning Stock Picks" and copy the 16 letters.
6. **Run setup.**

   ```bash
   python3 scripts/morning_app.py setup
   ```

   It asks for your Gmail address, the app password and the run time. It then sends a test email and turns on the weekday schedule.
7. **Optional: run a full morning right now** to see the whole thing work. This takes 15–40 minutes.

   ```bash
   python3 scripts/morning_app.py run --force
   ```

## Day to day

| Command | What it does |
|---|---|
| `python3 scripts/morning_app.py status` | Settings, last email sent, where the logs are |
| `python3 scripts/morning_app.py run --force` | Run a morning now |
| `python3 scripts/morning_app.py run --skip-research --force` | Tracking and calendar email only (quick) |
| `python3 scripts/morning_app.py run --dry-run` | Build the email without sending it; a preview is saved in `~/.precatalyst/` |
| `python3 scripts/morning_app.py unschedule` | Stop the weekday runs |
| `git pull` | Get improvements to the app |

Logs are in `~/.precatalyst/logs/`.

## What "for life" needs

- **The laptop must be on.**
  - Mac: if it was asleep at run time, the job runs when it wakes. To have it wake up by itself, keep it plugged in and run `sudo pmset repeat wake MTWRF 06:25:00`.
  - Windows: the task wakes the PC if it can, and otherwise runs as soon as the PC is on.
  - A laptop that is fully shut down won't run it; the email arrives later that day when you open it.
- **Your Claude plan stays active.** Each morning is a real research session that uses your plan's usage. Max gives more headroom than Pro.
- **The Gmail app password stays valid.** If you change your Google password, Google revokes app passwords: create a new one and run `setup` again.
- **The free data sources keep working.** These are SEC EDGAR and Yahoo Finance's public endpoints. If one changes, the morning email says the step failed rather than guessing, and the code can be updated.

## Not investment advice

Calls are research estimates with stated odds and they are tracked over time. Risky events, such as FDA decisions, can lose a large part of the money put in. The app never places trades.
