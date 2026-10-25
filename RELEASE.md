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


## RC3.3 — Mobile navigation scroll correction
- Based on RC3.2; reset mobile sidebar scroll to its top whenever the bottom Menu control opens it.
- Retain native Shiny/bslib drawer positioning and desktop layout; constrain mobile drawer height and independently scroll its contents.
- No changes to clinical calculations, guidelines, or product data.
- Requires real-device verification after deployment; static checks do not establish browser behavior.


## RC3.6 mobile header clearance
- Reserve a dedicated 58px row above the mobile sidebar brand for the native back/close control.
- Keep the Pocket Guide mark and title unobstructed; desktop styles unchanged.
- Live mobile-browser confirmation remains required.
