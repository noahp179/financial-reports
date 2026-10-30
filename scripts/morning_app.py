"""Run the Morning Stock Picks scanner on your own computer (stdlib only, Python 3.11+).

Commands:
  setup        one-time: Gmail settings, Claude Code check, weekday schedule, test email
  run          the morning job the schedule calls: tracking, research with Claude Code, email
  test-email   send today's tracked stocks and calendar as a test
  status       show settings, schedule and the last run
  unschedule   remove the weekday schedule

Settings live in ~/.precatalyst/config.json (readable only by you). The Gmail app password
never goes into the repository, and the research step cannot read that folder.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import platform
import plistlib
import re
import shutil
import smtplib
import subprocess
import sys
import time
from email.message import EmailMessage
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACK_DIR = REPO / "reports/pre-catalyst"
EMAIL_DIR = TRACK_DIR / "email"
PROMPT_FILE = TRACK_DIR / "daily_prompt.md"
TOOL = REPO / "scripts/precatalyst.py"
APP_DIR = Path.home() / ".precatalyst"
CONFIG_FILE = APP_DIR / "config.json"
STATE_FILE = APP_DIR / "state.json"
LOCK_FILE = APP_DIR / "run.lock"
LOG_DIR = APP_DIR / "logs"
LABEL = "com.precatalyst.morning"
WINDOWS_TASK = "PreCatalystMorning"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465
RESEARCH_TIMEOUT_MINUTES = 75


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line, flush=True)
    with (LOG_DIR / f"{dt.date.today():%Y-%m}.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_json(path: Path, data: dict, private: bool = False) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if private and os.name == "posix":
        path.chmod(0o600)


# ---------------------------------------------------------------- market holidays


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> dt.date:
    last = dt.date(year + month // 12, month % 12 + 1, 1) - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def easter(year: int) -> dt.date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return dt.date(year, month, day + 1)


def us_observed(day: dt.date) -> dt.date:
    shift = {5: -1, 6: 1}.get(day.weekday(), 0)
    return day + dt.timedelta(days=shift)


def ca_observed(day: dt.date) -> dt.date:
    shift = {5: 2, 6: 1}.get(day.weekday(), 0)
    return day + dt.timedelta(days=shift)


def nyse_holidays(year: int) -> set[dt.date]:
    good_friday = easter(year) - dt.timedelta(days=2)
    days = {
        nth_weekday(year, 1, 0, 3),
        nth_weekday(year, 2, 0, 3),
        good_friday,
        last_weekday(year, 5, 0),
        us_observed(dt.date(year, 6, 19)),
        us_observed(dt.date(year, 7, 4)),
        nth_weekday(year, 9, 0, 1),
        nth_weekday(year, 11, 3, 4),
        us_observed(dt.date(year, 12, 25)),
    }
    new_year = dt.date(year, 1, 1)
    if new_year.weekday() != 5:  # NYSE does not close for a Saturday New Year's Day
        days.add(us_observed(new_year))
    return days


def tsx_holidays(year: int) -> set[dt.date]:
    christmas = ca_observed(dt.date(year, 12, 25))
    boxing = ca_observed(dt.date(year, 12, 26))
    if boxing <= christmas:
        boxing = christmas + dt.timedelta(days=1)
    may24 = dt.date(year, 5, 24)
    return {
        ca_observed(dt.date(year, 1, 1)),
        nth_weekday(year, 2, 0, 3),
        easter(year) - dt.timedelta(days=2),
        may24 - dt.timedelta(days=may24.weekday()),
        ca_observed(dt.date(year, 7, 1)),
        nth_weekday(year, 8, 0, 1),
        nth_weekday(year, 9, 0, 1),
        nth_weekday(year, 10, 0, 2),
        christmas,
        boxing,
    }


def market_status(day: dt.date) -> str:
    """'open', 'us-closed', 'ca-closed' or 'both-closed' (weekends count as both closed)."""
    if day.weekday() >= 5:
        return "both-closed"
    us = day in nyse_holidays(day.year)
    ca = day in tsx_holidays(day.year)
    return {
        (True, True): "both-closed",
        (True, False): "us-closed",
        (False, True): "ca-closed",
    }.get((us, ca), "open")


# ---------------------------------------------------------------- helpers


def python_cmd() -> str:
    return "python" if os.name == "nt" else "python3"


def find_claude() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local/bin/claude",
        Path.home() / ".local/bin/claude.exe",
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def sync_from_github(stage: str) -> bool:
    """Rebase local commits onto GitHub so this copy never gets stuck behind it."""
    pulled = git("pull", "--rebase", "--autostash")
    if pulled.returncode != 0:
        git("rebase", "--abort")
        log(f"git pull ({stage}) failed; keeping the local copy: {pulled.stderr.strip()[:300]}")
        return False
    log(f"git pull ({stage}): {(pulled.stdout or pulled.stderr).strip()[:200]}")
    return True


def run_tool(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=300)


def report_link(day: str) -> str:
    remote = git("remote", "get-url", "origin").stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    path = f"reports/pre-catalyst/{day}.md"
    if "github.com" in remote:
        slug = remote.split("github.com")[-1].lstrip(":/").removesuffix(".git")
        return f"https://github.com/{slug}/blob/{branch}/{path}"
    return (REPO / path).as_uri()


def previous_email_date(state: dict, today: dt.date) -> str:
    last = state.get("last_sent")
    if last and last < today.isoformat():
        return last
    return (today - dt.timedelta(days=3 if today.weekday() == 0 else 1)).isoformat()


# ---------------------------------------------------------------- research step


def research(cfg: dict, today: dt.date, since: str) -> tuple[bool, str]:
    claude = cfg.get("claude_path") or find_claude()
    if not claude:
        return False, "Claude Code is not installed on this computer"
    py = python_cmd()
    prompt = PROMPT_FILE.read_text(encoding="utf-8").format(
        date=today.isoformat(),
        weekday=f"{today:%A}",
        short_date=f"{today:%a %b} {today.day}",
        since=since,
        py=py,
    )
    allowed = ["WebSearch", "WebFetch", "Edit(./reports/**)"] + [
        f"Bash({cmd} scripts/precatalyst.py *)" for cmd in ("python3", "python", "py")
    ]
    command = [
        claude,
        "-p",
        prompt,
        "--allowedTools",
        ",".join(allowed),
        "--disallowedTools",
        "Read(~/.precatalyst/**),Edit(~/.precatalyst/**)",
        "--permission-prompts",
        "none",
        "--max-turns",
        str(cfg.get("max_turns", 200)),
        "--output-format",
        "json",
    ]
    if cfg.get("model"):
        command += ["--model", cfg["model"]]
    log("research: starting Claude Code")
    try:
        done = subprocess.run(
            command,
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=RESEARCH_TIMEOUT_MINUTES * 60,
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            f"the research step ran past {RESEARCH_TIMEOUT_MINUTES} minutes and was stopped",
        )
    try:
        result = json.loads(done.stdout)
    except json.JSONDecodeError:
        result = {"result": (done.stdout or done.stderr)[-800:]}
    summary = str(result.get("result", "")).strip()
    log(f"research: exit {done.returncode}; {summary[:600]}")
    if done.returncode != 0 or result.get("is_error"):
        return False, f"the research step failed ({summary[:300] or done.stderr[-300:]})"
    return True, summary


# ---------------------------------------------------------------- email


def wrap_html(parts: list[str]) -> str:
    body = "".join(parts)
    return (
        "<html><body style='font-family:-apple-system,Segoe UI,Arial,sans-serif;font-size:14px;"
        f"line-height:1.45;color:#1a1a1a;max-width:900px'>{body}</body></html>"
    )


def build_email(today: dt.date, since: str, note: str | None) -> tuple[str, str, str]:
    day = today.isoformat()
    picks_file = EMAIL_DIR / f"{day}.html"
    subject_file = EMAIL_DIR / f"{day}.subject.txt"
    parts: list[str] = []
    if note:
        parts.append(
            "<p style='background:#fff4e5;padding:8px;border-left:3px solid #f0a020'>"
            f"<b>Heads-up:</b> {note}. Tracked stocks and the calendar below are still current.</p>"
        )
    if picks_file.exists():
        parts.append(picks_file.read_text(encoding="utf-8"))
    sections = APP_DIR / "sections.html"
    made = run_tool("email-sections", "--since", since, "--out", str(sections))
    if made.returncode == 0 and sections.exists():
        parts.append(sections.read_text(encoding="utf-8"))
    else:
        parts.append(f"<p>Tracked-stock table unavailable: {made.stderr[-300:]}</p>")
    link = report_link(day) if picks_file.exists() else None
    footer = "Not investment advice. Risky events can lose a large part of the money put in."
    if link:
        footer = f"<a href='{link}'>Full report with all sources</a> · " + footer
    parts.append(f"<p style='font-size:12px;color:#555'>{footer}</p>")
    if subject_file.exists():
        subject = subject_file.read_text(encoding="utf-8").strip()
    else:
        subject = f"Morning Stock Picks — {today:%a %b} {today.day} — tracking update"
    text = (
        f"{subject}\n\n"
        + (f"Heads-up: {note}.\n\n" if note else "")
        + made.stdout
        + (f"\nFull report: {link}\n" if link else "")
        + "\nNot investment advice."
    )
    return subject, wrap_html(parts), text


def send_email(cfg: dict, subject: str, html_body: str, text_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["gmail_user"]
    msg["To"] = cfg.get("email_to") or cfg["gmail_user"]
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.login(cfg["gmail_user"], cfg["app_password"])
        smtp.send_message(msg)


# ---------------------------------------------------------------- the morning run


def cmd_run(args: argparse.Namespace) -> None:
    cfg = load_json(CONFIG_FILE)
    if not cfg.get("gmail_user"):
        sys.exit("Not set up yet. Run: python3 scripts/morning_app.py setup")
    today = dt.date.today()
    state = load_json(STATE_FILE)
    status = market_status(today)
    # The owner buys only in Canadian dollars, so a day the TSX is closed has nothing to act on.
    if status in ("both-closed", "ca-closed") and not args.force:
        log(f"run: {today} is a weekend or a Canadian market holiday; nothing sent")
        return
    if state.get("last_sent") == today.isoformat() and not (args.force or args.dry_run):
        log("run: today's email was already sent")
        return
    if LOCK_FILE.exists() and time.time() - LOCK_FILE.stat().st_mtime < 3 * 3600:
        log("run: another run is in progress")
        return
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(str(os.getpid()))
    try:
        since = previous_email_date(state, today)
        log(f"run: starting for {today} (news since {since}, markets: {status})")
        if cfg.get("git_sync"):
            sync_from_github("start")
            delivered = git("log", "-1", "--format=%h %s", f"--grep=^Morning run {today}")
            if delivered.stdout.strip() and not (args.force or args.dry_run):
                found = delivered.stdout.strip()
                log(f"run: today's email already went out from another copy ({found})")
                state.update({"last_sent": today.isoformat(), "last_subject": "sent elsewhere"})
                save_json(STATE_FILE, state)
                return
        for step in (("check-logs",), ("update-log",), ("track-news", "--since", since)):
            done = run_tool(*step)
            log(f"{step[0]}: exit {done.returncode}; {done.stdout.strip().splitlines()[-1:]}")
        notes = []
        if status == "us-closed":
            notes.append("US markets are closed today, so US-linked CDR prices may not move")
        ok, summary = (False, "research skipped (--skip-research)")
        if not args.skip_research:
            ok, summary = research(cfg, today, since)
        if not ok:
            notes.append(f"today's research step didn't complete: {summary}")
        checked = run_tool("check-logs")
        log(f"check-logs: {' | '.join(checked.stdout.strip().splitlines())}")
        subject, html_body, text_body = build_email(today, since, "; ".join(notes) or None)
        if args.dry_run:
            preview = APP_DIR / "last_email_preview.html"
            preview.write_text(html_body, encoding="utf-8")
            log(f"dry run: email not sent; preview saved to {preview} (subject: {subject})")
            return
        send_email(cfg, subject, html_body, text_body)
        log(f"email sent: {subject}")
        state.update({"last_sent": today.isoformat(), "last_subject": subject, "research_ok": ok})
        save_json(STATE_FILE, state)
        git("add", "reports")
        committed = git("commit", "-m", f"Morning run {today}")
        log(f"git commit: {(committed.stdout or committed.stderr).strip()[:120]}")
        if cfg.get("git_sync") and sync_from_github("before push"):
            pushed = git("push")
            log(f"git push: exit {pushed.returncode} {pushed.stderr.strip()[:200]}")
    except Exception as exc:  # noqa: BLE001 - always try to tell the owner something failed
        log(f"run: FAILED {exc!r}")
        try:
            send_email(
                cfg,
                f"Morning Stock Picks — {today:%a %b} {today.day} — run failed",
                wrap_html([f"<p>This morning's run failed: {exc!r}. See {LOG_DIR}.</p>"]),
                f"This morning's run failed: {exc!r}. See {LOG_DIR}.",
            )
        except Exception as mail_exc:  # noqa: BLE001
            log(f"run: could not send the failure email either: {mail_exc!r}")
        raise
    finally:
        LOCK_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------- scheduling


def schedule_path_env() -> str:
    dirs = [str(Path(sys.executable).parent)]
    claude = find_claude()
    if claude:
        dirs.append(str(Path(claude).parent))
    git_path = shutil.which("git")
    if git_path:
        dirs.append(str(Path(git_path).parent))
    dirs += [
        str(Path.home() / ".local/bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    return os.pathsep.join(dict.fromkeys(dirs))


def install_schedule(hour: int, minute: int) -> str:
    system = platform.system()
    script = str(Path(__file__).resolve())
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if system == "Darwin":
        plist = Path.home() / f"Library/LaunchAgents/{LABEL}.plist"
        plist.parent.mkdir(parents=True, exist_ok=True)
        with plist.open("wb") as fh:
            plistlib.dump(
                {
                    "Label": LABEL,
                    "ProgramArguments": [sys.executable, script, "run"],
                    "WorkingDirectory": str(REPO),
                    "StartCalendarInterval": [
                        {"Weekday": d, "Hour": hour, "Minute": minute} for d in range(1, 6)
                    ],
                    "EnvironmentVariables": {"PATH": schedule_path_env()},
                    "StandardOutPath": str(LOG_DIR / "launchd.log"),
                    "StandardErrorPath": str(LOG_DIR / "launchd.log"),
                },
                fh,
            )
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
        loaded = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist)], capture_output=True, text=True
        )
        if loaded.returncode != 0:
            subprocess.run(["launchctl", "load", "-w", str(plist)], check=True)
        return f"macOS launchd job {LABEL} (runs on wake if the Mac was asleep)"
    if system == "Windows":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pythonw if pythonw.exists() else Path(sys.executable))
        ps = (
            f"$a = New-ScheduledTaskAction -Execute '{exe}' -Argument '\"{script}\" run' "
            f"-WorkingDirectory '{REPO}'; "
            "$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,"
            f"Thursday,Friday -At {hour:02d}:{minute:02d}; "
            "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun "
            "-ExecutionTimeLimit (New-TimeSpan -Hours 2); "
            f"Register-ScheduledTask -TaskName '{WINDOWS_TASK}' -Action $a -Trigger $t "
            "-Settings $s -Force | Out-Null"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
        return f"Windows Task Scheduler task {WINDOWS_TASK} (runs when the PC is next on)"
    line = (
        f"{minute} {hour} * * 1-5 PATH={schedule_path_env()} {sys.executable} {script} run "
        f">> {LOG_DIR / 'cron.log'} 2>&1 # {LABEL}"
    )
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    lines = [ln for ln in current.splitlines() if LABEL not in ln] + [line]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
    return "cron job (weekdays; a missed run is not caught up)"


def cmd_unschedule(_: argparse.Namespace) -> None:
    system = platform.system()
    if system == "Darwin":
        plist = Path.home() / f"Library/LaunchAgents/{LABEL}.plist"
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
        plist.unlink(missing_ok=True)
    elif system == "Windows":
        subprocess.run(
            ["schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"], capture_output=True, text=True
        )
    else:
        current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        lines = [ln for ln in current.splitlines() if LABEL not in ln]
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    print("Schedule removed.")


# ---------------------------------------------------------------- setup and status


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
YES, NO = {"y", "yes"}, {"n", "no"}
PROTECTED_MAC_FOLDERS = ("Desktop", "Documents", "Downloads", "Library/Mobile Documents")


def ask(question: str, default: str = "") -> str:
    shown = f" (press Enter for {default})" if default else ""
    return input(f"{question}{shown}: ").strip() or default


def ask_email(question: str, default: str = "") -> str:
    default = default if EMAIL_PATTERN.match(default or "") else ""
    while True:
        answer = ask(question, default)
        if answer.lower() in YES and default:
            return default
        if EMAIL_PATTERN.match(answer):
            return answer
        print(f"  '{answer}' isn't an email address. Type one like name@gmail.com.")


def ask_yes_no(question: str, default: bool) -> bool:
    while True:
        answer = ask(f"{question} (yes/no)", "yes" if default else "no").lower()
        if answer in YES | NO:
            return answer in YES
        print("  Please answer yes or no.")


def ask_time(question: str, default: str) -> tuple[int, int]:
    while True:
        answer = ask(question, default)
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", answer)
        if match and int(match[1]) < 24 and int(match[2]) < 60:
            return int(match[1]), int(match[2])
        print("  Use 24-hour HH:MM, for example 06:30.")


def protected_mac_folder() -> str | None:
    """macOS blocks scheduled background jobs from Desktop, Documents, Downloads and iCloud."""
    if platform.system() != "Darwin":
        return None
    for folder in PROTECTED_MAC_FOLDERS:
        if REPO.is_relative_to(Path.home() / folder):
            return folder
    return None


def cmd_test_email(_: argparse.Namespace) -> None:
    cfg = load_json(CONFIG_FILE)
    today = dt.date.today()
    since = (today - dt.timedelta(days=3)).isoformat()
    subject, html_body, text_body = build_email(today, since, "this is a test email from setup")
    send_email(cfg, f"[Test] {subject}", html_body, text_body)
    print(f"Test email sent to {cfg.get('email_to') or cfg['gmail_user']}.")


def cmd_setup(args: argparse.Namespace) -> None:
    if sys.version_info < (3, 11):  # noqa: UP036 - users may run an older system Python
        sys.exit(
            "Python 3.11 or newer is needed. Install it from https://www.python.org/downloads/"
        )
    cfg = load_json(CONFIG_FILE)
    print("Morning Stock Picks: local setup\n")
    blocked = protected_mac_folder()
    if blocked and not args.no_schedule:
        sys.exit(
            f"This folder is inside your {blocked} folder, and macOS stops scheduled background "
            "jobs from reading it, so the morning run would fail.\nMove it to your home folder, "
            "then run setup again:\n\n"
            f'  mv "{REPO}" ~/precatalyst\n  cd ~/precatalyst\n'
            "  python3 scripts/morning_app.py setup\n"
        )
    claude = find_claude()
    if claude:
        version = subprocess.run([claude, "--version"], capture_output=True, text=True)
        print(f"Claude Code found: {version.stdout.strip()} ({claude})")
        cfg["claude_path"] = claude
    else:
        install = (
            "irm https://claude.ai/install.ps1 | iex   (in PowerShell)"
            if os.name == "nt"
            else "curl -fsSL https://claude.ai/install.sh | bash"
        )
        print(
            "Claude Code is not installed yet, so emails will only carry tracking until it is.\n"
            f"  Install: {install}\n  Then run `claude` once to log in, and re-run this setup.\n"
        )
    cfg["gmail_user"] = args.gmail or ask_email(
        "Your Gmail address (the email is sent from it)", cfg.get("gmail_user", "")
    )
    cfg["email_to"] = args.to or ask_email(
        "Email address that should receive the morning email",
        cfg.get("email_to") if EMAIL_PATTERN.match(cfg.get("email_to", "")) else cfg["gmail_user"],
    )
    password = os.environ.get("PRECATALYST_APP_PASSWORD") or getpass.getpass(
        "Gmail app password (16 letters from https://myaccount.google.com/apppasswords; "
        "typing is hidden, press Enter to keep the saved one): "
    )
    cfg["app_password"] = password.replace(" ", "") or cfg.get("app_password", "")
    if not cfg["app_password"]:
        sys.exit("A Gmail app password is needed. Create one, then run setup again.")
    if args.time:
        hour, minute = (int(x) for x in args.time.split(":"))
    else:
        hour, minute = ask_time("Weekday run time, 24-hour", cfg.get("run_time", "06:30"))
    cfg["run_time"] = f"{hour:02d}:{minute:02d}"
    has_remote = git("remote").stdout.strip() != ""
    if args.git_sync:
        cfg["git_sync"] = args.git_sync == "y"
    else:
        cfg["git_sync"] = ask_yes_no(
            "Also save reports to GitHub each morning", cfg.get("git_sync", has_remote)
        )
    save_json(CONFIG_FILE, cfg, private=True)
    print(f"Settings saved to {CONFIG_FILE}")
    try:
        cmd_test_email(args)
    except smtplib.SMTPAuthenticationError:
        sys.exit(
            "Gmail rejected the login. Check the address and app password (2-Step Verification "
            "must be on for app passwords), then run setup again."
        )
    except smtplib.SMTPException as exc:
        sys.exit(f"Gmail refused the test email ({exc}). Run setup again and check the addresses.")
    if not args.no_schedule:
        print(f"Scheduled: {install_schedule(hour, minute)} at {cfg['run_time']}, Mon–Fri.")
    print(
        "\nDone. Each weekday morning this computer researches, updates the tracker and emails "
        "you.\nRun a full morning now with:  python3 scripts/morning_app.py run --force"
    )


def cmd_status(_: argparse.Namespace) -> None:
    cfg = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE)
    print(f"Repo:        {REPO}")
    print(f"Email to:    {cfg.get('email_to') or cfg.get('gmail_user') or 'not set up'}")
    print(f"Run time:    {cfg.get('run_time', 'not set')} Mon–Fri ({platform.system()})")
    print(f"Claude Code: {find_claude() or 'not installed'}")
    print(f"Git sync:    {cfg.get('git_sync')}")
    print(f"Last sent:   {state.get('last_sent', 'never')}  {state.get('last_subject', '')}")
    print(f"Logs:        {LOG_DIR}")
    print(f"Today:       markets {market_status(dt.date.today())}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup")
    setup.add_argument("--gmail")
    setup.add_argument("--to")
    setup.add_argument("--time", help="HH:MM, 24-hour local time (default 06:30)")
    setup.add_argument("--git-sync", choices=("y", "n"))
    setup.add_argument("--no-schedule", action="store_true")
    setup.set_defaults(func=cmd_setup)
    run = sub.add_parser("run")
    run.add_argument("--force", action="store_true", help="run even if already sent or closed")
    run.add_argument("--skip-research", action="store_true", help="tracking and email only")
    run.add_argument("--dry-run", action="store_true", help="build the email but don't send it")
    run.set_defaults(func=cmd_run)
    sub.add_parser("test-email").set_defaults(func=cmd_test_email)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("unschedule").set_defaults(func=cmd_unschedule)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
