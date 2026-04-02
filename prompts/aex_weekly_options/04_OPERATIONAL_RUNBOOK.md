# AEX Weekly Options — Operational Runbook

## Purpose
Define how the system is run each week and how automation matures over time.

## Core principle
This is an **analysis-to-plan** system first, not a blind execution engine.

## Automation maturity levels

### Level 1 — automated research, manual approval
Allowed:
- refresh inputs
- classify regimes
- generate report
- generate machine trade plan
- update draft state artifacts
- render HTML/PDF
- email report

Not allowed:
- broker execution

### Level 2 — automated order ticket draft
Allowed:
- everything in Level 1
- generate structured order ticket suggestions

Still not allowed:
- autonomous live execution

### Level 3 — conditional auto-routing
Allowed only if:
- option-surface freshness passes
- timing gates pass
- spread thresholds pass
- event gates pass
- user has explicitly enabled it

### Level 4 — full automation
Only after extended validation and explicit opt-in.

## Recommended default
Start at **Level 1**.

## Weekly execution sequence
### Step 1 — read control layer
1. `control/AEX_SYSTEM_INDEX.md`
2. `control/AEX_CURRENT_STATE.md`
3. `control/AEX_NEXT_ACTIONS.md`

### Step 2 — refresh macro snapshot
### Step 3 — refresh AEX primary technical snapshot
### Step 4 — refresh cross-market confirmation
### Step 5 — refresh option-surface snapshot
### Step 6 — validate freshness and completeness
If freshness or required inputs fail:
- downgrade automation level
- default toward no-trade

### Step 7 — run the two regime engines
- directional regime engine
- options regime engine

### Step 8 — apply structure-family gates
Only approved financing families may be considered.

### Step 9 — apply timing / calendar gates
Reject or downgrade if:
- major event too close
- expiry too short for the thesis horizon
- new short-premium leg is too close to expiry
- spread quality is poor
- implied move is already excessive relative to expected edge

### Step 10 — apply portfolio overlap / risk-budget gates
Reject if:
- net risk concentration becomes too high
- expiration bucketing becomes too crowded
- Greeks concentration becomes unsafe
- financing depends on overselling premium

### Step 11 — default to no-trade if burden of proof fails
### Step 12 — write outputs
### Step 13 — render and deliver
Use `send_aex_options_report.py` to:
- validate structure
- render HTML
- render PDF
- optionally send email
- produce a delivery manifest

## Hard calendar / timing gates
### Calendar gate 1
Do not initiate a new financed short-premium structure inside the configured event blackout window.

### Calendar gate 2
Do not initiate a new weekly structure if time-to-expiry is shorter than the thesis horizon requires.

### Calendar gate 3
Do not initiate new structures when liquidity / spread thresholds fail.

### Calendar gate 4
Do not approve a structure solely because the directional regime is clear if the options regime is unattractive.

## Cleanup rule
Keep the repo lean. Add only files that belong to the operating system.
Do not clutter the repo with temporary drafts unless they are part of a repeatable workflow.
