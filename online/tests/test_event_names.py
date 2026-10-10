"""GDD v3.1 1.10: event 'study' nazywa się „Dzień Nauki” (okno 6 h), ikona osobno."""
from server import economy as E


def test_study_renamed():
    ev = next(e for e in E.TIMED_EVENTS if e['id'] == 'study')
    assert ev['name'] == 'Dzień Nauki' and ev['icon'] == '📚'
    assert not any('Tydzień' in e['name'] for e in E.TIMED_EVENTS)
    assert E.EVENT_WINDOW == 6 * E.HOUR
