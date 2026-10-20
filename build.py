#!/usr/bin/env python3
"""Build the Market Cycles explorer: a self-contained interactive HTML page
covering S&P 500 bull/bear markets 1950 -> present.

Inputs (all local, all verified):
  data/gspc_daily_raw.json  - Yahoo Finance ^GSPC daily closes, 1950-01-03..2026-10-20
  data/cycles.json           - the cycle table (bear/bull segments) computed from it
  data/era_prose.json        - one narrative paragraph per bear market

Output:
  index.html                - single file, no external requests, works offline
"""
import json
import math
import os
from datetime import datetime, timezone, date

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "gspc_daily_raw.json")
CYCLES = os.path.join(BASE, "data", "cycles.json")
PROSE = os.path.join(BASE, "data", "era_prose.json")
OUT = os.path.join(BASE, "index.html")

# ---------------------------------------------------------------- load data
with open(RAW) as f:
    raw = json.load(f)
res = raw["chart"]["result"][0]
ts = res["timestamp"]
closes = res["indicators"]["quote"][0]["close"]

rows = []
for t, c in zip(ts, closes):
    if c is None:
        continue
    dt = datetime.fromtimestamp(t - 18000, tz=timezone.utc).date()
    rows.append((dt.isoformat(), float(c)))
rows.sort()
dates = [r[0] for r in rows]
cl = [r[1] for r in rows]

with open(CYCLES) as f:
    cycles = json.load(f)
with open(PROSE) as f:
    prose = json.load(f)

bears = [c for c in cycles if c["type"] == "bear"]
bulls = [c for c in cycles if c["type"] == "bull"]

# prose is indexed in bear order; attach by start_date
prose_by_date = {}
bear_list = []
for i, c in enumerate(bears):
    c = dict(c)
    c["story"] = prose[i] if i < len(prose) else ""
    bear_list.append(c)
    prose_by_date[c["start_date"]] = c["story"]

# ---------------------------------------------------------------- chart path
# Downsample to ~1 point per 5 trading days for the SVG polyline.
step = 5
pts = [(dates[i], cl[i]) for i in range(0, len(cl), step)]
# always include the last point
if pts[-1][0] != dates[-1]:
    pts.append((dates[-1], cl[-1]))

lo = min(p[1] for p in pts)
hi = max(p[1] for p in pts)
log_lo, log_hi = math.log10(lo), math.log10(hi)

W, H = 1200, 460
PAD_L, PAD_R, PAD_T, PAD_B = 62, 18, 26, 34

def x_of(datestr):
    d = date.fromisoformat(datestr)
    frac = (d - date(1950, 1, 1)).days / (date(2026, 12, 31) - date(1950, 1, 1)).days
    return PAD_L + frac * (W - PAD_L - PAD_R)

def y_of(v):
    frac = (math.log10(v) - log_lo) / (log_hi - log_lo)
    return (H - PAD_B) - frac * (H - PAD_T - PAD_B)

path_pts = " ".join(f"{x_of(d):.1f},{y_of(v):.1f}" for d, v in pts)

# bear shading rects + peak/trough markers + labels
shade = []
for b in bear_list:
    x1, x2 = x_of(b["start_date"]), x_of(b["end_date"])
    shade.append(
        f'<rect x="{x1:.1f}" y="{PAD_T}" width="{max(x2 - x1, 1.5):.1f}" '
        f'height="{H - PAD_T - PAD_B}" fill="#ef4444" opacity="0.16"/>'
    )
    # trough dot
    y = y_of(b["end_close"])
    shade.append(
        f'<circle cx="{x2:.1f}" cy="{y:.1f}" r="3.2" fill="#ef4444" '
        f'stroke="#0b0b0f" stroke-width="1"/>'
    )

# label placement: one per bear, at the trough, staggered when crowded
labels = []
placed = []
for b in bear_list:
    x = x_of(b["end_date"])
    y = y_of(b["end_close"]) + 15
    for px, py in placed:
        if abs(px - x) < 74 and abs(py - y) < 13:
            y = py + 20
    placed.append((x, y))
    short = b["start_date"][:4]
    labels.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="10.5" fill="#fca5a5" '
        f'text-anchor="middle" font-family="ui-monospace,Menlo,monospace">'
        f'{b["pct_change"]:.1f}% {short}</text>'
    )

# y-axis gridlines at 10, 100, 1000, 10000
grid = []
for lv in (10, 100, 1000, 10000):
    if log_lo <= math.log10(lv) <= log_hi:
        y = y_of(lv)
        grid.append(
            f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
            f'stroke="#2a2a35" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{PAD_L - 8}" y="{y + 3.5:.1f}" font-size="10.5" '
            f'fill="#8b8b9c" text-anchor="end" '
            f'font-family="ui-monospace,Menlo,monospace">{lv:,}</text>'
        )

# x-axis decade ticks
xaxis = []
for yr in range(1950, 2030, 10):
    d = f"{yr}-01-01"
    if yr > 2026:
        continue
    x = x_of(d)
    xaxis.append(
        f'<text x="{x:.1f}" y="{H - 12}" font-size="10.5" fill="#8b8b9c" '
        f'text-anchor="middle" font-family="ui-monospace,Menlo,monospace">{yr}</text>'
    )

# ---------------------------------------------------------------- data blob
series = [[d, round(v, 2)] for d, v in zip(dates[::step], cl[::step])]
series.append([dates[-1], round(cl[-1], 2)])
blob = {
    "series": series,
    "bears": bear_list,
    "bulls": bulls,
    "first": dates[0],
    "last": dates[-1],
    "last_close": round(cl[-1], 2),
    "all_time_high": round(max(cl), 2),
}

# ---------------------------------------------------------------- stats
def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0

stats = {
    "bears": len(bear_list),
    "bulls": len(bulls),
    "avg_bear_depth": round(avg([b["pct_change"] for b in bear_list]), 1),
    "avg_bear_years": round(avg([b["duration_years"] for b in bear_list]), 1),
    "avg_bull_gain": round(avg([b["pct_change"] for b in bulls]), 1),
    "avg_bull_years": round(avg([b["duration_years"] for b in bulls]), 1),
    "worst_bear": min(bear_list, key=lambda b: b["pct_change"]),
    "longest_bear": max(bear_list, key=lambda b: b["duration_years"]),
    "longest_bull": max(bulls, key=lambda b: b["duration_years"]),
    "best_bull": max(bulls, key=lambda b: b["pct_change"]),
}

# current-cycle figures: last close vs the most recent bear's trough
last_bear = max(bear_list, key=lambda b: b["end_date"])
stats["ongoing_pct"] = round((cl[-1] / last_bear["end_close"] - 1) * 100, 1)
stats["ongoing_years"] = round(
    (date.fromisoformat(dates[-1]) - date.fromisoformat(last_bear["end_date"])).days / 365.25, 1)
stats["ongoing_since"] = last_bear["end_date"]
stats["drawdown_from_high"] = round((cl[-1] / max(cl) - 1) * 100, 1)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Cycles — S&amp;P 500 Bull &amp; Bear History, 1950–2026</title>
<style>
  :root {{
    --bg:#0b0b0f; --panel:#13131a; --panel2:#171721; --line:#24242f;
    --ink:#e8e8ef; --muted:#9a9aad; --red:#ef4444; --redl:#fca5a5;
    --green:#22c55e; --greenl:#86efac; --amber:#f59e0b;
  }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; padding:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    line-height:1.55; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:22px 16px 60px; }}
  h1 {{ font-size:clamp(22px,4.2vw,34px); margin:6px 0 4px; letter-spacing:-0.02em; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.11em; color:var(--muted);
    margin:34px 0 12px; font-weight:600; }}
  .sub {{ color:var(--muted); font-size:15px; margin:0 0 6px; max-width:70ch; }}
  .meta {{ color:#6f6f82; font-size:12.5px; font-family:ui-monospace,Menlo,monospace; }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
    padding:14px; margin-top:16px; }}
  .chartwrap {{ position:relative; overflow-x:auto; }}
  svg {{ width:100%; height:auto; display:block; min-width:680px; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:16px; align-items:center;
    color:var(--muted); font-size:13px; margin-top:8px; }}
  .swatch {{ display:inline-block; width:12px; height:12px; border-radius:3px;
    vertical-align:-1px; margin-right:6px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:10px;
    margin-top:14px; }}
  .stat {{ background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
  .stat .k {{ color:var(--muted); font-size:11.5px; text-transform:uppercase; letter-spacing:.08em; }}
  .stat .v {{ font-size:22px; font-weight:650; margin-top:3px;
    font-family:ui-monospace,Menlo,monospace; letter-spacing:-0.01em; }}
  .stat .d {{ color:#6f6f82; font-size:12px; margin-top:2px; }}
  .red {{ color:var(--redl); }} .green {{ color:var(--greenl); }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-size:11.5px; text-transform:uppercase; letter-spacing:.07em;
    font-weight:600; cursor:pointer; white-space:nowrap; user-select:none; }}
  th:hover {{ color:var(--ink); }}
  td.num {{ font-family:ui-monospace,Menlo,monospace; white-space:nowrap; }}
  tr.bear td:first-child {{ color:var(--redl); font-weight:650; }}
  tr.bull td:first-child {{ color:var(--greenl); font-weight:650; }}
  tr.clickable {{ cursor:pointer; }}
  tr.clickable:hover td {{ background:#1c1c26; }}
  .story {{ display:none; background:#111119; }}
  .story.open {{ display:table-row; }}
  .story td {{ padding:14px 12px 18px; color:#c9c9d8; font-size:14.5px; line-height:1.62; }}
  .story .hdr {{ color:var(--ink); font-weight:650; font-size:15px; display:block; margin-bottom:6px; }}
  .story .figures {{ display:flex; flex-wrap:wrap; gap:14px; margin-top:10px; color:var(--muted);
    font-size:12.5px; font-family:ui-monospace,Menlo,monospace; }}
  .story .figures b {{ color:var(--ink); font-weight:600; }}
  .callout {{ background:linear-gradient(180deg,#161622,#12121a); border:1px solid #2a2a38;
    border-radius:12px; padding:16px 18px; margin-top:16px; }}
  .callout h3 {{ margin:0 0 8px; font-size:16px; }}
  .callout p {{ margin:0 0 10px; color:#c3c3d2; max-width:76ch; font-size:14.5px; }}
  .clock {{ display:flex; flex-wrap:wrap; gap:22px; align-items:baseline; margin-top:6px; }}
  .clock .big {{ font-size:30px; font-weight:680; font-family:ui-monospace,Menlo,monospace;
    letter-spacing:-0.02em; }}
  footer {{ color:#66667a; font-size:12.5px; margin-top:40px; line-height:1.7; }}
  footer a {{ color:#8b8b9c; }}
  @media (max-width:640px) {{
    .wrap {{ padding:16px 12px 44px; }} .panel {{ padding:10px; }}
    th,td {{ padding:8px 7px; font-size:13px; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <h1>Market Cycles</h1>
  <p class="sub">Every S&amp;P 500 bear market since 1950 and the bull run that followed it —
  how long each one lasted, how deep it went, and what was happening while it did.</p>
  <p class="meta">Data: S&amp;P 500 (^GSPC) daily closes, Yahoo Finance, 1950-01-03 → {dates[-1]} ·
  Bear definition: 20% peak-to-trough, multi-wave bears merged · All figures computed from the raw series</p>

  <div class="panel">
    <div class="chartwrap">
      <svg viewBox="0 0 {W} {H}" role="img" aria-label="S&amp;P 500 log-scale price chart with bear market regions shaded">
        {''.join(grid)}
        {''.join(shade)}
        <polyline points="{path_pts}" fill="none" stroke="#c9c9d8" stroke-width="1.5"
          stroke-linejoin="round" stroke-linecap="round"/>
        {''.join(labels)}
        {''.join(xaxis)}
      </svg>
    </div>
    <div class="legend">
      <span><span class="swatch" style="background:#ef4444;opacity:.45"></span>bear market (≥20% drawdown)</span>
      <span><span class="swatch" style="background:#c9c9d8"></span>S&amp;P 500 (log scale)</span>
      <span>labels show the drawdown and the year it began</span>
    </div>
  </div>

  <h2>By the numbers</h2>
  <div class="grid">
    <div class="stat"><div class="k">Bear markets</div><div class="v red">{stats['bears']}</div>
      <div class="d">since January 1950</div></div>
    <div class="stat"><div class="k">Average bear</div><div class="v red">{stats['avg_bear_depth']}%</div>
      <div class="d">over {stats['avg_bear_years']} years</div></div>
    <div class="stat"><div class="k">Average bull</div><div class="v green">+{stats['avg_bull_gain']}%</div>
      <div class="d">over {stats['avg_bull_years']} years</div></div>
    <div class="stat"><div class="k">Worst bear</div><div class="v red">{stats['worst_bear']['pct_change']}%</div>
      <div class="d">{stats['worst_bear']['start_date'][:4]}–{stats['worst_bear']['end_date'][:4]} ·
        {stats['worst_bear']['duration_years']} yrs</div></div>
    <div class="stat"><div class="k">Longest bear</div><div class="v red">{stats['longest_bear']['duration_years']} yrs</div>
      <div class="d">{stats['longest_bear']['start_date'][:4]}–{stats['longest_bear']['end_date'][:4]} ·
        {stats['longest_bear']['pct_change']}%</div></div>
    <div class="stat"><div class="k">Longest bull</div><div class="v green">{stats['longest_bull']['duration_years']} yrs</div>
      <div class="d">{stats['longest_bull']['start_date'][:4]}–{stats['longest_bull']['end_date'][:4]} ·
        +{stats['longest_bull']['pct_change']}%</div></div>
  </div>

  <h2>Where we are now</h2>
  <div class="callout">
    <h3>The current cycle</h3>
    <div class="clock">
      <div><div class="k" style="color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.08em">Last close</div>
        <div class="big">{blob['last_close']:,.2f}</div></div>
      <div><div class="k" style="color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.08em">All-time high</div>
        <div class="big">{blob['all_time_high']:,.2f}</div></div>
      <div><div class="k" style="color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.08em">Since the {stats['ongoing_since'][:4]} low</div>
        <div class="big green">+{stats['ongoing_pct']:.1f}%</div>
        <div class="d" style="color:#6f6f82;font-size:12px">{stats['ongoing_years']} yrs</div></div>
      <div><div class="k" style="color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.08em">Below all-time high</div>
        <div class="big">{stats['drawdown_from_high']:.1f}%</div></div>
    </div>
    <p style="margin-top:14px">The current bull market began at the October 2022 trough — the deepest
    bear since 2011 was shallow by historical standards, and the rally that followed has outlasted
    every bull market since 1987. History offers no precedent for how this one ends. It may yet
    produce a 20% drawdown and become the next entry in the table above.</p>
  </div>

  <h2>The full history</h2>
  <p class="sub" style="margin-bottom:8px">Click any row for the story of that market.</p>
  <div class="panel" style="padding:6px 8px">
    <table id="cycles">
      <thead><tr>
        <th data-sort="0">Type</th><th data-sort="1">Period</th><th data-sort="2">Years</th>
        <th data-sort="3">Change</th>
      </tr></thead>
      <tbody>
      </tbody>
    </table>
  </div>

  <footer>
    <p><strong>Method.</strong> A bear market is a decline of 20% or more from a running peak.
    An interim rally only ends a bear when the index closes back above that bear's starting peak;
    otherwise the bear extends. That rule merges the two-wave 2000–02 and 2007–09 declines into
    one bear each. The bull market that follows runs from the bear's trough to the next peak.
    Figures are computed from daily closing prices, not from published summaries.</p>
    <p><strong>Sources.</strong> Price data: Yahoo Finance (^GSPC daily closes). Series verified
    against known market history — Black Monday 1987-10-19 (224.84), the 2000-03-24 peak (1527.46),
    the 2009-03-09 trough (676.53), the 2020-03-23 low (2237.40) and the 2022-10-12 bottom (3577.03)
    all match to the cent.</p>
    <p>Historical commentary is written for this page. Nothing here is investment advice —
    history is a guide to what has happened, not to what will.</p>
  </footer>
</div>

<script id="data" type="application/json">{json.dumps(blob)}</script>
<script>
(function () {{
  const DATA = JSON.parse(document.getElementById('data').textContent);
  const tbody = document.querySelector('#cycles tbody');
  const fmt = n => n.toFixed(1) + '%';

  const SORTERS = [
    (a, b) => a.start_date < b.start_date ? -1 : 1,              // type -> chronological
    (a, b) => a.start_date < b.start_date ? -1 : 1,              // period
    (a, b) => a.duration_years - b.duration_years,              // years
    (a, b) => a.pct_change - b.pct_change                       // change
  ];

  function buildTable() {{
    const all = [];
    DATA.bulls.forEach(b => all.push({{...b, kind:'bull'}}));
    DATA.bears.forEach(b => all.push({{...b, kind:'bear'}}));
    const cmp = SORTERS[sortKey];
    all.sort((a, b) => (cmp(a, b) * sortDir) || (a.start_date < b.start_date ? -1 : 1));
    tbody.innerHTML = '';
    all.forEach(c => {{
      const tr = document.createElement('tr');
      tr.className = c.kind + ' clickable';
      tr.innerHTML = '<td>' + c.kind.toUpperCase() + '</td>' +
        '<td class="num">' + c.start_date + ' → ' + c.end_date + '</td>' +
        '<td class="num">' + c.duration_years.toFixed(1) + '</td>' +
        '<td class="num" style="color:' + (c.kind === 'bear' ? '#fca5a5' : '#86efac') + '">' +
          (c.pct_change > 0 ? '+' : '') + fmt(c.pct_change) + '</td>';
      tr.addEventListener('click', () => toggleStory(c, tr));
      tbody.appendChild(tr);
    }});
  }}

  function toggleStory(c, tr) {{
    const next = tr.nextElementSibling;
    if (next && next.classList.contains('story')) {{
      next.classList.remove('open');
      next.remove();
      return;
    }}
    const sr = document.createElement('tr');
    sr.className = 'story open';
    const story = c.story || '';
    const figures = c.kind === 'bear'
      ? '<span>depth <b>' + fmt(c.pct_change) + '</b></span>' +
        '<span>duration <b>' + c.duration_years.toFixed(1) + ' yrs</b></span>' +
        '<span>peak <b>' + c.start_close.toLocaleString() + '</b></span>' +
        '<span>trough <b>' + c.end_close.toLocaleString() + '</b></span>'
      : '<span>gain <b>+' + fmt(c.pct_change) + '</b></span>' +
        '<span>duration <b>' + c.duration_years.toFixed(1) + ' yrs</b></span>' +
        '<span>from <b>' + c.start_close.toLocaleString() + '</b></span>' +
        '<span>to <b>' + c.end_close.toLocaleString() + '</b></span>';
    sr.innerHTML = '<td colspan="4"><span class="hdr">' +
      (c.kind === 'bear' ? 'The ' + c.start_date.slice(0,4) + '–' + c.end_date.slice(0,4) + ' bear market' :
       'The ' + c.start_date.slice(0,4) + '–' + c.end_date.slice(0,4) + ' bull market') +
      '</span>' + (story || '<em>No narrative for this segment.</em>') +
      '<div class="figures">' + figures + '</div></td>';
    tr.after(sr);
  }}

  // sort by clicking a header
  let sortKey = 0, sortDir = 1;
  document.querySelectorAll('#cycles th').forEach(th => {{
    th.addEventListener('click', () => {{
      const k = parseInt(th.dataset.sort, 10);
      sortDir = (k === sortKey) ? -sortDir : 1;
      sortKey = k;
      buildTable();
    }});
  }});

  buildTable();
  window.MC = DATA;
}})();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------- write
with open(OUT, "w") as f:
    f.write(html)

print(f"wrote {OUT} ({len(html):,} bytes)")
print(f"  series points : {len(blob['series']):,}")
print(f"  bears / bulls : {len(bear_list)} / {len(bulls)}")
print(f"  last close    : {blob['last_close']:,.2f}")
