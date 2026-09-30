from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()

FORBIDDEN_UI_TERMS=("Patient Context","MRN","medical record number","patient name","date of birth","daily snapshot","patient summary")
FORBIDDEN_MODULES=("session_state.py","patient_report.py","handoff.py","monitoring.py","overview.py","clinical_validation.py")

def test_no_patient_documentation_language_in_app():
    lower=APP.lower()
    for term in FORBIDDEN_UI_TERMS:
        assert term.lower() not in lower

def test_legacy_documentation_modules_removed():
    for name in FORBIDDEN_MODULES:
        assert not (ROOT/"core"/name).exists()

def test_no_legacy_session_or_export_imports():
    tree=ast.parse(APP)
    imported={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    for mod in ("core.session_state","core.patient_report","core.handoff","core.monitoring","core.overview","core.clinical_validation"):
        assert mod not in imported

def test_calculator_inputs_are_transient_and_explicit():
    for input_id in ("req_weight","gir_weight","anth_weight","anth_height","del_limit_weight"):
        assert input_id in APP

def test_sidebar_states_privacy_boundary():
    assert "No patient identifiers or records are collected." in APP
