from clinical_rules.route_support import evaluate_enteral_access, evaluate_pn_route


def test_gastric_is_standard_when_no_intolerance_or_aspiration_risk():
    r = evaluate_enteral_access(gastric_feeding_intolerance=False, prokinetic_strategy_attempted=False,
                                intolerance_persists=False, high_aspiration_risk=False)
    assert r[0].status == "REFERENCE"
    assert r[0].recommendation_code == "R10"


def test_intolerance_without_prokinetic_surfaces_prokinetic_support():
    r = evaluate_enteral_access(gastric_feeding_intolerance=True, prokinetic_strategy_attempted=False,
                                intolerance_persists=True, high_aspiration_risk=False)
    assert any(x.status == "CONSIDER_PROKINETIC" for x in r)


def test_persistent_intolerance_after_prokinetic_surfaces_postpyloric():
    r = evaluate_enteral_access(gastric_feeding_intolerance=True, prokinetic_strategy_attempted=True,
                                intolerance_persists=True, high_aspiration_risk=False)
    assert any(x.status == "CONSIDER_POSTPYLORIC" for x in r)


def test_high_aspiration_risk_surfaces_postpyloric():
    r = evaluate_enteral_access(gastric_feeding_intolerance=False, prokinetic_strategy_attempted=False,
                                intolerance_persists=False, high_aspiration_risk=True)
    assert any(x.recommendation_code == "R12" for x in r)


def test_espen_pn_days_3_to_7_when_oral_and_en_contraindicated():
    r = evaluate_pn_route(icu_day=4, oral_and_en_contraindicated=True, receiving_en=False,
                          supplemental_pn_considered=False, known_malnutrition=False)
    assert r[0].status == "CONSIDER_PN"


def test_aspen_spn_deferred_before_day_7_in_average_patient():
    r = evaluate_pn_route(icu_day=5, oral_and_en_contraindicated=False, receiving_en=True,
                          supplemental_pn_considered=True, known_malnutrition=False)
    assert r[1].status == "DEFER_ROUTINE_SPN"


def test_aspen_spn_malnutrition_has_limited_applicability():
    r = evaluate_pn_route(icu_day=5, oral_and_en_contraindicated=False, receiving_en=True,
                          supplemental_pn_considered=True, known_malnutrition=True)
    assert r[1].status == "LIMITED_APPLICABILITY"


def test_aspen_spn_day_7_reassess():
    r = evaluate_pn_route(icu_day=7, oral_and_en_contraindicated=False, receiving_en=True,
                          supplemental_pn_considered=True, known_malnutrition=False)
    assert r[1].status == "REASSESS"
