#!/usr/bin/env python3
"""Backfill historical TWSE T86 foreign/trust/dealer net shares for existing history dates.
Only overwrite with validated numeric data; preserve all OHLC and other fields.
"""
import json, time, urllib.request
from datetime import datetime, timezone, timedelta

with open("history.json", encoding="utf-8") as f:
    history = json.load(f)
cutoff=(datetime.now(timezone(timedelta(hours=8)))-timedelta(days=48)).strftime("%Y-%m-%d")
dates=[d for d in sorted(history) if d>=cutoff]
headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
def field_index(fields, *needles):
    for i,f in enumerate(fields):
        if any(needle in f for needle in needles):return i
    return None
def number(value):
    try:return str(int(str(value).replace(",","").replace("+","").strip()))
    except (ValueError,TypeError):return None
changed=0; fetched=0; failures=[]
for day in dates:
    stocks=history[day].get("stocks",{})
    if not stocks:continue
    # Historical T86 accepts a date=YYYYMMDD query parameter.
    url=("https://www.twse.com.tw/rwd/zh/fund/T86?date="+day.replace("-","")+
         "&selectType=ALL&response=json")
    try:
        req=urllib.request.Request(url,headers=headers)
        with urllib.request.urlopen(req,timeout=30) as response:
            obj=json.load(response)
        if obj.get("stat")!="OK" or not obj.get("data"):
            failures.append(day+": empty or non-OK");continue
        reported=str(obj.get("date","")).replace("/","").replace("-","")
        if reported and reported!=day.replace("-",""):
            failures.append(day+": date mismatch "+reported);continue
        fields=obj.get("fields",[])
        code_i=field_index(fields,"證券代號")
        foreign_i=field_index(fields,"外陸資買賣超股數","外資及陸資買賣超股數")
        trust_i=field_index(fields,"投信買賣超股數")
        dealer_i=field_index(fields,"自營商買賣超股數")
        if code_i is None or foreign_i is None or trust_i is None:
            failures.append(day+": missing columns");continue
        fetched+=1
        for row in obj["data"]:
            if len(row)<=max(code_i,foreign_i,trust_i):continue
            code=str(row[code_i]).strip()
            if code not in stocks:continue
            foreign,trust=number(row[foreign_i]),number(row[trust_i])
            if foreign is None or trust is None:continue
            stocks[code]["foreign"]=foreign
            stocks[code]["trust"]=trust
            if dealer_i is not None and dealer_i<len(row):
                dealer=number(row[dealer_i])
                if dealer is not None:stocks[code]["dealer"]=dealer
            changed+=1
    except Exception as e:
        failures.append(day+": "+str(e))
    time.sleep(0.35)
with open("history.json","w",encoding="utf-8") as f:
    json.dump(history,f,ensure_ascii=False,indent=2)
print(f"INSTITUTION BACKFILL: dates={len(dates)} fetched={fetched} stock_rows={changed} failures={len(failures)}")
for x in failures[:15]:print("WARNING:",x)
if not fetched:
    print("WARNING: No verified historical institutional data; existing data retained.")
