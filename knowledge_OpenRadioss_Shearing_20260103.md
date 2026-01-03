# OpenRadioss Shearing Simulation Knowledge (2026-01-03)

## 1. Objective
*   **Goal:** Simulate Punch-Die shearing of Aluminum 1060 (0.5mm thickness).
*   **Constraint:** Complete calculation within ~5 hours on Core i9 Laptop (14 cores).

## 2. Methodology & Settings (Attempt 6 - Best Result)
*   **Software:** OpenRadioss (Engine/Starter Win64).
*   **Mesh:** Tetrahedral (C3D4 converted to TETRA4), Size ~0.1mm.
*   **Speed Up:**
    *   **Punch Velocity:** 5.0 m/s (15x actual speed).
    *   **Mass Scaling:** **NONE** (Removed due to instability/explosion risk).
    *   **Threads:** 20 (`-nt 20`).
*   **Runtime:** 4 hours 34 minutes.

## 3. Key Observations & Issues
### A. "Rubber-Like" Deformation
*   **Phenomenon:** The aluminum plate stretched excessively before breaking, looking like rubber.
*   **Cause:** **High Impact Velocity (5.0 m/s)**. The high speed causes inertial forces to dominate, preventing localized strain concentration. The material doesn't have "time" to neck and break naturally.
*   **Lesson:** To look realistic, speed must be lower (e.g., < 2.0 m/s), but this increases runtime linearly.

### B. Element Fracture & Slowdown
*   **Phenomenon:** Simulation speed dropped by 15x around 70% progress.
*   **Cause:** Massive element deletion (`EXCEEDED EPS_MAX`). As elements distort to the breaking point, the Time Step (DT) drops to maintain stability (from `1e-9` to `0.4e-10`).
*   **Result:** This "crunch time" is unavoidable in explicit fracture simulations.

### C. Numeric Explosion (Infinite Values)
*   **Phenomenon:** At the very end (Time 4), ParaView failed to read `A005.vtk` with "Unrecognized keyword: inf".
*   **Cause:** After the main fracture, some flying debris elements became unstable, their coordinates/velocity went to Infinity (NaN/Inf).
*   **Fix:** Created `fix_vtk.py` to scan VTK files and replace `inf`/`nan` with `0.0`.
    ```python
    content.replace(" -inf", " 0.0").replace(" inf", " 0.0")
    ```

## 4. Visualization Artifacts (Part IDs)
*   **Issue:** Parts appearing as zebra stripes or all blue.
*   **Cause 1 (Zebra):** Coincident surfaces. The Shell elements (Skin, ID 100+) perfectly overlap Solid elements (ID 1-4).
*   **Cause 2 (All Blue):** Auto-scaling of Part ID colors from 1 to 103 makes 1-4 indistinguishable.
*   **Solution:** Use ParaView Threshold filter (`ID 1-4`) or Rescale Color Map (`1-5`).

## 5. Next Steps (Recommended)
To achieve "Realistic (Non-Rubber) Shearing" within reasonable time:
1.  **Model Cutout:** Reduce model width to 1/6 or 1/8 (strip model).
2.  **Fine Mesh:** Refine to **0.05mm** (for sharp cutting edge).
3.  **Lower Velocity:** Reduce to **2.0 m/s**.
4.  **Est. Runtime:** ~10-15 hours (Overnight run).

## 6. Scripts Used
*   `inp2radioss_v6.py`: Main converter (Calculix INP -> OpenRadioss RAD).
*   `fix_vtk.py`: VTK sanitizer.
