# Weekly Indices Review — Input / State Contract

## Purpose
Define what data is authoritative and how conflicts are resolved.

## Authority order
1. Explicit user override in the current chat
2. `output_indices/index_portfolio_state.json`
3. Latest valid pricing audit in `output_indices/pricing/`
4. Most recent stored report in `output_indices/`
5. Deterministic assumptions

## Benchmark vs proxy rule
### Benchmark index closes govern
- analysis
- regime interpretation
- opportunity-board framing
- relative leadership comparison

### Proxy closes govern
- share counts
- market values
- weights
- cash
- NAV
- equity curve

## Planned state artifacts
- `output_indices/index_portfolio_state.json`
- `output_indices/index_trade_ledger.csv`
- `output_indices/index_valuation_history.csv`
- `output_indices/index_recommendation_scorecard.csv`
- `output_indices/index_recommendation_plan_YYMMDD.json`
- `output_indices/pricing/index_price_audit_YYYYMMDD.json`
