#!/usr/bin/env python3
"""Best-effort verified V4 market panel data; missing values remain null."""
import json,datetime,urllib.request,urllib.parse,time,os
from zoneinfo import ZoneInfo
now=datetime.datetime.now(ZoneInfo("Asia/Taipei"))
today=now.date()
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=18) as r:return json.load(r)
def num(x):
 try:return float(str(x).replace(",","").replace("+","").strip())
 except:return None
def twse_day(date):
 d=date.strftime("%Y%m%d")
 try:
  j=get("https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date="+d)
  rows=j.get("data",[])
  for row in reversed(rows):
   if len(row)<5:continue
   date_str=str(row[0])
   if date_str.split("/")[-1].lstrip("0")!=str(date.day) or date_str.split("/")[1].lstrip("0")!=str(date.month):continue
   close=num(row[4]);change=num(row[5]) if len(row)>5 else None
   if close is not None and change is not None:
    return {"date":date.isoformat(),"close":close,"change":change,"pct":round(100*change/(close-change),3) if close!=change else None}
 except Exception as e:print("TWSE index:",e)
 return None
def institutions(date):
 try:
  j=get("https://www.twse.com.tw/fund/BFI82U?response=json&dayDate="+date.strftime("%Y%m%d")+"&type=day")
  rows=j.get("data",[])
  vals={}
  for row in rows:
   if len(row)<4:continue
   name=str(row[0]);value=num(row[-1])
   if value is None:continue
   if ("外資及陸資" in name or "外資及陸資(不含外資自營商)" in name) and "自營商" not in name:vals["foreign"]=value
   elif "投信" in name:vals["trust"]=value
   elif "自營商" in name and ("合計" in name or name.strip()=="自營商"):vals["dealer"]=value
  if len(vals)==3:return {"date":date.isoformat(),**vals}
 except Exception as e:print("TWSE institution:",e)
 return None
def yahoo(symbol):
 try:
  q=urllib.parse.quote(symbol,safe="")
  j=get("https://query1.finance.yahoo.com/v8/finance/chart/"+q+"?range=5d&interval=1d")
  r=j["chart"]["result"][0];closes=[x for x in r["indicators"]["quote"][0]["close"] if x is not None]
  if len(closes)<2:return None
  return {"pct":round((closes[-1]/closes[-2]-1)*100,3),"close":round(closes[-1],3),"date":datetime.datetime.fromtimestamp(r["timestamp"][-1],ZoneInfo("America/New_York")).date().isoformat()}
 except Exception as e:print("Yahoo",symbol,e);return None
try:
 with open("market-overview.json",encoding="utf8") as f:old=json.load(f)
except:old={}
out=dict(old)
out["updated"]=now.isoformat()
for offset in range(8):
 d=today-datetime.timedelta(days=offset)
 if d.weekday()>=5:continue
 idx=twse_day(d)
 if idx:
  if not out.get("twse") or idx["date"]>=out["twse"].get("date",""):out["twse"]=idx
  break
for offset in range(8):
 d=today-datetime.timedelta(days=offset)
 if d.weekday()>=5:continue
 inst=institutions(d)
 if inst:
  if not out.get("institutions") or inst["date"]>=out["institutions"].get("date",""):out["institutions"]=inst
  break
us={}
for key,symbol in {"nasdaq":"^IXIC","sox":"^SOX","tsm":"TSM","nvda":"NVDA"}.items():
 val=yahoo(symbol)
 if val:us[key]=val
if us:
 oldus=out.get("us",{})
 for key,val in us.items():
  if not oldus.get(key) or val["date"]>=oldus[key].get("date",""):oldus[key]=val
 oldus["date"]=max((v["date"] for v in oldus.values() if isinstance(v,dict) and "date" in v),default="")
 out["us"]=oldus
with open("market-overview.json","w",encoding="utf8") as f:json.dump(out,f,ensure_ascii=False,indent=2)
print("Market overview updated",list(out))
