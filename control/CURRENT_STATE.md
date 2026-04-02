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
- Conservative **option-surface snapshot** producer with provider-file fallback
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

## Current strengths
- The repo is now clearly index-options focused.
- The control layer is AEX-native and restart-friendly.
- Snapshot production, report generation, validation, and delivery are separate layers.
- The system defaults to no-trade instead of forcing structures.
- Public option-surface data is fail-safe rather than over-trusted.

## Current weaknesses / open items
- There is still no dedicated macro snapshot producer.
- There is still no strike-selection / structure-builder engine.
- There is still no broker execution layer.
- Portfolio-state and Greeks-state refresh logic are not fully wired into the report generator yet.
- Dry-test workflow results were triggered by commit, but their final pass/fail status was not visible through the connector endpoint at the time of the last check.

## Dry-test state
A dry-test commit was pushed that:
- tightened workflow gates
- added the first report generator
- added a valid no-trade report/trade-plan pair for workflow validation

At the time of the last connector check, GitHub had not surfaced combined commit statuses yet.

## Current status label
**AEX operating system established and normalized — canonical control layer now belongs to daily-index, core snapshot/report/validation workflow exists, and the next work should focus on data depth, structure building, and verified workflow outcomes.**
