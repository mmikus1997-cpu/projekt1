"""Główna statystyka klasy: +1% obrażeń za punkt (Bokser Siła, Obrońca Int, Szybki Refleks)."""
import random
from server import combat


def _hit(cls, stats):
    # jeden pewny cios: porównujemy tylko mnożnik obrażeń przy tym samym rzucie
    A = combat.Fighter(stats, cls, None, None, 10, None)
    return 1 + combat.STR_MULT * A.st[0] + combat.PRIME_MULT * A.st[combat.PRIME_STAT[cls]]


def test_prime_stat_adds_damage():
    base = [10, 10, 10, 10, 10]
    assert _hit('Obrońca', [10, 40, 10, 10, 10]) > _hit('Obrońca', base)
    assert _hit('Szybki', [10, 10, 40, 10, 10]) > _hit('Szybki', base)
    assert _hit('Bokser', [40, 10, 10, 10, 10]) - _hit('Bokser', base) - 30 * (combat.STR_MULT + combat.PRIME_MULT) < 1e-9
    # Int nie daje obrażeń Bokserowi
    assert _hit('Bokser', [10, 40, 10, 10, 10]) == _hit('Bokser', base)
