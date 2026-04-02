# AEX Weekly Options — Output Contract

## Mission
Every completed weekly cycle must produce both:
1. a **human-readable weekly report**
2. a **machine-readable trade plan**

The report explains the decision.
The trade plan defines the executable state intent.

## Required output artifacts

### A. Human report
Path:
- `output_aex/weekly_aex_option_review_YYMMDD.md`
- or same-day versioned equivalent:
- `output_aex/weekly_aex_option_review_YYMMDD_NN.md`

### B. Machine trade plan
Path:
- `output_aex/aex_option_trade_plan_YYMMDD.json`
- or same-day versioned equivalent

### C. Updated implementation state
Paths:
- `output_aex/aex_option_portfolio_state.json`
- `output_aex/aex_option_risk_state.json`
- `output_aex/aex_trade_ledger.csv`
- `output_aex/aex_valuation_history.csv`
- `output_aex/aex_recommendation_scorecard.csv`

## Required report structure

# Weekly AEX Option Review

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary
## 2. Portfolio action snapshot
## 3. Macro / policy / geopolitical dashboard
## 4. AEX composition and sector transmission map
## 5. Technical integrity and confirmation check
## 6. Options regime and surface conditions
## 7. Approved structure family or no-trade decision
## 8. Structure ranking table
## 9. Calendar / timing gates and invalidators
## 10. Position changes executed this run
## 11. Current option portfolio, premium, and cash
## 12. Carry-forward input for next run
## 13. Disclaimer

## Required machine trade-plan fields
The JSON trade plan must contain at minimum:
- `report_date`
- `approval_status`
- `automation_level`
- `directional_regime`
- `options_regime`
- `primary_decision`
- `no_trade_reason` (required when no-trade)
- `structures_considered`
- `approved_structures`
- `portfolio_overlap_assessment`
- `timing_gate_status`
- `freshness_summary`
- `risk_budget_summary`

For each approved structure:
- `structure_name`
- `family`
- `regime_tag`
- `expiry`
- `long_legs`
- `short_legs`
- `net_debit_credit`
- `max_gain`
- `max_loss`
- `break_even`
- `financing_ratio`
- `convexity_retained_score`
- `theta_funding_score`
- `tail_cleanliness_score`
- `event_risk_note`
- `execution_status`

## Required risk-state fields
The risk state must carry:
- `as_of`
- `net_delta`
- `net_gamma`
- `net_theta`
- `net_vega`
- `premium_collected_cycle`
- `premium_spent_cycle`
- `expiration_buckets`
- `event_flags`
- `overlap_flags`
- `max_loss_total`
- `max_gain_total`
- `stress_scenarios`

## No-trade rule
No-trade is a valid and complete output.

If the decision is no-trade:
- the report must still be complete
- the trade plan must still be written
- the trade plan must explicitly state why approval failed

## Delivery rule
A run is complete only if:
1. the markdown report exists
2. the machine trade plan exists
3. rendering validation passes
4. if email delivery is enabled, a manifest / receipt is produced

Do not claim completion without all applicable artifacts.
