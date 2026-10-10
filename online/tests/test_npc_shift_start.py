"""M4: widok NPC zawiera start zmiany (shiftStartedAt) — aplikacja liczy z niego pasek postępu pracy w usłudze."""
from tests.test_npc_shift import env, player, post, hire, H  # noqa: F401


def test_shift_started_at_exposed(env):
    app, clock, db = env
    c = player(app, db, 'zmianowy')
    a = hire(c, db)
    r = post(c, 'npcs/batch', dict(action='dispatch', npcs=[a], service_id='minimarket', hours=2))
    assert r.status_code == 200, r.text
    n = next(x for x in r.json()['npcs'] if x['id'] == a)
    assert n['assigned_service_id'] == 'minimarket'
    assert n['shiftStartedAt'] and n['shiftEndsAt'] == n['shiftStartedAt'] + 2 * H
