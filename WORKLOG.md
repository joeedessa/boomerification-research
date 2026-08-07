# Boomerification — improvement loop worklog

The loop's memory. Each iteration: read this file and `data/sources.json`
(`still_unsourced`), pick the single highest-value open item, do it completely,
verify, push, then append here.

Hard constraint throughout: **zero cost**. Keyless public sources only. No paid
data, no subscriptions, no API keys of any kind — including free ones requiring
registration.

---

## Opening rank — 2026-08-07

Ranked by value, not by effort. The governing consideration: five of five
sourced indicators currently read confirming, and the ones cheapest to source
were not a random sample. **The marginal value of another confirming read is
low; the marginal value of a potentially disconfirming one is high.** That
reorders the list away from the easy wins.

| # | Item | P | Why here |
|---|---|---|---|
| 1 | **Health utilisation per capita, 75+** | P1 | The direct test of falsifier f3 (morbidity compression) — the only open item that can *kill* a limb rather than decorate one. Limb D is the largest sleeve in the book (51 of 127 names). If per-capita utilisation is flattening, the care-volume thesis is wrong and the go-go fade is wrong with it. Nothing else on this list carries that asymmetry. |
| 2 | SEC XBRL fundamentals for the universe | — | 127 names carry conviction and froth scores with no financials behind them. Free, keyless, and it converts opinion into something falsifiable at the name level. Large enough to span several iterations. |
| 3 | Services vs goods wage growth | P2 | Limb C's inflation claim, closable via the BLS API already in use. Best value-to-effort ratio on the board — but it is another *likely-confirming* read, which is exactly why it does not go first. |
| 4 | Apprenticeship completions | P2 | The untested half of the capacity-gap mechanism; the contractor positions (EME, FIX, MYRG, PWR) rest on it. DOL data is free. |
| 5 | Fund flows by investor age | P1 | Limb A's explicit falsifier, but "real work, not a fetch" — Fed distributional data cross-cut against ICI. Expensive in iterations relative to what it settles. |
| 6 | Metro turnover, retirement metros | P3 | Limb H only. Lowest limb weight, and the national series averages the signal away. |
| — | Annuity sales by product; RIA channel share | P1 | **Blocked.** LIMRA product detail and Cerulli channel data are paywalled. Free proxies only; recorded as such rather than approximated. |

**Chosen: #1.** It beats #2 and #3 because it is the only item with a real
chance of proving the thesis wrong, and a thesis that has only been tested where
testing was cheap has not been tested.

---

## Iteration 1 — 2026-08-07 — Health utilisation per capita, 75+

**Sources found (both keyless, both now automated):** CMS Medicare Geographic
Variation PUF via `data.cms.gov/data-api` — national, FFS 65+, 2014–2024, ~246
columns of per-1,000-beneficiary utilisation. And CMS Program Statistics —
Medicare SNF, which carries the age detail the GV PUF lacks (it only splits
`<65` / `>=65`). Added as a fifth block to `fetch_reference.py`; the SNF file
URL is discovered from the CMS catalogue each run so a re-publish is picked up
without a code change.

**What I found — two results pulling opposite ways.**

*Confirming, and stronger than the thesis claimed.* SNF days per 1,000
beneficiaries: 634 at 65–74, 1,712 at 75–84 (2.7x), 4,460 at 85+ (7.0x), 5,761
at 95+. Care hours genuinely scale with the 85+ band. The cohort clock's central
claim survives contact with the data and then some.

*Contradicting, and this is the first indicator to read against the thesis.*
Per-capita utilisation among FFS 65+ fell hard over 2014–2024: SNF days −31%,
home health visits −32%, inpatient days −18%, admissions −18%. Two compositional
forces bias that measure **up** — Medicare Advantage went 32% → 55% and
healthier lives select into MA leaving a sicker FFS residual, while average
beneficiary age also rose. The declines happened anyway, so they are understated.

**What it changed.** The thesis multiplied population growth straight through to
care volumes and never asked whether utilisation per head was constant. It is
not. Compounding the observed −3.6%/yr per-capita SNF decline against +4.6%/yr
85+ population growth gives **≈ +12% aggregate SNF days to 2040, versus the +96%
population alone implies.** Limb D keeps its direction and loses its magnitude.

**But it is probably not morbidity compression.** Ambulatory contact *rose* over
the same window — E&M +16%, imaging +12%, procedures +5%. A healthier population
sees doctors less, not more. The pattern is site-of-care shift plus payment
policy (SNF PDPM 2019, home health PDGM 2020). So the falsifier I set out to test
(f3) remains unproven, and the test surfaced a larger, unanticipated one instead.

**Changes shipped:**
- New falsifier **f11** — "the per-capita offset consumes the population
  arithmetic", state `warming`, partially realised rather than hypothetical.
- f3 annotated with the specific disconfirming evidence; indicator `hh` set to
  **contradicting**, the first non-confirming read on the board.
- Limb D gains a sourced block and a magnitude warning; `arithmetic_warning`
  renders as a red panel on the Limbs tab.
- **Positioning repriced** — a new block on the Positioning tab: down
  institutional operators (ENSG, NHC, EHC, PNTG) and SNF net-lease (OHI, CTRE,
  SBRA); up hospice (CHE, SCI, CSV — hospice was the *only* category where
  per-capita use rose, +21%), ambulatory (RDNT, PRVA, USPH, OPCH) and private-pay.
- Calls moved: **ENSG 3→2** on magnitude not quality; **CHE 2→3**.
- Cohort clock tab gains a two-panel "does care demand actually scale?" section —
  the gradient (confirms) next to the trend (contradicts), with five caveats.

**New gap discovered.** The CMS Medicare data excludes Medicaid-funded personal
care entirely — ADUS's core business and the largest category of aging-in-place
spend. Those positions are untested, not confirmed safe. Added to the unsourced
list as item 7.

**Next three, re-ranked:**
1. **Services vs goods wage growth (BLS ECI).** Promoted. Limb C is now the
   thesis's load-bearing limb given limb D just lost magnitude, and its inflation
   claim is untested. Keyless, same API already in use — cheap and now important.
2. **SEC XBRL fundamentals.** Unchanged in value. ENSG and CHE just moved on
   judgment alone; filings would let the whole universe move on evidence.
3. **Medicaid personal care utilisation.** New. Tests whether the repricing above
   should extend to ADUS/AVAH or stop at the Medicare-funded names.

---
