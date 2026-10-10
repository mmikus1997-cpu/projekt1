"""2.1a GDD v3.1: etykieta dzielnicy kontraktu = nazwa z mapy, więc inwestycje działają."""
from server import economy as E
from server import travel as T

def test_contract_labels_match_map():
    names=dict(T.DISTRICTS)
    for c in E.CONTRACTS:
        assert names[c['d']]==c['district'],c['id']

def test_invest_bonus_applies_to_campaign_and_expo():
    for cid in ('campaign','expo'):
        c=next(x for x in E.CONTRACTS if x['id']==cid)
        assert c['district'] in E.DISTRICTS
        s=E.new(0)
        base=E.invest_bonus(s,c['district'])
        s['invested']={c['district']:5000}
        assert E.invest_bonus(s,c['district'])==base+5
