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
  - utilisation  : per-capita Medicare utilisation, 2014-2024 trend (CMS
                   Geographic Variation PUF) plus the SNF age gradient (CMS
                   Program Statistics). This is the block that tests whether
                   care demand actually scales the way limb D assumes.
  - projections  : BLS Employment Projections — labour force EXIT rate by
                   occupation, which is the most direct free test of limb C's
                   premise that specific trades are ageing out.
  - wages        : Employment Cost Index by industry and occupation, from the
                   BLS flat files rather than the API — the API caps at 25
                   queries a day and this needs none of them. Tests limb C's
                   claim that non-tradable services wages are running hot.

Every block carries its source, citation and retrieval date. Anything that fails
to fetch leaves the previous block untouched rather than writing a hole — same
failure policy as the market robot.

These series move annually or quarterly, not nightly. Weekly is generous.
"""
import io, json, os, re, sys, time, urllib.error, urllib.request, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT = os.path.join(ROOT, 'reference.json')
UA = {'User-Agent': 'boomerification-research/1.0 (+https://github.com/joeedessa/boomerification-research)'}
# BLS rejects any User-Agent containing a URL with a 403; the contact-email form passes.
BLS_UA = {'User-Agent': 'boomerification-research/1.0 (joe.edessa@gmail.com)'}

CENSUS_T3 = ('https://www2.census.gov/programs-surveys/popproj/tables/2023/'
             '2023-summary-tables/np2023-t3.xlsx')
DFA_ZIP = 'https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip'
BLS_API = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
CMS_CATALOG = 'https://data.cms.gov/data.json'
# Medicare Geographic Variation, National/State/County — the only free series that
# gives per-capita Medicare utilisation annually over a long enough window to see
# a trend. FFS only, which is the block's central caveat.
CMS_GV_API = ('https://data.cms.gov/data-api/v1/dataset/'
              '6219697b-8f6c-4164-bed4-cd9317c58ebc/data')

# Per-1,000-beneficiary measures. Deliberately volume, not dollars: CMS
# "standardized" payments still carry annual rate updates, so dollars would
# conflate price with utilisation and the whole point here is utilisation.
GV_METRICS = {
    'IP_CVRD_STAYS_PER_1000_BENES': 'Inpatient admissions',
    'IP_CVRD_DAYS_PER_1000_BENES': 'Inpatient days',
    'ER_VISITS_PER_1000_BENES': 'ER visits',
    'SNF_CVRD_DAYS_PER_1000_BENES': 'SNF days',
    'HH_VISITS_PER_1000_BENES': 'Home health visits',
    'HOSPC_CVRD_DAYS_PER_1000_BENES': 'Hospice days',
    'IMGNG_EVNTS_PER_1000_BENES': 'Imaging events',
    'PRCDR_EVNTS_PER_1000_BENES': 'Procedures',
    'TESTS_EVNTS_PER_1000_BENES': 'Tests',
    'EM_EVNTS_PER_1000_BENES': 'E&M visits',
}
SNF_AGE_BANDS = ['55-64 Years', '65-74 Years', '75-84 Years',
                 '85-94 Years', '95 Years and Over']

# ECI, wages and salaries, current-dollar index, seasonally adjusted. Read from
# the BLS flat file: the public API caps at 25 queries a day and would make this
# block compete with the CPS and CEX pulls for the same budget.
ECI_FILE = 'https://download.bls.gov/pub/time.series/ci/ci.data.0.Current'
ECI_SERIES = {
    'CIS1020000000000I': ('All civilian', 'baseline'),
    'CIS102S000000000I': ('Service-providing (industry)', 'industry'),
    'CIS102G000000000I': ('Goods-producing (industry)', 'industry'),
    'CIS1026200000000I': ('Health care & social assistance (industry)', 'industry'),
    'CIS2022300000000I': ('Construction (industry, private)', 'industry'),
    'CIS1023000000000I': ('Manufacturing (industry)', 'industry'),
    'CIS2020000300000I': ('Service occupations', 'occupation'),
    'CIS2020000405000I': ('Construction & extraction (occupation)', 'occupation'),
    'CIS2020000430000I': ('Installation, maintenance & repair (occupation)', 'occupation'),
    'CIS2020000510000I': ('Production (occupation)', 'occupation'),
}
ECI_BASE = (2019, 'Q04')   # pre-pandemic anchor

# BLS Employment Projections, National Employment Matrix. Table 1.10 carries a
# "labor force exit rate" by occupation — BLS's own projection of who retires
# out. That is the single most direct measure of limb C's central premise, and
# it is free.
EP_FILE = 'https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx'
EP_OCCS = {
    '00-0000': ('All occupations', 'baseline'),
    '47-0000': ('Construction & extraction (all)', 'trades'),
    '47-2111': ('Electricians', 'trades'),
    '47-2152': ('Plumbers, pipefitters, steamfitters', 'trades'),
    '49-9021': ('HVAC mechanics & installers', 'trades'),
    '47-2211': ('Sheet metal workers', 'trades'),
    '47-2031': ('Carpenters', 'trades'),
    '47-1011': ('Construction first-line supervisors', 'trades'),
    '49-9041': ('Industrial machinery mechanics', 'trades'),
    '29-0000': ('Healthcare practitioners (all)', 'care-licensed'),
    '29-1141': ('Registered nurses', 'care-licensed'),
    '29-2061': ('Licensed practical nurses', 'care-licensed'),
    '31-0000': ('Healthcare support (all)', 'care-support'),
    '31-1120': ('Home health & personal care aides', 'care-support'),
    '31-1131': ('Nursing assistants', 'care-support'),
    '51-0000': ('Production (all)', 'comparator'),
}

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


def get(url, timeout=120, tries=4):
    """Fetch with backoff.

    Two BLS-specific quirks, both learned the hard way. download.bls.gov returns
    403 for any User-Agent containing a URL but accepts the contact-email form,
    so BLS hosts get their own header. And BLS returns 503 during its own
    maintenance windows often enough that a single-shot fetch will fail a
    scheduled run for no good reason — hence the retry.
    """
    hdrs = BLS_UA if 'bls.gov' in url else UA
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=hdrs), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            last = e
        if i < tries - 1:
            time.sleep(3 * (i + 1))
    raise last


def bls(series, startyear, endyear, tries=4):
    """Same retry policy as get() — the BLS API 503s during its own maintenance
    windows, and a scheduled weekly run should not fail because of one."""
    body = json.dumps({'seriesid': series, 'startyear': str(startyear),
                       'endyear': str(endyear)}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(BLS_API, data=body,
                                         headers={'Content-Type': 'application/json', **BLS_UA})
            r = json.load(urllib.request.urlopen(req, timeout=120))
            if r.get('status') != 'REQUEST_SUCCEEDED':
                raise RuntimeError(f"BLS: {r.get('status')} {r.get('message')}")
            return r['Results']['series']
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(3 * (i + 1))
    raise last


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


def _xlsx_rows(blob, sheet):
    """Minimal xlsx reader — stdlib only, so this runs in a bare Actions container."""
    NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = [''.join(t.text or '' for t in si.iter(NS + 't'))
              for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')]
    root = ET.fromstring(z.read(f'xl/worksheets/{sheet}'))
    out = []
    for row in root.iter(NS + 'row'):
        cells = []
        for c in row.findall(NS + 'c'):
            v = c.find(NS + 'v')
            cells.append('' if v is None else
                         (shared[int(v.text)] if c.get('t') == 's' else v.text))
        out.append(cells)
    return out


def utilisation():
    """Two questions, two sources.

    Trend: is per-capita Medicare utilisation rising or falling? This is the
    direct test of falsifier f3 and, as it turns out, of limb D's volume
    assumption generally.

    Gradient: does utilisation actually compound with age the way the cohort
    clock assumes? The GV PUF only splits <65 / >=65, so the age detail comes
    from CMS Program Statistics instead.
    """
    rows = json.loads(get(CMS_GV_API + '?filter[BENE_GEO_LVL]=National&size=200'))
    by = {(r['YEAR'], r['BENE_AGE_LVL']): r for r in rows}
    years = sorted({r['YEAR'] for r in rows})
    if len(years) < 5:
        raise RuntimeError(f'GV PUF returned only {len(years)} years')

    def num(y, k):
        v = (by.get((y, '>=65')) or {}).get(k)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    trend = {}
    for col, label in GV_METRICS.items():
        vals = [num(y, col) for y in years]
        if not any(vals):
            continue
        first, last = vals[0], vals[-1]
        trend[label] = {
            'values': [round(v, 1) if v is not None else None for v in vals],
            'change_pct': round((last / first - 1) * 100, 1) if first and last else None,
            'cagr_pct': round(((last / first) ** (1 / (len(years) - 1)) - 1) * 100, 2)
            if first and last else None,
        }

    context = {
        'ma_participation_pct': [round(float(by[(y, 'All')]['MA_PRTCPTN_RATE']) * 100, 1)
                                 for y in years],
        'ffs_benes_65plus_m': [round(float(by[(y, '>=65')]['BENES_OM_CNT']) / 1e6, 1)
                               for y in years],
        'avg_age': [round(float(by[(y, 'All')]['BENE_AVG_AGE']), 1) for y in years],
        'stdzd_pymt_per_capita': [round(float(by[(y, '>=65')]['TOT_MDCR_STDZD_PYMT_PC']))
                                  for y in years],
    }

    # SNF age gradient. Discover the newest year's file from the catalogue so a
    # CMS re-publish is picked up without a code change.
    gradient, grad_src = {}, None
    try:
        cat = json.loads(get(CMS_CATALOG))
        cands = []
        for ds in cat.get('dataset', []):
            if ds.get('title', '').startswith('CMS Program Statistics - Medicare Skilled Nursing'):
                for d in ds.get('distribution', []):
                    u = d.get('downloadURL') or ''
                    if u.endswith('.zip'):
                        cands.append((d.get('title', ''), u))
        cands.sort(key=lambda x: x[0], reverse=True)     # titles carry the year
        grad_src = cands[0][1]
        z = zipfile.ZipFile(io.BytesIO(get(grad_src)))
        xlsx = [n for n in z.namelist() if n.endswith('.xlsx')][0]
        # sheet3 is "by Demographic Characteristics"
        rws = _xlsx_rows(z.read(xlsx), 'sheet3.xml')
        agg = {'enrollees': 0.0, 'admits': 0.0, 'days': 0.0}
        for r in rws:
            if not r or r[0] not in SNF_AGE_BANDS:
                continue
            benes, adm, days = float(r[1]), float(r[3]), float(r[7])
            gradient[r[0]] = {'enrollees': int(benes),
                              'admits_per_1k': round(adm / benes * 1000, 1),
                              'days_per_1k': round(days / benes * 1000)}
            if r[0] in ('85-94 Years', '95 Years and Over'):
                agg['enrollees'] += benes; agg['admits'] += adm; agg['days'] += days
        if agg['enrollees']:
            gradient['85+'] = {'enrollees': int(agg['enrollees']),
                               'admits_per_1k': round(agg['admits'] / agg['enrollees'] * 1000, 1),
                               'days_per_1k': round(agg['days'] / agg['enrollees'] * 1000)}
        base = gradient.get('65-74 Years', {}).get('days_per_1k')
        if base:
            for k in gradient:
                gradient[k]['vs_65_74'] = round(gradient[k]['days_per_1k'] / base, 1)
    except Exception as e:
        print(f'utilisation: SNF age gradient failed ({e}) — trend still written', file=sys.stderr)

    return {
        'years': years,
        'population': 'Original Medicare (fee-for-service) beneficiaries aged 65+',
        'units': 'events or days per 1,000 beneficiaries per year',
        'trend': trend,
        'context': context,
        'snf_age_gradient': gradient,
        'gradient_year_note': 'Latest CMS Program Statistics SNF release; single year, not a trend',
        'caveats': [
            'FFS only. Medicare Advantage beneficiaries are excluded, and MA participation '
            'rose from 32% to 55% across this window. Healthier beneficiaries select into MA, '
            'so the residual FFS population should be getting sicker — which biases measured '
            'per-capita utilisation UP. Declines observed despite that bias are therefore '
            'understated, not overstated.',
            'Average beneficiary age rose over the window, which also biases utilisation up.',
            '2020-21 are COVID-distorted; read 2014-2019 and 2022-2024 as the clean segments.',
            'Payment-model changes are confounded with the volume trend: SNF PDPM (Oct 2019) '
            'and home health PDGM (Jan 2020) both explicitly reduced volume incentives.',
            'Excludes Medicaid-funded long-term and personal care entirely, which is the '
            'largest single category of aging-in-place spend and the core of ADUS.',
        ],
        'source': 'CMS Medicare Geographic Variation PUF (national, FFS 65+) and '
                  'CMS Program Statistics — Medicare Skilled Nursing Facility',
        'url': CMS_GV_API,
        'gradient_url': grad_src,
    }


def wages():
    """Limb C claims non-tradable services wages carry a structural floor. ECI is
    the right instrument because it holds composition constant — a mix shift toward
    better-paid workers does not show up as wage pressure, which is what you want
    when the question is scarcity rather than upgrading."""
    raw = get(ECI_FILE).decode('utf-8', 'replace').splitlines()
    series = {}
    for line in raw[1:]:
        p = [x.strip() for x in line.split('\t')]
        if len(p) < 4 or p[0] not in ECI_SERIES or not p[2].startswith('Q'):
            continue
        try:
            series.setdefault(p[0], []).append((int(p[1]), p[2], float(p[3])))
        except ValueError:
            continue
    if not series:
        raise RuntimeError('ECI flat file returned no matching series')

    cuts, latest = {}, None
    for sid, (label, kind) in ECI_SERIES.items():
        v = sorted(series.get(sid, []))
        if not v:
            continue
        base = next((x[2] for x in v if (x[0], x[1]) == ECI_BASE), v[0][2])
        last = v[-1]
        yrs = (last[0] + int(last[1][2:]) / 4) - (ECI_BASE[0] + int(ECI_BASE[1][2:]) / 4)
        cuts[label] = {
            'series_id': sid, 'kind': kind,
            'cum_pct': round((last[2] / base - 1) * 100, 1),
            'ann_pct': round(((last[2] / base) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 else None,
        }
        latest = f'{last[0]}{last[1]}'

    base_cum = cuts.get('All civilian', {}).get('cum_pct')
    if base_cum is not None:
        for c in cuts.values():
            c['vs_baseline_pp'] = round(c['cum_pct'] - base_cum, 1)

    return {
        'measure': 'Employment Cost Index, wages and salaries, current-dollar index, '
                   'seasonally adjusted',
        'base_period': f'{ECI_BASE[0]}{ECI_BASE[1]}',
        'latest_period': latest,
        'cuts': cuts,
        'caveats': [
            'ECI holds occupational and industry composition constant by design. That is '
            'the right control for a scarcity question, but it means a shift toward more '
            'skilled workers within a trade does not register as wage pressure.',
            'The construction industry cut blends licensed journeymen with general '
            'labourers, so it may understate scarcity in the licensed subset. The '
            'construction-and-extraction occupational cut is the sharper read and tells '
            'the same story.',
            'Anchored to 2019Q4 to strip the pandemic wage distortion out of the base.',
        ],
        'source': 'BLS Employment Cost Index (flat files, no API key or quota)',
        'url': ECI_FILE,
    }


def projections():
    """Who actually retires out, by occupation.

    Limb C's premise is that the exiting cohort is concentrated in licensed,
    hard-to-replace work. BLS projects a labour force exit rate per occupation,
    which tests that premise directly rather than by inference from wages.
    """
    blob = get(EP_FILE)
    NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = [''.join(t.text or '' for t in si.iter(NS + 't'))
              for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')]
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rid = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    rels = {r.get('Id'): r.get('Target')
            for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheet_of = {s.get('name'): rels[s.get(rid)].split('/')[-1] for s in wb.iter(NS + 'sheet')}

    def rows(sheet):
        root = ET.fromstring(z.read('xl/worksheets/' + sheet_of[sheet]))
        for row in root.iter(NS + 'row'):
            cells = []
            for c in row.findall(NS + 'c'):
                v = c.find(NS + 'v')
                cells.append('' if v is None else
                             (shared[int(v.text)] if c.get('t') == 's' else v.text))
            yield cells

    sep = {r[1]: r for r in rows('Table 1.10') if len(r) > 8}
    proj = {r[1]: r for r in rows('Table 1.2') if len(r) > 10}
    if '00-0000' not in sep:
        raise RuntimeError('EP table shape changed — total row missing')

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    occs, base = {}, None
    for soc, (label, group) in EP_OCCS.items():
        s = sep.get(soc)
        if not s:
            continue
        emp = num(s[3])
        opn = num(proj[soc][10]) if soc in proj and len(proj[soc]) > 10 else None
        occs[label] = {
            'soc': soc, 'group': group,
            'employment_2024_k': emp,
            'employment_change_pct': num(s[6]),
            'exit_rate_pct': num(s[7]),
            'transfer_rate_pct': num(s[8]),
            'annual_openings_k': round(opn, 1) if opn else None,
            'openings_pct_of_employment': round(opn / emp * 100, 1) if opn and emp else None,
        }
        if group == 'baseline':
            base = occs[label]['exit_rate_pct']
    if base:
        for v in occs.values():
            if v['exit_rate_pct'] is not None:
                v['exit_vs_baseline_pp'] = round(v['exit_rate_pct'] - base, 1)

    return {
        'horizon': '2024–2034',
        'baseline_exit_rate_pct': base,
        'occupations': occs,
        'reading': 'Exit rate is the share of the occupation projected to leave the labour '
                   'force each year — retirement, in practice. Above the all-occupation '
                   'baseline means the occupation is ageing out faster than the workforce.',
        'caveats': [
            'Projections, not outturns. BLS models these; they are not observations.',
            'A low exit rate can coexist with a genuine shortage if demand is growing '
            'faster than supply — read exit rate alongside employment change and openings.',
            'Occupational transfers (moving to a different job) are separated from labour '
            'force exits, which is what makes this a retirement measure rather than a churn one.',
        ],
        'source': 'BLS Employment Projections, 2024–34 National Employment Matrix, '
                  'Tables 1.2 and 1.10',
        'url': EP_FILE,
    }


def main():
    prev = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            prev = json.load(f)

    blocks = {'population': census_population, 'spending': cex_spending,
              'participation': participation, 'wealth': dfa_wealth,
              'utilisation': utilisation, 'wages': wages,
              'projections': projections}
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
