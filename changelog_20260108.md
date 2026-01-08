# OpenRadioss Configuration Changelog

## 2026-01-08: TYPE25 Contact Algorithm Migration

### Background
- TYPE7 contact consistently caused mesh explosion when Stripper contacted material
- Multiple Stfac values tested (10, 1, 0.1, 0.01, 0.0001) - all failed
- Decision: Try TYPE25 contact which uses constant penalty stiffness

### Changes Made

| Component | Before | After | Reason |
|-----------|--------|-------|--------|
| Stripper Contact | TYPE7 | TYPE25 | More stable for solid elements |
| Stfac | 0.0001 | 1.0 | TYPE25 handles stiffness differently |
| Igap | 3 | 0 | Zero gap for solid elements |

### Contact Definition Change

**Original TYPE7:**
```
/INTER/TYPE7/3
Stripper_Material_Contact
       400       600         4         0         3         0         1         0
             0.10000             0.00001             1.00000             0.00000         1.00000E+30
              0.0001             0.00000         0         2
```

**New TYPE25:**
```
/INTER/TYPE25/3
Stripper_Material_Contact_TYPE25
       400       600         4         0         0         0         1         0         0         0
             0.10000         0.00001         0.00000     1.00000E+30         1.0         0.0         0         2
```

### Expected Outcome
- Stripper contact should not cause mesh explosion
- Simulation should run to completion (35ms)
- Frame 0021 should load correctly in ParaView

### Rollback
If this fails, revert to TYPE7 with Stripper disabled.
