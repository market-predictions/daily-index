# Daily Index OS — Next Actions

## Status legend
- `[USER]` = manual user action
- `[ASSISTANT]` = can be done directly in repo/chat
- `[JOINT]` = assistant prepares, user wires providers, secrets, or external systems

---

## Phase 1 — establish the new primary product track

### 1. Confirm product priority
- Owner: `[JOINT]`
- Action:
  - treat **Weekly Indices Review** as the primary active reporting product
  - keep **AEX Weekly Options** parked but preserved
- Done when:
  - control files, prompts, workflows, and outputs clearly reflect the new primary track

### 2. Keep using the control-layer read order
1. `control/SYSTEM_INDEX.md`
2. `control/CURRENT_STATE.md`
3. `control/NEXT_ACTIONS.md`
4. only then the minimum relevant execution file(s)

### 3. Add a dedicated architecture note
- Owner: `[ASSISTANT]`
- Target file:
  - `control/INDICES_REVIEW_ARCHITECTURE.md`
- Goal:
  - define the benchmark/proxy model
  - define state files
  - define output contract
  - define workflow boundaries

---

## Phase 2 — port the ETF production framework into the repo safely

### 4. Create the production runtime prompt
- Owner: `[ASSISTANT]`
- Target file:
  - `index.txt`
- Goal:
  - ETF-style production runtime for Weekly Indices Review
  - preserve compact premium structure
  - support portfolio continuity and pricing audits
  - avoid ETF-specific object-model drift

### 5. Create the premium editorial layer
- Owner: `[ASSISTANT]`
- Target file:
  - `index-pro.txt`
- Goal:
  - preserve the premium ETF-like reading experience
  - remove internal workflow language from the client-facing report
  - keep the report selective, calm, and commercially credible

### 6. Create the split four-layer scaffold
- Owner: `[ASSISTANT]`
- Target path:
  - `prompts/weekly_indices/`
- Files:
  - `01_DECISION_FRAMEWORK.md`
  - `02_INPUT_STATE_CONTRACT.md`
  - `03_OUTPUT_CONTRACT.md`
  - `04_OPERATIONAL_RUNBOOK.md`
- Goal:
  - keep four-layer discipline explicit even if the production runtime remains more monolithic at first

---

## Phase 3 — define explicit indices state authority

### 7. Create the canonical output/state path
- Owner: `[ASSISTANT]`
- Target path:
  - `output_indices/`
- Goal:
  - separate the new product cleanly from `output_aex/`

### 8. Create indices portfolio state files
- Owner: `[ASSISTANT]`
- Planned files:
  - `output_indices/index_portfolio_state.json`
  - `output_indices/index_trade_ledger.csv`
  - `output_indices/index_valuation_history.csv`
  - `output_indices/index_recommendation_scorecard.csv`
  - `output_indices/index_recommendation_plan_YYMMDD.json`
- Goal:
  - reduce dependence on prior report parsing
  - make continuity and valuation authority explicit

### 9. Define benchmark / proxy authority rules
- Owner: `[ASSISTANT]`
- Goal:
  - benchmark index closes govern analysis
  - tradable proxy closes govern implemented portfolio valuation
  - both are stored in state where relevant
- Done when:
  - conflict resolution is deterministic and documented

### 10. Create indices pricing subsystem
- Owner: `[ASSISTANT]`
- Target path:
  - `pricing_indices/`
- Goal:
  - adapt only the ETF pricing pieces needed for index/proxy valuation
  - write machine-readable audits to `output_indices/pricing/`
  - keep source hierarchy and rate-limit rules explicit

---

## Phase 4 — port delivery and workflow

### 11. Create the delivery/render/send script
- Owner: `[ASSISTANT]`
- Target file:
  - `send_index_report.py`
- Goal:
  - validate report structure
  - render HTML
  - render PDF
  - send email
  - write manifest / receipt

### 12. Create the production GitHub Actions workflow
- Owner: `[ASSISTANT]`
- Target file:
  - `.github/workflows/send-weekly-indices-report.yml`
- Goal:
  - trigger only on production indices report output pushes
  - avoid resend on non-report code changes
  - keep workflow operational, not editorial

### 13. Add SMTP secrets if email delivery should be active
- Owner: `[USER]`
- Needed:
  - `MRKT_RPRTS_SMTP_HOST`
  - `MRKT_RPRTS_SMTP_PORT`
  - `MRKT_RPRTS_SMTP_USER`
  - `MRKT_RPRTS_SMTP_PASS`
  - `MRKT_RPRTS_MAIL_FROM`
  - `MRKT_RPRTS_MAIL_TO`

---

## Phase 5 — validate the new product end to end

### 14. Run one inaugural Weekly Indices Review
- Owner: `[ASSISTANT]`
- Goal:
  - confirm inaugural portfolio build works
  - confirm report remains premium and compact
  - confirm GitHub write path is correct

### 15. Run one continuation Weekly Indices Review
- Owner: `[ASSISTANT]`
- Goal:
  - confirm state carry-forward works
  - confirm pricing audit consumption works
  - confirm continuity section behaves cleanly

### 16. Run one same-day rerun
- Owner: `[ASSISTANT]`
- Goal:
  - confirm same-day versioning works
  - confirm workflow trigger remains correct
  - confirm no accidental overwrite

### 17. Validate delivery workflow
- Owner: `[JOINT]`
- Goal:
  - confirm render succeeds
  - confirm email succeeds
  - confirm manifest / receipt is produced
  - confirm success is never claimed without evidence

---

## Phase 6 — keep AEX options preserved but parked

### 18. Do not delete the AEX track
- Owner: `[JOINT]`
- Goal:
  - preserve files
  - preserve workflows
  - avoid mixing product logic
- Done when:
  - the repo can support both tracks cleanly without ambiguity

---

## Current checkpoint
**The next major implementation step is to stand up Weekly Indices Review inside `daily-index` as the new primary report product by adding `index.txt`, `index-pro.txt`, explicit indices state files, a pricing/audit path, and an ETF-style delivery workflow while keeping the AEX options track preserved but parked.**
