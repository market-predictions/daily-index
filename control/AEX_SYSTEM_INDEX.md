# Daily Index OS — AEX System Index

This file is the **first entry point** for meaningful AEX options work inside `market-predictions/daily-index`.

## Purpose
This repository now contains a dedicated operating system for structured **weekly AEX index option plays**.

The architecture is designed to avoid the monolith problem by separating:
- strategy logic
- state authority
- output requirements
- workflow / delivery mechanics

## Canonical AEX control files
- `control/AEX_CURRENT_STATE.md`
- `control/AEX_NEXT_ACTIONS.md`
- `control/AEX_DECISION_LOG.md`
- `control/AEX_PROJECT_BOOTSTRAP.md`

## Canonical AEX execution files
- `prompts/aex_weekly_options/01_DECISION_FRAMEWORK.md`
- `prompts/aex_weekly_options/02_INPUT_STATE_CONTRACT.md`
- `prompts/aex_weekly_options/03_OUTPUT_CONTRACT.md`
- `prompts/aex_weekly_options/04_OPERATIONAL_RUNBOOK.md`
- `send_aex_options_report.py`
- `.github/workflows/send-weekly-aex-options.yml`
- `templates/`

## Operating model
Read the AEX system in four layers.

### 1. Decision framework
Strategic regime, approved financing families, burden-of-proof rules, and no-trade default.

### 2. Input / state contract
Defines the AEX-primary technical layer, cross-market confirmation layer, option-surface layer, and risk state.

### 3. Output contract
Defines the weekly report, machine trade plan, and required state updates.

### 4. Operational runbook
Defines automation levels, refresh order, timing gates, and delivery behavior.

## Session start rule
For meaningful AEX architecture or workflow work, read in this order:
1. `control/AEX_SYSTEM_INDEX.md`
2. `control/AEX_CURRENT_STATE.md`
3. `control/AEX_NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

## Non-negotiable discipline
- Do not let the technical layer become the only decision engine.
- Do not collapse the four layers into one giant prompt.
- Do not treat “covered writing” as a vague concept.
- Do not force trades; **no-trade** is the default until the burden of proof is met.
- Do not claim delivery succeeded without a manifest or receipt.
