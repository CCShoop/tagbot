import time
import threading


class CountdownTimer:
    def __init__(self, duration_seconds: int):
        self.duration_seconds: int = duration_seconds
        self.running: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._thread: threading.Thread = None

    def _run(self):
        start_time = time.time()
        while self.running and self.remaining > 0:
            time.sleep(0.1)
            with self._lock:
                elapsed = time.time() - start_time
                self.remaining = max(self.duration_seconds - elapsed, 0)

    def reset(self, start: bool = False):
        with self._lock:
            if not self.finished:
                self.stop()
            self.start()

    def start(self):
        with self._lock:
            self.remaining = self.duration_seconds
            self.running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def resume(self):
        with self._lock:
            self.running = True

    def stop(self):
        with self._lock:
            self.running = False

    @property
    def remaining_time(self):
        with self._lock:
            return self.remaining

    @property
    def finished(self):
        with self._lock:
            return self.remaining <= 0
