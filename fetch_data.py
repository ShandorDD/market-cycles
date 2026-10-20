#!/usr/bin/env python3
"""Fetch S&P 500 (^GSPC) daily closes from Yahoo Finance and save as JSON.

Writes data/gspc_daily_raw.json — the raw chart-API payload the build reads.
A fresh clone can rebuild the page with:

    python3 fetch_data.py
    python3 build.py

Yahoo rate-limits plain curl requests from some IPs (HTTP 429). If you hit
that, fetch the URL in a browser and save the response body by hand, or wait
out the limit — the endpoint accepts a normal User-Agent.
"""
import json
import os
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data", "gspc_daily_raw.json")

# 1950-01-01 .. far future, so the range always covers "to present"
PERIOD1 = -631152000
PERIOD2 = int(time.time())
URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
    f"?period1={PERIOD1}&period2={PERIOD2}&interval=1d"
)
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
    except Exception as e:
        print("fetch failed:", e)
        print("If this is a 429, Yahoo is rate-limiting this IP.")
        print("Try again later, or fetch the URL in a browser and save the")
        print("response body to", OUT)
        return 1

    data = json.loads(body)
    res = data["chart"]["result"][0]
    n = len(res.get("timestamp", []))
    if n < 10000:
        print(f"suspicious: only {n} points returned — Yahoo may have")
        print("served a condensed payload. Check before using this file.")
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(body)
    print(f"wrote {OUT}")
    print(f"  points: {n:,}")
    print(f"  first : {res['timestamp'][0]}")
    print(f"  last  : {res['timestamp'][-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
