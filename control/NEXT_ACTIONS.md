# Daily Index OS — Next Actions

## Status legend
- `[USER]` = manual user action
- `[ASSISTANT]` = can be done directly in repo/chat
- `[JOINT]` = assistant prepares, user wires providers, secrets, or external systems

---

## Phase 1 — verify the current workflow state

### 1. Confirm the dry-test GitHub Actions results
- Owner: `[USER]`
- Action: inspect the Actions tab for commit `c58cc741f3bd96068ac8d713fc528aa964ac5f32`
- Goal: confirm which workflows passed, failed, or were skipped
- Why: the connector did not surface combined statuses yet

### 2. Keep using the control-layer read order
1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

---

## Phase 2 — improve data depth safely

### 3. Add a dedicated macro snapshot producer
Target artifact:
- `output_aex/aex_macro_snapshot.json`

### 4. Decide the option-chain provider path
Needed for:
- AEX option chains
- implied volatility / skew / term structure
- spot / futures reference pricing
- later structure building

### 5. Add richer AEX composition / concentration logic
Target outcome:
- explicit AEX sector / concentration module in the report generator

---

## Phase 3 — move from report scaffolding to structure intelligence

### 6. Build the first structure-selection engine
Target outcome:
- strike-aware defined-risk structure builder
- max-loss / max-gain / financing-ratio calculation
- approved-family enforcement

### 7. Add portfolio-state and Greeks-state refresh logic
Target artifacts:
- `output_aex/aex_option_portfolio_state.json`
- `output_aex/aex_option_risk_state.json`

### 8. Keep the first generator conservative until structure selection exists
Rule:
- default to no-trade until the structure builder is real, not implied

---

## Phase 4 — delivery hardening

### 9. Add SMTP secrets to the repo if email delivery should be active
Needed by workflow:
- `MRKT_RPRTS_SMTP_HOST`
- `MRKT_RPRTS_SMTP_PORT`
- `MRKT_RPRTS_SMTP_USER`
- `MRKT_RPRTS_SMTP_PASS`
- `MRKT_RPRTS_MAIL_FROM`
- `MRKT_RPRTS_MAIL_TO`

### 10. Confirm recipient(s)
Set the default recipient list for the AEX workflow.

---

## Phase 5 — housekeeping

### 11. Delete temporary branch `tmp-tree-test`
- Owner: `[USER]`
- Why: the connector exposed branch creation/search but not branch deletion

### 12. Keep the repo lean
- remove temporary test artifacts when they no longer serve a workflow purpose
- prefer canonical control filenames only
- avoid reintroducing FX-only files into this repo

---

## Current checkpoint
**Control-layer normalization completed; next priority is verifying current workflow outcomes and upgrading data/structure depth without relaxing the no-trade discipline too early.**
