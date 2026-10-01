"""TDCC weekly ownership snapshots; no scoring or daily trade inference."""
import csv
import io
import json
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

SOURCE = 'https://opendata.tdcc.com.tw/getOD.ashx?id=1-5'
OUTPUT = Path('ownership.json')

def parse_snapshot(text, wanted):
    grouped = {}
    for row in csv.DictReader(io.StringIO(text.lstrip('\ufeff'))):
        code = row['證券代號'].strip()
        if code not in wanted:
            continue
        date = row['資料日期'].strip()
        level = int(row['持股分級'])
        grouped.setdefault(date, {}).setdefault(code, {})[level] = {
            'people': int(row['人數'].replace(',', '')),
            'shares': int(row['股數'].replace(',', '')),
        }
    if not grouped:
        raise ValueError('TDCC returned no tracked stocks')
    date = max(grouped)
    datetime.strptime(date, '%Y%m%d')
    stocks = {}
    for code in wanted:
        levels = grouped[date].get(code, {})
        if not all(level in levels for level in [12, 13, 14, 15, 17]):
            raise ValueError(f'{code}: incomplete ownership data')
        total = levels[17]['shares']
        if total <= 0:
            raise ValueError(f'{code}: invalid total')
        shares400 = sum(levels[level]['shares'] for level in [12, 13, 14, 15])
        shares1000 = levels[15]['shares']
        stocks[code] = {
            'over400_pct': round(shares400 / total * 100, 4),
            'over1000_pct': round(shares1000 / total * 100, 4),
            'over1000_people': levels[15]['people'],
            'total_people': levels[17]['people'],
        }
    return f'{date[:4]}-{date[4:6]}-{date[6:]}', stocks

def main():
    wanted = set(re.findall(r'"(\d{4})":\s*\{', Path('index.html').read_text()))
    wanted.update(['2408', '2308', '2317'])
    for record in json.loads(Path('pk.json').read_text()).get('records', []):
        for role in ['user', 'partner', 'benchmark']:
            code = record.get(role, {}).get('code')
            if code:
                wanted.add(code)
    if os.environ.get('TDCC_INPUT'):
        text = Path(os.environ['TDCC_INPUT']).read_text(encoding='utf-8-sig')
    else:
        request = urllib.request.Request(SOURCE, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode('utf-8-sig')
    date, stocks = parse_snapshot(text, wanted)
    prior = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'weeks': {}}
    weeks = prior.get('weeks', {})
    if weeks and date < max(weeks):
        raise ValueError('Refusing older TDCC snapshot')
    weeks[date] = {'stocks': stocks}
    weeks = {key: weeks[key] for key in sorted(weeks)[-52:]}
    output = {'source': SOURCE, 'updated': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='minutes'),
              'latest_date': date, 'weeks': weeks}
    temp = OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    temp.replace(OUTPUT)
    print(f'TDCC {date}: {len(stocks)} stocks, {len(weeks)} weekly snapshots')

if __name__ == '__main__':
    main()
