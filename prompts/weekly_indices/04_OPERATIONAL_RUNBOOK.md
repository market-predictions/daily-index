# Weekly Indices Review — Operational Runbook

## Purpose
Define how the Weekly Indices Review is run and delivered.

## Core principle
This is an **analysis-to-allocation** system first, not a blind execution engine.

## Weekly execution sequence
### Step 1 — read control layer
1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`

### Step 2 — resolve latest portfolio and state
### Step 3 — run pricing pass
### Step 4 — classify macro regime
### Step 5 — classify geopolitical regime
### Step 6 — build second-order effects map
### Step 7 — run open discovery across candidate exposures
### Step 8 — score current positions and new challengers
### Step 9 — implement updated model portfolio
### Step 10 — write report and state artifacts
### Step 11 — render and deliver
Use `send_index_report.py` to:
- validate structure
- render HTML
- render PDF
- optionally send email
- produce a delivery manifest

## Workflow rule
The production send workflow should trigger only on new production report outputs under `output_indices/`.

## Cleanup rule
Keep the repo lean. Add only files that belong to the operating system.
Do not clutter the repo with temporary drafts unless they are part of a repeatable workflow.
