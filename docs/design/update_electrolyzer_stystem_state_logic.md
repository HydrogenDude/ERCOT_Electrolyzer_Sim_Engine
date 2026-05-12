# Electrolyzer System State Update Logic

This document defines the logical flow used to update the electrolyzer system state at each simulation timestep.

---

## Definitions

### Signals
- **cp**  = current electricity price  
- **ccr** = current clean energy ratio  

### Price Thresholds
- **p0** = price stop threshold  
  (price above which sustained operation is not allowed)

- **p1** = price turndown threshold  
  (price above which the system enters or remains in turndown)

- **p2** = price start threshold  
  (price at or below which startup and normal operation are allowed)

### Clean Ratio Thresholds
- **cr0** = clean ratio stop threshold  
  (clean ratio below which operation must stop)

- **cr1** = clean ratio turndown threshold  
  (clean ratio below which the system enters or remains in turndown)

- **cr2** = clean ratio start threshold  
  (clean ratio at or above which startup and normal operation are allowed)

---

## Per‑Timestep Logic (timestep *j*)

### 1. Read Inputs
- Read **cp** and **ccr**

---

### 2. Price Delay Logic
- **IF** `cp > p0`  
  → increment `price_violation_counter`
- **ELSE**  
  → reset `price_violation_counter`

- `price_allowed = (price_violation_counter < price_delay)`

---

### 3. Condition Definitions

- **can_start IF**  
  `ccr ≥ cr2 AND cp ≤ p2`

- **stop_conditions IF**  
  `ccr < cr0 OR price_allowed == false`

- **bad_conditions IF**  
  `ccr < cr1 OR cp > p1`

- **good_conditions IF**  
  `ccr ≥ cr2 AND cp ≤ p2`

---

## 4. State Update Logic

### A. Mode = ON
- Increment `runtime_steps`  
- Reset `offtime_steps`

- **Bad condition tracking**
  - IF `bad_conditions` → increment `turndown_counter`
  - ELSE → reset `turndown_counter`

- **Recovery tracking**
  - IF `good_conditions` → increment `recover_counter`
  - ELSE → reset `recover_counter`

- **Regime transitions**
  - IF `REG_NORMAL` AND `turndown_counter ≥ turndown_delay`  
    → switch to `REG_TURNDOWN`
  - IF `REG_TURNDOWN` AND `recover_counter ≥ recover_delay`  
    → switch to `REG_NORMAL`

- **Shutdown decision**
  - IF `REG_TURNDOWN`
  - AND `runtime_steps ≥ min_up_steps`
  - AND `stop_conditions`  
    → set `mode = OFF`, reset counters, increment shutdowns

---

### B. Mode = OFF
- Increment `offtime_steps`
- Reset `runtime_steps`
- Reset all regime and condition counters

- **Startup decision**
  - IF `offtime_steps ≥ min_down_steps`
  - AND `can_start`  
    → set `mode = ON`, increment startups

---

## 5. Power Command (Authoritative Output)

- Default: `P_cmd = 0`

- **IF mode = ON**
  - **REG_NORMAL** → `P_cmd = P_max`
  - **REG_TURNDOWN**
    - Discrete dispatch → `P_cmd = P_min`
    - Continuous dispatch → interpolate between `P_min` and `P_max` using `ccr`

---

## 6. Invariant
- **IF** `mode = OFF` **THEN** `P_cmd = 0`

This invariant is strictly enforced at every timestep.