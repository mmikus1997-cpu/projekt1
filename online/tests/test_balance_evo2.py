# Balans (Klub/Flutter): przewaga statystyk przełamuje kontrę klasową; poziom PvP i Ewolucje II.
import itertools
from server import combat as C
CLS=['bokser','obronca','szybki']
def win(a,d,ac,dc,seed=1,**kw):return C.simultaneous(a,d,None,None,seed,a_cls=ac,d_cls=dc,levels=(10,10),**kw)['winner']
def test_szybki_30_bije_obronce_10():
    for seed in range(20):
        assert win([30]*5,[10]*5,'szybki','obronca',seed)==0
        assert win([10]*5,[30]*5,'obronca','szybki',seed)==1
def test_dwukrotna_przewaga_zawsze_wygrywa_kazda_para():
    for ac,dc in itertools.product(CLS,CLS):
        assert win([20]*5,[10]*5,ac,dc)==0,(ac,dc)
        assert win([10]*5,[20]*5,dc,ac)==1,(ac,dc)
# Combat 3.0: test_rps_decyduje_przy_rownych_statach usunięty — RPS klas usunięty (zastępstwo: tests/test_combat3.py)

def test_counter_eff_skala():
    assert C.counter_eff([10]*5,[10]*5)==1
    assert C.counter_eff([10]*5,[20]*5)==0
    assert abs(C.counter_eff([10]*5,[15]*5)-0.5)<1e-9
def test_poziom_pvp():
    assert C.pvp_level(0,0,0)==1
    assert C.pvp_level(5,0,0)==2          # 15 pkt
    assert C.pvp_level(20,0,0)==5         # 60 pkt → Ewolucja I
    assert C.pvp_level(45,0,0)==10        # 135 pkt → Ewolucja II
    assert C.pvp_level(0,15,0)==2         # przegrane też liczą się (1 pkt)
    assert C.pvp_level(999,0,0)==C.PVP_LEVEL_MAX
def test_status_ewolucji():
    st=C.evolution_status('szybki',20,0,0,None,None)
    assert st['next']['stage']==1 and st['next']['available'] and len(st['next']['options'])==2
    st=C.evolution_status('szybki',20,0,0,'blyskawica',None)
    assert st['next']['stage']==2 and not st['next']['available']
    assert {o['code'] for o in st['next']['options']}=={'cien','zabojca'}
    assert C.evolution_status('szybki',99,0,0,'blyskawica','cien')['next'] is None
    assert C.evolution_status(None,99,0,0,None,None)['next'] is None
def test_evo2_dziala_w_silniku():
    base=C.simultaneous([12]*5,[12]*5,None,None,1,a_cls='bokser',d_cls='bokser')
    champ=C.simultaneous([12]*5,[12]*5,None,None,1,a_cls='bokser',d_cls='bokser',a_evo2='czempion')
    assert champ['hpStart'][0]>base['hpStart'][0] and champ['evolutions2'][0]=='czempion'
    assert len(C.EVOLUTIONS2)==6 and all(sum(1 for v in C.EVOLUTIONS2.values() if v['cls']==k)==2 for k in CLS)
