from pathlib import Path
ROOT=Path(__file__).parents[1]; APP=(ROOT/"app.py").read_text()
def test_navigation_population_separation():
 assert '"guidelines":"Critical Care Guidelines"' in APP
 assert '"pediatric":"Pediatric Critical Care"' in APP
 assert '"compare_products":"Compare Formulas"' in APP
 assert "nav-scope-legend" in APP
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
 assert "Please review the input:" in APP
 assert "The selected product cannot be calculated safely" in APP
 assert "Check the selected units and conversion direction." in APP
 assert "Select Male or Female to use the Devine ideal body weight equation." in APP
def test_safe_result_does_not_return_raw_exception_text():
 block=APP[APP.index("def safe_result(fn):"):APP.index("def result_card")]
 assert "return None, str(exc)" not in block
 assert "clinician_error_message(exc)" in block
