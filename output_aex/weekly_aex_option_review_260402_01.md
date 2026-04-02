# Weekly AEX Option Review 2026-04-02

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary
The current generator classifies the directional regime as **mixed** and the options regime as **surface_unavailable**.
The v1 output remains **NO_TRADE** because the burden of proof is not yet strong enough for automated structure approval. Main reason: option-surface data unavailable; v1 generator defaults to no-trade until a structure builder is added.

## 2. Portfolio action snapshot
- Primary decision: NO_TRADE
- Automation level: 1
- Position change: none
- Financing posture: preserve optionality; do not force premium harvesting

## 3. Macro / policy / geopolitical dashboard
- Cross-market confirmation: mixed_confirmation
- ECB / Europe-sensitive context: placeholder in v1 generator; macro snapshot generator still to be added
- Geopolitical filter: not explicitly modeled in this first report generator
- Interpretation: use this review as a disciplined operating baseline, not as a fully mature macro engine yet

## 4. AEX composition and sector transmission map
- AEX composition module is not yet fully computed in v1
- Treat semiconductor concentration and Europe-sensitive cyclicality as unresolved concentration risk
- Do not over-generalize from generic Europe equity behavior to AEX-specific structure approval

## 5. Technical integrity and confirmation check
- Primary technical trend: mixed
- Reference price: 995.35
- 20d realized vol: 0.182
- Technical confidence: medium
- Integrity note: the primary technical snapshot is based on the underlying, not on options

## 6. Options regime and surface conditions
- Surface provider mode: unavailable
- Surface regime: surface_unavailable
- Front expiry read: no expiry IV available
- Implied move next expiry: None
- Surface interpretation: option-surface data is treated conservatively and may fall back to provider-fed input when public coverage is incomplete

## 7. Approved structure family or no-trade decision
**Decision: NO_TRADE**

Reason: option-surface data unavailable; v1 generator defaults to no-trade until a structure builder is added.

## 8. Structure ranking table
| Candidate family | Status | Reason |
|---|---|---|
| overwrite_funded_hedge | reject in v1 | burden of proof not met |
| collar_style_protection | reject in v1 | burden of proof not met |
| defined_risk_bullish_financed_convexity | reject in v1 | burden of proof not met |
| defined_risk_bearish_financed_convexity | reject in v1 | burden of proof not met |
| range_defined_risk_premium_structure | reject in v1 | burden of proof not met |

## 9. Calendar / timing gates and invalidators
- Do not force a financed structure inside event-distorted or surface-unavailable conditions
- Do not approve a structure while the generator still lacks a dedicated strike-selection engine
- Invalidator for no-trade: upgrade only after a structure builder and richer macro snapshot are added

## 10. Position changes executed this run
- None

## 11. Current option portfolio, premium, and cash
- Portfolio state integration is not yet populated by the generator
- Premium collected this cycle: not updated here
- Premium spent this cycle: not updated here

## 12. Carry-forward input for next run
- Refresh the three snapshot JSON files
- Add a dedicated macro snapshot producer
- Add a structure builder with strikes, max loss, and financing metrics

## 13. Disclaimer
This report is for informational and educational purposes only; please see the disclaimer at the end.
