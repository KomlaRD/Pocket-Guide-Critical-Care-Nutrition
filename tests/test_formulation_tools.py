import pytest
from core.formulation_tools import *

def test_nacl_round_trip():
    mmol=mass_mg_to_compound_mmol(584.4,"nacl")
    assert mmol == pytest.approx(10)
    assert compound_mmol_to_mass_mg(mmol,"nacl") == pytest.approx(584.4)

def test_kcl_ion_stoichiometry():
    ions=ion_amounts(10,"kcl")
    assert ions["potassium"] == {"mmol":10.0,"mEq":10.0}
    assert ions["chloride"] == {"mmol":10.0,"mEq":10.0}

def test_magnesium_valence():
    ions=ion_amounts(5,"mgso4_7h2o")
    assert ions["magnesium"]["mmol"] == pytest.approx(5)
    assert ions["magnesium"]["mEq"] == pytest.approx(10)

def test_disodium_stoichiometry():
    ions=ion_amounts(3,"na2hpo4")
    assert ions["sodium"]["mmol"] == pytest.approx(6)
    assert ions["sodium"]["mEq"] == pytest.approx(6)

def test_invalid_formulation_rejected():
    with pytest.raises(ValueError): mass_mg_to_compound_mmol(100,"potassium")

def test_dextrose_concentration_and_rate():
    assert dextrose_concentration_percent(250,1000) == pytest.approx(25)
    assert infusion_rate_ml_hr(1440,24) == pytest.approx(60)

def test_pn_distribution_sums_to_100():
    d=pn_distribution(200,80,50)
    assert d["total_kcal"] == pytest.approx(1500)
    assert d["dextrose_percent"]+d["amino_acid_percent"]+d["lipid_percent"] == pytest.approx(100)

def test_validation():
    with pytest.raises(ValueError): dextrose_concentration_percent(10,0)
    with pytest.raises(ValueError): infusion_rate_ml_hr(1000,0)
    with pytest.raises(ValueError): pn_distribution(0,0,0)
