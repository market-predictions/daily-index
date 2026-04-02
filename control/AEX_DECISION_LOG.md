# Daily Index OS — AEX Decision Log

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
