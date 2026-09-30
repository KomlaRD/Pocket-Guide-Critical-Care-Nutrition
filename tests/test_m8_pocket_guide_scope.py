from pathlib import Path
APP = Path(__file__).parents[1].joinpath('app.py').read_text()

def test_documentation_surfaces_removed_from_navigation():
    nav = APP[APP.index('ui.input_radio_buttons('):APP.index("with ui.panel_conditional(\"input.page === 'home'\")")]
    for label in ('Patient Summary & Export','Clinical Workflow','Longitudinal Monitoring','Nutrition Overview'):
        assert label not in nav

def test_no_visible_patient_context_sidebar():
    sidebar = APP[APP.index('with ui.sidebar'):APP.index("with ui.panel_conditional(\"input.page === 'home'\")")]
    assert 'PATIENT CONTEXT' not in sidebar
    assert 'No patient identifiers or records are collected' in sidebar

def test_m8_reference_pages_present():
    assert "input.page === 'refeeding'" in APP
    assert "input.page === 'micronutrients'" in APP
    assert '10–20 kcal/kg' in APP
    assert 'C-reactive protein (CRP)' in APP
    assert '10.1002/ncp.10491' in APP
