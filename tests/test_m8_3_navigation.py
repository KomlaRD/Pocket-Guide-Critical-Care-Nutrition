from pathlib import Path
import re
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def test_visible_navigation_is_pocket_guide_focused():
    start=APP.index('ui.input_radio_buttons(')
    end=APP.index('selected="home"',start)
    nav=APP[start:end]
    for item in ("Critical Care Guidelines","Refeeding Syndrome","Micronutrients","Quick Reference","Energy & Protein","Nutrition Support","Anthropometry","Calculators & Conversions"): assert item in nav
    for stale in ("Clinical Workflow","Nutrition Overview","Longitudinal Monitoring","Patient Summary"): assert stale not in nav
def test_documentation_panels_removed():
    for key in ("workflow","overview","report","monitoring"): assert f"input.page === '{key}'" not in APP
def test_home_describes_pocket_guide_not_workspace():
    assert "compact clinical pocket guide" in APP
    assert "Your workspace" not in APP
def test_navigation_touch_target_css_present():
    css=(ROOT/"www/styles.css").read_text()
    assert "M8.3 bedside navigation" in css and "min-height:44px" in css
