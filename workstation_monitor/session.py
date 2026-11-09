"""Two bounded workers; GTK consumes the newest frame at its own pace."""

import threading
import time
from .collectors import SystemCollector, NvidiaCollector
from .model import Frame, History


class Session:
    def __init__(self, desktop_names=None, system=None, gpu=None):
        self.system = system or SystemCollector(desktop_names)
        self.gpu = gpu or NvidiaCollector()
        self.interval = 1
        self.hidden = False
        self.stop_event = threading.Event()
        self.latest = {"system": None, "gpu": None}
        self.threads = []
        self.history = History()
        self.consumed = {}

    @property
    def period(self):
        return max(self.interval, 5) if self.hidden else self.interval

    def start(self):
        for name, collector in (("system", self.system), ("gpu", self.gpu)):
            thread = threading.Thread(target=self._work, args=(name, collector),
                                      name=f"monitor-{name}", daemon=True)
            self.threads.append(thread)
            thread.start()

    def _work(self, name, collector):
        try:
            while not self.stop_event.is_set():
                started = time.monotonic()
                try:
                    frame = collector.collect()
                except Exception:
                    # Never print exception messages: provider exceptions can contain
                    # process names, paths, or other private runtime information.
                    frame = Frame(started, time.time(), status="Unavailable")
                self.latest[name] = frame
                delay = self.period if frame.status == "Available" else max(30, self.period)
                self.stop_event.wait(max(0.05, delay - (time.monotonic() - started)))
        finally:
            if hasattr(collector, "close"):
                try:
                    collector.close()
                except Exception:
                    pass

    def consume(self):
        for name, frame in self.latest.items():
            if frame is not None and self.consumed.get(name) != frame.timestamp:
                self.history.add(frame, self.period)
                self.consumed[name] = frame.timestamp

    def close(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=.15)
