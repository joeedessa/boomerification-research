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

## Iteration 2 — 2026-08-07 — Services vs goods wage growth

**Why this over SEC XBRL:** limb C became load-bearing the moment limb D lost its
magnitude, and its central claim — a structural floor under non-tradable services
wages — had never been tested. Testing the limb the thesis now leans on beats
adding evidence under names whose limb might not hold.

**Source.** BLS Employment Cost Index, wages and salaries, seasonally adjusted,
2019Q4–2026Q2. Read from the **flat files**, not the API: the public API caps at
25 queries a day and would have made this block compete with the CPS and CEX
pulls. ECI is the right instrument because it holds composition constant, so a
mix shift toward better-paid workers cannot masquerade as scarcity.

Two BLS quirks cost time and are now encoded in `get()`: `download.bls.gov`
returns **403 for any User-Agent containing a URL** but accepts the
contact-email form, and BLS **503s during its own maintenance windows** — which
happened mid-iteration and correctly triggered the keep-previous-snapshot
fallback. Both the flat-file fetch and the API path now retry with backoff.

**What I found — a split verdict, along a line the thesis never drew.**

| Cut | Cumulative since 2019Q4 | vs baseline |
|---|---|---|
| Service occupations | +37.5% | **+9.2pp** |
| Health care & social assistance | +31.6% | +3.3pp |
| Installation, maintenance & repair | +31.3% | +3.0pp |
| *All civilian (baseline)* | *+28.3%* | *—* |
| Construction & extraction (occupation) | +27.6% | **−0.7pp** |
| Construction (industry) | +26.7% | **−1.6pp** |

*Care labour: confirmed emphatically.* Service occupations — home health aides,
nursing assistants, personal care — is the **fastest-rising cut in the entire
index**. This is now the best-evidenced part of the thesis.

*Construction trades: not confirmed at all.* Construction runs below the
all-civilian baseline and behind manufacturing. If licensed trade labour were
irreplaceable it should command a rising relative wage. It does not.

*And the aggregate overclaims.* Services vs goods is +1.3pp over six and a half
years — real, but nothing like a "structural floor."

**What it changed.** Limb C splits in two and only one half survives. New
falsifier **f12** (state `warming`, not tripped — construction demand was soft
over part of the window, which is a confound that happens to favour the thesis,
so it is stated rather than leaned on). Indicator `wagesvc` set to **mixed**; a
status the scale did not previously have.

**Second repricing shipped**, kept as a list alongside the first so the trail of
which evidence moved which position stays visible:
- **Down** EME, PWR, MYRG, IESC — already froth-3 with no margin of safety on
  price; now the mechanism underneath them is unevidenced too.
- **Hold** FIX, APG, LMB — maintenance-weighted, and installation/maintenance
  /repair *is* running +3.0pp hot. The distinction is the finding.
- **Up** ATGE, AMN, LOPE — care-labour supply, now double-confirmed by ECI wages
  and by AACN's 93,000 turned-away applicants.
- **Down** ENSG, BKD, HCSG, NHC, WELL on the cost side. This **compounds
  iteration 1**: falling per-capita volumes *and* the fastest-rising labour costs
  in the economy, hitting the same P&Ls.

The matrix's "care-labour cost" internal contradiction is no longer an argument;
it is a measurement, and it is now sourced.

**Next three, re-ranked (superseded by iteration 3):**
1. **SEC XBRL fundamentals.** Now clearly top. Two iterations have moved six
   position groups on macro evidence alone, without once checking whether the
   companies' own filings support the calls. That gap is widening with each
   repricing.
2. **Apprenticeship completions (DOL).** Promoted by f12 — it is the independent
   second read on whether trades scarcity is real. If completions are also
   healthy, f12 moves toward tripped and the contractor sleeve should go, not
   shrink.
3. **Medicaid personal care utilisation.** Still open; still the untested half of
   the aging-in-place book.

---

## Iteration 3 — 2026-08-07 — SEC XBRL fundamentals

**Why:** two iterations had moved six position groups on macro evidence without
once checking whether the companies agreed. This is also the first of the two
required adversarial passes — the explicit goal was to test my own calls, not to
add supporting evidence.

**Source.** SEC EDGAR XBRL frames API, keyless and unquota'd. Revenue (three
us-gaap tags with fallback) and OperatingIncomeLoss, CY2019–CY2025, 110 of 126
names. Sixteen names file outside the SEC and cannot be covered — a structural
gap, now on the unsourced list.

**Three tests. The thesis lost two.**

*1 — the utilisation finding was over-applied.* Care-delivery revenue compounded
at a **9.9% median** through the decade per-capita SNF days fell 31%: ENSG 16.4%,
PNTG 18.7%, OPCH 16.1%. Consolidators outgrow fragmented shrinking markets. The
finding is a market-**size** warning, not a company-**revenue** prediction.
**Reversed the iteration-1 ENSG downgrade** — revenue +16.4% CAGR, margin +2.1pp.
f11 severity 3 → 2.

*2 — the wage squeeze hit the wrong row.* Operator margins did not compress
(median **+0.3pp**; ADUS +4.3, OPCH +6.0, AVAH +7.7). The staffing agencies took
it: **AMN −10.0pp, revenue $5.24bn peak → $2.73bn, margins now negative**; CCRN
−6.1pp. **Reversed the iteration-2 AMN raise**, cut to conviction 1. Inverted the
matrix's care-labour mitigation: avoid the intermediaries, not the operators.

*3 — contractor margins undercut f12.* Median **+5.1pp** expansion on 10–42%
revenue growth (APG +23.3, IESC +7.5, EME +5.1). Pricing power by a route the
wage data doesn't capture — the constraint may be contractor capacity, not labour
cost. f12 severity 3 → 2; reduction softened to a valuation call.

**Unprompted finding:** the automation sleeve — highest carry in the book,
explicitly priced for growth — has a **3.7% median revenue CAGR**, weakest of ten
verticals. Six years is long enough to need evidence.

**Universe hygiene — four corporate-action errors found:**
- **BK → BNY** (rebrand). Explains why the market robot could never price it.
- **ATGE → CVSA** (Adtalem → Covista, 10-K filed 2026-08-06). One of the
  highest-conviction names in the book, carrying a dead ticker.
- **AMED delisted** August 2025 on completion of its acquisition — carried as a
  live position for a year. Removed to `excluded.json`.
- **CCRN** filing to deregister.

Two engineering notes. The naive delisting rule (any Form 25/15 in recent
filings) produced **43 flags on 116 names** — large issuers routinely deregister
individual bond and preferred classes, so Lilly and Morgan Stanley looked like
they were delisting. Rewrote around ticker-absence, ticker-mismatch and filing
staleness: 3 high-severity, 12 low. Separately, `FIX` CY2025 came through at
$1.83bn against $7.03bn — a partial-period tagging artifact that would have shown
a fast-growing contractor as shrinking. Terminal years collapsing below 55% of
the prior year are now dropped and logged.

**Shipped:** `scripts/fetch_fundamentals.py` + weekly workflow; filed revenue and
margin on every company card; a corporate-action panel on Act now; a third
repricing recording both reversals; **a new CI gate that fails the push if any
structured ticker reference doesn't resolve to the universe** — the check that
would have caught BK and ATGE a year ago.

**Next three:**
1. **Apprenticeship completions (DOL).** f12 is now genuinely unresolved — wages
   say no scarcity, margins say pricing power. Completions-versus-retirements is
   the independent third read that breaks the tie.
2. **Medicaid personal care utilisation.** Still the untested half of the
   aging-in-place book, and ADUS is now a bigger position in relative terms.
3. **A non-US fundamentals route.** Sixteen names — including most of the
   private-pay sleeve, the part that has survived every finding — have no
   filings check at all. Company IR pages or exchange filings are free.

## Iteration 4 — 2026-08-07 — Trades scarcity: the third read

**Why:** f12 was left genuinely unresolved after iteration 3 — wages said no
scarcity, margins said pricing power. A falsifier sitting at `warming` on
contradictory evidence is the worst state to leave one in, and the contractor
sleeve was still carrying the top entry-window slot on the strength of it.

**The intended source failed.** DOL apprenticeship data is not usable: the
department's own statistics page is still headed *FY 2021* and carries no
machine-readable files. Rather than approximate it, I substituted a better
instrument — **BLS Employment Projections publish a labour force EXIT rate by
occupation**, the share projected to leave the workforce annually. That is a more
direct test of the premise than completions would have been, since the claim is
about retirement rather than about intake.

**The result is decisive, and it goes against the thesis.**

| Occupation | Exit rate | vs 4.7% baseline |
|---|---|---|
| Home health & personal care aides | **8.6%** | **+3.9pp** |
| Healthcare support (all) | 7.3% | +2.6pp |
| Nursing assistants | 6.6% | +1.9pp |
| Electricians | 3.2% | −1.5pp |
| Construction & extraction (all) | **3.1%** | **−1.6pp** |
| HVAC mechanics | 2.9% | −1.8pp |
| Carpenters | 2.8% | −1.9pp |
| **Registered nurses** | **2.8%** | **−1.9pp** |

**f12 is TRIPPED.** Every construction trade ages out *slower* than the workforce
average — the exact opposite of the premise. Across three independent reads: two
against (wages, exit rates), one for (margins), and the supportive one is equally
explicable by a datacentre capex cycle. The falsifier was written to retire the
contractor sleeve if this premise failed. It failed. **EME, PWR, MYRG and IESC
come out of the thesis**, EME is removed from the entry windows, and the "right
thesis, wrong price" note is replaced with "retired, not merely expensive."

**Limb C splits three ways and is cut to conviction 2.** Only care support
survives, and it survives on every read: highest exit rate, highest openings
(17.6% of employment annually), fastest wage growth (+9.2pp).

**Third self-correction in two iterations.** Registered nurses exit *below*
baseline at 2.8% with 4.9% employment growth over the decade — so the "nursing
shortage" is not the retirement story the thesis told, and the CVSA position
raised hours earlier rests on the wrong mechanism. Re-based rather than cut: the
AACN 93,000 turned-away figure is measured **applicant** demand and tuition is
paid by students, not by the employment market. Held at 3 with the reasoning
rewritten and RN employment growth added as the thing that would break it.

**Raised instead:** ADUS, AVAH, PNTG. They employ the single highest-churn
occupation in the US economy, and the filings show them expanding margins anyway
(ADUS +4.3pp, AVAH +7.7pp). Cost risk confirmed severe and demonstrably managed —
a competence signal rather than a warning.

**Shipped:** `projections` as a seventh auto-refreshed reference block; an exit-
rate panel under limb C; the fourth repricing; f12 rendered as the first tripped
falsifier on the board.

**Scoreboard after four iterations.** Eight indicators read: four confirming, two
contradicting, one split, one mixed. One falsifier tripped, two warming. Four
position groups reversed or retired, three of them reversals of my own earlier
calls. The dashboard is materially less confident than it was on Wednesday, which
is the point.

**Next three:**
1. **Medicaid personal care utilisation.** Now the most important open item by
   some distance — ADUS and AVAH have just been raised into the highest-churn
   labour market in the country, and their reimbursement side is still untested.
2. **A non-US fundamentals route.** Sixteen names, including most of the
   private-pay sleeve — the only part of the book that has survived every single
   finding, which makes its untested status the most uncomfortable gap left.
3. **Fund flows by investor age.** Limb A is now the least-tested limb; every
   iteration so far has hit C and D.

## Iteration 5 — 2026-08-07 — Medicaid personal care

**Why:** iteration 4 raised ADUS, AVAH and PNTG into the highest-churn labour
market in the country without having tested who pays them. The Medicare datasets
used in iterations 1 and 3 do not touch Medicaid personal care at all.

**Source hunt.** DOL-style dead end first: the Medicaid catalogue's metadata is
poor (the 1915(c) dataset's description is about well-child visits) and
distributions carry no download URLs unless you request reference IDs. Two usable
series once resolved, both keyless, both now discovered from the catalogue at run
time rather than hardcoded.

**Confirming, and from a completely separate dataset to iteration 1.**

*Medicaid is rebalancing toward home care.* 1915(c) HCBS waiver enrolment among
65+ went **686,607 (2020) → 1,043,473 (2022), +52%**, against 18% growth in the
65+ Medicaid population. Penetration **8.31% → 10.66%** — waiver enrolment grew
nearly three times faster than eligibility.

*And it survived the unwinding.* Managed LTSS enrolment rose **399,031 → 429,894
across 2023–24 (+7.7%)** while total Medicaid managed care **fell 13%**, from
85.0M to 73.7M. The aged and disabled LTSS population is categorically eligible
and was insulated from the disenrolment that removed millions of working-age
adults. That was the blind spot I expected to have to declare, and the MLTSS
series closed it.

**But it measures volume, not rate — and rate is the actual risk.** Medicaid LTSS
expenditure reporting stops at **FY2020** and is PDF only. The payer's price
behaviour is not observable at zero cost. Recorded as a permanent limitation
rather than an open task: any route to it runs through state budget documents one
at a time, which is real work, not a fetch.

**Shipped:** `medicaid` as an eighth reference block; a new P1 indicator (`hcbs`)
read on arrival; sourced evidence on the aging-in-place theme, plus a themes
renderer that actually displays `sourced` blocks — it had been silently ignoring
them; the fifth repricing, deliberately split into a "confirmed" move and a
"but the rate side is blind" hold on the same names.

**Also, unprompted:** added a favicon. All three research dashboards were
identical default globes in a tab bar. This one is the cohort clock at 16px — the
four age bands in the dashboard's own palette. The siblings should take their own
marks in the same style rather than reusing it.

**Scoreboard after five.** Nine indicators read: six confirming, two
contradicting, one mixed. One falsifier tripped, two warming. Five repricings,
three of which reversed my own earlier calls.

**Next three:**
1. **A non-US fundamentals route.** Sixteen names, including most of the
   private-pay sleeve — the only part of the book that has survived every single
   finding. Its untested status is now the most uncomfortable gap left.
2. **Fund flows by investor age.** Limb A remains the least-tested limb; five
   iterations have hit C and D almost exclusively.
3. **Term premium / the A-vs-E rate contradiction.** Weakness w2 says the rate
   view must be an explicit dated call. It still is not one, and the Treasury
   FiscalData API is keyless.

## Iteration 6 — 2026-08-07 — The untested sleeve

**Why:** sixteen names filed outside the SEC and were therefore exempt from the
filings pass that corrected two calls in iteration 3. Most of the private-pay
sleeve sat in that gap — the part of the book that had "survived every finding",
for a reason that should have been obvious sooner: no evidence had ever reached it.

**Route.** yfinance income statements, the only free source for Swiss, Danish,
Italian, Australian and Japanese filers. Ten of eleven covered (Paramount Bed
still unavailable). Records carry a `provenance` field marking vendor rather than
regulator data — shorter spans, vendor tagging, lower trust.

**It tests worst in the book.** Median revenue CAGR **4.2%**, median operating
margin **−1.3pp** — against 9.9% median revenue growth in US care delivery.

| | Revenue CAGR | Margin |
|---|---|---|
| Cochlear | **+12.4%** | −0.7pp |
| Demant | +5.2% | **+1.4pp** |
| Amplifon | +4.2% | **−4.1pp** |
| Straumann | +3.9% | −2.0pp |
| **Sonova** | **−1.2%** | −1.3pp |

**Fourth self-correction: SOON.SW cut 3 → 2.** A conviction-3 core position
should not be shrinking. Three caveats stated rather than leaned on — the window
is three years, it spans the post-COVID hearing-aid normalisation, and Sonova
reports in a strengthening franc while earning globally. Cut to 2 rather than 1,
and flagged as the most urgent name to re-underwrite.

Private-pay theme structural score cut 88 → 78. Its apparent invulnerability was
an artefact of never having been measured, which is the clearest illustration yet
of why the unsourced list matters more than the resolution log.

## Iteration 7 — 2026-08-07 — The rate call, finally made

**Why:** weakness w2 has said since the first draft that the rate view must be an
explicit dated call rather than an emergent property of the other limbs. Six
iterations in, it still was not one — and the contradiction monitor was item 4 on
the original priority ladder and had never been built.

**Source.** US Treasury daily par yield curve (keyless CSV, one file per year)
and FiscalData debt-to-the-penny. Note: the FiscalData `page[size]` parameter
must be URL-encoded or the endpoint returns HTML, which cost a first attempt.

**The arbiter, read for the first time.** 10s30s: **9bp end-2022 → 20bp end-2024
→ 66bp end-2025 → 53bp now**, with the 30-year at **5.22%**. Since 2019 the long
end has repriced 283bp against 267bp at the front. Debt held by the public
$32.1tn.

**The call: bias to a steeper long end and a wider term premium. Limb E beats
limb A.** Conviction 2, reviewed by 2027-02-07, falsified if 10s30s sustainably
compresses below 20bp.

**Sized small, for a reason the loop itself produced.** v1 justified a confident
"structural short duration" on economy-wide services inflation. Iterations 2 and
4 narrowed that channel to care-support labour alone — trades wages *and* trades
exit rates both run below baseline. One occupational group, however hot, is not a
macro inflation thesis. Direction stands; size does not.

Within equities this changes little, and that is worth stating: the REIT sleeve
and the spread insurers already sit on opposite sides of this. That internal
hedge is now deliberate rather than accidental.

## Iteration 8 — 2026-08-07 — Scoring the framework

**Why:** item 5 on the original ladder, and overdue. Six iterations had produced
six repricings and five reversals, but nothing measured whether the *framework*
was being applied evenly. It was not.

**Built:** an `evidence_score` block grading each limb on indicators read,
sourced claims and falsifier status — deliberately **separate from conviction**.
Conviction is belief; grade is testing. Conflating them is exactly how a thesis
stays confident about the parts nobody has looked at.

| Limb | Grade | Conviction | Names | Read |
|---|---|---|---|---|
| C Labour | **A** | 2 | 22 | 5/6 |
| D Consumption | **B** | 3 | 50 | 2/5 |
| E Fiscal | **B** | 2 | 5 | 2/4 |
| B Transfer | **C** | 2 | 17 | **0/3** |
| H Housing | **C** | 2 | 16 | 1/3 |
| **A Decumulation** | **D** | 2 | 16 | **0/3** |

**The finding is about me, not the market.** Seven iterations of evidence landed
almost entirely on C and D. **Limb A is graded D — 16 names, conviction 2, zero
indicators read, zero sourced claims. Limb B has 17 more names and zero reads.
33 of 126 names, a quarter of the universe, never checked.** I have been testing
where testing was interesting rather than where exposure was largest.

Conviction is not cut on these grounds — absence of evidence is not evidence of
absence — but the grade now says so on the face of the dashboard, and limbs A and
B are the next two iterations regardless of what looks more interesting.

## Iteration 9 — 2026-08-07 — Limb A, the grade-D limb

**Why:** the scorecard said go here regardless of what looked interesting. Limb A
carried 16 names at conviction 2 with zero indicators read.

**Source.** Fed Distributional Financial Accounts, generation-level equity
holdings and shares — already downloaded for the wealth block, never used for
this question.

**Confirming, and cleanly.** Limb A's central claim is that the cohort dies
holding rather than decumulating.

- Boomer equity holdings **$10.89tn (2016:Q1) → $29.71tn (2026:Q1), +173%**
- Boomer equity **share 54.9% → 53.9% — down 1.0pp in a decade**, 2.7pp off a
  2020 peak of 56.6%

Share is the right measure because valuation moves every holder alike. A cohort
whose share barely budges while the market triples is not a net seller.

**The Silent generation supplies the completed cycle:** equity share **83.9%
(1990) → 15.0% (2026)** — 68.9pp over thirty-six years, roughly 2pp a year, via
mortality and transfer rather than selling. If boomers follow that path they have
three decades of runway. That is the strongest available argument that the "asset
meltdown" is a category error about *timescale*, not a wrong direction.

**And the RMD mechanism is visible:** DC pension entitlements grew 27% while
taxable equity holdings grew 173% — money leaving the tax-deferred wrapper faster
than it leaves the market, exactly as the limb predicted.

**Honest limitation:** DFA cannot separate flows from valuation, so f4 as
literally written — net outflow in fund-flow data — cannot be tested at zero
cost. This is a strong proxy, not the thing itself, and the indicator says so.

**Limb A moves D → B.** Limb B is now the sole untested limb.

## Iteration 10 — 2026-08-07 — Limb B, and the end of the free data

**Why:** the last untested limb, and the scorecard said go there.

**Source.** SEC Form ADV firm compilation feed — every registered investment
adviser with AUM and client mix, keyless, 7MB gzipped XML.

**Half the question answers; the other half turns out to be unanswerable.**

23,621 registered advisers. Within individual clients, **high-net-worth
households are 16.2% of clients but hold 67.7% of the assets** — average account
$1.90m. That corroborates the Cerulli concentration finding ($62T of $124T from
2% of households) from a completely independent source, and it explains why the
widow-then-heir sequence matters commercially: the assets worth competing for sit
in a sixth of the relationships.

**But Form ADV covers RIAs only.** Broker-dealers and wirehouses file nothing
comparable. Measuring a share *shift* needs both sides, and the only source with
both is Cerulli, which is paid. **Limb B's central claim is structurally
untestable under a zero-cost constraint** — recorded plainly rather than left as
a silent gap.

---

# Loop closed — ten iterations

**Evidence.** Ten reference blocks auto-refreshing from Census, BLS (three ways),
the Fed, CMS, Medicaid, Treasury and SEC. Eleven indicators read: eight
confirming, two contradicting, one mixed. One falsifier tripped, two warming.

**What it cost the thesis.** Six repricings, **five of which reversed my own
earlier calls**:
- ENSG cut, then restored when the filings showed 16.4% revenue CAGR
- AMN raised, then cut to 1 when revenue had halved and margins gone negative
- f12 tripped: the trades-scarcity premise refuted on wages *and* exit rates;
  EME, PWR, MYRG, IESC out of the thesis entirely
- SOON.SW cut when the private-pay sleeve — the part that had "survived
  everything" — turned out never to have been measured, and tested worst
- Limb C cut 3→2, limb D's magnitude gutted, AMED found delisted for a year

**What survived.** The age gradient (7.0x at 85+). Care-support labour scarcity,
confirmed on wages, exit rates and openings. Medicaid rebalancing toward home
care. Hospice as the only care category with rising per-capita use. And limb A's
central claim — they die holding — confirmed at last.

**What is structurally out of reach at zero cost:** Medicaid LTSS rates, the
RIA/wirehouse share shift, and true fund flows by age. Named, not hidden.

The dashboard is materially less confident than it was ten iterations ago, and
considerably harder to fool.
