# Weekly Indices Review — Output Contract

## Mission
Every completed weekly cycle must produce:
1. a **human-readable weekly report**
2. machine-readable portfolio / recommendation state

## Required report artifact
Path:
- `output_indices/weekly_indices_review_YYMMDD.md`
- or same-day versioned equivalent

## Planned state artifacts
- `output_indices/index_portfolio_state.json`
- `output_indices/index_trade_ledger.csv`
- `output_indices/index_valuation_history.csv`
- `output_indices/index_recommendation_scorecard.csv`
- `output_indices/index_recommendation_plan_YYMMDD.json`
- `output_indices/index_candidate_ranking_YYMMDD.json`
- `output_indices/index_discovery_coverage_YYMMDD.json`
- `output_indices/pricing/index_price_audit_YYYYMMDD.json`
- `output_indices/research/index_macro_snapshot_YYMMDD.json`
- `output_indices/research/index_relative_strength_snapshot_YYMMDD.json`
- `output_indices/research/index_candidate_evidence_YYMMDD.json`

## Required report structure
# Weekly Indices Review YYYY-MM-DD

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive Summary
## 2. Portfolio Action Snapshot
## 3. Global Regime Dashboard
## 4. Index Opportunity Board
## 5. Key Risks / Invalidators
## 6. Bottom Line
## 7. Equity Curve and Portfolio Development
## 8. Regional / Style Allocation Map
## 9. Second-Order Effects Map
## 10. Current Position Review
## 11. Best New Index Opportunities
## 12. Portfolio Rotation Plan
## 13. Final Action Table
## 14. Position Changes Executed This Run
## 15. Current Portfolio Holdings and Cash
## 16. Continuity Input for Next Run
## 17. Disclaimer

## Section source rules
### Section 3 — Global Regime Dashboard
Default structured support source:
- `index_macro_snapshot_YYMMDD.json`

### Section 4 — Index Opportunity Board
Default source of truth:
- highest-ranked published entries from `index_candidate_ranking_YYMMDD.json`
- backed by `index_candidate_evidence_YYMMDD.json`

### Section 11 — Best New Index Opportunities
Default source of truth:
- strongest non-published challengers from `index_candidate_ranking_YYMMDD.json`
- especially the strongest omitted regional challenger when the final board remains narrow
- backed by `index_candidate_evidence_YYMMDD.json`

### Section 16 — Continuity Input for Next Run
Default source of truth:
- `index_discovery_coverage_YYMMDD.json`
- `index_candidate_ranking_YYMMDD.json`
- portfolio state and recommendation plan where relevant

This section should use those artifacts to populate:
- watchlist / dynamic radar memory
- strong challengers not published
- what would most likely change the board next run

## Breadth visibility rule
The final published report may remain compact, but broad internal discovery must remain visible in at least one of these ways:
- a strongest omitted regional challenger in **Best New Index Opportunities**
- a strongest omitted regional challenger in the continuity / watchlist section
- or both

This prevents the broader benchmark scan from disappearing in the final client-facing compression.

## Delivery rule
A run is complete only if:
1. the markdown report exists
2. rendering validation passes
3. if email delivery is enabled, a manifest / receipt is produced

Do not claim completion without all applicable artifacts.
