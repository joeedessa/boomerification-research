#!/usr/bin/env python3
"""Reference-data refresh for the Boomerification dashboard.

The market robot (fetch_market.py) moves prices. This one moves the *facts the
thesis rests on* — population, spending, participation, wealth shares — and it
exists because those were originally entered from memory and a dashboard that
cannot re-derive its own premises rots quietly.

Writes data/reference.json:
  - population   : US resident population by age band, Census 2023 National
                   Population Projections (main series), 2022-2050
  - spending     : average annual expenditures by age of reference person and
                   category, BLS Consumer Expenditure Survey (API)
  - participation: labour force participation rate, 65+, BLS CPS (API)
  - wealth       : share of household net worth by generation and by age band,
                   Federal Reserve Distributional Financial Accounts

Every block carries its source, citation and retrieval date. Anything that fails
to fetch leaves the previous block untouched rather than writing a hole — same
failure policy as the market robot.

These series move annually or quarterly, not nightly. Weekly is generous.
"""
import io, json, os, re, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT = os.path.join(ROOT, 'reference.json')
UA = {'User-Agent': 'boomerification-research/1.0 (+https://github.com/joeedessa/boomerification-research)'}

CENSUS_T3 = ('https://www2.census.gov/programs-surveys/popproj/tables/2023/'
             '2023-summary-tables/np2023-t3.xlsx')
DFA_ZIP = 'https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip'
BLS_API = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'

# Bands are defined once here and everywhere else in the dashboard refers to them.
BANDS = {
    'pre':    ['55 to 59 years', '60 to 64 years'],
    'gogo':   ['65 to 69 years', '70 to 74 years'],
    'slowgo': ['75 to 79 years', '80 to 84 years'],
    'nogo':   ['85 to 89 years', '90 to 94 years', '95 to 99 years', '100 years and over'],
}
PROJ_YEARS = [2022, 2025, 2030, 2035, 2040, 2045, 2050]

# CEX: CXU<item>LB04<nn>M. The nn codes are age-of-reference-person brackets.
CEX_AGES = {'0405': '45-54', '0406': '55-64', '0408': '65-74', '0409': '75+'}
CEX_CATS = {'TOTALEXP': 'Total expenditures', 'HEALTH': 'Healthcare',
            'ENTRTAIN': 'Entertainment', 'TRANS': 'Transportation'}
PARTICIPATION_65 = 'LNU01300097'   # Labour force participation rate, 65 years and over, NSA


def get(url, timeout=120):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def bls(series, startyear, endyear):
    body = json.dumps({'seriesid': series, 'startyear': str(startyear),
                       'endyear': str(endyear)}).encode()
    req = urllib.request.Request(BLS_API, data=body,
                                 headers={'Content-Type': 'application/json', **UA})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if r.get('status') != 'REQUEST_SUCCEEDED':
        raise RuntimeError(f"BLS: {r.get('status')} {r.get('message')}")
    return r['Results']['series']


def census_population():
    """Parse the Census projections workbook with the stdlib — no pandas, no openpyxl,
    because this has to run in a bare Actions container."""
    NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    z = zipfile.ZipFile(io.BytesIO(get(CENSUS_T3)))
    shared = [''.join(t.text or '' for t in si.iter(NS + 't'))
              for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')]
    root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    cols = dict(zip('BCDEFGHI', [2022, 2025, 2030, 2035, 2040, 2045, 2050, 2055]))
    rows = {}
    for row in root.iter(NS + 'row'):
        cells = {}
        for c in row.findall(NS + 'c'):
            v = c.find(NS + 'v')
            if v is None:
                continue
            col = re.match(r'[A-Z]+', c.get('r')).group(0)
            cells[col] = shared[int(v.text)] if c.get('t') == 's' else v.text
        label = (cells.get('A') or '').lstrip('.')
        # The workbook stacks Total / Male / Female panels; first occurrence is Total.
        if 'years' in label and 'B' in cells and label not in rows:
            rows[label] = {y: float(cells[col]) for col, y in cols.items() if col in cells}
    missing = [k for ks in BANDS.values() for k in ks if k not in rows]
    if missing:
        raise RuntimeError(f'Census table shape changed — missing rows: {missing}')
    series = {b: [round(sum(rows[k][y] for k in ks) / 1000, 1) for y in PROJ_YEARS]
              for b, ks in BANDS.items()}
    series['total65plus'] = [round(sum(series[b][i] for b in ('gogo', 'slowgo', 'nogo')), 1)
                             for i in range(len(PROJ_YEARS))]
    return {
        'years': PROJ_YEARS, 'units': 'millions, resident population as of July 1',
        'series': series,
        'source': 'US Census Bureau, 2023 National Population Projections, Main Series, Table 3',
        'url': CENSUS_T3,
        'vintage': '2023 (released November 2023; 2022 is the base estimate)',
    }


def cex_spending():
    ids = [f'CXU{c}LB{a}M' for c in CEX_CATS for a in CEX_AGES]
    out, year = {}, None
    for s in bls(ids, 2024, 2024):
        d = s.get('data') or []
        if not d:
            continue
        sid = s['seriesID']
        cat = sid[3:sid.index('LB')]
        age = sid[sid.index('LB') + 2:-1]
        out.setdefault(CEX_CATS[cat], {})[CEX_AGES[age]] = float(d[0]['value'])
        year = d[0]['year']
    if 'Total expenditures' not in out:
        raise RuntimeError('CEX: total expenditures missing')
    tot = out['Total expenditures']
    base = tot.get('55-64')
    return {
        'year': year, 'units': 'USD, average annual expenditures per consumer unit',
        'by_category': out,
        'index_vs_55_64': {a: round(100 * v / base, 1) for a, v in tot.items()},
        'health_share_pct': {a: round(100 * out['Healthcare'][a] / tot[a], 1)
                             for a in tot if a in out.get('Healthcare', {})},
        'source': 'BLS Consumer Expenditure Survey, age of reference person',
        'url': 'https://www.bls.gov/cex/',
    }


def participation():
    s = bls([PARTICIPATION_65], 2019, 2026)[0]
    d = [x for x in s.get('data', []) if x['value'] not in ('-', '')]
    if not d:
        raise RuntimeError('CPS: no participation data')
    by_year = {}
    for x in d:
        if x['period'].startswith('M') and x['period'] != 'M13':
            by_year.setdefault(x['year'], []).append(float(x['value']))
    annual = {y: round(sum(v) / len(v), 1) for y, v in sorted(by_year.items())}
    peak_year = max(annual, key=annual.get)
    return {
        'series_id': PARTICIPATION_65,
        'latest': {'period': f"{d[0]['periodName']} {d[0]['year']}", 'value': float(d[0]['value'])},
        'annual_average': annual,
        'peak': {'year': peak_year, 'value': annual[peak_year]},
        'source': 'BLS Current Population Survey — labour force participation rate, 65 years and over (NSA)',
        'url': 'https://www.bls.gov/cps/',
    }


def dfa_wealth():
    import csv
    z = zipfile.ZipFile(io.BytesIO(get(DFA_ZIP)))
    out = {}
    for name, key in (('dfa-generation-shares.csv', 'by_generation'),
                      ('dfa-age-shares.csv', 'by_age')):
        rows = list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
        latest = rows[-1]['Date']
        out[key] = {r['Category']: {
            'net_worth': float(r['Net worth']),
            'equities': float(r['Corporate equities and mutual fund shares']),
            'real_estate': float(r['Real estate']),
        } for r in rows if r['Date'] == latest}
        out['period'] = latest
        if key == 'by_generation':
            hist = [(r['Date'], float(r['Net worth'])) for r in rows if r['Category'] == 'BabyBoom']
            peak = max(hist, key=lambda x: x[1])
            out['boomer_net_worth_peak'] = {'period': peak[0], 'value': peak[1]}
    age = out['by_age']
    out['share_55plus'] = round(sum(age[k]['net_worth'] for k in age
                                    if k in ('age55to69', 'age70plus')), 1)
    out['source'] = 'Federal Reserve Distributional Financial Accounts (Z.1)'
    out['url'] = 'https://www.federalreserve.gov/releases/z1/dataviz/dfa/'
    return out


def main():
    prev = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            prev = json.load(f)

    blocks = {'population': census_population, 'spending': cex_spending,
              'participation': participation, 'wealth': dfa_wealth}
    out, failed = {}, []
    for name, fn in blocks.items():
        try:
            out[name] = fn()
            out[name]['retrieved'] = datetime.now(timezone.utc).date().isoformat()
            print(f'{name}: ok')
        except Exception as e:
            print(f'{name}: FAILED — {e}', file=sys.stderr)
            failed.append(name)
            if name in prev:
                out[name] = prev[name]          # keep the last good copy
                print(f'{name}: kept previous snapshot from {prev[name].get("retrieved")}')

    if len(failed) == len(blocks):
        print('FATAL: every block failed — leaving reference.json untouched', file=sys.stderr)
        sys.exit(1)

    out['_meta'] = {
        'description': 'Machine-sourced reference data — the facts the thesis rests on, '
                       'pulled from primary sources rather than entered by hand.',
        'as_of': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'failed_blocks': failed,
        'note': 'Refreshed weekly by .github/workflows/refresh-reference.yml. These series move '
                'annually or quarterly; a stale block keeps its previous values and its own '
                'retrieved date rather than writing a hole.',
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1)
    print(f'reference.json written ({len(blocks) - len(failed)}/{len(blocks)} blocks fresh)')


if __name__ == '__main__':
    main()
