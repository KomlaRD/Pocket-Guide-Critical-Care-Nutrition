from pathlib import Path
import pytest
from core.micronutrients import load_micronutrients, micronutrient_choices

ROOT=Path(__file__).parents[1]
def test_bundled_micronutrient_reference_has_essential_set():
    items=load_micronutrients(ROOT/"data/reference/espen_micronutrients.csv")
    assert len(items)==22
    ids={x.id for x in items}
    assert {"thiamine","selenium","zinc","vitamin_d","vitamin_c"} <= ids

def test_units_and_reference_context_are_explicit():
    items={x.id:x for x in load_micronutrients(ROOT/"data/reference/espen_micronutrients.csv")}
    assert "µg" in items["selenium"].en_1500kcal
    assert "1500" not in items["selenium"].en_1500kcal
    assert "mg" in items["thiamine"].pn_home_longterm

def test_duplicate_ids_fail_closed(tmp_path):
    p=tmp_path/"m.csv"
    p.write_text("id,name,category,en_1500kcal,pn_home_longterm,clinical_note\\na,A,C,1 mg,1 mg,n\\na,B,C,1 mg,1 mg,n\\n")
    with pytest.raises(ValueError): load_micronutrients(p)

def test_app_has_micronutrient_lookup_and_no_26_claim():
    text=(ROOT/"app.py").read_text()
    assert 'ui.input_select("mn_selected"' in text
    assert "addresses 26 micronutrients" not in text
    assert "Special Compounds Addressed by ESPEN" in text
