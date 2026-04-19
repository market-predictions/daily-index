# Daily Index OS — System Index

This file is the **first entry point** for meaningful work on `market-predictions/daily-index`.

## Purpose
This repository now contains two product tracks:

1. **Weekly Indices Review** — the primary active report product for a model portfolio of stock-index exposures with recommendations, continuity, valuation tracking, and delivery.
2. **AEX Weekly Options** — a parked but preserved options-native track for structured AEX option analysis, machine trade plans, and later possible reuse.

The architecture must keep four layers separate:
- decision framework
- input / state contract
- output contract
- operational runbook

Do not collapse those four layers back into one opaque prompt.

---

## Canonical control files
- `control/CURRENT_STATE.md`
- `control/NEXT_ACTIONS.md`
- `control/DECISION_LOG.md`
- `control/PROJECT_BOOTSTRAP.md`
- `control/CHATGPT_PROJECT_INSTRUCTIONS.md`
- `control/OPTIONAL_CUSTOM_GPT_SPEC.md`
- `control/INDICES_REVIEW_ARCHITECTURE.md`

---

## Canonical execution files

### Weekly Indices Review — primary active track
- `index.txt`
- `index-pro.txt`
- `prompts/weekly_indices/01_DECISION_FRAMEWORK.md`
- `prompts/weekly_indices/02_INPUT_STATE_CONTRACT.md`
- `prompts/weekly_indices/03_OUTPUT_CONTRACT.md`
- `prompts/weekly_indices/04_OPERATIONAL_RUNBOOK.md`
- `pricing_indices/`
- `send_index_report.py`
- `.github/workflows/send-weekly-indices-report.yml`
- `output_indices/`

### AEX Weekly Options — parked but preserved track
- `prompts/aex_weekly_options/01_DECISION_FRAMEWORK.md`
- `prompts/aex_weekly_options/02_INPUT_STATE_CONTRACT.md`
- `prompts/aex_weekly_options/03_OUTPUT_CONTRACT.md`
- `prompts/aex_weekly_options/04_OPERATIONAL_RUNBOOK.md`
- `build_aex_primary_technical_snapshot.py`
- `build_aex_cross_market_confirmation.py`
- `build_aex_macro_snapshot.py`
- `build_aex_option_surface_snapshot.py`
- `run_aex_snapshot_suite.py`
- `build_aex_structure_candidates.py`
- `refresh_aex_portfolio_and_risk_state.py`
- `generate_weekly_aex_option_review.py`
- `validate_aex_trade_plan.py`
- `send_aex_options_report.py`
- `.github/workflows/refresh-aex-snapshots.yml`
- `.github/workflows/build-weekly-aex-review.yml`
- `.github/workflows/validate-aex-trade-plan.yml`
- `.github/workflows/send-weekly-aex-options.yml`
- `output_aex/`

---

## Operating model

Read the repository in four layers.

### 1. Decision framework
What the Weekly Indices Review is trying to decide:
- macro regime classification
- portfolio changes
- opportunity-board ranking
- portfolio evolution through time

### 2. Input / state contract
Where authoritative facts come from, in what order, and how conflicts are resolved.

For Weekly Indices Review this must become explicit via:
- benchmark index closes for analysis
- tradable proxy closes for implemented model-portfolio valuation
- portfolio state files
- valuation history
- recommendation plan
- pricing audits
- continuity memory

### 3. Output contract
How the final report must be structured and rendered.

The Weekly Indices Review should feel comparable to ETF Review:
- executive
- premium
- compact
- decision-useful
- continuity-aware
- operationally auditable

### 4. Operational runbook
How the review is actually executed:
- control-layer read order
- pricing pass
- regime classification
- opportunity-board construction
- portfolio scoring
- report generation
- GitHub write
- render / PDF
- email delivery
- manifest / receipt

---

## Session start rule
For architecture work, debugging, workflow changes, state-authority work, or report redesign, read in this order:

1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

---

## Non-negotiable discipline
- Do not replace the repo with a blind ETF clone.
- Do not weaken the four-layer architecture.
- Do not delete the AEX options track; preserve it but park it.
- Do not treat benchmark-index closes and tradable-proxy closes as interchangeable.
- Do not claim delivery succeeded without a manifest or receipt.
- Do not let the report become a sprawling macro dump; it must remain compact and premium.
- Do not let the production workflow send mail on non-report code changes.

---

## Current direction of travel
The target architecture is:

- `daily-index` remains the host repo
- **Weekly Indices Review** becomes the primary active report product
- **AEX Weekly Options** remains available as a parked secondary product track
- `index.txt` becomes the production runtime prompt
- `index-pro.txt` becomes the premium editorial layer
- `send_index_report.py` plus GitHub Actions become the delivery layer
- `output_indices/` becomes the canonical output/state path
- benchmark index data drives analysis
- tradable proxy data drives implemented model-portfolio valuation
