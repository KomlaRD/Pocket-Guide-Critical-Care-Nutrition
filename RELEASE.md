# Pocket Guide Critical Care — RC1

**Status:** Release candidate  
**Clinical-content baseline:** M9.9  
**Scope:** Adult critical-care nutrition pocket guide and transient bedside calculators  
**Patient documentation:** None  
**Product database:** Deferred  
**Dedicated indirect calorimetry module:** Deferred  
**Pediatric critical care:** Deferred

## RC1 acceptance criteria
- Complete automated regression suite passes.
- Python source compiles.
- Static UI contract passes with zero issues.
- No active patient-documentation workflow is present.
- Product database is not represented as clinically verified.
- Dedicated indirect-calorimetry navigation is absent.
- All active M9 modules remain navigable.
- Distribution ZIP passes integrity testing.

A live multi-browser/mobile-device Shiny acceptance test is not included in the automated RC1 verification and should be performed in the deployment environment before a production/public launch.
