#!/usr/bin/env python3
"""Company fundamentals from SEC XBRL — free, keyless, no quota.

Why this exists: the dashboard had moved six position groups on macro evidence
without once checking whether the companies' own filings agreed. Two findings
needed testing at the name level rather than the sector level:

  1. Iteration 1 — per-capita institutional utilisation is falling. If true, care
     operators' revenue growth should be running well below the population
     arithmetic the thesis originally assumed.
  2. Iteration 2 — care-labour wages are running ~9pp above baseline. If true,
     the squeeze should show up as operating-margin compression in the operators
     whose largest cost line is that labour.

Both are testable against filed numbers, which is the point.

It also does something the universe badly needed: **corporate-action drift
detection**. Tickers rename, companies delist, deals close. A research universe
that never checks is quietly wrong. The first run found four errors in 127 names.

Writes data/fundamentals.json. Anything unfetchable is recorded as unavailable
rather than silently dropped.
"""
import json, os, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT = os.path.join(ROOT, 'fundamentals.json')
# SEC requires a descriptive UA with contact details and asks for <=10 req/sec.
UA = {'User-Agent': 'boomerification-research/1.0 (joe.edessa@gmail.com)'}
TICKER_FILE = 'https://www.sec.gov/files/company_tickers_exchange.json'
SUBMISSIONS = 'https://data.sec.gov/submissions/CIK{cik:010d}.json'
FRAMES = 'https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/CY{year}.json'

YEARS = list(range(2019, 2026))
# Revenue tagging is genuinely inconsistent across filers; take the first tag
# that yields a value for a given company-year.
REVENUE_TAGS = ['Revenues',
                'RevenueFromContractWithCustomerExcludingAssessedTax',
                'RevenueFromContractWithCustomerIncludingAssessedTax']
MARGIN_TAG = 'OperatingIncomeLoss'

# CIKs the SEC ticker files omit or list under a newer ticker. Verified against
# data.sec.gov/submissions rather than guessed — an earlier guess for ATGE
# resolved to an unrelated company, which is why these are pinned explicitly.
CIK_OVERRIDES = {
    'BK': 1390777,      # Bank of New York Mellon — now files/trades as BNY
    'ATGE': 730464,     # DeVry -> Adtalem -> Covista (CVSA) as of 2026
    'AMED': 896262,     # Amedisys — delisted 2025 on completion of acquisition
    'CCRN': 1141103,    # Cross Country Healthcare — 25-NSE filed 2026-07
}
DELISTING_FORMS = {'25-NSE', '25', '15-12B', '15-12G'}


def get(url, tries=4, timeout=90):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            last = e
        if i < tries - 1:
            time.sleep(2 * (i + 1))
    if isinstance(last, Exception):
        print(f'  fetch failed: {url} — {last}', file=sys.stderr)
    return None


def cik_map(tickers):
    """Universe ticker -> CIK, plus the overrides for names the SEC files miss."""
    raw = json.loads(get(TICKER_FILE))
    f = raw['fields']
    ti, ci = f.index('ticker'), f.index('cik')
    live = {r[ti]: r[ci] for r in raw['data']}
    out, unmapped = {}, []
    for t in tickers:
        if t in live:
            out[t] = live[t]
        elif t in CIK_OVERRIDES:
            out[t] = CIK_OVERRIDES[t]
        else:
            unmapped.append(t)
    return out, unmapped, live


def corporate_actions(cikmap, live_tickers):
    """Flag renames and delistings.

    The naive rule — any Form 25 or Form 15 in recent filings — produced 43 flags
    on 116 names, because large issuers routinely deregister individual bond,
    preferred and warrant classes. Lilly, Morgan Stanley and Stryker are not
    delisting. So the load-bearing signals are the ticker itself and whether the
    company is still filing periodic reports; Form 25/15 is only corroboration.
    """
    flags = {}
    today = datetime.now(timezone.utc).date()
    for tk, cik in sorted(cikmap.items()):
        blob = get(SUBMISSIONS.format(cik=cik))
        time.sleep(0.12)                      # stay well inside SEC's 10/sec
        if not blob:
            continue
        d = json.loads(blob)
        current = d.get('tickers') or []
        recent = d.get('filings', {}).get('recent', {})
        forms, dates = recent.get('form', []), recent.get('filingDate', [])

        last_periodic = next((dt for f, dt in zip(forms, dates)
                              if f in ('10-K', '10-Q', '20-F', '40-F')), None)
        months_stale = None
        if last_periodic:
            try:
                d0 = datetime.strptime(last_periodic, '%Y-%m-%d').date()
                months_stale = (today - d0).days / 30.44
            except ValueError:
                pass
        recent_exit = [(f, dt) for f, dt in zip(forms, dates)
                       if f in DELISTING_FORMS and dt >= str(today.replace(year=today.year - 1))]

        issue = None
        if not current:
            issue = {'kind': 'gone', 'severity': 'high',
                     'detail': 'SEC lists no active ticker for this filer'
                               + (f'; last periodic filing {last_periodic}' if last_periodic else '')}
        elif tk not in current:
            issue = {'kind': 'ticker-change', 'severity': 'high',
                     'detail': f'universe carries {tk}; SEC lists {current[0]}'}
        elif months_stale is not None and months_stale > 9:
            issue = {'kind': 'stopped-reporting', 'severity': 'medium',
                     'detail': f'last periodic filing {last_periodic} '
                               f'({months_stale:.0f} months ago)'}
        elif recent_exit:
            issue = {'kind': 'review', 'severity': 'low',
                     'detail': f'{recent_exit[0][0]} filed {recent_exit[0][1]} while still '
                               f'listed — usually a single security class, worth a look'}
        if issue:
            issue.update({'cik': cik, 'sec_name': d.get('name'), 'current_tickers': current,
                          'former_names': [f.get('name') for f in d.get('formerNames', [])][:3]})
            flags[tk] = issue
    return flags


def frames(tag, year):
    blob = get(FRAMES.format(tag=tag, year=year))
    time.sleep(0.12)
    if not blob:
        return {}
    try:
        return {r['cik']: r['val'] for r in json.loads(blob).get('data', [])}
    except Exception:
        return {}


def non_sec_financials(tickers):
    """The sixteen names that file outside the SEC.

    Most of the private-pay sleeve — Sonova, Demant, Amplifon, Straumann,
    Cochlear, Unicharm — reports to Swiss, Danish, Italian, Australian and
    Japanese regulators, so XBRL frames cannot see them. That sleeve has survived
    every finding in this programme, which makes it the least tested and most
    load-bearing part of the book. yfinance exposes filed income statements for
    them at no cost; the history is shorter and the tagging is a vendor's rather
    than a regulator's, so these records are marked with a lower provenance.
    """
    try:
        import warnings
        warnings.filterwarnings('ignore')
        import yfinance as yf
    except ImportError:
        print('  yfinance unavailable — non-SEC names skipped', file=sys.stderr)
        return {}
    out = {}
    for t in tickers:
        try:
            df = yf.Ticker(t).income_stmt
            if df is None or df.empty:
                continue
            idx = {str(i): i for i in df.index}
            rk = idx.get('Total Revenue') or idx.get('Operating Revenue')
            ok = idx.get('Operating Income')
            if rk is None:
                continue
            rev, margin = {}, {}
            for col in df.columns:
                y = str(col)[:4]
                try:
                    r = float(df.loc[rk, col])
                except Exception:
                    continue
                if r != r or r <= 0:
                    continue
                rev[y] = r
                if ok is not None:
                    try:
                        o = float(df.loc[ok, col])
                        if o == o:
                            margin[y] = round(o / r * 100, 1)
                    except Exception:
                        pass
            if len(rev) < 2:
                continue
            ys = sorted(rev)
            span = int(ys[-1]) - int(ys[0])
            rec = {'provenance': 'vendor (yfinance) — not a regulator filing',
                   'revenue': {y: rev[y] for y in ys},
                   'operating_margin_pct': {y: margin[y] for y in sorted(margin)}}
            if span > 0:
                rec['revenue_cagr_pct'] = round(((rev[ys[-1]] / rev[ys[0]]) ** (1 / span) - 1) * 100, 1)
                rec['revenue_span'] = f'{ys[0]}-{ys[-1]}'
            if len(margin) >= 2:
                ms = sorted(margin)
                rec['margin_delta_pp'] = round(margin[ms[-1]] - margin[ms[0]], 1)
                rec['margin_span'] = f'{ms[0]}-{ms[-1]}'
            out[t] = rec
            time.sleep(0.4)
        except Exception as e:
            print(f'  {t}: {type(e).__name__}', file=sys.stderr)
    return out


def main():
    with open(os.path.join(ROOT, 'companies.json')) as f:
        comp = json.load(f)['companies']
    tickers = [c['ticker'] for c in comp]
    meta = {c['ticker']: c for c in comp}

    cikmap, unmapped, live = cik_map(tickers)
    print(f'CIK mapped {len(cikmap)}/{len(tickers)} ({len(unmapped)} non-SEC filers)')

    flags = corporate_actions(cikmap, live)
    print(f'corporate-action flags: {len(flags)} — {sorted(flags)}')

    rev_by_year, op_by_year = {}, {}
    for y in YEARS:
        merged = {}
        for tag in REVENUE_TAGS:
            for cik, v in frames(tag, y).items():
                merged.setdefault(cik, v)      # first tag wins
        rev_by_year[y] = merged
        op_by_year[y] = frames(MARGIN_TAG, y)
        print(f'  CY{y}: revenue {len(merged)} filers, operating income {len(op_by_year[y])}')

    out, covered, partials = {}, 0, []
    for tk, cik in cikmap.items():
        rev = {y: rev_by_year[y].get(cik) for y in YEARS}
        op = {y: op_by_year[y].get(cik) for y in YEARS}
        # Some filers' tagging causes a CY frame to pick up a partial period —
        # Comfort Systems' CY2025 came through at $1.83bn against $7.03bn the
        # prior year, which would have shown a fast-growing contractor as
        # shrinking. Drop a terminal year that collapses implausibly and record
        # it, rather than letting one bad cell drive a position.
        have_r = [y for y in YEARS if rev.get(y)]
        while len(have_r) >= 2:
            last, prev = have_r[-1], have_r[-2]
            if rev[last] < rev[prev] * 0.55:
                partials.append(f'{tk} CY{last}')
                rev[last] = None
                op[last] = None
                have_r.pop()
            else:
                break
        margin = {y: round(op[y] / rev[y] * 100, 1)
                  for y in YEARS if rev.get(y) and op.get(y) and rev[y] > 0}
        have = [y for y in YEARS if rev.get(y)]
        rec = {'cik': cik, 'vertical': meta[tk]['vertical'], 'limb': meta[tk]['limb'],
               'revenue': {str(y): rev[y] for y in YEARS if rev.get(y)},
               'operating_margin_pct': {str(y): margin[y] for y in sorted(margin)}}
        if len(have) >= 2:
            first, last = have[0], have[-1]
            span = last - first
            if rev[first] and rev[first] > 0 and span > 0:
                rec['revenue_cagr_pct'] = round(((rev[last] / rev[first]) ** (1 / span) - 1) * 100, 1)
                rec['revenue_span'] = f'CY{first}-CY{last}'
        if len(margin) >= 2:
            ms = sorted(margin)
            rec['margin_delta_pp'] = round(margin[ms[-1]] - margin[ms[0]], 1)
            rec['margin_span'] = f'CY{ms[0]}-CY{ms[-1]}'
        if rec['revenue']:
            covered += 1
        out[tk] = rec

    nonsec = non_sec_financials(unmapped)
    for tk, rec in nonsec.items():
        rec.update({'vertical': meta[tk]['vertical'], 'limb': meta[tk]['limb']})
        out[tk] = rec
        covered += 1
    print(f'non-SEC filers covered via vendor data: {len(nonsec)}/{len(unmapped)}')

    payload = {
        '_meta': {
            'description': 'Company fundamentals from SEC XBRL frames — revenue and '
                           'operating margin, used to test the utilisation and wage '
                           'findings against filed numbers rather than sector narrative.',
            'as_of': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'years': YEARS,
            'coverage': f'{covered}/{len(tickers)} universe names with revenue data',
            'dropped_partial_periods': partials,
            'unmapped': unmapped,
            'unmapped_note': 'Non-US filers have no SEC XBRL. Since 2026-08-07 these are '
                             'covered via vendor income statements instead and carry a '
                             '"provenance" field marking them as vendor rather than '
                             'regulator data — shorter history, vendor tagging, lower trust.',
            'non_sec_covered': sorted(nonsec),
            'source': 'SEC EDGAR XBRL frames API (data.sec.gov), keyless',
            'caveats': [
                'Revenue tagging varies by filer; three us-gaap tags are tried in order '
                'and the first hit wins, so cross-company revenue levels are indicative '
                'rather than strictly comparable.',
                'CY frames align non-calendar fiscal years to the nearest annual period.',
                'Operating margin is OperatingIncomeLoss over revenue as filed — no '
                'adjustment for one-offs, impairments or accounting changes.',
                'REITs, insurers and asset managers do not report a meaningful operating '
                'margin on this definition; read the margin column for operators only.',
                'Terminal years that collapse to under 55% of the prior year are dropped as '
                'partial-period tagging artifacts and listed in dropped_partial_periods.',
                'Revenue growth conflates organic volume, price and acquisition. In a '
                'consolidating sector a share-gainer can outgrow a shrinking market, which '
                'is exactly what the care operators did — see the utilisation finding.',
            ],
        },
        'corporate_actions': flags,
        'companies': out,
    }
    with open(OUT, 'w') as f:
        json.dump(payload, f, indent=1)
    print(f'fundamentals.json written — {covered} names with revenue, {len(flags)} action flags')


if __name__ == '__main__':
    main()
