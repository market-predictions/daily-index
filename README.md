# Daily Index OS

A clean operating system for structured **European weekly AEX index option plays**.

## Purpose
This repository is the dedicated home for the index-options workflow that should not live as an add-on inside the FX repo.

The system is designed to:
- evaluate weekly AEX option opportunities through a **macro + technical + options-surface + risk-budget** framework
- treat **technicals as confirmation**, not as the full decision engine
- keep **no-trade** as the default burden-of-proof state
- produce both a **human report** and a **machine-readable trade plan**
- maintain explicit state files for portfolio, valuation, and Greeks/risk exposure
- support a phased path from **manual approval** to higher automation

## Core architecture
The repository is split into four layers:

1. **Decision framework**  
   Strategic regime, structure approval logic, financing-family rules.

2. **Input / state contract**  
   What data is authoritative and how conflicts are resolved.

3. **Output contract**  
   Required report structure, trade-plan JSON, state updates, delivery expectations.

4. **Operational runbook**  
   How the system is run each week.

## Current scope
The initial build implements the operating system, validation rules, templates, delivery script, and workflow scaffolding.

It does **not** yet include a live market-data provider for:
- AEX option chains
- implied volatility / skew / term structure snapshots
- broker execution

Those provider integrations can be added later without changing the operating model.

## Repo map
- `control/` — operating memory and restart files
- `prompts/aex_weekly_options/` — split framework files
- `templates/` — JSON templates for core state and input artifacts
- `output_aex/` — generated reports and state files
- `send_aex_options_report.py` — render / validate / optional delivery script
- `.github/workflows/send-weekly-aex-options.yml` — workflow skeleton

## First rule
For any meaningful architecture, debugging, prompt, workflow, or state task, start with:

1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`

and only then open the minimum relevant execution file(s).
