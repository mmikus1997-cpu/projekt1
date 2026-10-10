import pytest
import os
import tempfile
from pathlib import Path
_runtime=tempfile.TemporaryDirectory(prefix='city-empire-import-')
os.environ['CITY_DB']=str(Path(_runtime.name)/'import.sqlite3')
os.environ['CITY_SETUP_FILE']=str(Path(_runtime.name)/'setup.txt')


@pytest.fixture
def legacy_shop(monkeypatch):
    """7.3 GDD v3.1: stary sklep jest zamknięty (E.LEGACY_SHOP_OPEN=False). Testy dawnej mechaniki zakupów
    (rabat Charyzmy, idempotencja, unikaty) otwierają go jawnie tylko na czas testu."""
    from server import economy as E
    monkeypatch.setattr(E, 'LEGACY_SHOP_OPEN', True)


@pytest.fixture
def flat_stats(monkeypatch):
    """8.2 GDD v3.1: od Etapu 8 nawet startowe 10 pkt daje 1/3 capu PvE. Testy INNYCH mechanik (eventy, idempotencja,
    czasy podróży, skarbce) mają twarde kwoty liczone bez bonusu statystyk — ta fikstura jawnie zeruje bonus PvE."""
    from server import economy as E
    monkeypatch.setattr(E, 'pve_pct', lambda s, i: 0)
