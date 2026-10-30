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
  edgar-search --q '"PDUFA date of December"' [--forms 8-K,10-Q] [--since DATE] [--cik N]
                               SEC full-text search; prints date, form, company and filing link
  filing-text --url URL [--pattern REGEX] [--chars N]
                               plain text of an SEC filing, or the passages matching a pattern
  fundamentals TICKER          trailing-12-month revenue, profit, cash flow, cash, debt, shares
  check-logs                   repair CSV rows whose unquoted commas spilled into extra columns
  trial-results [--since DATE] trial readouts filed with the SEC (8-K/6-K), flagged positive or
                               negative, with the stock's latest move
  upcoming-trials [--days N] [--max-mcap B]
                               listed companies whose Phase 2/3 trials finish soon on
                               ClinicalTrials.gov (likely data readouts), smallest first
  trial-info NCT_ID            design, size, primary goal and status of one trial
  ca-movers [--min-move F] [--min-value C$] [--min-price C$] [--top N]
                               biggest TSX and TSX-V moves of the latest session, with volume
                               against normal and the latest headline
  ca-news [--since DATE] [--lists deals,public,mining] [--all]
                               Canadian press releases (newswire.ca) tagged with a TSX, TSX-V or
                               CSE ticker, sorted by catalyst type
  cad-listing TICKER...        whether a US-listed stock can be bought in Canadian dollars
                               (TSX/TSX-V/CSE/Cboe Canada shares, or a CAD-hedged CDR)

The owner buys only in Canadian dollars, so trial-results and upcoming-trials keep only companies
with a Canadian listing unless --us-too is given.

Market data comes from the public Yahoo Finance chart endpoint. Prices may be delayed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import functools
import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
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

# Canadian-dollar listings: Yahoo exchange codes, symbol suffixes and the exchange names used in
# candidate_log.csv. Wealthsimple trades all four exchanges in CAD.
CAD_EXCHANGES = {"TOR": "TSX", "VAN": "TSX-V", "CNQ": "CSE", "NEO": "Cboe Canada"}
CAD_SUFFIXES = (".TO", ".V", ".CN", ".NE")
CANADIAN_EXCHANGES = {"TSX", "TSX-V", "TSXV", "CSE", "CBOE CANADA", "NEO"}

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
    offset = dt.timedelta(seconds=res["meta"].get("gmtoffset", 0))
    rows = [
        ((dt.datetime.fromtimestamp(ts, dt.UTC) + offset).date(), close, vol or 0)
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
        price = meta["regularMarketPrice"]
        stamp = dt.datetime.fromtimestamp(meta["regularMarketTime"], dt.UTC).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        offset = dt.timedelta(seconds=meta.get("gmtoffset", 0))
        market_day = (dt.datetime.fromtimestamp(meta["regularMarketTime"], dt.UTC) + offset).date()
        # After the close Yahoo can drop the current session's daily bar for a while, so
        # split completed sessions from the latest one and take its figures from the quote.
        before = [r for r in rows if r[0] < market_day]
        today_vol = next((r[2] for r in rows if r[0] == market_day), None)
        if today_vol is None:
            today_vol = meta.get("regularMarketVolume") or 0
        closes = [r[1] for r in before] + [price]
        vols = [r[2] for r in before]
        avg20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else float("nan")
        rv250 = realized_vol(closes, 250)
        lo, hi = price_range(price, rv250, 63)
        prev = before[-1][1] if before else float("nan")
        ret_1m = (closes[-1] / closes[-22] - 1) * 100 if len(closes) > 22 else float("nan")
        parts = [
            f"{ticker} {meta.get('fullExchangeName', '?')} {meta.get('currency', '?')}",
            f"price={price:.3f} @ {stamp}",
            f"prev_close={prev:.3f} chg={(price / prev - 1) * 100:+.1f}%",
            f"vol={today_vol:,} avg20={avg20:,.0f} "
            f"rvol={today_vol / avg20 if avg20 else float('nan'):.2f}",
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
    return "XIU.TO" if exchange.upper() in CANADIAN_EXCHANGES else "SPY"


def is_canadian(symbol: str) -> bool:
    return symbol.upper().endswith(CAD_SUFFIXES)


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
    for rec in records:
        # An unquoted comma in a hand-written note spills into extra columns; fold them back.
        extra = rec.pop(None, None)
        if extra:
            rec[fields[-1]] = ",".join([rec.get(fields[-1]) or "", *extra])
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
    # Write to a temporary file first so a failure can never leave a truncated log behind.
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    tmp.replace(path)
    print(f"updated {len(records)} rows in {path}")


def cmd_check_logs(_: argparse.Namespace) -> None:
    """Repair hand-edited CSV rows whose unquoted commas spilled into extra columns."""
    for path in (DEFAULT_LOG, NEWS_LOG, ESTIMATES_LOG, CALENDAR):
        if not path.exists():
            continue
        with path.open(newline="") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            continue
        width = len(rows[0])
        fixed, changed = [rows[0]], 0
        for row in rows[1:]:
            if not row:
                changed += 1
                continue
            if len(row) > width:
                row = row[: width - 1] + [",".join(row[width - 1 :])]
                changed += 1
            elif len(row) < width:
                row = row + [""] * (width - len(row))
                changed += 1
            fixed.append(row)
        if changed:
            tmp = path.with_suffix(".csv.tmp")
            with tmp.open("w", newline="") as fh:
                csv.writer(fh).writerows(fixed)
            tmp.replace(path)
        print(f"{path.name}: {len(fixed) - 1} rows, {changed} repaired")


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


@functools.cache
def company_name(symbol: str) -> str:
    """Yahoo's company name for a symbol, or the symbol itself when the lookup fails."""
    try:
        meta = fetch_daily(symbol, "5d")[0]
    except Exception:  # noqa: BLE001 - the symbol still works as a search term
        return symbol
    return meta.get("longName") or meta.get("shortName") or symbol


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
        # A Canadian line has SEC filings only when the company is also US-listed and its US
        # ticker is recorded; a bare root like HLF would otherwise pick up another company.
        sec_ticker = rec.get("sec_ticker") or ("" if is_canadian(symbol) else ticker)
        try:
            # Yahoo returns no news for ".TO"-style symbols, so search Canadian names by company.
            query = company_name(symbol) if is_canadian(symbol) else symbol
            news = get_json(NEWS_URL.format(q=urllib.parse.quote(query))).get("news", [])
        except Exception as exc:  # noqa: BLE001 - report and continue with filings
            print(f"{ticker}: news unavailable ({exc})")
            news = []
        for item in news:
            published = dt.datetime.fromtimestamp(item["providerPublishTime"], dt.UTC)
            related = item.get("relatedTickers")
            if published.date() < since or (
                related and symbol not in related and (not sec_ticker or sec_ticker not in related)
            ):
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
        cik = ciks.get(sec_ticker) if sec_ticker else None
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
    text = f"{day:%b} {day.day}"
    return text if day.year == dt.date.today().year else f"{text}, {day.year}"


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
        # A change is today's call against the last one shown before today, so a
        # change made in an earlier run is not reported again.
        earlier = [r for r in history if r["date"] < today.isoformat()]
        previous = earlier[-1] if earlier and latest is not earlier[-1] else None
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
    # Only tracked names; the symbol keeps a TSX listing from linking to a US namesake.
    symbols = {t: rec.get("yahoo_symbol") or t for t, rec in active_names().items()}
    for row in sorted(read_csv(CALENDAR), key=lambda r: r["date"]):
        if row["ticker"] not in symbols:
            continue
        row["symbol"] = symbols[row["ticker"]]
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
                f'<div><a href="https://finance.yahoo.com/quote/{html.escape(e["symbol"])}">'
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


EFTS_URL = "https://efts.sec.gov/LATEST/search-index?"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FLOW_CONCEPTS = {
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ),
    "operating_income": ("OperatingIncomeLoss",),
    "d_and_a": (
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
}
BALANCE_CONCEPTS = {
    "cash": (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    "short_term_investments": (
        "ShortTermInvestments",
        "MarketableSecuritiesCurrent",
        "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
    ),
    "long_term_debt": ("LongTermDebtNoncurrent", "LongTermDebt"),
    "current_debt": ("LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings"),
    "total_liabilities": ("Liabilities",),
}


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def cmd_edgar_search(args: argparse.Namespace) -> None:
    params = {
        "q": args.q,
        "dateRange": "custom",
        "startdt": args.since,
        "enddt": args.until or dt.date.today().isoformat(),
    }
    if args.forms:
        params["forms"] = ",".join(f.strip() for f in args.forms.split(","))
    if args.cik:
        params["ciks"] = f"{int(args.cik):010d}"
    data: dict = {}
    for attempt in range(2):
        try:
            data = get_json(EFTS_URL + urllib.parse.urlencode(params), SEC_HEADERS)
        except urllib.error.HTTPError as exc:
            data = {"error": f"HTTP {exc.code} {exc.reason}"}
        except (urllib.error.URLError, TimeoutError) as exc:
            data = {"error": str(exc)}
        if "hits" in data:
            break
        if attempt == 0:
            time.sleep(5)
    if "hits" not in data:
        sys.exit(f"SEC search failed ({str(data)[:200]}); retry in a minute")
    hits = data["hits"]["hits"]
    print(f"{data['hits']['total']['value']} matches (showing {len(hits)})")
    seen = set()
    for hit in hits:
        src = hit["_source"]
        accession, _, doc = hit["_id"].partition(":")
        key = (src["display_names"][0], src["form"])
        if key in seen:
            continue
        seen.add(key)
        cik = int(src["ciks"][0])
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{doc}"
        print(f"{src['file_date']} {src['form']:14s} {src['display_names'][0][:60]:60s} {url}")


def cmd_filing_text(args: argparse.Namespace) -> None:
    req = urllib.request.Request(args.url, headers=SEC_HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = html_to_text(resp.read().decode("utf-8", "ignore"))
    if not args.pattern:
        print(text[: args.chars])
        return
    matches = list(re.finditer(args.pattern, text, re.IGNORECASE))
    print(f"{len(matches)} matches")
    for match in matches[: args.max_matches]:
        start = max(0, match.start() - 300)
        print("…" + text[start : match.start() + args.chars] + "…\n")


def days_between(start: str, end: str) -> int:
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def trailing_twelve_months(facts: dict, names: tuple[str, ...]) -> tuple[float, str, str] | None:
    """Latest fiscal year, rolled forward with the current year-to-date when one exists."""
    for name in names:
        rows = [
            r
            for r in facts.get(name, {}).get("units", {}).get("USD", [])
            if r.get("start") and r.get("form", "").split("/")[0] in ("10-K", "10-Q", "20-F")
        ]
        annual = [r for r in rows if 350 <= days_between(r["start"], r["end"]) <= 380]
        if not annual:
            continue
        year = max(annual, key=lambda r: r["end"])
        latest_end = max(r["end"] for r in rows)
        if year["end"] == latest_end:
            return year["val"], "fiscal year", year["end"]
        ytd = [
            r for r in rows if r["end"] == latest_end and days_between(r["start"], r["end"]) > 80
        ]
        if not ytd:
            return year["val"], "fiscal year", year["end"]
        current = max(ytd, key=lambda r: days_between(r["start"], r["end"]))
        length = days_between(current["start"], current["end"])
        prior = [
            r
            for r in rows
            if abs(days_between(r["start"], r["end"]) - length) < 10
            and abs(days_between(r["end"], current["end"]) - 365) < 10
        ]
        if prior:
            return year["val"] + current["val"] - prior[0]["val"], "12 months", latest_end
        return year["val"], "fiscal year", year["end"]
    return None


def latest_balance(facts: dict, names: tuple[str, ...]) -> tuple[float, str, str] | None:
    for name in names:
        rows = facts.get(name, {}).get("units", {}).get("USD", [])
        if rows:
            row = max(rows, key=lambda r: (r["end"], r.get("filed", "")))
            return row["val"], "balance", row["end"]
    return None


def cmd_fundamentals(args: argparse.Namespace) -> None:
    ciks = {v["ticker"]: v["cik_str"] for v in get_json(SEC_TICKERS_URL, SEC_HEADERS).values()}
    cik = ciks.get(args.ticker.upper().split(".")[0])
    if cik is None:
        sys.exit(f"{args.ticker}: no SEC filer found (Canadian-only names file on SEDAR+)")
    data = get_json(COMPANY_FACTS_URL.format(cik=cik), SEC_HEADERS)
    facts = {**data["facts"].get("ifrs-full", {}), **data["facts"].get("us-gaap", {})}
    print(f"{data['entityName']} (CIK {cik}); values in US$ millions")
    stale_before = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    values: dict[str, float] = {}
    for label, concepts in (*FLOW_CONCEPTS.items(), *BALANCE_CONCEPTS.items()):
        getter = trailing_twelve_months if label in FLOW_CONCEPTS else latest_balance
        found = getter(facts, concepts)
        if found is None:
            print(f"  {label:24s} not reported")
            continue
        value, kind, end = found
        stale = " (STALE, ignore)" if end < stale_before else ""
        if not stale:
            values[label] = value
        print(f"  {label:24s} {value / 1e6:>12,.1f}  {kind} to {end}{stale}")
    shares = data["facts"].get("dei", {}).get("EntityCommonStockSharesOutstanding", {})
    share_rows = shares.get("units", {}).get("shares", [])
    if share_rows:
        row = max(share_rows, key=lambda r: r["end"])
        print(f"  {'shares_outstanding':24s} {row['val'] / 1e6:>12,.2f}M at {row['end']}")
    if "operating_income" in values and "d_and_a" in values:
        ebitda = values["operating_income"] + values["d_and_a"]
        print(f"  approx EBITDA (op. income + D&A): {ebitda / 1e6:,.1f}")
    if "operating_cash_flow" in values and "capex" in values:
        fcf = values["operating_cash_flow"] - values["capex"]
        print(f"  free cash flow: {fcf / 1e6:,.1f}")


CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies"
POSITIVE_PHRASES = (
    "met its primary endpoint",
    "met the primary endpoint",
    "achieved its primary endpoint",
    "achieved the primary endpoint",
    "primary endpoint was met",
    "statistically significant improvement",
)
NEGATIVE_PHRASES = (
    "did not meet its primary endpoint",
    "did not meet the primary endpoint",
    "did not achieve its primary endpoint",
    "did not achieve the primary endpoint",
    "failed to meet its primary endpoint",
    "failed to meet the primary endpoint",
    "did not reach statistical significance on the primary endpoint",
)
NEUTRAL_PHRASES = ("topline results", "top-line results", "topline data", "top-line data")
# SEC industry codes for drugs, biologics, diagnostics, medical devices and medical research.
HEALTH_SICS = {"2833", "2834", "2835", "2836", "3826", "3841", "3842", "3843", "3844", "3845"}
HEALTH_SICS |= {"3851", "5047", "5122", "8000", "8011", "8071", "8090", "8731", "8733"}
HEALTH_NAME = re.compile(
    r"bio|pharm|therap|medic|onco|immun|genetic|genomic|vaccin|diagnos|clinic|life sci", re.I
)
NAME_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "plc",
    "llc",
    "lp",
    "sa",
    "ag",
    "nv",
    "se",
    "holdings",
    "holding",
    "group",
    "the",
}


def efts_hits(phrase: str, forms: str, since: str) -> list[dict]:
    params = {
        "q": f'"{phrase}"',
        "forms": forms,
        "dateRange": "custom",
        "startdt": since,
        "enddt": dt.date.today().isoformat(),
    }
    try:
        return get_json(EFTS_URL + urllib.parse.urlencode(params), SEC_HEADERS)["hits"]["hits"]
    except (urllib.error.URLError, TimeoutError, KeyError) as exc:
        print(f"  (search for '{phrase}' failed: {exc})")
        return []


def ticker_of(display_name: str) -> str:
    match = re.search(r"\(([A-Z][A-Z0-9.\-]*)(?:,[^)]*)?\)", display_name)
    return match.group(1) if match else ""


def last_move(symbol: str) -> str:
    try:
        meta, rows = fetch_daily(symbol, "1mo")
    except Exception:  # noqa: BLE001 - price is optional context
        return "price n/a"
    offset = dt.timedelta(seconds=meta.get("gmtoffset", 0))
    day = (dt.datetime.fromtimestamp(meta["regularMarketTime"], dt.UTC) + offset).date()
    before = [r[1] for r in rows if r[0] < day]
    price = money(meta["regularMarketPrice"], meta.get("currency", "USD"))
    if not before:
        return price
    change = meta["regularMarketPrice"] / before[-1] - 1
    return f"{price} ({change * 100:+.0f}% on {day:%b} {day.day})"


def cmd_trial_results(args: argparse.Namespace) -> None:
    since = args.since or (dt.date.today() - dt.timedelta(days=3)).isoformat()
    found: dict[str, dict] = {}
    for tone, phrases in (
        ("negative", NEGATIVE_PHRASES),
        ("positive", POSITIVE_PHRASES),
        ("check", NEUTRAL_PHRASES),
    ):
        for phrase in phrases:
            for hit in efts_hits(phrase, "8-K,6-K", since):
                src = hit["_source"]
                healthcare = bool(set(src.get("sics", [])) & HEALTH_SICS) or bool(
                    HEALTH_NAME.search(src["display_names"][0])
                )
                if not (args.all or healthcare or "primary endpoint" in phrase):
                    continue
                accession, _, doc = hit["_id"].partition(":")
                key = accession
                entry = found.setdefault(
                    key,
                    {
                        "date": src["file_date"],
                        "company": src["display_names"][0],
                        "ticker": ticker_of(src["display_names"][0]),
                        "tone": tone,
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(src['ciks'][0])}/"
                        f"{accession.replace('-', '')}/{doc}",
                    },
                )
                if tone == "negative":
                    entry["tone"] = "negative"
    rows = sorted(found.values(), key=lambda e: (e["date"], e["company"]), reverse=True)
    for entry in rows:
        entry["symbol"] = entry["ticker"]
        if not args.us_too and entry["ticker"]:
            name = re.sub(r"\s*\(.*", "", entry["company"])
            entry["symbol"] = cad_symbol(entry["ticker"], name, shares_only=True)
    if not args.us_too:
        rows = [e for e in rows if e["symbol"]]
    scope = "" if args.us_too else " at companies with a Canadian-dollar listing"
    print(f"{len(rows)} filings mentioning trial results since {since}{scope}")
    print("tone: positive / negative = a results phrase was found; check = read the filing")
    for entry in rows:
        move = last_move(entry["symbol"]) if entry["symbol"] and args.prices else ""
        print(
            f"{entry['date']} {entry['tone']:8s} {entry['symbol'] or '-':9s} "
            f"{entry['company'][:45]:45s} {move:28s} {entry['url']}"
        )


def normalize_company(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in NAME_SUFFIXES)


def sec_company_index() -> dict[str, tuple[str, int]]:
    """Normalized SEC company name -> (ticker, CIK); the first (main) ticker wins."""
    index: dict[str, tuple[str, int]] = {}
    for row in get_json(SEC_TICKERS_URL, SEC_HEADERS).values():
        index.setdefault(normalize_company(row["title"]), (row["ticker"], row["cik_str"]))
    return index


def match_sponsor(sponsor: str, index: dict[str, tuple[str, int]]) -> tuple[str, int] | None:
    key = normalize_company(sponsor)
    if key in index:
        return index[key]
    for name, value in index.items():
        if len(name) >= 8 and (key.startswith(name + " ") or name.startswith(key + " ")):
            return value
    return None


def market_cap(ticker: str, cik: int) -> float | None:
    try:
        shares = get_json(
            f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}"
            "/dei/EntityCommonStockSharesOutstanding.json",
            SEC_HEADERS,
        )["units"]["shares"]
        count = max(shares, key=lambda r: r["end"])["val"]
        price = fetch_daily(ticker, "5d")[0]["regularMarketPrice"]
    except Exception:  # noqa: BLE001 - foreign filers often lack the share count
        return None
    return count * price


def cmd_upcoming_trials(args: argparse.Namespace) -> None:
    today = dt.date.today()
    start = today - dt.timedelta(days=args.lookback)
    end = today + dt.timedelta(days=args.days)
    params = {
        "filter.advanced": "AREA[LeadSponsorClass]INDUSTRY AND AREA[Phase](PHASE2 OR PHASE3) "
        f"AND AREA[PrimaryCompletionDate]RANGE[{start},{end}]",
        "filter.overallStatus": "ACTIVE_NOT_RECRUITING,COMPLETED",
        "fields": "NCTId,BriefTitle,Phase,OverallStatus,PrimaryCompletionDate,LeadSponsorName,"
        "EnrollmentCount,HasResults",
        "pageSize": "1000",
    }
    studies: list[dict] = []
    token = None
    while True:
        query = dict(params, **({"pageToken": token} if token else {}))
        data = get_json(f"{CTGOV_URL}?{urllib.parse.urlencode(query)}")
        studies += data.get("studies", [])
        token = data.get("nextPageToken")
        if not token or len(studies) >= 5000:
            break
    index = sec_company_index()
    # TSX and TSX-V companies that don't file with the SEC are matched by name to their listing.
    ca_index: dict[str, tuple[str, int]] = {}
    if not args.us_too:
        try:
            for x in tsx_directory():
                if not (x["cdr"] or NON_SHARE_SUFFIX.search(x["symbol"])):
                    ca_index.setdefault(normalize_company(x["name"]), (x["yahoo"], 0))
        except Exception as exc:  # noqa: BLE001 - SEC filers are still checked
            print(f"TSX directory unavailable ({exc}); only SEC filers checked")
    caps: dict[str, float | None] = {}
    cad: dict[str, str] = {}
    rows = []
    for study in studies:
        proto = study["protocolSection"]
        sponsor = proto["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
        match = match_sponsor(sponsor, index)
        ca_match = None if match else match_sponsor(sponsor, ca_index)
        if match:
            ticker, cik = match
            if ticker not in caps:
                caps[ticker] = market_cap(ticker, cik)
            cap = caps[ticker]
            if cap is not None and (cap > args.max_mcap * 1e9 or cap < 20e6):
                continue
            if not args.us_too:
                if ticker not in cad:
                    cad[ticker] = cad_symbol(ticker, sponsor, shares_only=True)
                if not cad[ticker]:
                    continue
                ticker = cad[ticker]
        elif ca_match:
            ticker, cap = ca_match[0], None
        else:
            continue
        done = proto["statusModule"]["primaryCompletionDateStruct"]
        rows.append(
            (
                cap or 0,
                ticker,
                sponsor,
                done.get("date", "?"),
                done.get("type", "ESTIMATED").lower(),
                "/".join(p.replace("PHASE", "P") for p in proto["designModule"].get("phases", [])),
                proto["designModule"].get("enrollmentInfo", {}).get("count", "?"),
                proto["identificationModule"]["nctId"],
                proto["identificationModule"]["briefTitle"],
            )
        )
    rows.sort(key=lambda r: (r[0] == 0, r[0], r[3]))
    scope = "listed companies" if args.us_too else "companies with a Canadian-dollar listing"
    print(
        f"{len(rows)} Phase 2/3 trials at {scope} under US${args.max_mcap:g}B, finishing "
        f"{start}..{end}. Topline data usually follows 1–3 months after the finish date."
    )
    for cap, ticker, sponsor, date, kind, phase, enrolled, nct, title in rows:
        cap_text = f"US${cap / 1e9:.2f}B" if cap else "cap n/a"
        print(
            f"{ticker:9s} {cap_text:10s} {phase:6s} done {date} ({kind}) n={enrolled} {nct} "
            f"{sponsor[:28]} | {title[:70]}"
        )


def cmd_trial_info(args: argparse.Namespace) -> None:
    proto = get_json(f"{CTGOV_URL}/{args.nct_id}")["protocolSection"]
    ident, status, design = (
        proto["identificationModule"],
        proto["statusModule"],
        proto["designModule"],
    )
    print(f"{ident['nctId']}: {ident.get('officialTitle') or ident['briefTitle']}")
    print(f"  sponsor: {proto['sponsorCollaboratorsModule']['leadSponsor']['name']}")
    print(f"  phase: {design.get('phases')}  status: {status['overallStatus']}")
    print(f"  enrollment: {design.get('enrollmentInfo')}")
    print(f"  primary completion: {status.get('primaryCompletionDateStruct')}")
    print(f"  study completion: {status.get('completionDateStruct')}")
    info = design.get("designInfo", {})
    masking = info.get("maskingInfo", {}).get("masking")
    print(
        f"  design: {info.get('allocation')} / {info.get('interventionModel')} / masking {masking}"
    )
    for outcome in proto.get("outcomesModule", {}).get("primaryOutcomes", []):
        print(f"  primary outcome: {outcome.get('measure')} ({outcome.get('timeFrame')})")
    for arm in proto.get("armsInterventionsModule", {}).get("armGroups", []):
        print(f"  arm: {arm.get('label')} [{arm.get('type')}]")
    print(f"  conditions: {proto.get('conditionsModule', {}).get('conditions')}")
    print(f"  link: https://clinicaltrials.gov/study/{ident['nctId']}")


TSX_DIRECTORY_URL = "https://www.tsx.com/json/company-directory/search/{board}/%5E*"
SPARK_URL = "https://query1.finance.yahoo.com/v7/finance/spark?symbols={s}&range=5d&interval=1d"
QUOTE_SEARCH_URL = (
    "https://query1.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=12&newsCount=0"
)
NEWSWIRE_URL = "https://www.newswire.ca"
NEWSWIRE_LISTS = {
    "deals": "/news-releases/financial-services-latest-news/"
    "acquisitions-mergers-and-takeovers-list/",
    "public": "/news-releases/all-public-company-news/",
    "mining": "/news-releases/energy-latest-news/mining-list/",
}
BOARD_SUFFIX = {"tsx": ".TO", "tsxv": ".V"}
# Listings that are not plain CAD shares: US-dollar lines, debentures, warrants, preferreds,
# rights and notes. Trust units (.UN) are kept.
NON_SHARE_SUFFIX = re.compile(r"\.(U|DB|WT|PR|RT|NT|NO|SB|W)(\.|$)")
FUND_NAME = re.compile(
    r"\b(ETFs?|Fund|Index|Portfolio|Covered Call|Yield Shares|Split|Bitcoin|Ether|Solana|XRP)\b",
    re.I,
)
CA_TAG = re.compile(
    r"\((TSX[- ]?V(?:enture(?: Exchange)?)?|TSX|CSE|NEO|Cboe Canada)\s*:\s*([A-Z][A-Z0-9.]{0,9})",
    re.I,
)
CA_NEWS_KINDS = (
    (
        "takeover",
        r"arrangement agreement|plan of arrangement|take-?over bid|to be acquired|"
        r"to acquire all|definitive agreement|merger|unsolicited|going.private",
    ),
    ("asset sale", r"\bto sell\b|\bsale of\b|divest"),
    ("review", r"strategic review|strategic alternatives|special committee|sale process"),
    (
        "big holder",
        r"early warning|acquires (?:units|shares|common shares)|"
        r"(?:acquisition|disposition) of securities",
    ),
    ("buyback", r"substantial issuer bid|normal course issuer bid|dutch auction"),
    ("drug/medical", r"\bFDA\b|Health Canada|phase [123]|topline|primary endpoint"),
    (
        "mining result",
        r"\bdrill|g/t\b|intercept|resource estimate|feasibility|preliminary economic|"
        r"\bPEA\b|permit",
    ),
    ("financing", r"private placement|bought deal|\boffering\b|financing"),
)


@functools.lru_cache(maxsize=1)
def tsx_directory() -> tuple[dict, ...]:
    """Every TSX and TSX-V listing: symbol, Yahoo symbol, company, exchange, and CDR flag."""
    listings = []
    for board, label in (("tsx", "TSX"), ("tsxv", "TSX-V")):
        for company in get_json(TSX_DIRECTORY_URL.format(board=board))["results"]:
            for inst in company.get("instruments") or [{"symbol": company["symbol"]}]:
                listings.append(
                    {
                        "symbol": inst["symbol"],
                        "yahoo": inst["symbol"].replace(".", "-") + BOARD_SUFFIX[board],
                        "name": company["name"],
                        "exchange": label,
                        "cdr": "CDR" in company["name"],
                    }
                )
    return tuple(listings)


def spark(symbols: list[str]) -> dict[str, tuple[dict, list[float]]]:
    """Latest quote and recent daily closes for up to 20 Yahoo symbols in one request."""
    url = SPARK_URL.format(s=urllib.parse.quote(",".join(symbols), safe=",.-"))
    for attempt in range(2):
        try:
            results = get_json(url)["spark"]["result"]
            break
        except Exception:  # noqa: BLE001 - one retry, then skip this batch
            if attempt:
                return {}
            time.sleep(2)
    out = {}
    for item in results:
        resp = (item.get("response") or [{}])[0]
        if "meta" not in resp:
            continue
        quote = resp.get("indicators", {}).get("quote", [{}])[0]
        out[item["symbol"]] = (resp["meta"], [c for c in quote.get("close", []) if c is not None])
    return out


def spark_many(symbols: list[str]) -> dict[str, tuple[dict, list[float]]]:
    batches = [symbols[i : i + 20] for i in range(0, len(symbols), 20)]
    out: dict[str, tuple[dict, list[float]]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(spark, batches):
            out.update(result)
    return out


def volume_vs_normal(symbol: str) -> str:
    """Latest session's volume as a multiple of the previous 20 sessions' average."""
    try:
        vols = [r[2] for r in fetch_daily(symbol, "3mo")[1]]
    except Exception:  # noqa: BLE001 - context only
        return "?"
    avg = sum(vols[-21:-1]) / 20 if len(vols) > 20 else 0
    return f"{vols[-1] / avg:.1f}x" if avg else "?"


def latest_headline(name: str, symbols: set[str], days: int = 4) -> str:
    """The newest headline Yahoo ties to one of these symbols in the last few days, with link."""
    try:
        query = urllib.parse.quote(normalize_company(name) or name)
        news = get_json(NEWS_URL.format(q=query)).get("news", [])
    except Exception:  # noqa: BLE001 - context only
        return ""
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    for item in news:
        published = dt.datetime.fromtimestamp(item["providerPublishTime"], dt.UTC)
        if symbols & set(item.get("relatedTickers") or []) and published >= cutoff:
            return (
                f"{item['title']} ({item.get('publisher', '')}, {published:%b} {published.day})"
                f" {item['link']}"
            )
    return ""


def cmd_ca_movers(args: argparse.Namespace) -> None:
    listings = [
        x
        for x in tsx_directory()
        if not NON_SHARE_SUFFIX.search(x["symbol"])
        and not FUND_NAME.search(x["name"])
        and (args.cdrs or not x["cdr"])
    ]
    quotes = spark_many([x["yahoo"] for x in listings])
    movers = []
    for listing in listings:
        meta, closes = quotes.get(listing["yahoo"], ({}, []))
        if len(closes) < 2:
            continue
        price, move = closes[-1], closes[-1] / closes[-2] - 1
        traded = price * (meta.get("regularMarketVolume") or 0)
        if price >= args.min_price and traded >= args.min_value and abs(move) >= args.min_move:
            movers.append((move, price, traded, listing))
    movers.sort(key=lambda m: -abs(m[0]))
    print(
        f"{len(quotes)} of {len(listings)} TSX/TSX-V shares priced. {len(movers)} moved at least "
        f"{args.min_move:.0%} in the latest session with C${args.min_value:,.0f}+ traded and a "
        f"price of C${args.min_price:.2f}+. Volume is against the 20-day average."
    )
    for move, price, traded, listing in movers[: args.top]:
        # Yahoo often tags interlisted companies with their US ticker, usually the same root.
        tags = {listing["yahoo"], listing["symbol"]}
        headline = latest_headline(listing["name"], tags) or "no headline found"
        print(
            f"{move:+7.1%} {listing['yahoo']:10s} C${price:<8.2f} C${traded / 1e6:6.2f}M "
            f"vol {volume_vs_normal(listing['yahoo']):>6s} {listing['name'][:32]:32s} | {headline}"
        )


def tag_symbol(exchange: str, ticker: str) -> str:
    """Press-release tag such as (TSXV: ABC.B) -> Yahoo symbol ABC-B.V."""
    board = exchange.upper()
    if board.startswith("TSX") and "V" in board[3:]:
        suffix = ".V"
    else:
        suffix = {"TSX": ".TO", "CSE": ".CN"}.get(board, ".NE")
    return ticker.upper().rstrip(".").replace(".", "-") + suffix


def newswire_items(path: str, pages: int) -> list[dict[str, str]]:
    items = []
    for page in range(1, pages + 1):
        req = urllib.request.Request(
            f"{NEWSWIRE_URL}{path}?page={page}&pagesize=100", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", "replace")
        for href, body in re.findall(
            r'<a class="newsreleaseconsolidatelink[^"]*" href="([^"]+)">(.*?)</a>', text, re.S
        ):
            stamp = re.search(r"<small>([^<]*)</small>", body)
            title = re.search(r"</small>\s*(.*?)</h3>", body, re.S)
            summary = re.search(r'<p class="remove-outline">(.*?)</p>', body, re.S)
            if not (stamp and title):
                continue
            when = stamp.group(1).strip()
            day = (
                dt.datetime.strptime(when[:12], "%b %d, %Y").date()
                if "," in when
                else dt.date.today()
            )
            items.append(
                {
                    "date": day.isoformat(),
                    "title": html_to_text(title.group(1)),
                    "summary": html_to_text(summary.group(1)) if summary else "",
                    "url": NEWSWIRE_URL + href,
                }
            )
    return items


def cmd_ca_news(args: argparse.Namespace) -> None:
    since = (dt.date.fromisoformat(args.since) if args.since else default_since()).isoformat()
    seen: dict[str, dict[str, str]] = {}
    for name in args.lists.split(","):
        try:
            for item in newswire_items(NEWSWIRE_LISTS[name.strip()], args.pages):
                if item["date"] >= since:
                    seen.setdefault(item["url"], item)
        except Exception as exc:  # noqa: BLE001 - report and continue with the other lists
            print(f"newswire list '{name}' unavailable ({exc})")
    rows = []
    for item in seen.values():
        tag = CA_TAG.search(item["title"] + " " + item["summary"])
        if not tag and not args.all:
            continue
        text = item["title"] + " " + item["summary"]
        kind = next(
            (k for k, pattern in CA_NEWS_KINDS if re.search(pattern, text, re.I)), "other news"
        )
        item["kind"] = kind
        item["symbol"] = tag_symbol(*tag.groups()) if tag else ""
        rows.append(item)
    order = [k for k, _ in CA_NEWS_KINDS[:-1]] + ["other news", "financing"]
    rows.sort(key=lambda r: r["date"], reverse=True)
    rows.sort(key=lambda r: order.index(r["kind"]))
    quotes = spark_many(sorted({r["symbol"] for r in rows if r["symbol"]}))
    print(
        f"{len(rows)} Canadian press releases since {since} (newswire.ca: {args.lists}). "
        "Move = latest session vs the one before."
    )
    for r in rows:
        meta, closes = quotes.get(r["symbol"], ({}, []))
        move = f"{closes[-1] / closes[-2] - 1:+.0%}" if len(closes) > 1 else ""
        price = f"C${closes[-1]:.2f}" if closes else ""
        print(
            f"{r['date']} {r['kind']:13s} {r['symbol'] or '-':10s} {price:>9s} {move:>5s} "
            f"{r['title'][:95]} {r['url']}"
        )


@functools.cache
def cad_listings(ticker: str, name: str = "") -> tuple[dict[str, str], ...]:
    """Ways to own a stock in Canadian dollars: its shares on a Canadian exchange, or a CDR."""
    if is_canadian(ticker):
        suffix = "." + ticker.rsplit(".", 1)[1].upper()
        exchange = dict(zip(CAD_SUFFIXES, CAD_EXCHANGES.values(), strict=True))[suffix]
        return ({"symbol": ticker, "exchange": exchange, "kind": "shares"},)
    name = name or company_name(ticker)
    key = normalize_company(name)
    quotes: dict[str, dict] = {}
    try:
        # Yahoo matches "Curaleaf" but not "Curaleaf Holdings, Inc.", so try the bare name first.
        for query in dict.fromkeys(q for q in (key, name) if q):
            found = get_json(QUOTE_SEARCH_URL.format(q=urllib.parse.quote(query))).get("quotes")
            for quote in found or []:
                quotes.setdefault(quote["symbol"], quote)
        hedged = {x["yahoo"] for x in tsx_directory() if x["cdr"]}
    except Exception:  # noqa: BLE001 - treat as no Canadian listing found
        return ()
    lines = []
    for quote in quotes.values():
        label = quote.get("longname") or quote.get("shortname") or ""
        other = normalize_company(label)
        if (
            quote.get("exchange") not in CAD_EXCHANGES
            or quote.get("quoteType") != "EQUITY"
            or FUND_NAME.search(label)
            or not key
            or not (other == key or other.startswith(key + " ") or key.startswith(other + " "))
        ):
            continue
        if quote["symbol"] in hedged or "hedged" in other.split():
            kind = "CDR, currency-hedged"
        elif "cdr" in other.split():
            kind = "CDR"
        else:
            kind = "shares"
        lines.append(
            {"symbol": quote["symbol"], "exchange": CAD_EXCHANGES[quote["exchange"]], "kind": kind}
        )
    # Cboe Canada also trades TSX-listed shares, but a US company found only there is a CDR.
    if not any(x["kind"] == "shares" and x["exchange"] != "Cboe Canada" for x in lines):
        for line in lines:
            if line["kind"] == "shares":
                line["kind"] = "CDR"
    lines.sort(key=lambda x: ("shares", "CDR, currency-hedged", "CDR").index(x["kind"]))
    return tuple(lines)


def cad_symbol(ticker: str, name: str = "", shares_only: bool = False) -> str:
    """The preferred Canadian-dollar symbol; shares_only skips CDRs (large US companies)."""
    lines = [x for x in cad_listings(ticker, name) if not shares_only or x["kind"] == "shares"]
    return lines[0]["symbol"] if lines else ""


def cmd_cad_listing(args: argparse.Namespace) -> None:
    for ticker in args.tickers:
        lines = cad_listings(ticker.upper())
        if not lines:
            print(f"{ticker.upper()}: no Canadian-dollar listing found (US only)")
            continue
        for line in lines:
            print(
                f"{ticker.upper()}: {line['symbol']} on {line['exchange']} ({line['kind']}), "
                f"{last_move(line['symbol'])}"
            )


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

    search = sub.add_parser("edgar-search")
    search.add_argument("--q", required=True, help="phrase(s), e.g. '\"PDUFA date of December\"'")
    search.add_argument("--forms", help="comma-separated form types, e.g. 8-K,10-Q,6-K")
    search.add_argument("--since", default=(dt.date.today() - dt.timedelta(days=90)).isoformat())
    search.add_argument("--until")
    search.add_argument("--cik")
    search.set_defaults(func=cmd_edgar_search)

    filing = sub.add_parser("filing-text")
    filing.add_argument("--url", required=True)
    filing.add_argument("--pattern", help="case-insensitive regex; prints surrounding text")
    filing.add_argument("--chars", type=int, default=1500)
    filing.add_argument("--max-matches", type=int, default=3)
    filing.set_defaults(func=cmd_filing_text)

    sub.add_parser("check-logs").set_defaults(func=cmd_check_logs)

    funda = sub.add_parser("fundamentals")
    funda.add_argument("ticker")
    funda.set_defaults(func=cmd_fundamentals)

    results = sub.add_parser("trial-results")
    results.add_argument("--since", help="YYYY-MM-DD (default: three days ago)")
    results.add_argument("--no-prices", dest="prices", action="store_false")
    results.add_argument("--all", action="store_true", help="include non-healthcare filers")
    results.add_argument("--us-too", action="store_true", help="include US-only listings")
    results.set_defaults(func=cmd_trial_results)

    upcoming = sub.add_parser("upcoming-trials")
    upcoming.add_argument("--days", type=int, default=90, help="finish dates up to N days ahead")
    upcoming.add_argument("--lookback", type=int, default=45, help="and up to N days back")
    upcoming.add_argument("--max-mcap", type=float, default=10.0, help="US$ billions")
    upcoming.add_argument("--us-too", action="store_true", help="include US-only listings")
    upcoming.set_defaults(func=cmd_upcoming_trials)

    trial = sub.add_parser("trial-info")
    trial.add_argument("nct_id")
    trial.set_defaults(func=cmd_trial_info)

    movers = sub.add_parser("ca-movers")
    movers.add_argument("--min-move", type=float, default=0.08, help="fraction, e.g. 0.08")
    movers.add_argument("--min-value", type=float, default=250_000, help="C$ traded")
    movers.add_argument("--min-price", type=float, default=0.50, help="C$")
    movers.add_argument("--top", type=int, default=30)
    movers.add_argument("--cdrs", action="store_true", help="include CDRs of US companies")
    movers.set_defaults(func=cmd_ca_movers)

    ca_news = sub.add_parser("ca-news")
    ca_news.add_argument("--since", help="YYYY-MM-DD (default: three days ago)")
    ca_news.add_argument("--lists", default="deals,public,mining", help="comma-separated")
    ca_news.add_argument("--pages", type=int, default=2, help="100 releases per page")
    ca_news.add_argument("--all", action="store_true", help="include releases without a ticker")
    ca_news.set_defaults(func=cmd_ca_news)

    listing = sub.add_parser("cad-listing")
    listing.add_argument("tickers", nargs="+")
    listing.set_defaults(func=cmd_cad_listing)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
