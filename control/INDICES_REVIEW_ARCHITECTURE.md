# Weekly Indices Review — Architecture

## Purpose
This file defines the intended architecture for the new **Weekly Indices Review** product inside `market-predictions/daily-index`.

The goal is to publish a premium weekly report for a model portfolio of stock-index exposures that is:
- comparable in end-user value and presentation quality to ETF Review
- cleaner in state authority than current ETF production
- explicit about benchmark vs tradable implementation logic
- operationally auditable through GitHub outputs and delivery receipts

---

## Core product definition
Weekly Indices Review is a **model portfolio review** for stock-index exposures.

It is not:
- a pure macro commentary product
- a pure ETF review
- a futures-only system
- an options-structure recommendation product

It should combine:
- macro regime
- geopolitical regime
- second-order transmission
- regional / style / size leadership
- portfolio allocation decisions
- continuity-aware recommendations
- implemented portfolio valuation

---

## Four-layer architecture

### 1. Decision framework
The system decides:
- which index exposures best fit the current regime
- which current exposures still deserve capital
- which exposures are replaceable
- which new exposures deserve promotion into the live opportunity board
- how the implemented model portfolio changes through time

### 2. Input / state contract
The system resolves:
- latest stored portfolio state
- latest pricing audit
- benchmark index closes
- tradable proxy closes
- FX basis
- continuity memory
- current constraints

### 3. Output contract
The system must produce:
- a premium markdown report
- machine-readable portfolio / recommendation state
- HTML and PDF delivery artifacts
- a manifest / receipt after delivery

### 4. Operational runbook
The weekly cycle runs:
1. control-layer read
2. pricing pass
3. regime classification
4. second-order map
5. candidate exposure discovery
6. scoring / ranking
7. portfolio implementation
8. report generation
9. GitHub write
10. render / send
11. manifest / receipt

---

## Core object model

### Exposure object
The primary unit is an **index exposure**, not an ETF sleeve and not an options structure.

Each exposure should carry:
- `exposure_id`
- `display_name`
- `benchmark_symbol`
- `benchmark_name`
- `primary_proxy`
- `alternative_proxy`
- `region`
- `style`
- `direction`
- `role`
- `original_thesis`

### Valuation object
Each held exposure should store both:
- benchmark index close
- tradable proxy close

### Recommendation object
Each weekly cycle should produce:
- action bucket
- score
- conviction tier
- funding/replacement logic
- continuity state

---

## Benchmark vs proxy authority

### Benchmark index closes govern
- analysis
- regime interpretation
- opportunity-board framing
- regional/style leadership interpretation
- narrative comparison across markets

### Tradable proxy closes govern
- share counts
- market value
- weights
- cash
- total portfolio NAV
- equity curve

### Design rule
The report should remain **indices-first in identity**, but **proxy-based in implementation realism**.

---

## Proposed output artifacts

### Human-readable report
- `output_indices/weekly_indices_review_YYMMDD.md`
- or versioned same-day equivalent

### Pricing audit
- `output_indices/pricing/index_price_audit_YYYYMMDD.json`

### Implementation state
- `output_indices/index_portfolio_state.json`
- `output_indices/index_trade_ledger.csv`
- `output_indices/index_valuation_history.csv`
- `output_indices/index_recommendation_scorecard.csv`

### Recommendation plan
- `output_indices/index_recommendation_plan_YYMMDD.json`

### Delivery artifacts
- rendered HTML
- PDF
- delivery manifest / receipt

---

## Required report structure

# Weekly Indices Review YYYY-MM-DD

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive Summary
## 2. Portfolio Action Snapshot
## 3. Global Regime Dashboard
## 4. Index Opportunity Board
## 5. Key Risks / Invalidators
## 6. Bottom Line
## 7. Equity Curve and Portfolio Development
## 8. Regional / Style Allocation Map
## 9. Second-Order Effects Map
## 10. Current Position Review
## 11. Best New Index Opportunities
## 12. Portfolio Rotation Plan
## 13. Final Action Table
## 14. Position Changes Executed This Run
## 15. Current Portfolio Holdings and Cash
## 16. Continuity Input for Next Run
## 17. Disclaimer

---

## Delivery model
The delivery model should follow the ETF production pattern:
- a new production report markdown file is written to the canonical output path
- GitHub Actions triggers on that report output path
- rendering occurs
- email is sent
- manifest / receipt is written
- completion is not claimed without positive evidence

---

## Non-negotiable design rules
- Keep the report compact and premium.
- Keep the control layer explicit.
- Keep benchmark and proxy authority separate.
- Keep AEX options logic out of the primary indices runtime.
- Keep the workflow operationally gated to production report outputs only.
- Keep machine-readable state files as first-class outputs.
- Keep the user-facing product comparable in feel to ETF Review.

---

## Migration rule
Do not replace the repo with a blind copy of `daily-etf`.

Instead:
- use `daily-etf` as the donor for:
  - runtime prompt structure
  - premium editorial layer
  - pricing-audit discipline
  - render/send logic
  - push-trigger workflow model
- use `daily-index` as the host for:
  - control layer
  - explicit state files
  - long-term architecture
  - multi-product clarity
