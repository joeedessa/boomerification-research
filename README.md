# Boomerification Research

Investment-research dashboard: the US wealth-and-age transition — what happens as the cohort holding the majority of household net worth converts from earners into spenders, decumulators and bequeathers, and how to be positioned for it.

**Live dashboard:** https://joeedessa.github.io/boomerification-research/

The thesis is not that the population is aging — that has been forecastable since the 1960s and every allocator has had forty years to price it. It is that three consequences are mispriced: the **gradient** (businesses paid by the 65–74 band face a population that peaks around 2030; those paid by 75+ have a tailwind past 2040, and the market prices both as "aging"), the **labour limb** (nobody is positioned for aging to be inflationary), and the **structure** (the same demographics that guarantee healthcare volume make healthcare price the most politically exposed line in the budget).

- `index.html` — the app (single-file, no build step)
- `THESIS.md` — the written thesis the dashboard is built from
- `data/*.json` — the research: 126 companies across six limbs, the cohort clock, universe matrix, themes, sequencing, indicators, falsifiers, policy map, positioning, glossary, sources and exclusions — plus nightly machine data (quotes, indices, news, alerts, performance) and weekly reference data
- `scripts/fetch_market.py` + `.github/workflows/refresh-data.yml` — the nightly market robot
- `scripts/fetch_reference.py` + `.github/workflows/refresh-reference.yml` — the weekly reference robot: ten blocks — Census projections, BLS spending/participation/wages/employment-projections, Fed wealth shares, CMS utilisation, Medicaid HCBS, Treasury rates, SEC adviser data
- `scripts/fetch_fundamentals.py` + `.github/workflows/refresh-fundamentals.yml` — SEC XBRL fundamentals and **corporate-action drift detection**
- `.github/workflows/ci.yml` — push-time validation (data JSON, referential integrity, ticker resolution, app JS)
- `archive/` — frozen historical snapshots
- `WORKLOG.md` — the improvement loop's memory: what each iteration tested, found and changed
- `ENGINEERING-LOG.md` — **every bug, data-source trap and analytical error hit while building this, with what fixed it.** Read it before touching a fetch script: most entries are undocumented behaviours of government data sources, not bugs in this repo.

## Structure

Everything hangs off `data/thesis.json`, which defines six limbs — **A** decumulation and flows, **B** the wealth transfer, **C** labour supply, **D** consumption mix, **E** fiscal and policy, **H** housing. Each limb carries a mechanism, its observables, the expression, and the falsifier that retires it. Every company, indicator, falsifier and matrix row references a limb id, and CI fails the push if any reference does not resolve.

The **cohort clock** (`data/clock.json`) is the master time axis. Every other panel indexes to it.

## Status

**Ten evidence iterations completed 2026-08-07.** v1 shipped with no figure pulled from a primary source. Since then the whole verification queue has been worked, and the thesis is materially less confident than it started — which is the point.

**Ten reference blocks now auto-refresh** from Census, BLS (three separate routes), the Federal Reserve, CMS, Medicaid, Treasury and SEC. Eleven indicators read: **eight confirming, two contradicting, one mixed.** One falsifier tripped, two warming.

**Six repricings, five of which reversed my own earlier calls:**

- **f12 tripped** — the skilled-trades scarcity premise is refuted on wages *and* on BLS labour-force exit rates (construction ages out *slower* than the workforce average). EME, PWR, MYRG and IESC are out of the thesis entirely.
- **Limb D keeps its direction and loses its magnitude** — per-capita institutional utilisation fell 18–32% over 2014–24 while the 85+ population grew. But the ENSG downgrade that triggered was then **reversed** when the filings showed 16.4% revenue CAGR straight through it: a market-size finding is not a company-revenue prediction.
- **AMN raised, then cut to 1** — the care-labour shortage is real but accrued to the employers, not the staffing intermediaries.
- **SOON.SW cut** — the private-pay sleeve "survived every finding" only because sixteen non-SEC filers were structurally exempt from every evidence pass. First time measured, it tested worst.
- **OASI depletion is 2032, not the mid-2030s**; **go-go spending indexes at 77, not 93.** Both were wrong from memory.
- **Four corporate-action errors found** — BK→BNY, ATGE→CVSA, AMED delisted for a year, CCRN deregistering. A CI gate now fails the push if any ticker reference doesn't resolve.

**The rate call is finally made, dated and sized** (10s30s widened 9bp → 53bp; limb E beats limb A; small, because limb C's inflation channel narrowed to care-support labour alone).

**Three things are structurally unavailable at zero cost** and are named as permanent limits rather than open tasks: Medicaid LTSS *rates*, the RIA/wirehouse *channel share shift*, and true *fund flows by age*.

Full iteration history in `WORKLOG.md`; every bug and data-source trap in `ENGINEERING-LOG.md`.

## Running it locally

```bash
python3 -m http.server
```

Then open `http://localhost:8000`. Opening `index.html` directly from the filesystem also works — it falls back to fetching data from GitHub raw.

## License & disclaimer

© 2026 Joe Edessa. All rights reserved. This repository is public for personal-hosting convenience — **no license is granted** for republication or commercial reuse of the research content or code. Personal investment research, **not investment advice**. Nothing here is a recommendation to buy or sell any security. Market data comes from free public feeds and is not guaranteed accurate. Corporate actions are checked weekly against SEC EDGAR.

Sibling maps: [hard-assets-research](https://github.com/joeedessa/hard-assets-research) · [ai-hardware-research](https://github.com/joeedessa/ai-hardware-research)
