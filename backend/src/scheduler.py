import threading
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class DataScheduler:
    """Runs a trigger_fn when auto-update is due and data is stale."""

    def __init__(self, trigger_fn, check_seconds=300):
        self.trigger_fn = trigger_fn
        self.check_seconds = check_seconds
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.check_seconds):
            try:
                self._maybe_run()
            except Exception:
                pass  # never kill the scheduler loop

    def _maybe_run(self):
        from . import upstox_fetcher as F

        settings = F.get_settings()
        if not settings.get("auto_update"):
            return

        now = datetime.now(IST)
        if now.weekday() >= 5:  # weekend only
            return

        try:
            hh, mm = str(settings.get("update_time", "19:00")).split(":")
            cutoff = dtime(int(hh), int(mm))
        except Exception:
            cutoff = dtime(19, 0)
        if now.time() < cutoff:
            return

        status = F.all_data_status()
        if any(not s["is_fresh"] for s in status.values()):
            self.trigger_fn()