# Daily Pre-Catalyst Stock Scanner

This folder holds the daily pre-catalyst research reports (`YYYY-MM-DD.md`) and the historical candidate log (`candidate_log.csv`).

## Mandate (summary of the owner's standing instructions)

- **Schedule:** Run every US/Canadian trading day (Mon–Fri, excluding NYSE/TSX holidays).
- **Delivery:** Target 7:30–8:00 a.m. America/Toronto. Email only through an authorized, connected integration, and confirm delivery only when the email system reports success.
- **Universe:** NYSE, Nasdaq, TSX and TSX-V common stocks, about US$50M–US$10B market cap, with exceptions flagged.
  - Flag illiquidity, low float, dilution, OTC status and extreme volatility.
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
  - **No email connector was connected as of 2026-10-26.**
