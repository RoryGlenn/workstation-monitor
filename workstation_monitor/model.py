"""Measurement semantics shared by collectors, UI, and deterministic tests."""

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Value:
    number: float | None = None
    status: str = "Measuring…"

    @classmethod
    def ok(cls, number):
        return cls(float(number), "Available")


def size(number):
    if number is None:
        return "Unavailable"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if abs(number) < 1024 or unit == "PiB":
            return f"{number:,.1f} {unit}"
        number /= 1024


def formatted(value, unit=""):
    if value.number is None:
        return value.status
    if unit in ("bytes", "bytes/s"):
        return size(value.number) + ("/s" if unit.endswith("/s") else "")
    return f"{value.number:,.1f}{' ' if unit and unit != '%' else ''}{unit}"


@dataclass(frozen=True)
class Metric:
    key: str
    title: str
    value: Value
    unit: str
    category: str
    detail: str = ""


@dataclass(frozen=True)
class Process:
    pid: int
    started: float
    name: str
    owner: str
    uid: int
    state: str
    parent: int
    threads: int
    cpu: Value
    rss: Value
    read: Value
    write: Value
    app_id: str = ""
    app_name: str = ""

    @property
    def identity(self):
        return self.pid, self.started


@dataclass(frozen=True)
class Frame:
    timestamp: float
    wall_time: float
    metrics: dict = field(default_factory=dict)
    processes: dict = field(default_factory=dict)
    interfaces: tuple = ()
    filesystems: tuple = ()
    duration_ms: float = 0
    status: str = "Available"
    process_vram: dict = field(default_factory=dict)


class Rates:
    def __init__(self):
        self.previous = {}

    def rate(self, key, counter, now, valid=True, scale=1):
        old = self.previous.get(key)
        if counter is None or not valid:
            self.previous.pop(key, None)
            return Value(None, "Unavailable")
        self.previous[key] = (float(counter), now)
        if old is None or now <= old[1] or counter < old[0]:
            return Value()
        return Value.ok((counter - old[0]) / (now - old[1]) * scale)

    def retain(self, keys):
        self.previous = {k: v for k, v in self.previous.items() if k in keys}

    def clear(self):
        self.previous.clear()


class History:
    def __init__(self, seconds=300):
        self.seconds = seconds
        self.series = {}
        self.selected = None

    def select(self, identity):
        if self.selected != identity:
            self.series.pop("selected.cpu", None)
            self.selected = identity

    def add(self, frame, expected_interval=None):
        cutoff = frame.timestamp - self.seconds
        for key, metric in frame.metrics.items():
            points = self.series.setdefault(key, deque(maxlen=302))
            if points and expected_interval and frame.timestamp - points[-1][0] > 1.5 * expected_interval:
                points.append(((points[-1][0] + frame.timestamp) / 2, None))
            points.append((frame.timestamp, metric.value.number))
        if self.selected and frame.processes:
            proc = frame.processes.get(self.selected)
            points = self.series.setdefault("selected.cpu", deque(maxlen=302))
            if points and expected_interval and frame.timestamp - points[-1][0] > 1.5 * expected_interval:
                points.append(((points[-1][0] + frame.timestamp) / 2, None))
            points.append((frame.timestamp, proc.cpu.number if proc else None))
        for key in list(self.series):
            points = self.series[key]
            while points and points[0][0] < cutoff:
                points.popleft()
            if not points:
                del self.series[key]


@dataclass(frozen=True)
class AppGroup:
    identity: tuple
    name: str
    members: tuple
    cpu: Value
    rss: Value
    read: Value
    write: Value
    partial: bool


def aggregate(values):
    numbers = [v.number for v in values if v.number is not None]
    if not numbers:
        statuses = {v.status for v in values}
        return Value(None, next(iter(statuses)) if len(statuses) == 1 else "Unavailable")
    return Value(sum(numbers), "Partial" if len(numbers) < len(values) else "Available")


def groups(processes):
    buckets = {}
    for proc in processes.values():
        key = ("app", proc.uid, proc.app_id) if proc.app_id else ("process", *proc.identity)
        buckets.setdefault(key, []).append(proc)
    result = []
    for key, members in buckets.items():
        values = [aggregate([getattr(p, attr) for p in members])
                  for attr in ("cpu", "rss", "read", "write")]
        result.append(AppGroup(key, members[0].app_name or members[0].name,
                               tuple(members), *values,
                               any(v.status != "Available" for v in values)))
    return result


def stale(timestamp, now, interval):
    return now - timestamp >= 2 * interval


def cpu_delta(old, new):
    """Linux guest time is already included in user/nice; iowait is idle."""
    if old is None or len(old) != len(new):
        return Value()
    total = sum(new) - sum(old)
    if total <= 0 or any(b < a for a, b in zip(old, new)):
        return Value()
    idle = (new[3] - old[3]) + (new[4] - old[4] if len(new) > 4 else 0)
    return Value.ok(max(0, min(100, (total - idle) / total * 100)))
