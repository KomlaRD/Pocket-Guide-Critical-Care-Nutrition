import pytest
from clinical_rules.safety import (
    evaluate_en_safety, evaluate_early_en, evaluate_refeeding,
    carbohydrate_rate_mg_kg_min, evaluate_carbohydrate_limit, evaluate_iv_lipid_limit,
)

def test_en_uncontrolled_shock_alert():
    out = evaluate_en_safety(uncontrolled_shock=True, grv_ml_6h=100)
    assert out[0].status == "ALERT"
    assert out[-1].status == "NOT_TRIGGERED"

def test_grv_threshold_strictly_above_500():
    assert evaluate_en_safety(grv_ml_6h=500)[-1].status == "NOT_TRIGGERED"
    assert evaluate_en_safety(grv_ml_6h=501)[-1].status == "ALERT"

def test_early_en_alert_at_48h_when_oral_impossible_and_not_started():
    r = evaluate_early_en(oral_possible=False, hours_since_icu_admission=48, en_started=False)
    assert r.status == "ALERT"

def test_early_en_not_applicable_when_oral_possible():
    assert evaluate_early_en(oral_possible=True, hours_since_icu_admission=60, en_started=False).status == "NOT_APPLICABLE"

def test_refeeding_threshold_by_absolute_phosphate():
    assert evaluate_refeeding(current_phosphate_mmol_l=0.64).status == "ALERT"
    assert evaluate_refeeding(current_phosphate_mmol_l=0.65).status == "NOT_TRIGGERED"

def test_refeeding_threshold_by_drop():
    assert evaluate_refeeding(current_phosphate_mmol_l=0.70, previous_phosphate_mmol_l=0.87).status == "ALERT"

def test_carbohydrate_rate():
    assert carbohydrate_rate_mg_kg_min(300, 70) == pytest.approx(2.97619, rel=1e-5)

def test_carbohydrate_limit():
    assert evaluate_carbohydrate_limit(600, 70).status == "ALERT"
    assert evaluate_carbohydrate_limit(300, 70).status == "WITHIN_LIMIT"

def test_iv_lipid_limit():
    assert evaluate_iv_lipid_limit(106, 70).status == "ALERT"
    assert evaluate_iv_lipid_limit(100, 70).status == "WITHIN_LIMIT"
