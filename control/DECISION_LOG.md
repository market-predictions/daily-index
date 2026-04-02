# Daily Index OS — Decision Log

## 2026-04-02
### Decision
Create a dedicated repository for index-options workflow instead of continuing inside the FX repo.

### Why
The system needs to be options-native, AEX-specific, and cleanly separated from FX assumptions.

---

## 2026-04-02
### Decision
Use an **AEX-primary technical layer** and treat broader cross-market signals as secondary confirmation.

### Why
Reusing the FX ranking environment as the primary technical authority would create a model mismatch.

---

## 2026-04-02
### Decision
Replace vague “covered writing” language with **strict financing families**.

### Why
The phrase is too loose for automation and can hide unsafe short-premium behavior.

---

## 2026-04-02
### Decision
Separate **directional regime** from **options regime**.

### Why
A good directional view does not automatically imply a good weekly options trade.

---

## 2026-04-02
### Decision
Default to **automation maturity level 1** first.

### Why
Weekly options are too path-dependent to jump immediately to full automation.

---

## 2026-04-02
### Decision
Maintain both a **human report** and a **machine-readable trade plan**.

### Why
Narrative output alone is not enough for safe state updates and later execution routing.

---

## 2026-04-02
### Decision
Use **no-trade** as the default burden-of-proof state.

### Why
Weekly options systems fail when they are biased toward forcing a structure every cycle.

---

## 2026-04-02
### Decision
Treat public AEX option-chain coverage as **fallback-grade**, not production-grade.

### Why
Public coverage can be incomplete; the option-surface producer must fail safe and prefer provider-fed input when available.

---

## 2026-04-02
### Decision
Validate the machine trade plan before render/send.

### Why
A report should not be rendered or mailed if the trade-plan artifact is internally inconsistent.

---

## 2026-04-02
### Decision
Add a first snapshot-driven weekly report generator that still defaults to **no-trade**.

### Why
The repository needed a real end-to-end pipeline, but it should stay conservative until a real structure builder existed.

---

## 2026-04-03
### Decision
Normalize the control layer to canonical filenames inside `daily-index` and remove inherited FX-only control drift.

### Why
A dedicated AEX repo should not require AEX-prefixed control filenames or contain stale FX control documents as its primary entry points.

---

## 2026-04-03
### Decision
Add a conservative macro snapshot producer, a first strike-aware structure builder, and a portfolio/Greeks refresh layer.

### Why
The repository needed real data depth and a path from regime assessment to structure candidates and live risk-state tracking without jumping to auto-execution.
