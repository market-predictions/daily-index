# Daily Index OS — Next Actions

## Status legend
- `[USER]` = manual user action
- `[ASSISTANT]` = can be done directly in repo/chat
- `[JOINT]` = assistant prepares, user wires providers, secrets, or external systems

---

## Phase 1 — verify the current workflow state

### 1. Confirm the GitHub Actions results
- Owner: `[USER]`
- Action: inspect the Actions tab for the latest daily-index commits
- Goal: confirm which workflows passed, failed, or were skipped
- Why: the connector did not surface combined statuses yet

### 2. Keep using the control-layer read order
1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

---

## Phase 2 — improve execution realism safely

### 3. Decide the option-chain provider path
Needed for:
- AEX option chains
- implied volatility / skew / term structure
- spot / futures reference pricing
- better strike selection

### 4. Decide how execution events will be recorded
Target input:
- `input_aex/aex_execution_events.json`

### 5. Confirm whether the model portfolio should carry explicit long AEX exposure
Why:
- collar / overwrite-style families should only activate when underlying exposure is real

---

## Phase 3 — move from structure scaffolding to structure quality

### 6. Upgrade the first structure builder
Target outcome:
- wider strike search
- better expiry selection
- stronger candidate ranking
- better financing and convexity scoring

### 7. Deepen the macro producer
Target outcome:
- richer AEX composition notes
- better Europe / ECB / energy classification
- less placeholder use

### 8. Keep automation conservative
Rule:
- approved structures remain proposal-only until explicit execution confirmation arrives

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
**Macro snapshot, strike-aware structure candidates, and portfolio/Greeks refresh now exist; next priority is verifying workflow outcomes and improving the realism of chain data and execution ingestion.**
