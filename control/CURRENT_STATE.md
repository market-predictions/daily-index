# Daily Index OS — Current State

## Snapshot date
2026-04-03

## What this repository currently is
A dedicated operating environment for **weekly AEX index option plays** with a cleaner, more options-native structure than the earlier FX-shaped draft.

## What is implemented now
- Dedicated AEX control layer in `control/`
- Split four-layer framework in `prompts/aex_weekly_options/`
- Live public **AEX primary technical snapshot** producer
- Live public **cross-market confirmation** producer
- Conservative **macro snapshot** producer with optional manual overlay
- Conservative **option-surface snapshot** producer with provider-file fallback
- First **strike-aware structure-candidate builder**
- First **portfolio / Greeks refresh** layer
- First **snapshot suite runner**
- First **weekly AEX review generator**
- **Trade-plan validator** with business-rule checks
- **Delivery / render / manifest** script for report output
- GitHub Actions workflows for:
  - snapshot refresh
  - weekly review build
  - trade-plan validation
  - render/send flow

## Core architectural decisions in force
1. **AEX-primary technical layer**
2. **Strict financing families**
3. **Directional regime separated from options regime**
4. **Automation maturity levels**
5. **Richer options risk state**
6. **Dual outputs**
7. **No-trade as default**
8. **Validation gate before render/send**
9. **Public option-chain coverage treated conservatively**
10. **Automation level 1 does not auto-apply approved trade plans to live portfolio state**

## Current strengths
- The repo is clearly index-options focused.
- The control layer is AEX-native and restart-friendly.
- Snapshot production, structure building, report generation, validation, and delivery are separate layers.
- The system still defaults to no-trade unless the new structure-candidate gates are met.
- Public option-surface data is fail-safe rather than over-trusted.
- Portfolio and Greeks state now have a real refresh path.

## Current weaknesses / open items
- There is still no broker execution layer.
- The macro snapshot is still a conservative scrape/overlay design, not a full institutional data pipeline.
- The structure builder is still a first-pass strike selector, not yet a full optimizer.
- Portfolio-state updates still require explicit execution events at automation level 1.
- Dry-test workflow results were triggered by commit, but their final pass/fail status was not visible through the connector endpoint at the time of the last check.

## Current status label
**AEX operating system materially expanded — macro snapshot, structure candidate board, and portfolio/Greeks refresh now exist; the next work should focus on workflow verification, execution ingestion, and better structure optimization.**
