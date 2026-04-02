# AEX Weekly Options — Decision Framework

## Mission
Produce one disciplined weekly decision for AEX index options using a framework that is:
- macro-aware
- technically confirmed
- options-surface aware
- risk-budget aware
- explicit about when the answer is **no trade**

## Primary question
What is the best defined-risk AEX weekly option structure for the next expiry cycle, if any?

## Burden-of-proof rule
The default answer is **NO TRADE**.

A structure is approved only if all of the following pass:
1. directional regime pass
2. options regime pass
3. technical confirmation pass
4. timing / calendar gate pass
5. portfolio overlap / risk-budget pass
6. financing-family validation pass

## Separate the two regime engines

### A. Directional regime engine
Allowed outputs:
- bullish continuation
- bearish continuation
- range / mean reversion
- unstable / event-dominated
- no-trade

Inputs:
- macro regime
- ECB / rates / inflation impulse
- geopolitics / energy / tariff spillover
- Europe growth sensitivity
- AEX composition and sector concentration
- high-level technical structure
- event calendar

### B. Options regime engine
Allowed outputs:
- long premium favorable
- short premium favorable
- financed premium favorable
- event-distorted
- surface unattractive
- no-trade

Inputs:
- implied volatility vs realized volatility
- skew
- term structure
- spread / liquidity quality
- days to expiry
- event premium distortion
- strike availability / financing efficiency

## Structure approval logic
A strong directional view is not enough.

Use this sequence:
1. determine directional regime
2. determine options regime
3. determine whether both regimes support one of the allowed financing families
4. if not, default to **no-trade**

## Approved financing families
Only the following are allowed:

### 1. Overwrite-funded hedge
Long AEX exposure plus call overwrite premium used to finance downside protection.

### 2. Collar-style protection
Long underlying exposure, long downside put, short upside call.

### 3. Defined-risk bullish financed convexity
Call debit spread, optionally partially financed by a separate defined-risk credit component only if total max loss remains explicit and acceptable.

### 4. Defined-risk bearish financed convexity
Put debit spread financed by a defined-risk upside credit spread or equivalent capped-risk overlay.

### 5. Range-only defined-risk premium structure
Allowed only in low-event, low-instability conditions.

### 6. No-trade
Always permitted and preferred whenever the evidence is insufficient.

## Forbidden structure behaviors
- naked short calls
- naked short puts
- undefined tail exposure
- financing that destroys the long convexity thesis
- event-week premium selling without strict justification
- forcing a trade because a weekly cycle exists

## Core scoring model
### Directional regime score
- macro / policy backdrop: 0–5
- geopolitical / energy / tariff context: 0–4
- AEX composition translation: 0–4
- primary technical state: -2 to +2
- cross-market confirmation: -2 to +2
- event-risk penalty: 0 to -4

### Options regime score
- IV vs realized-vol relationship: 0–4
- skew quality for chosen thesis: 0–3
- term-structure fit: 0–3
- liquidity / spread quality: 0–3
- financing efficiency: 0–3
- calendar / expiry suitability: 0–4
- event-distortion penalty: 0 to -4

## Hard default
If either regime engine returns:
- unstable / event-dominated
- surface unattractive
- no-trade

then the overall decision must be **no-trade** unless an explicitly approved hedge-only structure is justified.

## AEX composition module
Do not treat AEX as generic “Europe”.

Explicitly assess:
- semiconductor / tech concentration
- energy / materials sensitivity
- financials and rates sensitivity
- defensives vs cyclicals
- major constituent event risk
- whether index behavior is broad or concentrated

## Decision output
The framework must end with exactly one of:
- approve one structure family
- approve one hedge-only structure
- no-trade
