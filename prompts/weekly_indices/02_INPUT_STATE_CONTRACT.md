# Weekly Indices Review — Input / State Contract

## Purpose
Define what data is authoritative and how conflicts are resolved.

## Authority order
1. Explicit user override in the current chat
2. `output_indices/index_portfolio_state.json`
3. Latest valid pricing audit in `output_indices/pricing/`
4. Matching research snapshots in `output_indices/research/` if they exist for the run date
5. Most recent stored report in `output_indices/`
6. Most recent candidate-ranking / discovery-coverage artifacts if they exist
7. Deterministic assumptions

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
- `output_indices/index_candidate_ranking_YYMMDD.json`
- `output_indices/index_discovery_coverage_YYMMDD.json`
- `output_indices/pricing/index_price_audit_YYYYMMDD.json`
- `output_indices/research/index_macro_snapshot_YYMMDD.json`
- `output_indices/research/index_relative_strength_snapshot_YYMMDD.json`
- `output_indices/research/index_candidate_evidence_YYMMDD.json`

## Research snapshot rule
If matching research snapshots exist for the run date, they should be treated as the preferred structured evidence base for:
- macro regime support
- cross-market confirmation
- relative strength across index candidates
- candidate evidence-pack construction

## Candidate ranking artifact
The candidate ranking artifact should record the internal ranked list before publication compression.
It should include, at minimum:
- public benchmark name
- primary proxy
- regional group
- score
- publish decision
- if not published, the main reason code

## Discovery coverage artifact
The discovery coverage artifact should record whether each broad regional group was:
- actively considered
- ruled out
- or surfaced as a near-miss

This is the mechanism that makes broad discovery auditable rather than merely implied.
