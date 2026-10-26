"""Helpers for the daily pre-catalyst scanner (stdlib only).

Commands:
  snapshot TICKER...           price, volume, relative volume, realized vol and a 3-month 80% range
  rate --price P --scenario "label:prob:target" ... [--ticker T --note TEXT]
                               probability-weighted expected return and the rule-based rating;
                               with --ticker the estimate is appended to estimates_log.csv
  update-log [--log PATH]      fill 1/5/20/60 trading-day returns (absolute and vs benchmark)
  track-news [--since DATE]    append new news and SEC filings for active names to news_log.csv
  email-sections [--since DATE] [--weeks N] [--out PATH]
                               HTML for the morning email: tracked-stock updates and a calendar

Market data comes from the public Yahoo Finance chart endpoint. Prices may be delayed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range={r}"
NEWS_URL = "https://query1.finance.yahoo.com/v1/finance/search?q={q}&newsCount=10&quotesCount=0"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_HEADERS = {"User-Agent": "PreCatalystResearch nepollack@gmail.com"}
TRACK_DIR = Path(__file__).resolve().parent.parent / "reports/pre-catalyst"
DEFAULT_LOG = TRACK_DIR / "candidate_log.csv"
NEWS_LOG = TRACK_DIR / "news_log.csv"
ESTIMATES_LOG = TRACK_DIR / "estimates_log.csv"
CALENDAR = TRACK_DIR / "calendar.csv"
NEWS_FIELDS = ["seen_date", "published", "ticker", "kind", "title", "url"]
ESTIMATE_FIELDS = [
    "date",
    "ticker",
    "price",
    "rating",
    "expected_return",
    "upside",
    "p_upside",
    "downside",
    "p_downside",
    "note",
]
# Routine filings that rarely move a catalyst thesis; insider trades are reviewed separately.
SKIP_FORMS = {"3", "4", "5", "3/A", "4/A", "144", "S-8", "FWP", "SC 13G", "SC 13G/A"}
SKIP_FORM_PREFIXES = ("424B", "SCHEDULE 13G")
RETURN_DAYS = (1, 5, 20, 60)
Z80 = 1.2816  # two-sided 80% interval under a lognormal approximation

RATING_BANDS = (
    ("Strong Buy", 0.20),
    ("Buy", 0.08),
    ("Hold", -0.05),
    ("Sell", -0.15),
)
CONFIDENCE_LEVELS = ("low", "medium", "medium-high", "high")


def fetch_daily(ticker: str, rng: str = "1y") -> tuple[dict, list[tuple[dt.date, float, int]]]:
    req = urllib.request.Request(
        CHART_URL.format(t=ticker, r=rng), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read())["chart"]["result"][0]
    quote = res["indicators"]["quote"][0]
    rows = [
        (dt.date.fromtimestamp(ts), close, vol or 0)
        for ts, close, vol in zip(res["timestamp"], quote["close"], quote["volume"], strict=False)
        if close is not None
    ]
    return res["meta"], rows


def realized_vol(closes: list[float], window: int) -> float:
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))][-window:]
    if len(rets) < 2:
        return float("nan")
    mean = sum(rets) / len(rets)
    return math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) * 252)


def price_range(price: float, annual_vol: float, trading_days: int) -> tuple[float, float]:
    sigma = annual_vol * math.sqrt(trading_days / 252)
    return price * math.exp(-Z80 * sigma), price * math.exp(Z80 * sigma)


def cmd_snapshot(args: argparse.Namespace) -> None:
    for ticker in args.tickers:
        try:
            meta, rows = fetch_daily(ticker)
        except Exception as exc:  # noqa: BLE001 - report and continue with the next ticker
            print(f"{ticker}: ERROR {exc}")
            continue
        closes = [r[1] for r in rows]
        vols = [r[2] for r in rows]
        price = meta["regularMarketPrice"]
        stamp = dt.datetime.fromtimestamp(meta["regularMarketTime"], dt.UTC).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        avg20 = sum(vols[-21:-1]) / 20 if len(vols) > 21 else float("nan")
        rv250 = realized_vol(closes, 250)
        lo, hi = price_range(price, rv250, 63)
        prev = closes[-2] if len(closes) > 1 else float("nan")
        ret_1m = (closes[-1] / closes[-22] - 1) * 100 if len(closes) > 22 else float("nan")
        parts = [
            f"{ticker} {meta.get('fullExchangeName', '?')} {meta.get('currency', '?')}",
            f"price={price:.3f} @ {stamp}",
            f"prev_close={prev:.3f} chg={(price / prev - 1) * 100:+.1f}%",
            f"vol={vols[-1]:,} avg20={avg20:,.0f} rvol={vols[-1] / avg20:.2f}",
            "(rvol is partial-day if intraday)",
            f"1m={ret_1m:+.1f}%",
            f"RV20={realized_vol(closes, 20):.0%} RV60={realized_vol(closes, 60):.0%}",
            f"RV250={rv250:.0%}",
            f"52w={meta.get('fiftyTwoWeekLow')}-{meta.get('fiftyTwoWeekHigh')}",
            f"3m80%range={lo:.2f}-{hi:.2f}",
        ]
        print(" ".join(parts))


def rate(
    expected_return: float,
    worst_material_return: float,
    confidence: str,
    capped: bool,
) -> str:
    """Map an expected return to a rating, applying the confidence and liquidity guards."""
    rating = "Strong Sell"
    for name, floor in RATING_BANDS:
        if expected_return >= floor:
            rating = name
            break
    level = CONFIDENCE_LEVELS.index(confidence)
    if rating == "Strong Buy" and (worst_material_return < -0.15 or level < 2):
        rating = "Buy"
    if rating == "Strong Sell" and level < 1:
        rating = "Sell"
    if capped:
        rating = {"Strong Buy": "Buy", "Strong Sell": "Sell"}.get(rating, rating)
    return rating


def cmd_rate(args: argparse.Namespace) -> None:
    scenarios = []
    for spec in args.scenario:
        label, prob, target = spec.rsplit(":", 2)
        scenarios.append((label, float(prob), float(target)))
    total = sum(p for _, p, _ in scenarios)
    if abs(total - 1) > 1e-6:
        sys.exit(f"scenario probabilities sum to {total:.3f}, expected 1.0")
    expected_price = sum(p * t for _, p, t in scenarios)
    expected_return = expected_price / args.price - 1
    material = [t / args.price - 1 for _, p, t in scenarios if p >= 0.15]
    worst = min(material) if material else min(t / args.price - 1 for _, _, t in scenarios)
    for label, p, t in scenarios:
        print(f"  {label:40s} p={p:5.0%} target={t:9.2f} return={t / args.price - 1:+7.1%}")
    rating = rate(expected_return, worst, args.confidence, args.capped)
    returns = [(p, t / args.price - 1) for _, p, t in scenarios]
    best = max(r for _, r in returns)
    p_big_gain = sum(p for p, r in returns if r >= 0.25)
    p_big_loss = sum(p for p, r in returns if r <= -0.25)
    print(
        f"expected price={expected_price:.2f} expected return={expected_return:+.1%} "
        f"worst material (p>=15%) return={worst:+.1%} -> {rating}"
    )
    print(
        f"  upside potential={best:+.0%}  P(gain>=25%)={p_big_gain:.0%}  "
        f"P(loss>=25%)={p_big_loss:.0%}"
    )
    for name, floor in RATING_BANDS[:2]:
        print(
            f"  price at which expected return reaches {name} ({floor:+.0%}): "
            f"{expected_price / (1 + floor):.2f} (scenario targets held fixed)"
        )
    if args.ticker:
        p_up, up = max(returns, key=lambda pr: pr[1])
        p_down, down = min(returns, key=lambda pr: pr[1])
        append_csv(
            ESTIMATES_LOG,
            ESTIMATE_FIELDS,
            [
                {
                    "date": dt.date.today().isoformat(),
                    "ticker": args.ticker,
                    "price": f"{args.price:g}",
                    "rating": rating,
                    "expected_return": f"{expected_return:.4f}",
                    "upside": f"{up:.4f}",
                    "p_upside": f"{p_up:.2f}",
                    "downside": f"{down:.4f}",
                    "p_downside": f"{p_down:.2f}",
                    "note": args.note,
                }
            ],
        )
        print(f"  logged estimate for {args.ticker} to {ESTIMATES_LOG.name}")


def benchmark_for(exchange: str) -> str:
    return "XIU.TO" if exchange.upper().startswith("TSX") else "SPY"


def trading_day_return(
    rows: list[tuple[dt.date, float, int]], start: dt.date, days: int
) -> float | None:
    """Close-to-close return from the first close on/after `start` to `days` sessions later."""
    idx = next((i for i, r in enumerate(rows) if r[0] >= start), None)
    if idx is None or idx + days >= len(rows):
        return None
    return rows[idx + days][1] / rows[idx][1] - 1


def cmd_update_log(args: argparse.Namespace) -> None:
    path = Path(args.log)
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        records = list(reader)
    for col in [f"excess_{n}d" for n in RETURN_DAYS]:
        if col not in fields:
            fields.append(col)
    cache: dict[str, list[tuple[dt.date, float, int]]] = {}
    for rec in records:
        start = dt.date.fromisoformat(rec["first_seen_date"])
        ticker = rec.get("yahoo_symbol") or rec["ticker"]
        bench = benchmark_for(rec["exchange"])
        for sym in (ticker, bench):
            if sym not in cache:
                cache[sym] = fetch_daily(sym, "2y")[1]
        for n in RETURN_DAYS:
            ret = trading_day_return(cache[ticker], start, n)
            bret = trading_day_return(cache[bench], start, n)
            if ret is not None:
                rec[f"ret_{n}d"] = f"{ret:.4f}"
                if bret is not None:
                    rec[f"excess_{n}d"] = f"{ret - bret:.4f}"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(f"updated {len(records)} rows in {path}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def append_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    new_file = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def active_names(log: Path = DEFAULT_LOG) -> dict[str, dict[str, str]]:
    """Active candidate-log rows keyed by ticker (the first-seen row wins)."""
    names: dict[str, dict[str, str]] = {}
    for rec in read_csv(log):
        if rec.get("status", "active") == "active" and rec["ticker"] not in names:
            names[rec["ticker"]] = rec
    return names


def default_since() -> dt.date:
    return dt.date.today() - dt.timedelta(days=3)


def cmd_track_news(args: argparse.Namespace) -> None:
    since = dt.date.fromisoformat(args.since) if args.since else default_since()
    known = {row["url"] for row in read_csv(NEWS_LOG)}
    try:
        ciks = {v["ticker"]: v["cik_str"] for v in get_json(SEC_TICKERS_URL, SEC_HEADERS).values()}
    except Exception as exc:  # noqa: BLE001 - news still works without SEC filings
        print(f"SEC ticker map unavailable: {exc}")
        ciks = {}
    today = dt.date.today().isoformat()
    new_rows: list[dict[str, str]] = []
    for ticker, rec in active_names().items():
        symbol = rec.get("yahoo_symbol") or ticker
        try:
            news = get_json(NEWS_URL.format(q=urllib.parse.quote(symbol))).get("news", [])
        except Exception as exc:  # noqa: BLE001 - report and continue with filings
            print(f"{ticker}: news unavailable ({exc})")
            news = []
        for item in news:
            published = dt.datetime.fromtimestamp(item["providerPublishTime"], dt.UTC)
            related = item.get("relatedTickers")
            if published.date() < since or (related and symbol not in related):
                continue
            if not is_relevant(item["title"], ticker, rec):
                continue
            new_rows.append(
                {
                    "seen_date": today,
                    "published": published.strftime("%Y-%m-%d %H:%M UTC"),
                    "ticker": ticker,
                    "kind": f"news: {item.get('publisher', '')}",
                    "title": item["title"],
                    "url": item["link"],
                }
            )
        cik = ciks.get(ticker)
        if not cik:
            continue
        try:
            recent = get_json(SEC_SUBMISSIONS_URL.format(cik=cik), SEC_HEADERS)["filings"]["recent"]
        except Exception as exc:  # noqa: BLE001 - report and continue with the next ticker
            print(f"{ticker}: filings unavailable ({exc})")
            continue
        for i, form in enumerate(recent["form"]):
            if recent["filingDate"][i] < since.isoformat():
                break
            if form in SKIP_FORMS or form.startswith(SKIP_FORM_PREFIXES):
                continue
            accession = recent["accessionNumber"][i].replace("-", "")
            items = recent.get("items", [""] * len(recent["form"]))[i]
            new_rows.append(
                {
                    "seen_date": today,
                    "published": recent["filingDate"][i],
                    "ticker": ticker,
                    "kind": "filing",
                    "title": f"{form} {items}".strip(),
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
                    f"{recent['primaryDocument'][i]}",
                }
            )
    fresh = [row for row in new_rows if row["url"] not in known]
    fresh = list({row["url"]: row for row in fresh}.values())
    append_csv(NEWS_LOG, NEWS_FIELDS, fresh)
    for row in fresh:
        print(f"{row['ticker']:6s} {row['published'][:10]} {row['kind'][:24]:24s} {row['title']}")
    print(f"{len(fresh)} new items appended to {NEWS_LOG.name}")


NOISE_PREFIXES = (
    "sector update",
    "top midday",
    "top premarket",
    "top gainers",
    "top losers",
    "bc-most active",
    "stock market midday",
    "marketbeat week in review",
)
FORM_LABELS = {
    "8-K": "Company announcement",
    "6-K": "Company announcement",
    "10-Q": "Quarterly report",
    "10-K": "Annual report",
    "20-F": "Annual report",
    "40-F": "Annual report",
    "SCHEDULE 13D": "Big-holder filing",
    "SCHEDULE 13D/A": "Big-holder update",
    "SC TO-I": "Buyback offer document",
    "SC TO-I/A": "Buyback offer update",
    "SC TO-T": "Takeover offer document",
    "SC TO-T/A": "Takeover offer update",
    "SC 14D9": "Board response to takeover offer",
    "SC 14D9/A": "Board response to takeover offer (update)",
    "SC14D9F": "Board response to takeover bid",
    "SC14D9F/A": "Board response to takeover bid (update)",
    "DEFA14A": "Shareholder vote material",
    "DEFM14A": "Merger vote document",
    "PREM14A": "Draft merger vote document",
    "DEF 14A": "Annual meeting document",
    "425": "Merger communication",
    "S-4": "Merger registration",
}
ITEM_LABELS = {
    "1.01": "major agreement",
    "1.02": "agreement ended",
    "1.03": "bankruptcy",
    "2.01": "deal completed",
    "2.02": "results",
    "2.05": "restructuring",
    "2.06": "write-down",
    "3.01": "listing notice",
    "3.02": "share sale",
    "5.01": "change of control",
    "5.02": "leadership change",
    "5.03": "bylaw change",
    "5.07": "shareholder vote results",
    "8.01": "other news",
}


def is_relevant(title: str, ticker: str, rec: dict[str, str]) -> bool:
    """Drop market round-ups and headlines that never name the company."""
    lowered = title.lower()
    if lowered.startswith(NOISE_PREFIXES):
        return False
    keywords = [k.strip().lower() for k in rec.get("keywords", "").split(";") if k.strip()]
    if not keywords:
        return True
    return ticker.lower() in lowered.split() or any(k in lowered for k in keywords)


def plain_title(row: dict[str, str]) -> str:
    if row["kind"] != "filing":
        return row["title"]
    title = row["title"]
    form = next(
        (f for f in sorted(FORM_LABELS, key=len, reverse=True) if title.startswith(f)),
        title.partition(" ")[0],
    )
    items = title[len(form) :].strip()
    label = FORM_LABELS.get(form, f"SEC filing ({form})")
    details = [ITEM_LABELS[i] for i in items.split(",") if i in ITEM_LABELS]
    return f"{label}: {', '.join(details)}" if details else label


def shorten(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def pct(value: float) -> str:
    return "0%" if abs(value) < 0.005 else f"{value:+.0%}"


def money(value: float, currency: str) -> str:
    return f"{'C$' if currency == 'CAD' else '$'}{value:,.2f}"


def status_note(status: str) -> str:
    """Calendar marker for dates the company has not itself confirmed."""
    return "" if status == "confirmed" else f" <i>({html.escape(status)})</i>"


def short_date(iso: str) -> str:
    day = dt.date.fromisoformat(iso[:10])
    return f"{day:%b} {day.day}"


def tracked_updates(since: dt.date) -> list[dict[str, str]]:
    """One row per active name: price since pick, call change, new items, next event."""
    estimates: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(ESTIMATES_LOG):
        estimates.setdefault(row["ticker"], []).append(row)
    names = active_names()
    news: dict[str, list[dict[str, str]]] = {}
    seen_titles: set[tuple[str, str]] = set()
    for row in sorted(read_csv(NEWS_LOG), key=lambda r: r["published"], reverse=True):
        rec = names.get(row["ticker"])
        if rec is None or row["published"][:10] < since.isoformat():
            continue
        if row["kind"] != "filing" and not is_relevant(row["title"], row["ticker"], rec):
            continue
        key = (row["ticker"], plain_title(row)[:45].lower())
        if key not in seen_titles:
            seen_titles.add(key)
            news.setdefault(row["ticker"], []).append(row)
    today = dt.date.today()
    events: dict[str, list[dict[str, str]]] = {}
    for row in sorted(read_csv(CALENDAR), key=lambda r: r["date"]):
        if row["date"] >= today.isoformat():
            events.setdefault(row["ticker"], []).append(row)
    cache: dict[str, float] = {}
    out = []
    for ticker, rec in names.items():
        symbol = rec.get("yahoo_symbol") or ticker
        bench = benchmark_for(rec["exchange"])
        try:
            for sym in (symbol, bench):
                if sym not in cache:
                    cache[sym] = fetch_daily(sym, "5d")[0]["regularMarketPrice"]
        except Exception as exc:  # noqa: BLE001 - keep the row without a live price
            print(f"{ticker}: price unavailable ({exc})")
        first = float(rec["price_first_seen"])
        now = cache.get(symbol)
        history = sorted(estimates.get(ticker, []), key=lambda r: r["date"])
        latest = history[-1] if history else None
        previous = history[-2] if len(history) > 1 else None
        if latest is None:
            call = rec.get("rating", "")
        elif previous is None or previous["rating"] == latest["rating"]:
            call = f"{latest['rating']} (unchanged)" if previous else latest["rating"]
        else:
            call = f"{previous['rating']} → {latest['rating']}"
        odds = ""
        if latest:
            odds = f"{pct(float(latest['upside']))} · {float(latest['p_upside']):.0%} chance"
            if previous and previous["p_upside"] != latest["p_upside"]:
                odds += f" (was {float(previous['p_upside']):.0%})"
        upcoming = events.get(ticker, [])
        currency = rec.get("currency", "USD")
        out.append(
            {
                "ticker": ticker,
                "symbol": symbol,
                "picked": f"{short_date(rec['first_seen_date'])} @ {money(first, currency)}",
                "now": money(now, currency) if now else "n/a",
                "change": pct(now / first - 1) if now else "n/a",
                "call": call,
                "odds": odds,
                "news": news.get(ticker, []),
                "next_event": (
                    f"{short_date(upcoming[0]['date'])}: {upcoming[0]['event']}"
                    if upcoming
                    else "none dated"
                ),
            }
        )
    return out


def calendar_html(weeks: int) -> str:
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday())
    end = start + dt.timedelta(weeks=weeks)
    by_day: dict[str, list[dict[str, str]]] = {}
    later = []
    for row in sorted(read_csv(CALENDAR), key=lambda r: r["date"]):
        day = dt.date.fromisoformat(row["date"])
        if start <= day < end:
            by_day.setdefault(row["date"], []).append(row)
        elif day >= end:
            later.append(row)
    cell = "border:1px solid #ddd;padding:4px;vertical-align:top;width:14%;font-size:12px"
    parts = [
        '<table style="border-collapse:collapse;width:100%"><tr>',
        *(
            f'<th style="{cell};background:#f2f2f2">{d}</th>'
            for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        ),
        "</tr>",
    ]
    for week in range(weeks):
        parts.append("<tr>")
        for offset in range(7):
            day = start + dt.timedelta(weeks=week, days=offset)
            shade = ";background:#fff8dc" if day == today else ""
            items = "".join(
                f'<div><a href="https://finance.yahoo.com/quote/{html.escape(e["ticker"])}">'
                f'<b>{html.escape(e["ticker"])}</b></a> {html.escape(e["event"])}'
                f"{status_note(e['status'])}</div>"
                for e in by_day.get(day.isoformat(), [])
            )
            parts.append(
                f'<td style="{cell}{shade}"><div style="color:#888">{day:%b %d}</div>{items}</td>'
            )
        parts.append("</tr>")
    parts.append("</table>")
    if later:
        parts.append(
            "<p style='font-size:12px'>Later: "
            + "; ".join(
                f"{short_date(e['date'])} {html.escape(e['ticker'])} {html.escape(e['event'])}"
                for e in later
            )
            + "</p>"
        )
    return "".join(parts)


def cmd_email_sections(args: argparse.Namespace) -> None:
    since = dt.date.fromisoformat(args.since) if args.since else default_since()
    rows = tracked_updates(since)
    cell = "border:1px solid #ddd;padding:5px;vertical-align:top;font-size:13px"
    head = ("Stock", "Picked", "Now", "Since pick", "Call", "If it works", "What's new", "Next")
    table = ['<table style="border-collapse:collapse"><tr>']
    table += [f'<th style="{cell};background:#f2f2f2">{h}</th>' for h in head]
    table.append("</tr>")
    text = [f"Tracked stocks (news since {since}):"]
    for r in rows:
        links = (
            "<br>".join(
                f'<a href="{html.escape(n["url"])}">{html.escape(shorten(plain_title(n)))}</a>'
                for n in r["news"][:2]
            )
            or "nothing new"
        )
        cells = (
            f'<a href="https://finance.yahoo.com/quote/{html.escape(r["symbol"])}">'
            f'{html.escape(r["ticker"])}</a>',
            r["picked"],
            r["now"],
            r["change"],
            html.escape(r["call"]),
            html.escape(r["odds"]),
            links,
            html.escape(r["next_event"]),
        )
        table.append("<tr>" + "".join(f'<td style="{cell}">{c}</td>' for c in cells) + "</tr>")
        text.append(
            f"- {r['ticker']}: {r['now']} ({r['change']} since pick), {r['call']}; "
            f"{len(r['news'])} new items; next: {r['next_event']}"
        )
    table.append("</table>")
    page = (
        f"<h3>Tracked stocks</h3>{''.join(table)}" f"<h3>Calendar</h3>{calendar_html(args.weeks)}"
    )
    Path(args.out).write_text(page, encoding="utf-8")
    print("\n".join(text))
    print(f"HTML written to {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot")
    snap.add_argument("tickers", nargs="+")
    snap.set_defaults(func=cmd_snapshot)

    rt = sub.add_parser("rate")
    rt.add_argument("--price", type=float, required=True)
    rt.add_argument("--scenario", action="append", required=True, help="label:probability:target")
    rt.add_argument("--confidence", choices=CONFIDENCE_LEVELS, default="medium")
    rt.add_argument("--capped", action="store_true", help="illiquid, OTC or heavy-dilution name")
    rt.add_argument("--ticker", help="append this estimate to estimates_log.csv")
    rt.add_argument("--note", default="", help="short reason stored with the estimate")
    rt.set_defaults(func=cmd_rate)

    upd = sub.add_parser("update-log")
    upd.add_argument("--log", default=str(DEFAULT_LOG))
    upd.set_defaults(func=cmd_update_log)

    news = sub.add_parser("track-news")
    news.add_argument("--since", help="YYYY-MM-DD (default: three days ago)")
    news.set_defaults(func=cmd_track_news)

    sections = sub.add_parser("email-sections")
    sections.add_argument("--since", help="show news published on/after YYYY-MM-DD")
    sections.add_argument("--weeks", type=int, default=5)
    sections.add_argument("--out", default="email_sections.html")
    sections.set_defaults(func=cmd_email_sections)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
