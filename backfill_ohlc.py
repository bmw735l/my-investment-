#!/usr/bin/env python3
"""Backfill at least one month of TWSE OHLCV without erasing institutional history."""
import json, time, urllib.request
from datetime import datetime, timedelta, timezone

HISTORY = "history.json"
with open(HISTORY, encoding="utf-8") as f:
    history = json.load(f)
with open("stocks.json", encoding="utf-8") as f:
    latest = json.load(f)

# Keep the existing radar universe, including symbols absent from today's snapshot.
codes = set(latest.get("stocks", {}))
for day in history.values():
    codes.update(day.get("stocks", {}))
codes = sorted(codes)
now = datetime.now(timezone(timedelta(hours=8)))
start = now - timedelta(days=48)  # >= one calendar month, ~30-34 trading days
months = set()
dt = start.replace(day=1)
while dt <= now:
    months.add(dt.strftime("%Y%m01"))
    dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)

def clean(x):
    return str(x).replace(",", "").strip()

def valid(x):
    try:
        return float(clean(x)) > 0
    except (ValueError, TypeError):
        return False

def load_month(code, month):
    url = ("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
           f"?date={month}&stockNo={code}&response=json")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                obj = json.load(resp)
            if obj.get("stat") == "OK":
                return obj.get("data", [])
            return []
        except Exception as exc:
            if attempt == 2:
                print(f"WARN {code} {month}: {exc}")
            time.sleep(1.5*(attempt+1))
    return []

updated = 0
for code in codes:
    # If the last month is already populated, avoid repeat requests.
    count = sum(
        1 for date, day in history.items()
        if date >= start.strftime("%Y-%m-%d") and
        valid(day.get("stocks", {}).get(code, {}).get("high")) and
        valid(day.get("stocks", {}).get(code, {}).get("low"))
    )
    if count >= 20:
        continue
    for month in sorted(months):
        for row in load_month(code, month):
            if len(row) < 8 or not all(valid(row[i]) for i in (3,4,5,6)):
                continue
            try:
                y,m,d = (int(x) for x in row[0].strip().split("/"))
                date = f"{y+1911:04d}-{m:02d}-{d:02d}"
            except (ValueError, IndexError):
                continue
            if date < start.strftime("%Y-%m-%d") or date > now.strftime("%Y-%m-%d"):
                continue
            day = history.setdefault(date, {"trade_date": date, "stocks": {}})
            stock = day.setdefault("stocks", {}).setdefault(code, {})
            # Preserve original institution data, user data, and existing price.
            for key, idx in (("open",3),("high",4),("low",5)):
                stock[key] = clean(row[idx])
            if not valid(stock.get("price")):
                stock["price"] = clean(row[6])
            if not valid(stock.get("volume")) and valid(row[1]):
                stock["volume"] = clean(row[1])
            if "name" not in stock and code in latest.get("stocks", {}):
                stock["name"] = latest["stocks"][code].get("name",code)
            updated += 1
        time.sleep(0.4)
# Do not remove older original records. Keep at least 60 trading dates.
if len(history) > 90:
    for date in sorted(history)[:-90]:
        del history[date]
with open(HISTORY, "w", encoding="utf-8") as f:
    json.dump(dict(sorted(history.items())), f, ensure_ascii=False, indent=2)
covered = sum(1 for d,v in history.items() if valid(v.get("stocks",{}).get("2408",{}).get("high")))
print(f"BACKFILL: codes={len(codes)}, updated_rows={updated}, dates={len(history)}, 2408_OHLC_days={covered}")
