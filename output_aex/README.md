# output_aex

This folder is the home for generated AEX weekly report artifacts and state files.

## Expected generated files
- `weekly_aex_option_review_YYMMDD.md`
- `aex_option_trade_plan_YYMMDD.json`
- `aex_option_portfolio_state.json`
- `aex_option_risk_state.json`
- `aex_trade_ledger.csv`
- `aex_valuation_history.csv`
- `aex_recommendation_scorecard.csv`

## Rule
Do not treat template files as live state.
Live state should only be treated as authoritative after a real run updates these artifacts.
