from pathlib import Path
import pytest
from core.refeeding import adult_refeeding_risk, diagnostic_severity, initial_calorie_range

ROOT=Path(__file__).parents[1]

def test_adult_moderate_risk_needs_two_moderate_criteria():
    r=adult_refeeding_risk({"bmi":"moderate","intake":"moderate","electrolytes":"none"})
    assert r.level=="Moderate risk"

def test_one_significant_criterion_is_significant_risk():
    r=adult_refeeding_risk({"bmi":"none","intake":"significant"})
    assert r.level=="Significant risk"

@pytest.mark.parametrize("drop,expected",[(9.9,"Does not meet ASPEN diagnostic decrement threshold"),(10,"Mild"),(19.9,"Mild"),(20,"Moderate"),(30,"Moderate"),(30.1,"Severe")])
def test_diagnostic_severity_boundaries(drop,expected):
    assert diagnostic_severity(drop)==expected

def test_organ_dysfunction_makes_severe_with_timing():
    assert diagnostic_severity(5,organ_dysfunction=True)=="Severe"

def test_timing_required():
    assert diagnostic_severity(40,within_five_days=False)=="Does not meet ASPEN timing criterion"

def test_initial_calorie_range():
    assert initial_calorie_range(70)==(700,1400)

def test_app_uses_erratum_and_non_documenting_language():
    text=(ROOT/"app.py").read_text()
    assert "published erratum" in text
    assert "transient inputs only" in text
    assert "100 mg before feeding" in text
    assert "every 12 hours for the first 3 days" in text
