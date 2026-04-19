# Daily Index OS — Current State

## Snapshot date
2026-04-19

## What this repository currently is
This repository is currently a dedicated operating environment for **weekly AEX index option plays** with:
- a four-layer prompt scaffold
- snapshot producers
- a structure-candidate builder
- portfolio / Greeks refresh
- validation
- render / send logic
- machine-readable trade-plan output

## What has changed conceptually
A new primary product direction has now been chosen:

### New primary active direction
**Weekly Indices Review** — a premium weekly report for a model portfolio of stock-index exposures with recommendations, continuity, valuation tracking, and delivery.

### Existing but parked direction
**AEX Weekly Options** remains preserved in the repo but is now parked as a secondary track rather than the primary active reporting product.

## What the new Weekly Indices Review should become
A production-style review system comparable in end-user value and premium feel to ETF Review, but built around:
- stock-index exposures
- benchmark index analysis
- tradable proxy implementation
- explicit machine-readable portfolio state
- quota-aware pricing audits
- GitHub-write plus render/send workflow

## Core architectural decisions now in force
1. `daily-index` remains the host repo.
2. AEX options is preserved but parked.
3. Weekly Indices Review becomes the primary active report product.
4. The new product should **port the ETF framework and workflow**, not blindly copy the whole ETF repo.
5. Analysis should be driven by **benchmark index closes** where appropriate.
6. Implemented model-portfolio valuation should be driven by **tradable proxy closes**.
7. The report must remain premium, compact, and decision-useful.
8. The workflow should follow the ETF-style push-triggered production send model.
9. Explicit state files should exist from the start rather than relying mainly on prior report parsing.
10. The four-layer architecture remains non-negotiable.

## Current strengths
- The repo already has a clean four-layer operating-system structure.
- The control layer is restart-friendly.
- Machine-readable output thinking already exists.
- Validation-before-delivery discipline already exists.
- The repo is better suited than ETF as the long-term host for explicit state authority.

## Current weaknesses
### 1. Primary product mismatch
The current active execution files are still aimed at AEX options rather than a stock-indices portfolio review.

### 2. No indices-native production runtime yet
Still missing:
- `index.txt`
- `index-pro.txt`
- `send_index_report.py`
- `.github/workflows/send-weekly-indices-report.yml`

### 3. No explicit indices state layer yet
Still missing:
- `output_indices/index_portfolio_state.json`
- `output_indices/index_trade_ledger.csv`
- `output_indices/index_valuation_history.csv`
- `output_indices/index_recommendation_scorecard.csv`
- `output_indices/index_recommendation_plan_YYMMDD.json`
- `output_indices/pricing/index_price_audit_YYYYMMDD.json`

### 4. Benchmark / proxy authority not yet implemented
The new product requires explicit conflict-resolution rules between:
- benchmark index data used for analysis
- tradable proxy data used for portfolio valuation

### 5. Delivery layer not yet ported
ETF already has a production-style report-send workflow and manifest discipline. The equivalent indices workflow is not yet in place.

## Target architecture
### ChatGPT side
- one active runtime prompt for Weekly Indices Review: `index.txt`
- one premium editorial layer: `index-pro.txt`
- live GitHub reads remain authoritative
- control layer remains the session restart discipline

### GitHub side
- `output_indices/` becomes the source of truth for the indices report family
- explicit state files become first-class artifacts
- pricing audits are stored under `output_indices/pricing/`
- the weekly markdown report remains the visible report artifact
- a machine-readable recommendation plan supports continuity and auditability

### Delivery side
- `send_index_report.py` handles validation, HTML render, PDF render, email send, and manifest write
- a dedicated GitHub Actions workflow sends only when a new production indices report is written
- non-report code changes must not resend the latest client report

## Immediate priorities
### Priority A — establish the new product track
Still required:
- create `index.txt`
- create `index-pro.txt`
- create split framework files under `prompts/weekly_indices/`

### Priority B — define explicit state authority
Still required:
- create indices state files
- define benchmark/proxy pricing precedence
- define continuity input format
- define recommendation-plan authority

### Priority C — port delivery and workflow
Still required:
- create `send_index_report.py`
- create `send-weekly-indices-report.yml`
- validate manifest/receipt behavior

### Priority D — keep AEX options preserved
Still required:
- avoid destructive changes to the AEX track
- keep files intact for later reuse
- avoid mixing AEX options logic into the new indices runtime

## Recommended session start sequence
For any future Weekly Indices Review architecture or implementation session:
1. read `control/SYSTEM_INDEX.md`
2. read this file
3. read `control/NEXT_ACTIONS.md`
4. only then open the specific execution file relevant to the task

## Current status label
**AEX options remains preserved but parked; a new primary product direction has been chosen for this repo: Weekly Indices Review, using ETF-style production workflow and premium report discipline, with benchmark-index analysis and tradable-proxy implementation as the governing model.**
