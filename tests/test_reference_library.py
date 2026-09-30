from pathlib import Path
from core.reference_library import ReferenceLibrary

DATA=Path(__file__).parents[1]/'data'/'reference'
def test_load_and_sources():
    lib=ReferenceLibrary(DATA); assert len(lib.items)>=16; assert lib.source('ESPEN_ICU_2023')['year']=='2023'
def test_search_topic():
    lib=ReferenceLibrary(DATA); assert any(x.reference_id=='CALC-GIR' for x in lib.search('glucose infusion'))
def test_category_filter():
    lib=ReferenceLibrary(DATA); xs=lib.search(category='Conversion'); assert len(xs)>=7 and all(x.category=='Conversion' for x in xs)
def test_reference_does_not_define_executable_rules():
    lib=ReferenceLibrary(DATA); assert not hasattr(lib, 'evaluate')

def test_m51_expanded_categories_and_sources():
    lib=ReferenceLibrary(DATA)
    assert len(lib.items) >= 40
    categories={x.category for x in lib.items}
    for expected in {'Weight & obesity','Fluid & electrolytes','Parenteral nutrition','Indirect calorimetry','Renal / KRT','Refeeding','Micronutrients'}:
        assert expected in categories
    assert lib.source('ESPEN_KIDNEY_2024')['verification_status']=='VERIFIED_CURRENT'
    assert lib.source('ESPEN_MICRO_2024')['year']=='2024'

def test_all_clinical_reference_sources_are_known_and_verified():
    lib=ReferenceLibrary(DATA)
    for item in lib.items:
        src=lib.source(item.source_id)
        assert src['source_id']==item.source_id
        assert item.verified_on
        assert item.evidence_status
        if src['source_type']=='GUIDELINE':
            assert src['verification_status']=='VERIFIED_CURRENT'
            assert src['url'].startswith('https://')

def test_search_expanded_topics():
    lib=ReferenceLibrary(DATA)
    assert any(x.reference_id=='CALC-DEX-KCAL' for x in lib.search('dextrose'))
    assert any(x.reference_id=='REF-KRT-LOSSES' for x in lib.search('kidney replacement'))
    assert any(x.reference_id=='CONV-VALENCE' for x in lib.search('valence'))
