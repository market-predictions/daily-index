# Daily Index OS — System Index

This file is the **first entry point** for meaningful work on `market-predictions/daily-index`.

## Purpose
This repository contains a dedicated operating system for structured **weekly AEX index option plays**.

The architecture is designed to keep four layers separate:
- decision framework
- input / state contract
- output contract
- operational runbook

## Canonical control files
- `control/CURRENT_STATE.md`
- `control/NEXT_ACTIONS.md`
- `control/DECISION_LOG.md`
- `control/PROJECT_BOOTSTRAP.md`
- `control/CHATGPT_PROJECT_INSTRUCTIONS.md`
- `control/OPTIONAL_CUSTOM_GPT_SPEC.md`

## Canonical execution files
### Framework files
- `prompts/aex_weekly_options/01_DECISION_FRAMEWORK.md`
- `prompts/aex_weekly_options/02_INPUT_STATE_CONTRACT.md`
- `prompts/aex_weekly_options/03_OUTPUT_CONTRACT.md`
- `prompts/aex_weekly_options/04_OPERATIONAL_RUNBOOK.md`

### Snapshot / data producers
- `build_aex_primary_technical_snapshot.py`
- `build_aex_cross_market_confirmation.py`
- `build_aex_option_surface_snapshot.py`
- `run_aex_snapshot_suite.py`

### Report / validation / delivery
- `generate_weekly_aex_option_review.py`
- `validate_aex_trade_plan.py`
- `send_aex_options_report.py`

### Workflows
- `.github/workflows/refresh-aex-snapshots.yml`
- `.github/workflows/build-weekly-aex-review.yml`
- `.github/workflows/validate-aex-trade-plan.yml`
- `.github/workflows/send-weekly-aex-options.yml`

## Operating model
Read the repository in four layers.

### 1. Decision framework
Strategic regime, approved financing families, burden-of-proof rules, and no-trade default.

### 2. Input / state contract
Defines the AEX-primary technical layer, cross-market confirmation layer, option-surface layer, and risk state.

### 3. Output contract
Defines the weekly report, machine trade plan, and required state updates.

### 4. Operational runbook
Defines automation levels, refresh order, timing gates, validation gates, and delivery behavior.

## Session start rule
For architecture work, debugging, workflow changes, or state-authority work, read in this order:
1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

## Non-negotiable discipline
- Do not let technicals become the only decision engine.
- Do not collapse the four layers into one giant prompt.
- Do not treat “covered writing” as a vague concept.
- Do not force trades; **no-trade** is the default until the burden of proof is met.
- Do not claim delivery succeeded without a manifest or receipt.
- Do not treat incomplete public option-chain coverage as if it were production-grade surface data.
