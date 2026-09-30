import math, pytest
from core.calculators import *

def test_bmi(): assert math.isclose(bmi(72,168).value,25.5102,rel_tol=1e-4)
def test_weight_loss(): assert math.isclose(percent_weight_loss(80,72).value,10)
def test_energy_range():
    lo,hi=weight_based_range(70,20,25,"kcal/kg/day","kcal/day"); assert lo.value==1400 and hi.value==1750
def test_weir(): assert math.isclose(weir_energy(250,200).value,1737.288,rel_tol=1e-6)
def test_en_rate(): assert math.isclose(en_rate(1800,1.5,24).value,50)
def test_gir(): assert math.isclose(gir(300,70).value,2.976190476,rel_tol=1e-6)
def test_propofol(): assert math.isclose(propofol_energy(15,24).value,396)
def test_nb(): assert math.isclose(nitrogen_balance(100,12).value,0)
def test_npcn(): assert math.isclose(npc_n_ratio(2000,100).value,100)
def test_adequacy(): assert math.isclose(adequacy(1420,1800,"kcal").value,78.8888889,rel_tol=1e-6)
def test_invalid():
    with pytest.raises(ValueError): bmi(70,0)
