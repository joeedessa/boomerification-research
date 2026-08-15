# Engineering & QA log

Every bug, data-source trap, tooling failure and analytical error hit while
building this dashboard, with what actually fixed it.

**Why this file exists.** Most of what follows cost real time to diagnose and
would cost the same again next time. Several entries are not bugs in this repo at
all — they are undocumented behaviours of government data sources that will bite
anyone who touches them. The section on *research-process errors* is deliberately
included alongside the code: the analytical mistakes were more expensive than the
software ones.

**Keep it alive.** Append to the relevant section when something new surfaces.
Each entry: symptom → root cause → fix → what it means next time. Undiagnosed
issues go in §6 rather than being left in a commit message.

---

## 1. Data-source traps

The most reusable section. Nearly all of these are undocumented.

### BLS

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1.1 | `download.bls.gov` returns **403** | BLS rejects any User-Agent **containing a URL**. The contact-email form passes. | Separate `BLS_UA` header for `bls.gov` hosts. See `get()` in `fetch_reference.py`. |
| 1.2 | Intermittent **503** on both API and flat files | BLS maintenance windows. A single-shot fetch fails a scheduled run for no reason. | Retry with backoff on 429/5xx. Fired for real mid-iteration-2 and the keep-previous-snapshot fallback worked. |
| 1.3 | Silent data truncation | Public API **caps requests at 10 years**; it truncates and tells you only in `message[]`. | Read `message[]`. For long series use flat files. |
| 1.4 | Quota exhaustion | API allows **25 queries/day** keyless. Three blocks competing for it is fragile. | Moved ECI to `download.bls.gov/pub/time.series/ci/` flat files — no quota at all. Prefer flat files for anything recurring. |
| 1.5 | `csv.DictReader` → `KeyError: 'series_id'` | BLS flat-file headers are **space-padded** and line-ended `\r\n`: `"series_id        \tyear\t..."` | Split manually and `.strip()` every field. Do not trust `DictReader` on BLS files. |
| 1.6 | Guessed series IDs return "Series does not exist" | ECI IDs are **not derivable** from the pattern. Five guesses failed (`CIU2020000620000I` etc.); the real one is `CIS1026200000000I`. | Download `ci.series` and grep the titles. Never guess a BLS series ID. |
| 1.7 | CES series return "Database is locked" | Persistent BLS-side lock on the CES database, not transient. | No fix. Used ECI instead — better instrument anyway since it controls for composition. |

### Census

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1.8 | Population figures came out **half** the true value | The projections workbook **stacks Total / Male / Female panels** in one sheet. Keying a dict by row label meant the Female panel silently overwrote the Total. | Take the **first occurrence** of each label. This produced plausible-but-wrong numbers — the worst failure mode, since nothing errors. |
| 1.9 | 2024/2025 vintage directories 404 | 2023 is still the current National Population Projections vintage. | Pin 2023; the fetcher fails loudly if the table shape changes. |

### CMS / Medicare

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1.10 | Geographic Variation PUF has no fine age bands | National level only splits `<65` / `>=65`. | Age detail comes from **CMS Program Statistics** instead — different dataset, ZIP/xlsx only, no API. |
| 1.11 | Hardcoded CMS file URL would rot | Program Statistics files are **year-stamped** in the path. | Discover the newest from `data.cms.gov/data.json` at run time. |
| 1.12 | Standardised payments looked like volume growth | CMS "standardized" strips *geography*, not annual **rate updates**. Dollars conflate price with utilisation. | Use per-1,000-beneficiary counts only. Never use CMS dollars for a volume question. |

### Medicaid

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1.13 | Dataset descriptions are wrong | The 1915(c) waiver dataset's description is **about well-child visits**. Catalogue metadata is unreliable. | Ignore descriptions; inspect the actual CSV. |
| 1.14 | Distributions have no `downloadURL` | Only returned when you pass **`show-reference-ids=true`**. | Always request reference IDs against `data.medicaid.gov`. |
| 1.15 | LTSS expenditure data unavailable | CMS **stopped machine-readable publication after FY2020**; reports are PDF and five years stale. | **Unfixable at zero cost.** Recorded as a permanent limitation — this is the rate side of ADUS/AVAH and it cannot be tracked. |

### Treasury / SEC / DOL

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1.16 | FiscalData returns HTML, `json.load` explodes | **`page[size]` must be URL-encoded** as `page%5Bsize%5D`. Unencoded, it silently serves HTML with a 200. | Encode square brackets. A 200 is not proof of JSON. |
| 1.17 | `company_tickers.json` missing live filers | SEC's ticker files **omit real companies** — BK, CCRN, ATGE, AMED were all absent. | Try `company_tickers_exchange.json` too, then an explicit `CIK_OVERRIDES` map. |
| 1.18 | **Guessed CIK resolved to the wrong company** | Guessed ATGE = 730464. That CIK *was* DeVry→Adtalem, but is now **Covista**, an unrelated-looking entity. A plausible-looking wrong answer. | Always verify against `data.sec.gov/submissions/CIK…json` and check `formerNames`. Never guess a CIK. |
| 1.19 | Revenue missing for many filers | Revenue tagging is **genuinely inconsistent** across filers. | Try `Revenues` → `RevenueFromContractWithCustomerExcludingAssessedTax` → `…IncludingAssessedTax`, first hit wins. Cross-company *levels* remain indicative only. |
| 1.20 | A fast-growing contractor appeared to be **shrinking** | `FIX` CY2025 came through as **$1.83bn against $7.03bn** the prior year — a partial-period tagging artifact in the CY frame. | Drop terminal years below 55% of prior and **log them** (`dropped_partial_periods`). One bad cell nearly drove a position. |
| 1.21 | 43 delisting flags on 116 names | Naive rule flagged any Form 25/15. Large issuers **routinely deregister individual bond and preferred classes** — Lilly and Morgan Stanley looked like they were delisting. | Rebuilt around ticker-absence, ticker-mismatch and filing staleness. 43 → 3 high / 12 low. |
| 1.22 | DOL apprenticeship data unusable | The department's statistics page is still headed **FY 2021** with no machine-readable files. | Substituted BLS Employment Projections *labour force exit rate* — a better instrument for the actual question anyway. |

### General fetching

- **1.23 — `WebFetch` 403s on most `.gov`.** ssa.gov, congress.gov, dol.gov, bls.gov and cnbc.com all refuse it. Use `curl` with a browser-ish UA, or find a mirror. Several facts were sourced from analysis sites because the primary refused automated fetches.
- **1.24 — vendor data for non-US filers.** yfinance `income_stmt` works for `.SW`, `.CO`, `.MI`, `.AX`, `.T` tickers but gives only 3–5 years with vendor tagging. Records carry a `provenance` field so this is never confused with regulator data.

---

## 2. Application bugs

| # | Bug | Cause | Fix |
|---|---|---|---|
| 2.1 | Band colour rendered as invalid CSS | Typo `"#D9770 6"` — a space inside a hex value. | JSON validates; CSS does not. Nothing caught it but the eye. |
| 2.2 | Matrix cells unreadable at high intensity | Text tinted with the *same* colour as its background tint. | Step text to `--color-text-primary` once a cell is filled. |
| 2.3 | Entry-window header read `#1817.42` | Rank and price concatenated with no separator. | Emit the separator only when a quote exists — the five names the fetch missed still render a clean rank. |
| 2.4 | Chart label read "millions — millions…" | Heading hardcoded "millions" *and* appended the units string. | Let the sourced units string own it. |
| 2.5 | **Evidence written into themes never rendered** | `buildThemes` silently ignored `sourced` blocks. Data was correct; the view dropped it. | Added the renderer. **Class of bug to watch: adding a field to JSON without touching the view is a silent no-op.** |
| 2.6 | Glossary search box unstyled | Styling was bound to `#co-q` by ID, so a second input inherited nothing. | Shared `.srch` class. |
| 2.7 | Chart broke when series moved to `reference.json` | Shape changed from list-of-objects to dict-keyed-by-band. | Build the stack from `CLOCK.bands` order and ignore derived aggregates like `total65plus`. |
| 2.8 | `repricing` → `repricings` | Went from single object to list; renderer expected an object. | Renderer accepts both; history is now visible rather than overwritten. |
| 2.9 | **Fabricated favicon base64** | I wrote a base64 PNG from memory as a "fallback". It was invented data that had never been verified to decode. | Caught before commit; replaced with a genuinely generated 32×32 PNG. **Never emit encoded binary from memory.** |

---

## 3. Research-process errors

The expensive ones. All were caught by later evidence, which is the argument for
the falsifier discipline rather than a point in its favour.

- **3.1 — Confused a market-size finding with a company-revenue prediction.**
  Per-capita SNF utilisation is falling, so I cut ENSG. The filings then showed
  16.4% revenue CAGR *through* that decline — consolidators outgrow fragmented
  shrinking markets. **A sector finding is not a company conclusion.**

- **3.2 — Applied a mechanism to the wrong party.** Raised AMN on "whoever
  supplies scarce labour has pricing power". False for intermediaries: AMN's
  revenue halved and margins went negative while its *customers'* margins
  expanded. **Ask who captures the rent, not who is near it.**

- **3.3 — Never tested the sleeve that kept surviving.** The private-pay names
  "survived every finding" because sixteen non-SEC filers were structurally
  exempt from every evidence pass. First time measured, they tested worst.
  **Apparent invulnerability is usually an artefact of not looking.**

- **3.4 — Tested where interesting, not where exposed.** Seven iterations landed
  almost entirely on limbs C and D while 33 names sat on limbs with zero
  indicators read. Fixed by building an **evidence grade** separate from
  conviction, which made the imbalance visible on the dashboard.

- **3.5 — Badly specified indicator.** "Services vs goods wage growth" was too
  aggregate to test a claim about *non-tradable licence-gated* services. The
  aggregate showed +1.3pp; the occupational cut showed +9.2pp for care and
  −0.7pp for construction. **Specify the indicator at the resolution of the
  claim.**

- **3.6 — Left a falsifier at `warming` on contradictory evidence.** f12 sat
  unresolved between wage data (against) and margin data (for) while the
  contractor sleeve kept the top entry-window slot. **Contradictory evidence
  demands a third read, not a middle state.**

- **3.7 — Internal inconsistency after repricing.** AMN was cut to conviction 1
  while still ranked an entry window; EME was retired by a tripped falsifier
  while still ranked #1. **A cut name cannot also be a buy candidate — check
  downstream lists whenever a call moves.**

- **3.8 — Stale universe references.** BK had renamed to BNY, ATGE to CVSA, and
  AMED had been delisted **for a year** while carried as a live position. Nothing
  checked. Fixed by automated corporate-action detection plus a **CI gate that
  fails the push if any structured ticker reference does not resolve**.

---

## 4. Environment & tooling

- **4.1 — No `node` locally.** JS syntax checking happens only in CI. Verify app
  changes by exercising every view in the browser and reading the DOM.
- **4.2 — `timeout` is not on macOS.** Use the Bash tool's own `timeout` param.
- **4.3 — PEP 668.** `pip3 install` needs `--break-system-packages` here.
- **4.4 — No `openpyxl`.** All xlsx parsing is stdlib `zipfile` + `ElementTree`
  so it runs in a bare Actions container. Header/sheet discovery goes through
  `workbook.xml.rels` because sheet order ≠ file order.
- **4.5 — Port conflicts.** Other sessions hold ports; use `autoPort` in
  `.claude/launch.json`.
- **4.6 — Screenshots blank after programmatic scroll** in the browser pane.
  Verify scrolled content by reading the DOM instead; top-of-page screenshots
  work fine.
- **4.7 — Git conflicts with the bots.** `reference.json` conflicted with
  `reference-data-bot` three times. Resolve by taking the local version **after
  verifying it has more blocks**, never blindly.
- **4.8 — Heredoc quoting.** Python 3.14 + nested f-string quotes inside `<<'EOF'`
  breaks easily. Keep heredoc Python simple; use `.format()` or plain
  concatenation for anything nested.

---

## 5. What now prevents recurrence

| Guard | Catches |
|---|---|
| CI: JSON validity | Malformed data files |
| CI: referential integrity | Limb / vertical / theme IDs that don't resolve |
| CI: **ticker resolution** | Stale symbols in matrix, repricings, entry windows (§3.8) |
| CI: `node --check` on extracted script blocks | JS syntax errors (§4.1) |
| `fetch_fundamentals`: corporate-action detection | Renames, delistings, stopped reporting |
| `fetch_fundamentals`: partial-period guard | §1.20 |
| `fetch_reference`: keep-previous-snapshot | Transient source outages (§1.2) |
| `fetch_reference`: shape assertions | Census panel/format changes (§1.8) |
| Workflow validation: coverage floor | Silent collapse in SEC tagging |
| `provenance` field | Vendor data mistaken for regulator data (§1.24) |

---

## 6. Open / recurring

- **Screenshot-after-scroll** (§4.6) — unresolved, worked around.
- **Bot merge conflicts** (§4.7) — recurring by design; two robots write to the
  repo on schedules. Acceptable, but resolve deliberately.
- **`7817.T` (Paramount Bed)** — no free financials from any route tried.
- **Structurally unavailable at zero cost**, named so they are not mistaken for
  open tasks: Medicaid LTSS **rates** (§1.15), the RIA/wirehouse **channel share
  shift** (Form ADV sees only one side), and true **fund flows by age** (Fed DFA
  cannot separate flows from valuation).
- **Silent-no-op class** (§2.5) — adding a JSON field without a renderer produces
  no error. No guard exists. Worth one if it recurs.

---

## 7. Pre-flight checklist

Before shipping a change here:

1. `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('data/*.json')]"`
2. Referential integrity **including ticker resolution** — CI runs it; run it locally first.
3. If a JSON field was added, **confirm a renderer consumes it** (§2.5).
4. If a call moved, **check the downstream lists** — entry windows, matrix rows, repricings (§3.7).
5. Serve the app, exercise every view, check the console, check light **and** dark.
6. If a fetch script changed, run it locally **and** confirm the workflow succeeds in Actions — a script that only works on one machine is not done.
7. Never guess an identifier — CIK, series ID, ticker. Verify it (§1.6, §1.18).
8. Never emit encoded binary or precise figures from memory (§2.9).
