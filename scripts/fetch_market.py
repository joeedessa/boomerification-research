#!/usr/bin/env python3
"""Nightly market-data refresh for the Boomerification dashboard.

Zero-cost pipeline: runs in GitHub Actions, pulls free data, commits JSON the
dashboard already knows how to fetch.
  - data/quotes.json      : price / 1d / 1mo / 52w-drawdown / 50-200DMA / mcap for
                            every ticker in companies.json (+ best-effort fwd P/E
                            for conviction-3 and froth-tagged names)
  - data/indices.json     : the benchmarks this thesis is actually judged against
  - data/news.json        : Google News RSS headlines tagged by ticker
  - data/alerts.json      : live prices checked against the dashboard's own judgments
  - data/performance.json : basket returns, scored only from the date the judgment was made

Failure policy: never clobber a good snapshot with a bad one — on wholesale
fetch failure the previous JSON files are left untouched.
"""
import json, os, re, sys, time, urllib.parse
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')

# Benchmarks that matter for this thesis specifically. XLV/IHI are the consensus
# "aging trade"; ITB and XLRE carry limb H; ^TNX/^TYX carry the limbs A-vs-E
# rate contradiction the dashboard refuses to average away.
INDICES = {
    'SPY': 'S&P 500 ETF', 'XLV': 'Health Care Sector', 'IHI': 'Medical Devices',
    'XLF': 'Financials Sector', 'XLRE': 'Real Estate Sector', 'ITB': 'US Home Construction',
    'XLY': 'Consumer Discretionary', 'XLP': 'Consumer Staples',
    '^TNX': 'US 10Y yield', '^TYX': 'US 30Y yield', '^IRX': 'US 13W bill',
}

NEWS_QUERIES = [
    ('Medicare Advantage rates CMS', ['UNH', 'HUM', 'ALHC', 'ELV']),
    ('senior housing occupancy', ['WELL', 'VTR', 'BKD']),
    ('nursing shortage staffing', ['AMN', 'ATGE', 'CCRN']),
    ('home health Medicaid reimbursement', ['ADUS', 'AMED', 'BTSG']),
    ('skilled nursing facility rates', ['ENSG', 'CTRE', 'OHI', 'NHC']),
    ('wealth transfer inheritance advisors', ['LPLA', 'MS', 'RJF', 'NTRS']),
    ('annuity sales retirement income', ['EQH', 'CRBG', 'JXN', 'APO']),
    ('skilled trades labor shortage electricians', ['EME', 'FIX', 'MYRG', 'PWR']),
    ('TAVR aortic valve volumes', ['EW']),
    ('cataract surgery premium IOL', ['ALC', 'BLCO']),
    ('hearing aid market OTC', ['SOON.SW', 'DEMANT.CO', 'AMP.MI']),
    ('Alzheimer\'s treatment uptake', ['LLY', 'BIIB']),
    ('GLP-1 elderly health outcomes', ['LLY', 'RMD', 'DVA']),
    ('Social Security trust fund depletion', []),
    ('immigration policy healthcare workers', []),
    ('cruise bookings older travelers', ['VIK', 'RCL', 'CCL']),
    ('reverse mortgage home equity seniors', ['FOA']),
    ('funeral cremation death care', ['SCI', 'CSV']),
    ('aging in place home modification', ['HD', 'LOW']),
    ('long-term care costs', []),
]

# Long-form RSS from the demographic, healthcare-policy and retirement-economics
# voices. The free proxy for the paid research: most of what is worth reading on
# this thesis publishes here with open RSS.
VOICES = [
    ('Citrini Research', 'https://www.citriniresearch.com/feed'),
    ('KFF Health News', 'https://kffhealthnews.org/feed/'),
    ('Health Affairs Forefront', 'https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff'),
    ('Calculated Risk', 'https://feeds.feedburner.com/CalculatedRisk'),
    ('Center for Retirement Research', 'https://crr.bc.edu/feed/'),
    ('Peterson Foundation', 'https://www.pgpf.org/rss.xml'),
    ('Senior Housing News', 'https://seniorhousingnews.com/feed/'),
    ('Home Health Care News', 'https://homehealthcarenews.com/feed/'),
]

# Our ticker convention -> Yahoo's. Mirrors yahooSymbol() in index.html.
SPECIAL = {
    'GWO.TO': 'GWO.TO',
    'ESSITY-B.ST': 'ESSITY-B.ST',
    'DEMANT.CO': 'DEMANT.CO',
    'SOON.SW': 'SOON.SW',
    'STMN.SW': 'STMN.SW',
    'AMP.MI': 'AMP.MI',
    'COH.AX': 'COH.AX',
}


def yahoo_symbol(t):
    """Map our ticker conventions to Yahoo's. Most already match; the map exists
    so a convention change has one place to live rather than two."""
    return SPECIAL.get(t, t)


def pct(a, b):
    return round((a / b - 1) * 100, 1) if a and b else None


def main():
    import yfinance as yf
    import pandas as pd

    with open(os.path.join(ROOT, 'companies.json')) as f:
        comp = json.load(f)['companies']
    tickers = [c['ticker'] for c in comp]
    ymap = {t: yahoo_symbol(t) for t in tickers}
    pe_targets = {c['ticker'] for c in comp if c.get('conviction') == 3 or c.get('froth')}

    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    errors = []

    # ── Price history for everything (one threaded batch) ──
    all_syms = sorted(set(ymap.values()) | set(INDICES))
    hist = yf.download(all_syms, period='1y', interval='1d', auto_adjust=True,
                       group_by='ticker', progress=False, threads=True)

    def metrics(sym):
        try:
            df = hist[sym].dropna(subset=['Close'])
            if len(df) < 5:
                return None
            close = df['Close']
            p = float(close.iloc[-1])
            return {
                'p': round(p, 2),
                'd1': pct(p, float(close.iloc[-2])),
                'm1': pct(p, float(close.iloc[-22])) if len(close) >= 22 else None,
                'dd': round((p / float(close.max()) - 1) * 100, 1),
                'a50': round(float(close.tail(50).mean()), 2),
                'a200': round(float(close.tail(200).mean()), 2) if len(close) >= 200 else None,
            }
        except Exception:
            return None

    quotes = {}
    for t in tickers:
        m = metrics(ymap[t])
        if m:
            quotes[t] = m
        else:
            errors.append(t)

    # Stooq fallback for plain US tickers Yahoo missed (free CSV, no key)
    import urllib.request
    for t in list(errors):
        if not re.match(r'^[A-Z]+$', t):
            continue
        try:
            url = f'https://stooq.com/q/d/l/?s={t.lower()}.us&i=d'
            rows = urllib.request.urlopen(url, timeout=15).read().decode().strip().split('\n')[1:]
            closes = [float(r.split(',')[4]) for r in rows[-260:] if r.count(',') >= 4]
            if len(closes) >= 5:
                p = closes[-1]
                quotes[t] = {'p': round(p, 2), 'd1': pct(p, closes[-2]),
                             'm1': pct(p, closes[-22]) if len(closes) >= 22 else None,
                             'dd': round((p / max(closes) - 1) * 100, 1),
                             'a50': round(sum(closes[-50:]) / min(50, len(closes)), 2),
                             'a200': round(sum(closes[-200:]) / 200, 2) if len(closes) >= 200 else None,
                             'src': 'stooq'}
                errors.remove(t)
        except Exception:
            pass

    if len(quotes) < len(tickers) * 0.5:
        print(f'FATAL: only {len(quotes)}/{len(tickers)} quotes — keeping previous snapshot')
        sys.exit(1)

    # ── Market cap + best-effort forward P/E for the priority set ──
    for t in list(quotes):
        try:
            fi = yf.Ticker(ymap[t]).fast_info
            mc = getattr(fi, 'market_cap', None)
            if mc:
                quotes[t]['mc'] = int(mc)
        except Exception:
            pass
        if t in pe_targets:
            try:
                info = yf.Ticker(ymap[t]).info
                fpe = info.get('forwardPE')
                if fpe and 0 < fpe < 1000:
                    quotes[t]['fpe'] = round(fpe, 1)
                dy = info.get('dividendYield')
                if dy:
                    quotes[t]['dy'] = round(float(dy) * (100 if float(dy) < 1 else 1), 2)
                time.sleep(0.3)
            except Exception:
                pass

    with open(os.path.join(ROOT, 'quotes.json'), 'w') as f:
        json.dump({'_meta': {'as_of': now, 'source': 'Yahoo Finance (unofficial, via yfinance)',
                             'coverage': f'{len(quotes)}/{len(tickers)}', 'errors': errors},
                   'quotes': quotes}, f, separators=(',', ':'))
    print(f'quotes.json: {len(quotes)}/{len(tickers)} ({len(errors)} misses: {errors[:8]})')

    idx = {}
    for sym, name in INDICES.items():
        m = metrics(sym)
        if m:
            m['n'] = name
            idx[sym] = m
    # 10s30s — the spread where the limbs A-vs-E contradiction is actually settled.
    if '^TNX' in idx and '^TYX' in idx:
        idx['SPREAD_10_30'] = {'n': '10s30s spread (bp)',
                               'p': round((idx['^TYX']['p'] - idx['^TNX']['p']) * 10, 1),
                               'd1': None, 'm1': None, 'dd': None, 'a50': None, 'a200': None}
    with open(os.path.join(ROOT, 'indices.json'), 'w') as f:
        json.dump({'_meta': {'as_of': now}, 'symbols': idx}, f, separators=(',', ':'))
    print(f'indices.json: {len(idx)}')

    # ── Alerts: live data checked against the dashboard's own judgments ──
    froth = {c['ticker']: c.get('froth') for c in comp}
    conv = {c['ticker']: c.get('conviction') for c in comp}
    names = {c['ticker']: c['name'] for c in comp}
    themes = {c['ticker']: set(c.get('themes', [])) for c in comp}
    alerts = []
    for t, q in quotes.items():
        dd, d1 = q.get('dd'), q.get('d1')
        if froth.get(t) == 1 and dd is not None and dd <= -15:
            alerts.append({'tk': t, 'type': 'window', 'val': dd,
                           'msg': f"{names[t]} ({t}) is {dd}% off its 52w high — insulated name past the entry threshold"})
        if froth.get(t) == 3 and dd is not None and dd >= -5:
            alerts.append({'tk': t, 'type': 'froth', 'val': dd,
                           'msg': f"{names[t]} ({t}) back within 5% of its 52w high — froth rebuilt"})
        if conv.get(t) == 3 and d1 is not None and abs(d1) >= 6:
            alerts.append({'tk': t, 'type': 'move', 'val': d1,
                           'msg': f"{names[t]} ({t}) moved {d1:+}% today — core position, check the tape"})
        # Thesis-specific: the go-go fade list making new highs is the fade window,
        # not a problem. The dashboard's own timing call, checked against the tape.
        if 'go-go-fade' in themes.get(t, ()) and dd is not None and dd >= -3:
            alerts.append({'tk': t, 'type': 'fade', 'val': dd,
                           'msg': f"{names[t]} ({t}) within 3% of its 52w high — go-go fade candidate into strength"})
    order = {'window': 0, 'move': 1, 'fade': 2, 'froth': 3}
    alerts.sort(key=lambda a: (order[a['type']], a['val']))
    with open(os.path.join(ROOT, 'alerts.json'), 'w') as f:
        json.dump({'_meta': {'as_of': now}, 'alerts': alerts}, f, separators=(',', ':'))
    print(f'alerts.json: {len(alerts)} alerts')

    # ── Performance scoreboard ──
    # Honesty rule: a judgment can only be scored from the date it was MADE.
    # Trailing returns of a basket picked today describe the past, they do not
    # test the framework — so they are reported separately and labelled.
    INCEPTION = {'conviction': '2026-08-06', 'limb': '2026-08-06'}

    def series_of(sym):
        try:
            df = hist[sym].dropna(subset=['Close'])
            return df.index, [float(x) for x in df['Close']]
        except Exception:
            return None, []

    def ret_since(sym, date_str):
        idx_, cl = series_of(sym)
        if idx_ is None or len(cl) < 2:
            return None
        try:
            pos = idx_.searchsorted(pd.Timestamp(date_str))
            if pos >= len(cl) - 1:
                return None
            return (cl[-1] / cl[pos] - 1) * 100
        except Exception:
            return None

    def avg(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    perf = {'_meta': {'as_of': now, 'inception': INCEPTION,
                      'note': 'Baskets are equal-weighted and scored only from the date the judgment was recorded. '
                              'Trailing columns describe the past and do not test the framework.'}}
    conv3 = [t for t in quotes if conv.get(t) == 3]
    perf['conviction3'] = {'n': len(conv3),
                           'since_inception': avg([ret_since(ymap[t], INCEPTION['conviction']) for t in conv3]),
                           'trailing_1m': avg([quotes[t].get('m1') for t in conv3])}
    by_limb = {}
    for c in comp:
        if c['ticker'] in quotes:
            by_limb.setdefault(c['limb'], []).append(c['ticker'])
    perf['by_limb'] = {L: {'n': len(ts),
                           'since_inception': avg([ret_since(ymap[t], INCEPTION['limb']) for t in ts]),
                           'trailing_1m': avg([quotes[t].get('m1') for t in ts])}
                       for L, ts in sorted(by_limb.items())}
    for b in ('SPY', 'XLV', 'IHI'):
        perf.setdefault('benchmarks', {})[b] = {
            'since_inception': round(ret_since(b, INCEPTION['limb']), 2) if ret_since(b, INCEPTION['limb']) else None,
            'trailing_1m': idx.get(b, {}).get('m1')}
    with open(os.path.join(ROOT, 'performance.json'), 'w') as f:
        json.dump(perf, f, separators=(',', ':'))
    print('performance.json written')

    # ── News ──
    try:
        import feedparser
    except ImportError:
        print('feedparser missing — skipping news')
        return

    seen, news = set(), []
    for query, tks in NEWS_QUERIES:
        url = ('https://news.google.com/rss/search?q='
               + urllib.parse.quote(query) + '&hl=en-US&gl=US&ceid=US:en')
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:5]:
            title = getattr(e, 'title', '')
            if not title or title in seen:
                continue
            seen.add(title)
            news.append({'t': title, 'u': getattr(e, 'link', ''),
                         'd': getattr(e, 'published', '')[:16],
                         'src': getattr(getattr(e, 'source', None), 'title', '') or 'Google News',
                         'tk': tks, 'q': query})
        time.sleep(0.4)

    voices = []
    for name, url in VOICES:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:4]:
            title = getattr(e, 'title', '')
            if not title:
                continue
            voices.append({'t': title, 'u': getattr(e, 'link', ''),
                           'd': getattr(e, 'published', '')[:16], 'src': name})
        time.sleep(0.3)

    with open(os.path.join(ROOT, 'news.json'), 'w') as f:
        json.dump({'_meta': {'as_of': now}, 'news': news[:120], 'voices': voices[:60]},
                  f, separators=(',', ':'))
    print(f'news.json: {len(news)} headlines, {len(voices)} long-form')


if __name__ == '__main__':
    main()
