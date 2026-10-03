from pathlib import Path
ROOT=Path(__file__).parents[1]; APP=(ROOT/"app.py").read_text()
def test_navigation_population_separation():
 assert '"guidelines":"Critical Care Guidelines"' in APP
 assert '"pediatric":"Pediatric Critical Care"' in APP
 assert '"compare_products":"Compare Formulas"' in APP
 assert "nav-section-label" in APP
def test_no_demo_catalogue_copy():
 assert "demonstration data only" not in APP
 assert "DEMO_" not in APP
def test_no_patient_identifier_fields():
 for x in ["MRN","patient_name","date_of_birth"]:
  assert x not in APP
def test_bolus_guardrails_visible():
 assert "Use for gastric delivery only." in APP
 assert "not a universal safe-volume threshold" in APP
def test_product_decision_support_not_formula_ranking():
 assert "does not select a preferred formula" in APP
def test_pediatric_energy_guardrails_preserved():
 assert "Do not add a stress factor during the acute phase." in APP
 assert "Do not use adult predictive equations, Harris–Benedict" in APP

def test_no_positional_ui_card_construction():
 import re
 for line in APP.splitlines():
  stripped=line.strip()
  if "ui.card(" in stripped and not stripped.startswith("with ui.card("):
   raise AssertionError(f"Positional ui.card construction is incompatible with Shiny Express Card API: {stripped}")

def test_developer_credit_present():
 assert "Developer: Eric Anku" in APP
 assert "https://github.com/KomlaRD" in APP

def test_clinical_limitation_and_responsibility_message():
 assert "Clinical use & limitations" in APP
 assert "The treating clinician remains responsible" in APP
 assert "current product labeling" in APP
 assert "institutional policies" in APP
def test_developer_home_card():
 assert "Eric Anku — Registered Dietitian and developer of Pocket Guide Critical Care." in APP
 assert "GitHub · KomlaRD" in APP

def test_nutrition_delivery_has_no_catalogue_banner():
 assert 'ui.strong("Product catalogue: ")' not in APP
def test_adequacy_inputs_and_percent_outputs_are_explicit():
 assert 'ui.h2("Nutrition Adequacy")' in APP
 assert '"energy_prescribed"' in APP and '"energy_delivered"' in APP
 assert '"protein_prescribed"' in APP and '"protein_delivered"' in APP
 assert 'result_card("Energy adequacy", f"{num(r.value, 1)}%"' in APP
 assert 'result_card("Protein adequacy", f"{num(r.value, 1)}%"' in APP

def test_user_errors_are_clinician_readable():
 assert "def clinician_error_message(exc):" in APP
 assert "The calculation could not be completed with the values entered." in APP
 assert "The selected product cannot be calculated safely" in APP
 assert "Check the selected units and conversion direction." in APP
 assert "Select Male or Female to use the Devine ideal body weight equation." in APP
def test_safe_result_does_not_return_raw_exception_text():
 block=APP[APP.index("def safe_result(fn):"):APP.index("def result_card")]
 assert "return None, str(exc)" not in block
 assert "clinician_error_message(exc)" in block

def test_compare_formulas_is_comparison_only():
 sec=APP[APP.index("input.page === 'compare_products'"):APP.index("input.page === 'delivery'")]
 assert 'ui.h2("Formula Comparison")' in sec
 assert "Continuous EN from clinician-entered target" not in sec
 assert "Gastric bolus feeding" not in sec
def test_feeding_regimen_tools_are_under_nutrition_support():
 sec=APP[APP.index("input.page === 'support'"):APP.index("input.page === 'products'")]
 assert "Continuous EN from clinician-entered target" in sec
 assert "Gastric bolus feeding" in sec
def test_weight_change_uses_signed_gain_loss_convention():
 sec=APP[APP.index("input.page === 'anthro'"):APP.index("input.page === 'support'")]
 assert "change_pct=(current-usual)/usual*100" in sec
 assert 'signed_change=f"{change_pct:+.1f}"' in sec
 assert "Negative = weight loss; positive = weight gain." in sec
def test_clinician_error_adapter_never_returns_raw_exception_message():
 sec=APP[APP.index("def clinician_error_message"):APP.index("def safe_result")]
 assert "return f\"Please review the input: {msg}\"" not in sec
 assert "return raw" not in sec
 assert "The calculation could not be completed with the values entered." in sec

def test_cleared_anthropometry_fields_do_not_expose_python_errors():
 sec=APP[APP.index("def anthro_results():"):APP.index("with ui.card():", APP.index("def anthro_results():"))]
 assert "missing_inputs(input.anth_weight(), input.anth_height(), input.usual_weight())" in sec
 assert 'enter_prompt("current weight, height, and usual weight")' in sec
def test_direct_numeric_cast_renderers_guard_empty_inputs():
 assert "def missing_inputs(*values):" in APP
 assert 'enter_prompt("actual weight, ideal/reference weight, and adjustment factor")' in APP
 assert 'enter_prompt("age, weight, and sex")' in APP
 assert 'enter_prompt("weight, EN delivery, feed composition, and current goals")' in APP

def test_rc28_navigation_has_clinical_concept_order():
 nav=APP[APP.index('"home":"Home"'):APP.index('selected="home"', APP.index('"home":"Home"'))]
 order=['"home":"Home"','"find":"Find Guidance"','"reference":"Quick Reference"','"pediatric":"Pediatric Critical Care"','"guidelines":"Critical Care Guidelines"','"renal":"Renal & KRT"','"requirements":"Energy & Protein"','"anthro":"Anthropometry"','"products":"Product Reference"']
 pos=[nav.index(v) for v in order]
 assert pos==sorted(pos)
def test_rc28_mobile_navigation_has_touch_target_rules():
 css=(ROOT/"www"/"styles.css").read_text()
 assert "RC2.8 adaptive information architecture" in css
 assert "max-width:min(88vw,360px)" in css
 assert "min-height:50px" in css
 for label in ("GUIDANCE","CLINICAL CONDITIONS","NUTRITION SUPPORT","CALCULATORS","PRODUCTS"):
  assert label in css
