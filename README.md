# Boomerification Research

Investment-research dashboard: the US wealth-and-age transition — what happens as the cohort holding the majority of household net worth converts from earners into spenders, decumulators and bequeathers, and how to be positioned for it.

**Live dashboard:** https://joeedessa.github.io/boomerification-research/

The thesis is not that the population is aging — that has been forecastable since the 1960s and every allocator has had forty years to price it. It is that three consequences are mispriced: the **gradient** (businesses paid by the 65–74 band face a population that peaks around 2030; those paid by 75+ have a tailwind past 2040, and the market prices both as "aging"), the **labour limb** (nobody is positioned for aging to be inflationary), and the **structure** (the same demographics that guarantee healthcare volume make healthcare price the most politically exposed line in the budget).

- `index.html` — the app (single-file, no build step)
- `THESIS.md` — the written thesis the dashboard is built from
- `data/*.json` — the research: 127 companies across six limbs, the cohort clock, universe matrix, themes, sequencing, indicators, falsifiers, policy map, positioning, glossary, sources and exclusions — plus nightly machine data (quotes, indices, news, alerts, performance) and weekly reference data
- `scripts/fetch_market.py` + `.github/workflows/refresh-data.yml` — the nightly market robot
- `scripts/fetch_reference.py` + `.github/workflows/refresh-reference.yml` — the weekly reference robot: Census population projections, BLS spending and participation, Fed wealth shares
- `.github/workflows/ci.yml` — push-time validation (data JSON, thesis referential integrity, app JS)
- `archive/` — frozen historical snapshots

## Structure

Everything hangs off `data/thesis.json`, which defines six limbs — **A** decumulation and flows, **B** the wealth transfer, **C** labour supply, **D** consumption mix, **E** fiscal and policy, **H** housing. Each limb carries a mechanism, its observables, the expression, and the falsifier that retires it. Every company, indicator, falsifier and matrix row references a limb id, and CI fails the push if any reference does not resolve.

The **cohort clock** (`data/clock.json`) is the master time axis. Every other panel indexes to it.

## Status

**Sourced as of 2026-08-07.** v1 shipped with no figure pulled from a primary source. The verification queue has since been worked in full: eight claims resolved — five confirmed, one confirmed with a material correction, one confirmed with a caveat, and **two wrong**. The resolution log is on the Sources tab and in `data/sources.json`.

The two that were wrong matter:

- **OASI trust fund depletion is 2032, not the mid-2030s** (2026 Trustees Report). Limb E's forcing function is three years nearer than the thesis assumed, which moves it inside the horizon of most positions rather than beyond it.
- **Go-go spending indexes at 77, not 93** against a 55–64 base (BLS CEX 2024). Spending falls 23% at the retirement transition, far more sharply than assumed.

A third claim was corrected: the go-go band **plateaus rather than declines** (Census: 38.0M in 2030 → 35.1M in 2040 → 37.0M by 2050), which narrows the fade call from "the customer disappears" to "the customer stops growing while priced for growth." Corrections are rendered in the app rather than silently overwritten.

Four series — population, spending, participation and wealth shares — refresh weekly from Census, BLS and the Federal Reserve via `scripts/fetch_reference.py`, so the dashboard can no longer rot against its own premises. **What remains unsourced is listed on the Sources tab and is not small** — most importantly health utilisation per capita in the 75+ bands, which is the direct test of the morbidity-compression falsifier.

## Running it locally

```bash
python3 -m http.server
```

Then open `http://localhost:8000`. Opening `index.html` directly from the filesystem also works — it falls back to fetching data from GitHub raw.

## License & disclaimer

© 2026 Joe Edessa. All rights reserved. This repository is public for personal-hosting convenience — **no license is granted** for republication or commercial reuse of the research content or code. Personal investment research, **not investment advice**. Nothing here is a recommendation to buy or sell any security. Market data comes from free public feeds and is not guaranteed accurate. Corporate actions after mid-2026 may not be reflected in the universe.

Sibling maps: [hard-assets-research](https://github.com/joeedessa/hard-assets-research) · [ai-hardware-research](https://github.com/joeedessa/ai-hardware-research)
