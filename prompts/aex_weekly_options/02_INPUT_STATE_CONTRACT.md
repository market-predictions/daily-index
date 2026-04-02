# AEX Weekly Options — Input / State Contract

## Purpose
Define which files are authoritative and how stale or conflicting inputs are handled.

## Primary principle
This system is **AEX-primary**.

Cross-market data may inform the decision, but it must not replace the dedicated AEX technical and options-state layers.

## Authoritative input layers

### 1. Strategy / architecture intent
Authoritative files:
- `control/AEX_SYSTEM_INDEX.md`
- `control/AEX_CURRENT_STATE.md`
- `control/AEX_NEXT_ACTIONS.md`
- `prompts/aex_weekly_options/*.md`

### 2. Macro / policy / geopolitical snapshot
Primary file:
- `output_aex/aex_macro_snapshot.json`

### 3. AEX primary technical snapshot
Primary file:
- `output_aex/aex_primary_technical_snapshot.json`

This must become the main technical authority for:
- trend state
- major support / resistance
- realized-vol context
- near-term structural bias
- freshness / timestamp

### 4. Cross-market confirmation
Secondary file:
- `output_aex/aex_cross_market_confirmation.json`

Use for:
- DAX / Euro Stoxx confirmation
- US index spillover
- rates / bund / treasury spillover
- EUR / USD risk sentiment context
- volatility complex context

This file is a confirmation layer, not the primary decision engine.

### 5. Option-surface state
Primary file:
- `output_aex/aex_option_surface_snapshot.json`

This must contain:
- snapshot timestamp
- expiries considered
- ATM IV by expiry
- skew metrics
- term-structure metrics
- spread / liquidity stats
- estimated implied move
- execution warnings

### 6. Portfolio implementation state
Primary file:
- `output_aex/aex_option_portfolio_state.json`

### 7. Portfolio risk state
Primary file:
- `output_aex/aex_option_risk_state.json`

Use for:
- net delta
- net gamma
- net theta
- net vega
- scenario exposure
- overlap flags
- event flags

### 8. Trade / valuation history
Supporting files:
- `output_aex/aex_trade_ledger.csv`
- `output_aex/aex_valuation_history.csv`
- `output_aex/aex_recommendation_scorecard.csv`

### 9. Machine-readable trade intent
Primary file for target intent:
- `output_aex/aex_option_trade_plan_YYMMDD.json`

## Optional legacy / external confirmation
The repo may optionally ingest or reference external technical artifacts such as:
- `market-predictions/daily-fx/mt5_output/latest/`

But those may only be used as **supplementary context**, not as the primary AEX technical authority.

## Authority rules
When files disagree, use this order:

### Live implementation facts
1. `output_aex/aex_option_portfolio_state.json`
2. `output_aex/aex_option_risk_state.json`
3. trade ledger / valuation history

### Strategic target intent
1. latest `aex_option_trade_plan_YYMMDD.json`
2. latest weekly report

### Technical decision facts
1. `aex_primary_technical_snapshot.json`
2. `aex_cross_market_confirmation.json`
3. optional external confirmation

### Macro / policy facts
1. `aex_macro_snapshot.json`

## Staleness rules
### Technical staleness
Reject technical approval if:
- primary AEX technical snapshot timestamp is missing
- snapshot is older than the allowed weekly window
- the underlying reference session is unclear

### Options-surface staleness
Reject structure approval if:
- option-surface snapshot is stale
- spreads / liquidity are stale
- event repricing may have invalidated the snapshot

### Macro staleness
Downgrade confidence if macro snapshot is stale, but do not allow a stale macro file to override fresh option-surface or technical conditions.

## Required state completeness
A production-quality run should not be considered fully authoritative unless these exist:
- macro snapshot
- primary AEX technical snapshot
- option-surface snapshot
- portfolio state
- risk state

## Default if incomplete
If one or more required inputs are missing:
- reduce automation level
- downgrade approval status
- prefer hedge-only or no-trade
- never force a financed structure from incomplete inputs
