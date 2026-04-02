# Daily Index OS — AEX Next Actions

## Status legend
- `[USER]` = manual user action
- `[ASSISTANT]` = can be done directly in repo/chat
- `[JOINT]` = assistant prepares, user approves or wires secrets/providers

---

## Phase 1 — stabilize the operating core

### 1. Keep using the control-layer read order
1. `control/AEX_SYSTEM_INDEX.md`
2. `control/AEX_CURRENT_STATE.md`
3. `control/AEX_NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

### 2. Preserve the four-layer model
Keep decision framework, input/state contract, output contract, and runbook separate.

### 3. Keep no-trade as the default
Reject any drift toward “the system should always produce a weekly trade”.

---

## Phase 2 — wire live data safely

### 4. Build the AEX primary technical snapshot producer
Target artifact:
- `output_aex/aex_primary_technical_snapshot.json`

### 5. Add cross-market confirmation producer
Target artifact:
- `output_aex/aex_cross_market_confirmation.json`

### 6. Add option-surface snapshot producer
Target artifact:
- `output_aex/aex_option_surface_snapshot.json`

### 7. Decide provider path
Needed for:
- AEX option chains
- implied volatility / skew / term structure
- spot / futures reference pricing
- eventual execution

---

## Phase 3 — move from architecture to repeatable weekly operation

### 8. Start at automation maturity level 1
Use automated analysis + machine trade plan + manual approval.

### 9. Add machine validation of trade plan
Validate structure family, max loss, financing ratio, timing gates, and freshness before delivery.

### 10. Add portfolio Greeks / risk updater
Target artifact:
- `output_aex/aex_option_risk_state.json`

---

## Phase 4 — delivery and workflow hardening

### 11. Add SMTP secrets to repo
Needed by workflow:
- `MRKT_RPRTS_SMTP_HOST`
- `MRKT_RPRTS_SMTP_PORT`
- `MRKT_RPRTS_SMTP_USER`
- `MRKT_RPRTS_SMTP_PASS`
- `MRKT_RPRTS_MAIL_FROM`
- `MRKT_RPRTS_MAIL_TO`

### 12. Decide recipient(s)
Confirm default mail recipient(s) for the AEX workflow.

### 13. Run first dry test
Create a valid dummy report + trade plan, render HTML/PDF, and verify manifest creation without live trade execution.

---

## Current checkpoint
**The repo does not need cleanup first. It is better to keep it lean and add only files that belong to the operating system.**
