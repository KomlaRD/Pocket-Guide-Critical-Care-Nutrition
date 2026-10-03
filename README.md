# M10.1 — Pediatric Critical Care Nutrition & Question/Evidence Layout

M10.1 reopens the RC1 baseline for pediatric-specific critical-care nutrition. The Pediatric Critical Care module keeps pediatric recommendations separate from adult targets and is based primarily on ASPEN/SCCM 2017 and ESPNIC 2020. It covers scope, assessment, EN timing/advancement, energy, protein, formula strategy, hemodynamic support, PN and monitoring.

Clinical-question controls now have a distinct visual treatment from evidence/content cards; pediatric source cards are grouped in a separate evidence zone. No patient documentation is introduced.

# Release Candidate RC1 — Pocket Guide Critical Care

This build closes the M9 clinical-content expansion and is the current release-candidate baseline.

## Release scope

Pocket Guide Critical Care is a **non-documenting adult critical-care nutrition reference and bedside calculation tool**. It does not collect or store patient identifiers, patient records, search history, checklist completion status, or longitudinal clinical data. Calculator inputs are transient and exist only to support the current bedside calculation.

The release consolidates:
- Critical-care nutrition guideline reference and quick guidance
- ASPEN refeeding syndrome pathway
- ESPEN micronutrient reference
- Energy, protein, nutrition-support and adequacy calculators
- Anthropometry and dosing-weight tools
- Safety and monitoring reference
- Renal dysfunction and KRT
- Obesity in critical illness
- Acute pancreatitis
- Liver disease in critical illness
- GI losses, high-output stoma, fistula and intestinal-failure guidance
- Trauma, burns, sepsis and surgical ICU modifiers
- Phase-based nutrition monitoring checklist
- Find Guidance bedside index

## Explicitly deferred

- **Product database:** deferred for a later development phase. Existing historical/demo product-data code, if present in the repository, is not promoted as clinically verified product information.
- **Dedicated indirect calorimetry interpretation module:** deferred until it becomes relevant to the intended practice context.
- **Pediatric critical-care nutrition:** outside the current release scope.
- Patient documentation, ADIME records, patient summaries, handoffs and longitudinal patient-state workflows remain outside scope.

## Clinical-use boundary

This application is a cognitive aid and reference. Guideline values and calculators support, but do not replace, clinician assessment, local policy, product verification, or specialist input. Weight descriptors and units should be confirmed before applying calculated recommendations. Missing nutrient/product information must be treated as unknown rather than assumed to be zero.

## Release maintenance

After RC1, routine work should prioritize bug fixes, usability/accessibility improvements, guideline/source updates, citation/version maintenance and validation. New clinical modules or product-database work should be treated as separate scoped milestones.

# Pocket Guide Critical Care Nutrition — M2.4

M2.4 adds the first data-driven **Nutrition Delivery** workflow to the tested M2.2 Shiny Express scaffold.

## Included
- Existing M2.2 bedside calculators.
- Normalized CSV product architecture: products, preparations, nutrients, sources.
- Pure-Python delivery engine supporting an arbitrary number of commercial nutrition sources.
- Liquid products and gram-based modular products.
- Optional custom-product calculation.
- Prescribed versus delivered volume calculation.
- Automatic nutrient totals for energy, protein, carbohydrate, fat, fibre, free water, sodium, potassium, phosphorus and magnesium.
- Nutrient completeness states: `COMPLETE`, `PARTIAL`, `UNAVAILABLE`.
- Missing nutrient values are never treated as zero.
- Shiny Nutrition Delivery page with two commercial source slots plus a custom-product source.

## Important data warning
The bundled products are **synthetic demonstration records only** for software testing and are **not for clinical use**. Replace them with current, verified manufacturer or institutional product data before clinical deployment.

## Run
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
shiny run --reload app.py
```

## Tests
```bash
pytest -q
```

## M2.4 additions

- Tracks propofol and IV dextrose as optional **non-nutrition energy** sources.
- Keeps nutrition energy, non-nutrition energy, and total energy exposure separate.
- Adds a source-by-source energy breakdown.
- Calculates energy adequacy both from nutrition delivery and from total tracked energy exposure, while protein adequacy remains nutrition-derived.
- Adds unit-tested helpers for IV dextrose energy, propofol energy from delivered volume, and combined energy exposure.

Non-nutrition energy values are calculation inputs, not treatment recommendations. Confirm the actual product/formulation and institutional practice before clinical use.

## M3.1 — Guideline/rule engine

M3 adds a deterministic guideline repository and rule evaluator backed by CSV data for a first high-value subset of ESPEN 2023 and ASPEN 2022 adult ICU recommendations. The engine distinguishes `APPLICABLE`, `NOT_APPLICABLE`, and `INSUFFICIENT_CONTEXT`; calculation rules return candidate targets while preserving `CLINICIAN_CONFIRMATION_REQUIRED`. The Shiny UI adds a Guideline Explorer and guided energy target panel. Recommendation summaries are paraphrased and include official-source provenance.

The initial M3 dataset is intentionally selective rather than a claim of complete guideline coverage. It includes ESPEN R17, R18, R22, R23 and R25, plus ASPEN 2022 Q1–Q4. Additional safety and monitoring rules should be added only after source verification and tests.


## M3.1 safety and monitoring decision support

M3.1 adds a deterministic safety layer for ESPEN 2023 early EN timing, selected conditions where EN should be delayed/reassessed, refeeding hypophosphatemia monitoring, and calculated carbohydrate/glucose and IV-lipid limit checks. These outputs are decision support, not autonomous treatment orders. Electrolyte replacement doses and medication orders are intentionally not generated.

The Nutrition Delivery page also surfaces delivery-linked carbohydrate/glucose and IV-lipid checks when sufficient inputs are available. Product/formulation-specific propofol lipid concentration must be confirmed by the clinician.

### Verification

- 41 automated tests passing in M3.1.
- Project Python sources compile successfully.
- Safety threshold boundary cases are explicitly tested.
- Live Shiny browser startup was not performed in this execution environment when Shiny runtime support is unavailable; install `requirements.txt` in the target environment.

## M3.2 — Route, feeding tolerance and PN escalation support

M3.2 adds a separate, unit-tested route-support layer so EN contraindication/delay logic is not conflated with feeding intolerance or access escalation. It adds:

- Gastric access as the ESPEN default reference approach for EN initiation.
- Contextual postpyloric support when gastric intolerance persists despite a reported prokinetic strategy.
- Postpyloric support when a high aspiration-risk context is reported.
- Prokinetic decision support for gastric feeding intolerance without generating medication orders or doses.
- ESPEN PN timing support when oral nutrition and EN are both contraindicated, retaining the 3–7 day context and the requirement to attempt reasonable EN-tolerance strategies where relevant.
- A distinct ASPEN 2022 supplemental-PN pathway: routine supplemental PN is not surfaced before ICU day 7 for the average critically ill adult receiving EN, while known malnutrition is explicitly marked as limited applicability because the informing trials excluded that population.

These outputs remain clinician-confirmation decision support. The application does not autonomously choose an enteral access route, prescribe a prokinetic, initiate PN, or decide that EN is safe.

## M3.3 — Longitudinal monitoring

M3.3 adds a pure-Python daily monitoring model and a Shiny Longitudinal Monitoring page. It tracks daily energy/protein targets and delivery, cumulative adequacy, fluid input/output and cumulative balance, selected GI-tolerance symptoms, and recorded glucose/triglyceride values. Missing fluid components remain unknown rather than being converted to zero.

Glucose and triglyceride entries are deliberately presented as trend/context monitoring. The app does not invent a universal treatment threshold. Likewise, diarrhea, constipation, vomiting and abdominal distension are contextual signals rather than automatic reasons to stop EN. The current UI provides three session-based observations as a first bedside workflow; it does not create a patient record.

## M4 — Bedside Nutrition Overview

M4 adds a mobile-first **Nutrition Overview** page and a reusable `core/overview.py` summary layer. The overview combines clinician-confirmed energy/protein targets, current nutrition and non-nutrition energy exposure, protein delivery, ICU-day/dosing-weight context, and selected active safety signals. It deliberately preserves missing information and filters out reassuring `NOT_TRIGGERED`/`WITHIN_LIMIT` results from the priority-signal area without claiming that their absence establishes safety. Detailed source workflows remain available on their original pages.

## M4.1 — Shared session state
M4.1 adds `core/session_state.py`, a testable session-level state boundary for dosing context, clinician-confirmed targets, latest delivery, safety signals, and daily monitoring snapshots. Candidate calculations remain separate from confirmed prescriptions. Daily snapshots use total tracked energy exposure (nutrition plus tracked non-nutrition energy) and replace an existing observation for the same ICU day rather than creating duplicate-day ambiguity.

## M4.2 — explicit workflow handoffs

M4.2 reduces duplicate bedside entry while preserving clinician control:

- Sidebar dosing weight, height and ICU day synchronize to temporary shared session context.
- Energy & Protein calculations remain candidates until **Use as confirmed target** is pressed.
- The clinician explicitly chooses the lower or upper calculated energy and protein candidate before confirmation.
- Nutrition Delivery calculations remain candidates until **Confirm current delivery** is pressed.
- Confirmed delivery writes nutrition energy, non-nutrition energy and protein to shared state for the Overview and daily snapshot workflow.
- Safety & Monitoring displays the shared ICU day and dosing weight while keeping safety-specific clinical findings independently editable.
- Calculation never implies confirmation; the handoff layer has dedicated regression tests for this boundary.

The session remains temporary and is not a patient record.

## M4.3 — session workflow and usability refinement

M4.3 adds visible shared-session status, clearer incomplete-data guidance, and two deliberate reset paths. **Clear clinical data** removes confirmed targets, current delivery, safety signals, and daily snapshots while preserving calculation context. **Reset entire session** clears both context and clinical state. The reset logic is unit-tested so stale clinical values cannot survive a reset. The Overview also surfaces whether confirmed targets or delivery are still missing, and the compact status strip is optimized for bedside/mobile use.

## M5.1 — Evidence & Quick Reference Library

M5 adds a searchable, source-traceable Quick Reference library while preserving the boundary between **informational evidence** and **executable clinical rules**. Reference entries include category/topic, concise summary, formula or threshold where relevant, source, evidence status, source locator, and verification date.

The initial curated adult ICU set covers ESPEN 2023 and ASPEN adult critical-care guidance plus commonly used bedside formulas and energy conversions. The library is intentionally curated rather than exhaustive; expansion should follow source verification and review.

## M5.1 expanded bedside reference library

M5.1 broadens Quick Reference with weight/obesity calculation conventions, fluid and electrolyte arithmetic/conversions, PN calculations, indirect-calorimetry/ventilation references, renal/KRT considerations, refeeding monitoring, micronutrient context, and common unit conversions. Clinical entries retain source/version/evidence metadata; generic equations remain calculation references and do not become executable rules. The renal and micronutrient source families are tracked separately from the ICU guideline.

## M5.2 — Calculators & Conversions toolkit

M5.2 promotes selected arithmetic/reference equations into a dedicated bedside toolkit while preserving the boundary between calculation and prescription. Added tools include Devine ideal body weight, clinician-selected adjusted body weight factor, fluid balance, enteral formula free water, PN macronutrient energy with editable product-specific lipid energy density, respiratory quotient alongside Weir EE, common kg/lb, cm/in, L/mL and kcal/kJ conversions, and valence-aware mmol↔mEq arithmetic. The electrolyte converter deliberately does not generalize mg↔mmol because that requires compound-specific molecular weight and formulation context.

All outputs are labeled as calculations/conversions rather than clinical prescriptions. Existing guideline rules, shared-state confirmation behavior, delivery calculations, monitoring, and safety logic are unchanged.

## M5.3 — formulation-aware electrolyte and PN tools

M5.3 adds a chemical-formulation catalog and compound-specific mass↔mmol plus ion mmol/mEq arithmetic. Molecular weight, stoichiometry, valence, hydration-state warnings and formulation identity are explicit; the app does not infer a salt from a generic electrolyte name. Commercial product concentrations still require label confirmation. The bedside toolkit also adds dextrose % w/v, PN infusion rate, and macronutrient energy-distribution calculations. These remain arithmetic tools, not prescriptions.

## M6 — production readiness and data quality

M6 adds a standalone dataset audit (`python audit_data.py`) that can run in CI or before deployment. Structural errors fail closed: missing datasets, duplicate identifiers/composite nutrient rows, orphan product/preparation/nutrient/guideline/reference links, invalid product verification states, and missing required guideline provenance are errors. Incomplete-but-permitted content is surfaced as a warning rather than converted to zero or silently accepted as verified. The bundled nutrition products remain explicitly `DEMO_ONLY`; the audit therefore reports four expected warnings until manufacturer-verified compositions replace them.

Production deployment should run both `PYTHONPATH=. pytest -q` and `python audit_data.py` before release. Clinical content remains versioned/source-traceable and the app continues to distinguish calculations, informational references, executable rules, and clinician-confirmed state.

### M6 compatibility fix: Shiny Express UI outputs

Shiny Express automatically places `@render.ui` functions at their declaration locations. Removed three `ui.output_ui(...)` calls (an API not exposed by `shiny.express.ui`) for session status, Overview confirmation status, and Quick Reference results. Keep `@render.ui` declarations where the outputs should appear. This fixes the reported import-time attribute error; a live browser smoke test remains recommended in the deployment environment.

## Material 3-inspired UI refresh

This edition refreshes the visual hierarchy, sidebar navigation, card surfaces, typography, forms, action buttons, confirmation states and mobile spacing using a Material 3-inspired token palette. The app remains Shiny Express/Bootstrap, not the Android Material library. Clinical logic and existing form identifiers are unchanged. The bundled product compositions remain synthetic demonstration data and are not suitable for clinical use.


### Material 3 scrolling and card readability update
The Shiny Express page uses `fillable=False` so long clinical sections scroll as
one readable page rather than constraining every card to an independent scroll
container. Card bodies and reactive results expand to fit content. Responsive
input and result grids collapse on narrow viewports. Wide tables can still
scroll horizontally when necessary. Card titles use consistent title case while
clinical abbreviations (PN, EN, mmol, mEq, VO2 and VCO2) retain standard case.


### M6.2 — Independent nutrition product review

Added digest-bound, independent reviewer attestation and a separate controlled export for manufacturer product staging. This milestone does not introduce invented Ghana-market products or automatically enable any unverified product in patient calculations. See `staging/README.md`.


### M6.3 — Controlled product catalog promotion

The `core.product_promotion` CLI merges an independently reviewed M6.2 export into a **new, separate full data directory**. It refuses existing IDs, missing/altered candidate files, unreviewed records, incomplete release authorization, and structural audit failures. The original bundled database is never modified. This does not introduce or claim verification of any real manufacturer product.

1. Obtain authentic market-specific manufacturer documentation and complete the M6.1 staging and M6.2 independent review.
2. Independently check the exact reviewed CSVs and fill `staging/release_authorization.template.json` with the M6.2 manifest batch digest and SHA-256 of **each exported CSV**. A third named institutional authorizer (different from submitter and reviewer) must document authorization.
3. Run `python -m core.product_promotion staging/reviewed_batch data staging/release_authorization.json staging/release_candidate_data`. The output path must not exist.
4. Inspect the new `release_manifest.json`, compare source documents again if needed, perform clinical acceptance tests and institutional deployment approval **before** deliberately replacing a deployed catalog. No automatic deployment occurs.

The demonstration products remain demonstration-only until authentic documents and the required human checks are supplied.

**Export immutability:** M6.3 adds `export_file_sha256` to new M6.2 review manifests. Generate a **fresh M6.2 reviewed export using this release** before attempting M6.3 promotion; legacy review exports without these per-file checksums intentionally fail closed.


### Patient Context and Session Controls (M6.3 maintenance fix)

The sidebar dosing weight, height, and ICU day automatically synchronize with the
shared calculation context; **Apply Patient Context** also provides an explicit
confirmation and visible notification. **Clear Clinical Data** clears confirmed
targets, delivery, alerts and daily snapshots while retaining context. **Reset
Entire Session** clears these and restores the editable sidebar defaults of
70 kg, 170 cm and ICU day 1; these are placeholders, **not clinical prescriptions**.
The UI uses a reactive revision signal so dependent shared-state panels refresh.


### Guidelines and navigation UI update
Guideline headings now use consistent capitalization while preserving clinical abbreviations (EN, PN, ICU, IV, EE). The navigation sidebar fills the viewport height, scrolls to expose all sections and session controls, and wraps long labels instead of truncating them.


## M7.1 — Unified Patient Context

Patient Context fields are drafts until **Apply Patient Context** is selected.
The status bar displays the applied dosing weight, height, and ICU day.
Calculators use only applied values. Changes to context never silently
recalculate or overwrite clinician-confirmed targets: an explicit
**Prescription review needed** warning appears until targets are reconfirmed
or clinical data is cleared. This is temporary in-memory session state, not
a patient record. A live browser interaction check is recommended before
clinical deployment.


## M7.2 — Integrated Clinical Workflow
The **Clinical Workflow** navigation page provides a reactive, clinician-controlled sequence: applied patient context → assessment acknowledgment → confirmed prescription → confirmed current delivery → ICU-day snapshot. It reads existing shared session state, does not auto-confirm any clinical decision, and flags targets requiring reconfirmation after patient-context changes. New daily snapshots are blocked while a prescription review is outstanding. Product verification remains deferred.


## M7.3 — Clinical safety and validation

- Centralized, testable pre-capture validation for missing, invalid and stale inputs.
- A change in patient context requires assessment review and explicit reconfirmation of **both** prescription and delivery before a new snapshot through the Shiny monitoring workflow. The legacy low-level snapshot method remains available for backward compatibility; integrations must call the validator explicitly. Existing clinical decisions remain visible; they are not silently overwritten.
- The monitoring page displays actionable pre-capture findings and honest session-level provenance limitations.
- This release does not validate clinical appropriateness, persist individual calculation methods or product provenance, or constitute a clinical device validation.


## M7.4 — Patient Summary and Export

Use **Patient Summary & Export** in the sidebar to review the applied context, clinical confirmation status, prescription, delivery and captured monitoring. **Download Printable Patient Summary (HTML)** creates a standalone, print-friendly report with detailed daily records and limitations. Use your browser’s Print → Save as PDF if needed. The report intentionally does not collect patient identifiers. It does not assert manufacturer/product provenance or persist a medical record. Prior daily observations can reflect earlier context; check before interpretation.

### M7.4 download compatibility fix

The patient-summary download button uses `shiny.ui.download_button` (imported as `core_ui`) rather than the Shiny Express `ui` namespace. The `@render.download` handler remains unchanged.

## M7.5 — Interface and end-to-end reliability

M7.5 adds a CI-friendly static Shiny UI contract audit (`python audit_ui.py`) that catches the compatibility regressions encountered during development: unsupported Shiny Express `ui.output_ui`/`ui.download_button` calls, positional children passed to `ui.layout_columns`, duplicate literal input IDs, and manual download controls that duplicate an `@render.download` output. The Material 3 CSS also standardizes touch targets, sidebar action spacing, input rhythm, mobile button width and unclipped validation/dropdown content.

The automated checks do **not** replace live browser testing. This build environment does not include the Shiny package or a browser runtime, so deployment acceptance should still exercise navigation, patient-context apply/reset, prescription/delivery reconfirmation, snapshot capture, and patient-summary download in the target Shiny environment.

## M8 — Pocket Guide Scope Reset

Pocket Guide Critical Care is a reference and bedside calculation tool, not a documentation system. The user-facing application does not request patient identifiers, create patient records, or provide patient-summary exports. Legacy workflow/report/longitudinal-monitoring surfaces have been removed from navigation. Generic clinical values entered into individual calculators are transient calculation inputs only.

M8 adds:
- ASPEN 2020 refeeding syndrome bedside reference, explicitly accounting for the published erratum (DOI 10.1002/ncp.10491).
- ESPEN micronutrient bedside reference based on the 2022 scientific guideline and 2024 practical short guideline.
- Direct source links and guideline/version provenance.

Clinical content is decision support only and must be interpreted by qualified clinicians in context.

## M8.1 — Expanded ESPEN Micronutrient Bedside Reference

M8.1 adds a searchable bedside lookup for 22 essential vitamins and trace elements summarized from the ESPEN practical short micronutrient guideline (Clinical Nutrition 43, 2024, 825–857). The lookup separates routine adult EN provision (approximately 1500 kcal/day) from home/long-term PN reference provision, retains units explicitly, and adds concise clinical interpretation cautions.

L-carnitine, choline, and coenzyme Q10 are identified separately because ESPEN discusses them outside the routine essential vitamin/trace-element provision table. Routine provision values must not be interpreted as deficiency-treatment doses.

Primary source: Berger MM, Shenkin A, Dizdar OS, et al. ESPEN practical short micronutrient guideline. Clinical Nutrition. 2024;43:825–857.
Scientific source: Berger MM, Shenkin A, et al. ESPEN micronutrient guideline. Clinical Nutrition. 2022;41:1357–1424.

## M8.2 — ASPEN Refeeding Syndrome Bedside Pathway

M8.2 expands the refeeding section into a non-documenting adult bedside pathway based on the 2020 ASPEN Consensus Recommendations for Refeeding Syndrome and its published erratum. It includes corrected adult risk criteria, consensus diagnostic severity, prefeeding electrolyte/thiamin checks, initial calorie reference arithmetic, advancement, electrolyte monitoring, response to precipitous electrolyte decline, and early monitoring.

The risk and diagnostic tools use transient inputs only. They are clinical reference aids and do not create patient records, diagnoses, treatment orders, or persistent histories.

## M8.3 — Guideline Navigation & Bedside UX

M8.3 simplifies visible navigation around pocket-guide tasks and removes obsolete documentation-oriented panels (Clinical Workflow, Nutrition Overview, Patient Summary, and Longitudinal Monitoring). Nutrition Delivery and Adequacy remain transient bedside calculators.

Navigation now prioritizes critical-care guidelines, ASPEN refeeding syndrome, ESPEN micronutrients, quick reference, requirements, nutrition support, safety, anthropometry, and calculators. Sidebar targets are sized for touch use and long labels wrap rather than truncate.

## M8.4 — Critical Care Guideline Expansion

M8.4 replaces the prior rule-centric guideline screen with a bedside topic library centered on the ESPEN 2023 practical and partially revised ICU guideline. Topics include route/timing, energy, protein, EN intolerance, PN/supplemental PN, obesity, kidney disease/RRT, liver failure, and special ICU situations.

Recommendations remain source-labelled and are presented as bedside reference guidance rather than patient documentation or automated prescriptions. Dedicated ASPEN refeeding and ESPEN micronutrient modules remain separate.

## M8.5 — Safety & Monitoring Reference

M8.5 replaces the previous state-linked safety workflow with a problem-oriented, non-documenting bedside reference. Topics include EN delay/holding conditions, gastric residual volume and intolerance, aspiration risk, diarrhea, constipation, refeeding/electrolytes, glucose, triglycerides/IV lipid, fluid balance, and PN safety.

The reference emphasizes reassessment rather than reflexively stopping nutrition. It distinguishes uncontrolled shock and true gastrointestinal contraindications from potentially manageable feeding intolerance, and it avoids inventing universal thresholds where product-, institution-, or patient-specific context is required.

## M8.6 — Calculator & Anthropometry Consolidation

M8.6 audits and consolidates bedside calculations. Anthropometry now uses explicit transient weight/height inputs rather than hidden session context, combines BMI and weight change, and places Devine/adjusted-weight calculations beside an explicit warning that weight descriptors are method-specific and not interchangeable.

Duplicate weight tools were removed from the general calculator suite. Feeding-duration and daily propofol-energy calculations now reject durations above 24 hours, and negative percentage weight change is explicitly identified as weight gain rather than being mislabeled as weight loss. Existing formulation-aware electrolyte, PN, indirect calorimetry, fluid and unit-conversion arithmetic remains covered by automated tests.

## M8.7 — Pocket-Guide Architecture Cleanup

M8.7 removes the obsolete patient/session/documentation architecture rather than merely hiding it. Removed modules include session state, patient reporting, clinical handoffs, longitudinal monitoring, overview aggregation, and snapshot validation. Their dedicated legacy tests were retired and replaced with pocket-guide boundary tests.

Energy/protein, GIR, anthropometry, and delivery-linked limit checks now use explicit transient calculation inputs. There is no shared patient context, target confirmation state, delivery confirmation state, daily snapshot workflow, or patient-summary export in the application. Automated contract tests enforce the absence of patient-identifying/documentation surfaces and legacy session imports.

## M9.1 — Renal Dysfunction & KRT/CRRT Nutrition

M9.1 adds a non-documenting adult bedside module based primarily on the 2024 ESPEN practical guideline for hospitalized patients with acute or chronic kidney disease. It separates critically ill patients not receiving KRT, conventional intermittent KRT, and CKRT/PIKRT; highlights guideline protein ranges and reference-weight cautions; and covers energy/route, extracorporeal nutrient losses, fluid/electrolyte interpretation, and monitoring.

The module explicitly warns against reducing protein merely to avoid/delay KRT and against translating quoted CKRT nutrient losses into fixed replacement prescriptions.

## M9.2 — Obesity in Critical Illness

M9.2 adds a non-documenting adult ICU obesity module. It prioritizes indirect calorimetry, assessment for sarcopenic obesity, and explicit weight descriptors. The ESPEN pathway includes the pragmatic adjusted-body-weight fallback and protein guidance when urinary nitrogen losses or lean-body-mass measurement are unavailable.

A separately labelled ASPEN card summarizes its hypocaloric high-protein framework. The two society approaches are deliberately not merged. The module includes an ESPEN adjusted-weight calculator with applicability safeguards and bedside monitoring prompts for overfeeding, protein delivery, non-nutritional calories, glucose, triglycerides, fluid status, and muscle loss.


## M9.3 revision — Indirect calorimetry deferred

The dedicated indirect-calorimetry interpretation module introduced in the initial M9.3 build has been removed because it is not currently relevant to the intended practice context. Brief references to indirect calorimetry remain only where guideline recommendations use it to explain why a fallback method or weight convention is being used. A dedicated IC module can be revisited later.

## M9.4 — Acute Pancreatitis Nutrition

M9.4 adds an adult acute-pancreatitis bedside nutrition pathway based on the 2024 ESPEN practical guideline. It covers early oral feeding, EN timing, nasogastric versus nasojejunal access, enteral formula selection, PN indications, severe/necrotizing disease, pancreatic enzyme considerations, and nutrition monitoring.

The module explicitly avoids obsolete 'pancreatic rest' logic: oral feeding does not require normalization of serum lipase, EN is preferred to PN when oral feeding is not possible, nasogastric feeding is the usual initial EN route, and standard polymeric formula is appropriate for most patients.

## M9.5 — Liver Disease in Critical Illness

M9.5 adds a non-documenting adult liver-disease nutrition module based primarily on the ESPEN practical liver guideline. It covers nutrition assessment in fluid overload, cirrhosis energy/protein, hepatic encephalopathy, acute liver failure, route selection, prolonged fasting and late-evening snacks, ascites/sodium/fluid considerations, micronutrients/refeeding, and bedside monitoring.

The module explicitly prevents routine protein restriction for hepatic encephalopathy and warns that ascites/edema can make scale weight and BMI misleading. Sodium and fluid advice is contextual rather than an automatic restriction.

## M9.6 — GI Losses, High-Output Stoma & Intestinal Failure

M9.6 adds a non-documenting adult bedside module for high-output small-bowel stomas, enterocutaneous fistulae and short-bowel/intestinal-failure situations. It emphasizes that clinically important high output is defined by its consequences as well as volume; assesses anatomy and reversible causes; and provides practical fluid, sodium, oral/enteral, PN and monitoring guidance.

A prominent safety warning prevents generic 'drink more water' advice in high-output jejunostomy/ileostomy. The module highlights glucose-saline oral rehydration with approximately 90–120 mmol/L sodium, cautions against excessive hypotonic and hypertonic sugary fluids, and makes anatomy/functional absorption central to route decisions.

## M9.7 — Trauma, Burns, Sepsis & Special ICU Situations

M9.7 adds condition-specific nutrition modifiers for sepsis/septic shock, major trauma, major burns, postoperative/surgical critical illness and open-abdomen/wound-loss situations. It is intentionally layered on top of the general ICU guideline rather than duplicating it.

Safety emphasis includes withholding advancement during uncontrolled shock, progressive rather than immediate full energy delivery, treating energy and protein as separate decisions, avoiding unnecessary postoperative starvation, accounting for procedure-related feed interruptions and wound/GI losses, and referring major burns to burn-specific protocols rather than inventing a universal calorie or micronutrient prescription.

## M9.8 — Nutrition Monitoring Checklist

M9.8 adds a non-documenting bedside monitoring checklist organized by phase: before initiation/change, first 72 hours and advancement, established EN, established PN, refeeding/high electrolyte risk, prolonged ICU review, and review after interruptions or major clinical change.

It also provides a six-step daily cognitive aid covering route, actual delivery, tolerance/safety, biochemistry, fluids/non-nutritional calories, and trajectory. The checklist intentionally stores no patient information or completion status and avoids prescribing one universal laboratory schedule for every ICU patient.

## M9.9 — Find Guidance & Clinical-Content Harmonization

M9.9 consolidates the M9 clinical expansion. A new **Find Guidance** bedside index routes common questions to the appropriate pocket-guide module without storing search history or patient information. The index covers EN initiation, shock, EN intolerance, refeeding, micronutrients/electrolytes, energy/protein, obesity, renal/KRT, liver disease, pancreatitis, GI losses/intestinal failure, special ICU situations, PN, monitoring, anthropometry and calculators.

The milestone also adds regression checks that preserve major safety messages and terminology contracts: no full EN advancement in uncontrolled shock, contextual GRV interpretation, no routine protein restriction for hepatic encephalopathy, explicit weight descriptors, continued availability of all active M9 modules, and continued exclusion of the deferred dedicated indirect-calorimetry module.

## M10.2 — Pediatric Calculations & Growth

Adds a pediatric bedside energy/protein calculator for children >1 month to <18 years using Schofield weight-only equations as a guideline-supported fallback when measured REE is unavailable. No stress factor is added in the acute phase. The calculator also displays the ASPEN/SCCM 1.5 g/kg/day minimum protein reference with an explicit reminder that protein and energy are separate decisions and that the protein evidence requires clinical interpretation.

Adds pediatric anthropometry/growth guidance emphasizing age- and sex-appropriate growth references, BMI-for-age rather than adult BMI cutoffs, multidimensional interpretation of growth, and fluid-status limitations in critical illness. Z-scores are deliberately not approximated without validated LMS reference data.

## M10.3 — Pediatric EN Workflow

Adds transient pediatric EN delivery/adequacy calculations using clinician-entered, verified feed composition: daily volume, EN fluid mL/kg, energy delivery and adequacy, protein delivery in g/day and g/kg/day, and protein adequacy. Product composition is never assumed.

Adds a pediatric EN advancement/safety pathway grounded in ESPNIC and ASPEN/SCCM guidance: early EN in eligible children, protocolized stepwise advancement, minimizing avoidable interruptions, fluid-aware formula selection, and explicit hemodynamic safeguards. No universal mL/kg/hour advancement schedule is invented; local pediatric feeding protocols remain necessary.

## M10.4 — Pediatric Quick Reference & Phase-Based Monitoring

Adds a one-screen pediatric critical-care nutrition quick reference covering route/timing, acute-phase energy, protein, PN, hemodynamic feeding and growth/recovery. It retains the explicit >1 month to <18 years ASPEN/SCCM scope boundary and warns against neonatal application.

Adds a non-documenting pediatric monitoring pathway organized by acute/early PICU, stable nutrition advancement, recovery/rehabilitation/growth, and post-interruption/clinical deterioration. A five-step daily review reinforces clinical phase, route, actual delivery, safety/tolerance and growth trajectory. Responses remain transient and are not stored.

## M11.1 — Ghana-Relevant Product Database Foundation

Reopens the product-database work using the attached Abbott Nutrition Product Guide as a manufacturer source. A new `staging/abbott_ghana_2026` batch contains four source-backed candidate formulations: Ensure Original Shake, Ensure Plus Nutrition Shake, Glucerna Shake, and PediaSure Enteral Formula 1.0 Cal.

All records remain inactive and `PENDING_VERIFICATION` because exact equivalence with products currently sold in Ghana has not yet been established. Nutrient data are retained on the manufacturer's exact 8 fl oz/237 mL basis; inequality values are not converted into invented point estimates. The ingestion validator now accepts a traceable uploaded manufacturer PDF with page/version locator rather than requiring an external URL.

The schema remains manufacturer-agnostic so Ghanaian/local formulas can later be added with independent provenance, formulation/preparation details, and verification status before promotion into clinical calculations.

## M11.2 — Expanded Ghana Reference Catalogue

Based on local practice input, Abbott formulations are now treated as Ghana-relevant reference products while retaining exact formulation identities. The catalogue includes Ensure Original, Ensure Plus, standard PediaSure (PediaSure Enteral Formula 1.0 Cal), and all 12 Glucerna products/formulations listed in the source guide.

Glucerna liquid enteral formulas, oral-only shakes, powder and solid snack/bar products are intentionally distinct. `product_use_policy.csv` prevents powder/bars from entering liquid volume/rate calculations and prevents oral-only products from being silently treated as tube feeds. This supports the reality that different Glucerna forms may appear on the Ghanaian market.

The catalogue remains in the existing independent-review/promotion pipeline. Future Ghanaian/local formulas can be added as independent products with their own composition evidence and provenance.

## M11.3 — Product Reference UI & Calculation Integration

Promotes the 15-product Abbott Ghana-reference catalogue into the app runtime and replaces the former demonstration catalogue. Adds a clinician-facing Product Reference page with exact formulation selection, manufacturer reference basis, route/form, core composition, missing-value display, source context, and transient energy/protein target calculations.

Runtime product metadata now includes route, physical form, use class and liquid-volume calculation eligibility. Nutrition Delivery rejects powders and solid products from liquid delivery calculations; oral-only products retain their route identity. The Product Reference calculator can still express energy/protein quantities in the manufacturer's native source unit without implying a liquid rate.

Calculations answer how much selected product would provide a clinician-entered nutrient amount; they do not establish a patient prescription. Missing nutrient values remain unknown rather than zero.

## M11.4 — Formula Comparison & Feeding Prescription Support

Adds neutral side-by-side comparison of three eligible liquid formulas using energy density (kcal/mL) and protein, water, carbohydrate, sodium, potassium, phosphorus and magnesium normalized per 1000 kcal. Missing manufacturer values remain visibly unavailable rather than being imputed.

Adds a continuous-EN support calculator driven by clinician-entered energy target and planned feeding hours. It calculates formula volume (mL/day), rate (mL/h), protein delivered, protein adequacy against a separately entered protein target, and formula water when reported. Energy and protein remain separate prescription decisions.

Only products marked eligible for liquid-volume calculations can enter this workflow; powders and solid snack products remain excluded. The interface does not rank or recommend a formula.

## M11.5 — Product Consolidation & Gastric Bolus Feeding

Consolidates the product workflow and adds a Ghana-relevant gastric bolus calculator. For an eligible liquid formula, clinician-entered daily energy and protein targets and number of feeds/day produce total formula volume, mL/feed, protein/day and per feed, protein adequacy, and formula water when reported.

Bolus is explicitly limited to gastric delivery in this decision-support workflow. Small-bowel selection fails closed. The app intentionally does not hard-code a universal maximum bolus volume: calculated mL/feed must be assessed against individual tolerance, aspiration risk, enteral access and local protocol. Administration time and water flush volume remain clinician-prescribed rather than inferred from formula volume.

Source framing follows nutrition-support references that distinguish bolus, intermittent/gravity, cyclic and continuous administration and call for bolus/intermittent orders to specify feeding number, volume/rate, advancement and water flushes.

## RC2 — Release Readiness Consolidation

RC2 freezes the M11.5 clinical/product feature set and performs a release-level regression pass. No new clinical module is introduced.

Release checks cover adult/pediatric navigation identity, absence of patient identifier fields and runtime patient persistence, pediatric energy guardrails, gastric-only bolus safeguards, product-form restrictions, neutral formula comparison, manufacturer-data catalogue integrity, responsive UI contract, and preservation of all prior milestone tests.

A compact navigation scope legend was added to make the adult, pediatric, calculator and product surfaces easier to distinguish without changing existing navigation keys or clinical content.

## Clinical use and limitations

Pocket Guide Critical Care is an evidence-informed clinical reference and decision-support application. It does not replace individualized nutrition assessment, professional clinical judgment, current manufacturer/product information, institutional policy, or locally applicable protocols. Clinicians remain responsible for verifying the appropriateness and accuracy of information used from the application and for clinical decisions, prescriptions, monitoring, and patient care arising from its use.

Guidelines, evidence, and product formulations may change; clinically consequential information should be checked against current primary sources, manufacturer information, and local policy.

## Developer

**Eric Anku** — Registered Dietitian and developer of Pocket Guide Critical Care.  
GitHub: https://github.com/KomlaRD



## RC2.8 — Adaptive Navigation & Information Architecture
Navigation is ordered around clinicians' conceptual tasks: quick access, guidance, clinical conditions, nutrition support, calculators, and products. Pediatric Critical Care remains a prominent distinct pathway. Narrow screens use larger touch targets and a compact sidebar surface; clinical content and calculation logic are unchanged.
