"""Helpers for the daily pre-catalyst scanner (stdlib only).

Commands:
  snapshot TICKER...           price, volume, relative volume, realized vol and a 3-month 80% range
  rate --price P --scenario "label:prob:target" ...
                               probability-weighted expected return and the rule-based rating
  update-log [--log PATH]      fill 1/5/20/60 trading-day returns (absolute and vs benchmark)

Market data comes from the public Yahoo Finance chart endpoint. Prices may be delayed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
import urllib.request
from pathlib import Path

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range={r}"
DEFAULT_LOG = Path(__file__).resolve().parent.parent / "reports/pre-catalyst/candidate_log.csv"
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
    rt.set_defaults(func=cmd_rate)

    upd = sub.add_parser("update-log")
    upd.add_argument("--log", default=str(DEFAULT_LOG))
    upd.set_defaults(func=cmd_update_log)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
