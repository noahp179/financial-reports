# Daily Pre-Catalyst Stock Scanner

This folder holds the daily pre-catalyst research reports (`YYYY-MM-DD.md`) and the historical candidate log (`candidate_log.csv`).

## Mandate (summary of the owner's standing instructions)

- **Schedule:** Run every US/Canadian trading day (Mon–Fri, excluding NYSE/TSX holidays).
- **Delivery:** Target 7:30–8:00 a.m. America/Toronto. Email only through an authorized, connected integration, and confirm delivery only when the email system reports success.
- **Universe:** NYSE, Nasdaq, TSX and TSX-V common stocks, about US$50M–US$10B market cap, with exceptions flagged.
  - Flag illiquidity, low float, dilution, OTC status and extreme volatility.
- **Owner's priority (clarified 2026-10-26):** the *highest potential return in a short time*, and **small and micro-caps are welcome**.
  - Every report includes a **small-cap, short-horizon section** that scans for dated catalysts in the next 1–60 days. The core is:
    - FDA decision dates (PDUFA) and advisory committees;
    - Phase 2 and 3 topline readouts;
    - tender offers and Dutch auctions;
    - activist 13Ds at small caps;
    - strategic reviews and sale processes;
    - hostile bids;
    - contract awards;
    - earnings at heavily shorted names.
  - **Practical floor:** market cap of at least US$20M, price of at least US$1, and 20-day average daily dollar volume (ADV) of at least US$250K. Names below the floor can be mentioned but are flagged and `--capped`.
  - **Ranking:** by expected return. Each name also shows its **upside potential** (best-scenario return), P(gain ≥ 25%) and P(loss ≥ 25%), so the highest-potential lottery tickets are visible but are not confused with good bets.
  - **Binary events:** state plainly when the most likely outcome is a large loss.
  - **Sizing:** never recommend position sizes. Note "binary — size accordingly".
- **Catalyst categories:**
  - M&A
  - SEC and SEDAR+ filings (8-K, 13D, Form 4, merger and tender filings, proxies, early warning reports, SEDI)
  - activism
  - commercial wins
  - earnings and fundamentals
  - regulatory and legal
  - market anomalies (leads only)
  - restructuring
- **Sources, in priority order:**
  1. EDGAR, SEDAR+ and SEDI
  2. issuer investor-relations releases
  3. exchanges
  4. government and court documents
  5. Reuters and Bloomberg
  6. industry and market-data sources (supporting evidence only)
  - Social media is a lead only and must be corroborated.
  - Link sources with dates, separate fact from inference, never fabricate, and disclose gaps.
- **Score (0–100, illustrative, not a probability):**
  - catalyst evidence 0–30
  - ownership/activist/transaction 0–25
  - strategic fit or commercial significance 0–20
  - valuation 0–15
  - price/volume 0–10
  - Bands: 80+ highest · 65–79 high · 50–64 watchlist · <50 normally excluded.
  - Explain any adaptation of the components.
- **Report sections:**
  1. Executive summary
  2. Top candidates
  3. Early-stage candidates
  4. New filings and developments
  5. Unusual price/volume
  6. 1–30 day catalyst calendar
  7. Negative evidence
  8. Watchlist changes and outcomes
  9. Final priority list
  - On no-trade days, say so and do not pad the report.
- **Subject line:** `Pre-Catalyst Stock Scanner — [DATE] — [N Priority Candidates]`.
- **Safeguards:**
  - Use public, lawful information only; no material non-public information.
  - Make no allegations without evidence.
  - Do not execute trades.
  - Treat acquisition premiums as hypothetical unless an offer is confirmed.
- **Tracking:** For each candidate, log first-seen date, score, evidence, price, catalyst, later announcements, 1/5/20/60 trading-day returns, outcome and invalidation. Avoid look-ahead bias and survivorship bias.

## Extra checks added after the 2026-10-26 post-mortem

The 2026-10-26 post-mortem looked at that day's top movers and found three kinds of public signal that existed beforehand. Run these checks every day.

1. **Dated scientific presentations.** Companies often announce weeks ahead that trial data will be presented at a medical meeting (ESMO, ASCO, ASH, SITC, AACR, AASLD, and others).
   - Xencor announced on 2026-08-05 that its XmAb819 data would be an oral presentation at ESMO (Oct 23–27). The stock then moved +39% pre-market and closed +14%.
   - Use EDGAR full-text search, for example `"accepted for" "oral presentation"` or the conference name, over the last 90 days. Add any presentation in the next 30 days to the calendar as a binary event.
   - Note that meeting abstracts often go online days early.
2. **Re-bid watchlist.** Track companies where a controlling holder or bidder made a proposal within the last 2 years that ended without a deal, and that now trade well below the old bid.
   - Surgery Partners: Bain bid US$25.75 in January 2025; talks ended in June 2025; the stock sat at US$15.75 before HealthSpan's US$23.50 deal on 2026-10-26.
   - This gives no timing, so treat it as a watchlist with a low probability per week, not a Buy.
3. **Open sale process plus a volume spike.** Flag companies with a public strategic review or sale process whose volume runs above 3× average, or whose price rises more than 10% in a week, with no news.
   - Logan Energy: review began 2026-08-14; volume was 4.7× average and the stock rose 14% the week before its 10/26 deal.
   - This is a lead, not evidence of a leak.
4. **Pre-market check (about 7:00 ET).** For overnight deal reports or data releases, compare the pre-market price with any announced or reported terms. Say "room left vs. terms" or "already moved, don't chase".
   - Xencor faded from +39% pre-market to +14% at the close.

**What these checks cannot do:** predict the timing of unannounced deals, or unexplained intraday rallies. Examples from that day: EQT/Range, High Liner, GrafTech (EAF), Xtend (XTND). Don't claim otherwise. Don't trade on suspected leaks.

## Morning email (the owner's single daily email — keep it short and plain)

Send **one** email each trading morning to nepollack@gmail.com. Don't send separate addenda. The full detailed report stays in the repo and is linked at the bottom of the email.

- **Subject:** `Morning Stock Picks — <Ddd Mon D> — <N> Buy` (for example, `Morning Stock Picks — Tue Oct 27 — 1 Buy`). Use `No Buys today` when there are none.
- **Plain words, no jargon.**

  | Instead of | Write |
  |---|---|
  | PDUFA | FDA decision |
  | 13D | activist investor / big holder |
  | Dutch-auction tender | company buyback offer |
  | expected return | our estimate |
  | CRL | FDA rejection |
  | merger arb | already-agreed takeover |

  Never use RVOL, EV/EBITDA, Brier, scenario, base rate or market-implied in the email.
- **Layout** (aim for one screen; at most 3 short sections plus the table):
  1. **One-line headline:** the single best idea today, or "No strong ideas today".
  2. **Table**, sorted Buy first, then the closest-to-Buy names, then long shots. Columns:
     - **Stock:** ticker linked to `https://finance.yahoo.com/quote/<TICKER>`, plus the company name.
     - **Price.**
     - **What's coming:** plain words and date.
     - **Call:** Buy / Hold (buy under $X) / Sell / Long shot.
     - **If it works:** the % move and its chance, written out in full (for example, "+32% · 78% chance"), never a bare bracketed number.
     - **If it fails:** the % move and its chance, in the same format (for example, "−48% · 22% chance").
     - When the two chances don't add up to 100%, add a short note under the table saying the rest is in-between outcomes.
     - **Source:** a link to the primary filing or news item.

     At most about 8 rows.
  3. **Why:** one short line per Buy or near-Buy name.
  4. **Key dates:** the next 2–3 weeks, one line each.
  5. **Changes since yesterday:** new, removed, call changes, and results of past calls once events resolve, as one line each.
  6. **Footer:** a link to the full report on GitHub, plus "Not investment advice; risky events can lose a large part of the money put in."
- **Prices:** say how fresh they are (for example, "prices: Oct 26 close" or "pre-market 7:15 ET").

## Ratings and predictions (added 2026-10-26 at the owner's request)

Every researched name gets a **Strong Buy / Buy / Hold / Sell / Strong Sell** rating. The rating is separate from the 0–100 research-priority score:

- the **score** measures how strong the catalyst evidence is;
- the **rating** measures risk and reward at today's price.

1. **Scenarios.** Write 2–4 scenarios over a 6-month horizon (or to the next decisive event). Give each a probability and a price target. The probabilities must sum to 1.
2. **Anchor the probabilities.** Use two references:
   - **Base rates:** about one-third of press-reported takeover rumours become an announced deal within 12 months (Ahern & Sosyura, 2015); announced definitive deals complete about 90% or more of the time; activist-13D targets earn about +7% abnormal return around filing, concentrated in targets later sold.
   - **The market-implied probability:** (price − no-deal price) / (deal price − no-deal price).
   - Depart from the market-implied probability by more than about 15 percentage points only with specific, cited evidence.
3. **Compute the rating.** Run `python3 -I scripts/precatalyst.py rate --price P --scenario "label:prob:target" ... --confidence {low,medium,medium-high,high} [--capped]`. The bands are:
   - **Strong Buy:** expected return at least +20%, provided no scenario with 15%+ probability loses more than 15%, and confidence is medium-high or better.
   - **Buy:** at least +8%.
   - **Hold:** between −5% and +8%.
   - **Sell:** −5% or worse.
   - **Strong Sell:** −15% or worse (needs at least medium confidence).
   - Use `--capped` for OTC, illiquid or heavy-dilution names, which caps them at Buy/Sell.
   - The tool also prints upside potential, P(gain ≥ 25%) and P(loss ≥ 25%). Report all three for short-horizon names.
   - Also report the price at which the rating would change.
4. **Realistic range.** `python3 -I scripts/precatalyst.py snapshot TICKER` gives a 3-month 80% band from 1-year realized volatility. Do not use it for announced-deal names; use the deal and break scenarios instead.
5. **Log predictions** in `candidate_log.csv`: rating, expected return, a precisely defined event with probability and deadline, and the 80% range with its date. Each run, run `python3 -I scripts/precatalyst.py update-log` to fill in returns and excess returns at 1, 5, 20 and 60 trading days (versus SPY for US names, XIU.TO for Canadian ones). When an event deadline passes, record `event_outcome` (1/0).
6. **Calibration.** When there are 10 or more resolved events, report the Brier score and the hit rate of the 80% ranges. If the ranges hit less than about 70% of the time, widen them. Until there are 30 or more resolved predictions, say plainly that the ratings are uncalibrated. Never claim an edge without that evidence.
7. **Not rated.** Leave a name unrated rather than guess when there was no scenario or valuation work.

## Runbook (data access that worked from the cloud environment, 2026-10-26)

- **EDGAR current feed:**
  - URL: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=SCHEDULE%2013D&count=40&output=atom`. Since 2024 the form type is `SCHEDULE 13D`, not `SC 13D`.
  - Send a descriptive `User-Agent` header with a contact address.
- **EDGAR full-text search:**
  - URL: `https://efts.sec.gov/LATEST/search-index?q="<phrase>"&forms=8-K,6-K&dateRange=custom&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD`.
  - Useful phrases: "strategic alternatives", "agreement and plan of merger", "special committee", "non-binding proposal".
- **13D Item 4 text:** `https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/primary_doc.xml`. Read the `transactionPurpose` and `percentOfClass` tags.
- **Company filings and share counts:**
  - `https://data.sec.gov/submissions/CIK##########.json`
  - `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/dei/EntityCommonStockSharesOutstanding.json`
- **Prices and volume:**
  - Price history: `https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?interval=1d&range=3mo`. TSX tickers use `.TO`; TSXV tickers use `.V`.
  - Screeners: `https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers|most_actives|small_cap_gainers`.
  - Ticker news: `https://query1.finance.yahoo.com/v1/finance/search?q=<TICKER>&newsCount=6`.
  - The `v7/quote` endpoint is **not** accessible (unauthorized).
- **Canadian M&A releases:** `https://www.newswire.ca/news-releases/financial-services-latest-news/acquisitions-mergers-and-takeovers-list/`.
- **Insider cluster buys (secondary source):** `http://openinsider.com/latest-cluster-buys`.
- **Known gaps:**
  - SEDAR+ and SEDI have no direct programmatic access.
  - There is no short-interest or options-flow feed.
  - Paywalled outlets (WSJ, Bloomberg, The Information, Semafor) can only be cited through secondary coverage.
  - The Yahoo `quoteSummary` endpoint (analyst estimates, short interest) and options chains are blocked; use realized volatility and SEC XBRL instead.
- **Fundamentals:** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`. Take revenue, operating income, D&A, operating cash flow and capex as trailing 12 months (latest fiscal year + current year-to-date − prior year-to-date), and cash and debt at the latest balance-sheet date.
- **Email:** the Gmail connector was connected on 2026-10-26. Send the report to nepollack@gmail.com as an HTML email with the subject line above, and confirm only when `send_message` returns a message id.
