# Daily Pre-Catalyst Stock Scanner

**Run it on your own computer:** see [`LOCAL_APP.md`](../../LOCAL_APP.md). There, `scripts/morning_app.py` schedules the weekday run, starts Claude Code for research using `daily_prompt.md`, and sends the email through Gmail.

This folder holds the daily pre-catalyst research reports (`YYYY-MM-DD.md`) and the historical candidate log (`candidate_log.csv`).

## Mandate (summary of the owner's standing instructions)

- **Schedule:** Run every Canadian trading day (Mon–Fri, excluding TSX holidays). US-only holidays still get an email.
- **Delivery:** Target 7:30–8:00 a.m. America/Toronto. Email only through an authorized, connected integration, and confirm delivery only when the email system reports success.
- **Universe: Canadian-dollar listings only (owner's instruction, 2026-10-30).** The owner buys through Wealthsimple in Canadian dollars and loses money converting to US dollars. See "Canadian dollars only" below.
  - Recommend only stocks that trade in C$ on the TSX, TSX-V, CSE or Cboe Canada, including CDRs (the Canadian versions of large US stocks).
  - A US-listed company qualifies only through its Canadian line: interlisted shares (ACB.TO for Aurora) or a CDR (AAPL.TO for Apple). Quote, rate and track it on that line, in C$.
  - Never recommend, rate or track a US-only listing, and don't put US-only ideas in the email.
  - Exclude TSX lines quoted in US dollars (symbols ending in `.U`).
  - Flag illiquidity, low float, dilution, extreme volatility and CSE-only listings (the CSE has the lightest listing rules).
- **Owner's priority (clarified 2026-10-26):** the *highest potential return in a short time*, and **small and micro-caps are welcome**.
  - Every report includes a **small-cap, short-horizon section** that scans for dated catalysts in the next 1–60 days at Canadian-listed companies. The core is:
    - takeover bids and plans of arrangement, including hostile bids and competing offers;
    - strategic reviews and sale processes;
    - early warning reports (a holder crossing 10%) and activist campaigns;
    - substantial issuer bids (company buyback offers) and Dutch auctions;
    - mining results: drill results, resource estimates, PEA/PFS/feasibility studies, permits, first production;
    - FDA, Health Canada and trial readouts at Canadian-listed drug and device companies;
    - contract awards;
    - earnings at heavily shorted names;
    - S&P/TSX index changes and TSX-V graduations to the TSX.
  - **Practical floor:** market cap of at least C$25M, price of at least C$0.50, and 20-day average daily traded value of at least C$250K. Names below the floor can be mentioned but are flagged and `--capped`. The C$0.50 price floor is lower than the old US$1 because many real Canadian small caps trade under C$1.
  - **Ranking:** by expected return. Each name also shows its **upside potential** (best-scenario return), P(gain ≥ 25%) and P(loss ≥ 25%), so the highest-potential lottery tickets are visible but are not confused with good bets.
  - **Binary events:** state plainly when the most likely outcome is a large loss.
  - **Sizing:** never recommend position sizes. Note "binary — size accordingly".
- **Catalyst categories:**
  - M&A
  - SEDAR+ and SEDI filings (material change reports, take-over bid circulars, arrangement circulars, early warning reports, insider trades), plus SEC filings for interlisted companies (6-K, 40-F, 8-K, 13D)
  - activism
  - commercial wins
  - earnings and fundamentals
  - regulatory and legal
  - market anomalies (leads only)
  - restructuring
- **Sources, in priority order:**
  1. SEDAR+ and SEDI (and EDGAR for interlisted companies)
  2. issuer releases (newswire.ca, GlobeNewswire, Newsfile, Accesswire, company sites)
  3. exchanges (TSX/TSX-V bulletins, halts, index notices)
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

## Canadian dollars only (owner's instruction, 2026-10-30)

The owner buys through Wealthsimple and wants to avoid the US-dollar conversion. Every pick must be buyable in C$.

**What counts:**

| Listing | Example | Notes |
|---|---|---|
| TSX (`.TO`) | `WCP.TO` | The main board. |
| TSX-V (`.V`) | `LUCA.V` | Venture exchange: small caps, juniors and explorers. |
| CSE (`.CN`) | `SNDL.CN` | Lightest listing rules; flag liquidity and dilution. |
| Cboe Canada (`.NE`) | `SHOP.NE` | Also trades TSX-listed shares, and lists CDRs. |
| Interlisted shares | `ACB.TO` for Nasdaq `ACB` | The same shares as the US line, in C$. Use the Canadian line. |
| CDR | `AAPL.TO`, `MSFT.NE` | A Canadian version of one of about 150 large US companies. The TSX lists them as "CDR (CAD Hedged)", so the return tracks the US stock without the exchange-rate swing. They don't exist for US small caps. |

**How to check a US idea:** run `cad-listing TICKER`. It prints the C$ lines (interlisted shares first, then hedged CDRs, then other CDRs) or "no Canadian-dollar listing found (US only)". If there's none, drop the idea. Don't mention it in the email.

**Daily Canadian scans** (US small-cap scans no longer apply):
1. **`ca-news --since <last email>`.** Lists press releases from the newswire.ca deals, public-company and mining lists that carry a TSX, TSX-V or CSE ticker. It shows the latest price and move, and sorts them by type: takeover, asset sale, review, big holder, buyback, drug/medical, mining result, other, financing.
   - Read the takeover, review, big-holder and buyback items first.
   - Check terms against the price: "room left vs. terms" or "already priced in".
   - The newswire.ca lists don't include GlobeNewswire or Newsfile releases, so also run a web search for "TSX-V" or "TSXV" plus "arrangement agreement", "take-over bid", "strategic review" and "drill results" over the last day.
2. **`ca-movers`.** The biggest TSX and TSX-V moves of the latest session (default: at least 8%, C$250K traded, price C$0.50+). It shows volume against the 20-day average and the latest Yahoo headline.
   - A big move with heavy volume and no headline is a lead to research, not a pick.
   - Use `--cdrs` to include CDRs.
3. **US catalysts** at large US companies with a CDR can still be used: check with `cad-listing`, and rate on the CDR's C$ price.

**Canadian deal mechanics** (use when writing scenarios):
- **Plan of arrangement:** a friendly deal that needs a two-thirds shareholder vote and court approval. It often closes in 2–4 months, longer when regulators must approve.
- **Take-over bid:** must stay open at least 105 days (the target's board can shorten this to 35). It needs more than 50% of the shares not held by the bidder to be tendered, and is then extended 10 days.
- **Early warning report:** required when a holder crosses 10% (5% while a take-over bid is outstanding). A news release must come out by the next trading day's open.
- **Substantial issuer bid (SIB):** the Canadian term for a company's buyback offer. A normal course issuer bid (NCIB) is an ordinary market buyback.
- SEDAR+ has no public API. Read the company's news release, which must be issued for material changes, and link the SEDAR+ profile when citing a filing.

## Clinical trial results and upcoming readouts (added 2026-10-27)

**Canadian-dollar filter (2026-10-30):** `trial-results` and `upcoming-trials` now keep only companies with Canadian-listed shares; CDRs are skipped because one trial rarely moves a company that large. Use `--us-too` only to research context, never for picks.
- `upcoming-trials` also matches trial sponsors against TSX and TSX-V company names.
- `trial-results` searches SEC filings, so it only covers interlisted companies. For TSX-only drug companies, read the `drug/medical` items from `ca-news` and search the web.

Small drug companies often move 30–90% in a day on trial results, which makes them the biggest short-term catalysts in the universe.

**Every morning:**
1. **Run `trial-results --since <last email>`.** It lists 8-K/6-K filings from drug, biotech and device companies that report trial results. It flags them positive (a "met its primary endpoint" style phrase), negative ("did not meet") or check (read it), and shows the stock's latest move.
2. **Read each notable one** with `filing-text --url ... --pattern "primary endpoint|p=|p<|placebo"`. Note:
   - the main goal, and whether it was met;
   - the size of the effect against placebo or standard care;
   - safety;
   - the next step (filing for approval, Phase 3, partnering);
   - the cash runway.
3. **Compare the result with the price move**, including pre-market.
   - Weak data plus a big jump, or strong data plus a small move or a drop, are the cases worth rating.
   - A clean positive Phase 3 in a well-funded company that has fallen on financing fears can be a Buy.
   - A positive headline on a secondary goal, after missing the main one, is usually a Sell.
4. **Rate it** with `rate --ticker` when it's actionable, and add it to the tracker. Then put the top readouts in the email's "Trial results" section.

**For upcoming readouts:**
1. **Run `upcoming-trials --days 90 --max-mcap 10`** at least on Mondays, and when the calendar looks thin. It lists Phase 2/3 trials at listed companies whose main data collection finishes within the window, smallest companies first.
   - Topline results usually come **1–3 months after** the finish date in that listing.
2. **Confirm the timing** the company itself gives with `edgar-search --q '"topline data" "fourth quarter of 2026"'` (or similar), or from its latest 10-Q.
3. **Add expected readouts to `calendar.csv`.** Use status `estimated` for timing a company has guided to; `confirmed` is only for a fixed date, such as a medical-meeting presentation.
4. **Look up the design** with `trial-info NCT…`: size, placebo control, main goal. A small, open-label or single-arm trial is weaker evidence than a large placebo-controlled one.

**Base rates for scenarios** (industry studies; treat as rough):

| Stage | Chance the trial succeeds |
|---|---|
| Phase 2 | about 30% |
| Phase 3 | about 55–60% |
| A trial of a drug whose earlier trials succeeded | higher |
| A drug already rejected once, or with a negative advisory panel | lower |

Price reactions are lopsided. A failure often costs 50–90% for a single-drug company. A success is often +20–100%, less when it's already priced in.

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
   - Most TSX and TSX-V names don't trade before 9:30 ET, so "Price" is usually yesterday's close. For interlisted names, the US line's pre-market move times the exchange rate is a guide.

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
  | plan of arrangement | agreed takeover (needs a shareholder vote and court approval) |
  | early warning report | big-holder filing |
  | substantial issuer bid | company buyback offer |
  | CDR | Canadian version of a US stock (CDR) |
  | PEA / PFS / feasibility study | mine study (early / middle / final) |

  Never use RVOL, EV/EBITDA, Brier, scenario, base rate or market-implied in the email.
- **Canadian dollars:** every price is in C$ and written "C$". Every pick is a Canadian listing. Link the Yahoo symbol with its suffix, for example `https://finance.yahoo.com/quote/ACB.TO`.
- **Layout** (aim for one screen; at most 3 short sections plus the table):
  1. **One-line headline:** the single best idea today, or "No strong ideas today".
  2. **Table**, sorted Buy first, then the closest-to-Buy names, then long shots. Columns:
     - **Stock:** ticker linked to `https://finance.yahoo.com/quote/<YAHOO SYMBOL>` (for example `WCP.TO`), plus the company name and its exchange (TSX, TSX-V, CSE, or "CDR" for the Canadian version of a US stock).
     - **Price:** in C$.
     - **What's coming:** plain words and date.
     - **Call:** Buy / Hold (buy under $X) / Sell / Long shot.
     - **If it works:** the % move and its chance, written out in full (for example, "+32% · 78% chance"), never a bare bracketed number.
     - **If it fails:** the % move and its chance, in the same format (for example, "−48% · 22% chance").
     - When the two chances don't add up to 100%, add a short note under the table saying the rest is in-between outcomes.
     - **Source:** a link to the primary filing or news item.

     At most about 8 rows.
  3. **Why:** one short line per Buy or near-Buy name.
  4. **Changes since yesterday:** new, removed, call changes, and results of past calls once events resolve, as one line each.
  4b. **Trial results** (only when there are notable ones): at most 5 lines, one per readout since the last email, for Canadian-listed drug and medical companies under about C$10B. Each line covers:
      - company and ticker;
      - what was tested, in plain words ("a pill for X");
      - whether it worked ("met its main goal" or "missed it"), with the key number;
      - the stock's move;
      - our take ("already priced in", "overreaction worth watching", or "now a Buy/Sell because…").
  5. **Tracked stocks and Calendar:** paste the HTML produced by `email-sections` (see "Tracking news, prices and estimates" below). It replaces a separate key-dates list.
  6. **Footer:** a link to the full report on GitHub, plus "Not investment advice; risky events can lose a large part of the money put in."
- **Prices:** say how fresh they are (for example, "prices: Oct 26 close" or "pre-market 7:15 ET").

## Tracking news, prices and estimates (added 2026-10-26)

Every active name in `candidate_log.csv` is followed day to day. The data lives in four files in this folder:

| File | What it holds |
|---|---|
| `candidate_log.csv` | First-seen price, first call and the `keywords` used to filter headlines. `yahoo_symbol` is the Canadian line (for example `ACB.TO`) and sets the price and currency. `sec_ticker` is the US ticker of an interlisted company, so its SEC filings are tracked; leave it blank otherwise, so that a TSX root like `HLF` doesn't pull in a US namesake's filings. |
| `news_log.csv` | News headlines and SEC filings per stock (appended, never rewritten) |
| `estimates_log.csv` | Every call and estimate over time, so changes such as "Hold → Buy" or "78% → 85%" are visible |
| `calendar.csv` | Dated upcoming events, with `status` set to confirmed, reported or estimated |

**Daily steps:**

1. **Fetch news.** Run `python3 -I scripts/precatalyst.py track-news`. It appends the last 3 days of news and filings for active names, skips routine insider and registration forms, and drops market round-ups and headlines that don't name the company.
   - Yahoo returns no news for `.TO`-style symbols, so Canadian names are searched by company name.
   - SEDAR+ filings aren't fetched (there's no public API). Material changes come out as news releases, which appear here or in `ca-news`.
2. **Read and re-rate.** Read anything material. Re-rate the stock if the news changes the odds by running `rate ... --ticker T --note "why"`, which appends to `estimates_log.csv`. Re-log a stock whenever its price has moved enough to change the estimate.
3. **Keep the calendar current.**
   - Add new dated events.
   - Fix dates the company has since confirmed. For example, Vanda's own release moved Q3 results to Oct 28.
   - Set status to `confirmed` only when the company or a regulator gave the date.
   - When an event resolves, record the outcome in `candidate_log.csv`.
4. **Build the email sections.** Run `python3 -I scripts/precatalyst.py email-sections --since <previous email date> --out <scratch>/sections.html`. Paste the HTML into the morning email under the picks table.
5. **Retire names.** When a name stops mattering (the deal closed, or the thesis is dead), set `status` to `closed` in `candidate_log.csv` with an `event_outcome`, and it drops out of tracking. Closed names also drop off the email calendar.
   - On 2026-10-30 every US-only name was closed this way when the owner switched to Canadian dollars. Aurora moved to its TSX line, `ACB.TO`.
   - `update-log` still fills in returns for closed rows, so past calls can be scored.

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
5. **Log predictions** in `candidate_log.csv`: rating, expected return, a precisely defined event with probability and deadline, and the 80% range with its date. Each run, run `python3 -I scripts/precatalyst.py update-log` to fill in returns and excess returns at 1, 5, 20 and 60 trading days (versus XIU.TO for Canadian listings; SPY only for the closed US rows). When an event deadline passes, record `event_outcome` (1/0).
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
- **Canadian sources (tested 2026-10-30):**
  - **Every TSX and TSX-V listing:** `https://www.tsx.com/json/company-directory/search/tsx/%5E*` (and `/tsxv/`). CDRs are named "… CDR (CAD Hedged)".
  - **Batch quotes:** `https://query1.finance.yahoo.com/v7/finance/spark?symbols=A.TO,B.V&range=5d&interval=1d`. At most 20 symbols per request; daily closes only, and the meta carries the latest volume.
  - **Yahoo symbols:** TSX share classes and units use a dash (`BBD-B.TO`, `REI-UN.TO`); TSX-V is `.V`, CSE is `.CN`, Cboe Canada is `.NE`.
  - **Yahoo news:** search by company name; `.TO` symbol searches return nothing. Stories are tagged with the `.TO` symbol, or the US ticker for interlisted names.
  - **Canadian lines of a US stock:** Yahoo search by company name. Exchange codes TOR, VAN, CNQ and NEO are Canadian.
  - **newswire.ca list pages** (add `?page=1&pagesize=100`): deals `…/financial-services-latest-news/acquisitions-mergers-and-takeovers-list/`, all public companies `…/news-releases/all-public-company-news/`, mining `…/energy-latest-news/mining-list/`.
  - **Not reachable from here:** newswire.ca, GlobeNewswire, Newsfile and Accesswire RSS feeds (blocked or empty), and SEDAR+.
- **Insider cluster buys (secondary source):** `http://openinsider.com/latest-cluster-buys`.
- **Known gaps:**
  - SEDAR+ and SEDI have no direct programmatic access.
  - There is no short-interest or options-flow feed.
  - Paywalled outlets (WSJ, Bloomberg, The Information, Semafor) can only be cited through secondary coverage.
  - The Yahoo `quoteSummary` endpoint (analyst estimates, short interest) and options chains are blocked; use realized volatility and SEC XBRL instead.
- **Fundamentals:** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`. Take revenue, operating income, D&A, operating cash flow and capex as trailing 12 months (latest fiscal year + current year-to-date − prior year-to-date), and cash and debt at the latest balance-sheet date.
- **Email:** the Gmail connector was connected on 2026-10-26. Send the report to nepollack@gmail.com as an HTML email with the subject line above, and confirm only when `send_message` returns a message id.
