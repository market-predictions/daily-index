# Weekly AEX Option Review 2026-04-03

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary
The current cycle classifies the directional regime as **mixed** and the options regime as **surface_unavailable**.
The output remains **NO_TRADE** because the current option-chain source policy is **provider_first**, the provider-fed chain file is missing, and the Yahoo fallback did not provide a complete enough AEX options surface for structure selection.

## 2. Portfolio action snapshot
- Primary decision: NO_TRADE
- Automation level: 1
- Position change: none
- Financing posture: preserve optionality; do not force premium harvesting from incomplete chain data

## 3. Macro / policy / geopolitical dashboard
- Macro regime: restrictive_with_inflation_reacceleration
- Dominant driver: inflation_reacceleration
- ECB deposit / MRO / marginal lending: 2.00% / 2.15% / 2.40%
- Euro area inflation: 2.5% (March 2026 flash estimate)
- Euro area unemployment: 6.2% (February 2026)
- Euro area GDP / employment qoq: 0.2% / 0.2% (Q4 2025)
- Cross-market confirmation: supportive_risk
- Geopolitical / energy flags: ['march_energy_reacceleration']

## 4. AEX composition and sector transmission map
- Semiconductor / tech concentration remains a live transmission issue for the index.
- Europe-sensitive inflation and energy repricing still matter for Dutch large-cap risk appetite.
- AEX index-level structure selection should remain conservative when the macro story is broader than the index’s internal breadth.

## 5. Technical integrity and confirmation check
- Primary technical trend: mixed
- Reference price: 1002.90
- 20d realized vol: 0.182
- Technical confidence: medium
- Integrity note: the primary technical snapshot is based on the underlying, not on a validated option-chain surface.

## 6. Options regime and surface conditions
- Surface provider mode: unavailable
- Source policy: provider_first
- Provider input path: input_aex/aex_option_chain_provider.json
- Surface regime: surface_unavailable
- Front expiry read: no expiry IV available
- Implied move next expiry: None
- Surface interpretation: public Yahoo AEX options coverage was not sufficiently complete to support a strike-aware weekly structure.

## 7. Approved structure family or no-trade decision
**Decision: NO_TRADE**

Reason: option-chain source policy is provider_first; provider input file is missing; Yahoo fallback was incomplete; therefore the options regime remains surface_unavailable and the burden of proof for a weekly defined-risk structure is not met.

## 8. Structure ranking table
| Candidate family | Status | Selection confidence | Notes |
|---|---|---:|---|
| collar_style_protection | reject | n/a | no actual underlying exposure in portfolio state |
| defined_risk_bullish_financed_convexity | reject | n/a | no valid option-chain payload |
| defined_risk_bearish_financed_convexity | reject | n/a | no valid option-chain payload |
| range_defined_risk_premium_structure | reject | n/a | no valid option-chain payload |

## 9. Calendar / timing gates and invalidators
- Do not force a financed structure while the option surface is unavailable.
- Do not auto-apply proposals to live portfolio state at automation level 1.
- Invalidators: provider-fed chain becomes available, Yahoo fallback becomes materially usable, or structure evidence materially improves.

## 10. Position changes executed this run
- None automatically.
- No explicit execution events were present.

## 11. Current option portfolio, premium, and cash
- Open structures: 0
- Cash EUR: 0.0
- Net delta / gamma / theta / vega: 0.0 / 0.0 / 0.0 / 0.0
- Max loss total: 0.0

## 12. Carry-forward input for next run
- Refresh the live snapshots.
- Re-check the current option-chain source policy and whether a provider-fed chain file exists.
- Rebuild structure candidates only after a valid AEX option-chain payload is available.

## 13. Disclaimer
This report is for informational and educational purposes only; please see the disclaimer at the end.
