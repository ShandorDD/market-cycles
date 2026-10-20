# Market Cycles

An interactive history of S&P 500 bull and bear markets from 1950 to the present.

Every bear market of 20% or more since January 1950, and the bull market that
followed it — how long each lasted, how deep it went, and what was happening in
the world while it did.

**Live site:** https://shandordd.github.io/market-cycles/

## What's in it

- Log-scale price chart, 1950–2026, with each bear market shaded and labeled
- The full cycle table — click any row for the story of that market
- Computed statistics: average bear depth and duration, average bull gain and
  duration, worst bear, longest bear, longest bull
- A "where we are now" panel: the current cycle's length and drawdown

## Method

A **bear market** is a decline of 20% or more from a running peak. An interim
rally only ends a bear when the index closes back above that bear's starting
peak; otherwise the bear simply extends. That rule merges the two-wave
2000–02 and 2007–09 declines into one bear each, matching how the market is
usually described.

The **bull market** that follows runs from the bear's trough to the next peak.

All figures are computed from daily closing prices rather than copied from
published summaries, so the table and the chart can never disagree.

## Data

S&P 500 (^GSPC) daily closes, 1950-01-03 to present, via Yahoo Finance.

The series is verified against known market history — Black Monday
(1987-10-19, 224.84), the dot-com peak (2000-03-24, 1527.46), the GFC trough
(2009-03-09, 676.53), the COVID low (2020-03-23, 2237.40) and the 2022 bottom
(2022-10-12, 3577.03) all match to the cent.

## Rebuilding

```bash
python3 build.py
```

Reads `data/gspc_daily_raw.json` (raw daily closes), `data/cycles.json` (the
computed cycle table) and `data/era_prose.json` (one narrative paragraph per
bear market), and writes a single self-contained `index.html` — no external
requests, no build tooling, works offline.

## Disclaimer

Historical commentary is written for this page. Nothing here is investment
advice — history is a guide to what has happened, not to what will.
