"""P1b: idempotency guard at 1h boundary — simulation must not fire twice
for the same boundary ts (real-money double-execution protection)."""
import sys, os
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "live"))
os.chdir(ROOT)

def make_loop():
    from live.loop import LiveLoop
    from persistence.database import Database
    db = Database(":memory:")
    db.connect()
    db.create_tables()
    loop = LiveLoop.__new__(LiveLoop)
    loop.db = db
    loop._running = False
    loop._sim_running = False
    loop._got_15m_boundary = False
    loop._got_1h_boundary = False
    loop._boundary_ts = None
    loop._boundary_deadline = None
    loop._last_boundary_fired_ts = None
    loop._update_htf_metrics = MagicMock()
    loop._run_v18_simulation = MagicMock()
    return loop, db

def test_fire_boundary_idempotent():
    loop, db = make_loop()
    loop._boundary_ts = 1700000000
    loop._got_15m_boundary = True
    loop._got_1h_boundary = True
    loop._boundary_deadline = 0.0  # expired-ish but both arrived
    # First fire runs sim
    loop._fire_boundary_simulation()
    assert loop._run_v18_simulation.call_count == 1, "sim should run once"
    assert loop._last_boundary_fired_ts == 1700000000
    # State reset
    assert loop._boundary_ts is None
    # Second fire for same ts (re-set state to simulate re-entry) must NOT run sim
    loop._boundary_ts = 1700000000
    loop._got_15m_boundary = True
    loop._got_1h_boundary = True
    loop._fire_boundary_simulation()
    assert loop._run_v18_simulation.call_count == 1, "sim must not run twice for same ts"
    db.close()
    print("PASS: _fire_boundary_simulation idempotent for same ts")

def test_try_fire_boundary_idempotent():
    loop, db = make_loop()
    loop._boundary_ts = 1700000000
    loop._last_boundary_fired_ts = 1700000000  # already fired
    loop._got_15m_boundary = True
    loop._got_1h_boundary = True
    loop._boundary_deadline = None
    loop._try_fire_boundary()
    assert loop._run_v18_simulation.call_count == 0, "try_fire must skip already-fired ts"
    db.close()
    print("PASS: _try_fire_boundary skips already-fired ts")

if __name__ == "__main__":
    test_fire_boundary_idempotent()
    test_try_fire_boundary_idempotent()
    print("\nAll P1b tests passed!")