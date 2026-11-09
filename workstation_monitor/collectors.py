"""Read-only Linux and NVIDIA adapters. No shell polling or workload control."""

from pathlib import Path
import pwd
import re
import time

import psutil

from .model import Frame, Metric, Process, Rates, Value, cpu_delta


def attempt(call):
    try:
        return call(), "Available"
    except (psutil.AccessDenied, PermissionError):
        return None, "Permission denied"
    except (psutil.NoSuchProcess, psutil.ZombieProcess, FileNotFoundError, ProcessLookupError):
        return None, "Exited"
    except (OSError, NotImplementedError):
        return None, "Unavailable"


def app_scope(text, desktop_names):
    """Only use an actual desktop ID match, never executable-name similarity."""
    for component in reversed(text.strip().split("/")):
        if not component.startswith("app-") or not component.endswith((".scope", ".service")):
            continue
        component = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m[1], 16)), component)
        for desktop_id in sorted(desktop_names, key=len, reverse=True):
            stem = desktop_id.removesuffix(".desktop")
            for candidate in (f"app-{stem}", f"app-gnome-{stem}", f"app-flatpak-{stem}"):
                if component in (candidate + ".scope", candidate + ".service") or component.startswith(candidate + "-"):
                    # Scope instance is part of the grouping identity. Separate launches
                    # still share a display name but do not cross session boundaries.
                    return component, desktop_names[desktop_id]
    return "", ""


def physical_disks(sysroot=Path("/sys/class/block")):
    result = {}
    for path in sysroot.iterdir():
        if (path / "partition").exists() or path.name.startswith(("loop", "ram", "sr", "dm-", "zram")):
            continue
        if (path / "device").exists():
            try:
                identity = (str(path.resolve()), (path / "dev").read_text().strip())
                result[path.name] = identity
            except OSError:
                continue
    return result


class SystemCollector:
    def __init__(self, desktop_names=None):
        self.rates = Rates()
        self.desktop_names = desktop_names or {}
        self.metadata = {}
        self.users = {}
        self.cpu_previous = None
        self.topology = None
        self.previous_boot_gap = None
        self.last = None
        self.cached_filesystems = ()
        self.fs_at = 0
        self.disk_info = {}
        self.disk_at = 0
        self.interface_seen = {}

    def _processes(self, now, cpu_count, live_keys):
        rows = {}
        alive = {}
        for p in psutil.process_iter():
            try:
                with p.oneshot():
                    started = p.create_time()
                    identity = (p.pid, started)
                    cached = self.metadata.get(identity)
                    if cached is None or now - cached[0] > 10:
                        uid_info, _ = attempt(p.uids)
                        uid = uid_info.real if uid_info else -1
                        if uid not in self.users:
                            try:
                                self.users[uid] = pwd.getpwuid(uid).pw_name
                            except KeyError:
                                self.users[uid] = str(uid) if uid >= 0 else "Unknown"
                        scope, _ = attempt(lambda: Path(f"/proc/{p.pid}/cgroup").read_text())
                        app_id, app_name = app_scope(scope or "", self.desktop_names)
                        name, _ = attempt(p.name)
                        cached = (now, uid, self.users[uid], name or f"PID {p.pid}", app_id, app_name)
                    alive[identity] = cached
                    _, uid, owner, name, app_id, app_name = cached
                    times, cpu_status = attempt(p.cpu_times)
                    cpu_key = ("proc", identity, "cpu", cpu_count)
                    live_keys.add(cpu_key)
                    cpu = self.rates.rate(cpu_key, times.user + times.system if times else None,
                                          now, scale=100 / cpu_count)
                    if times is None:
                        cpu = Value(None, cpu_status)
                    mem, mem_status = attempt(p.memory_info)
                    rss = Value.ok(mem.rss) if mem else Value(None, mem_status)
                    io, io_status = attempt(p.io_counters)
                    values = []
                    for attr in ("read_bytes", "write_bytes"):
                        key = ("proc", identity, attr)
                        live_keys.add(key)
                        measured = self.rates.rate(key, getattr(io, attr) if io else None, now)
                        values.append(measured if io else Value(None, io_status))
                    state, _ = attempt(p.status)
                    parent, _ = attempt(p.ppid)
                    threads, _ = attempt(p.num_threads)
                    rows[identity] = Process(p.pid, started, name, owner, uid, state or "Unknown",
                                             parent or 0, threads or 0, cpu, rss, *values, app_id, app_name)
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
        self.metadata = alive
        return rows

    def collect(self):
        start = time.monotonic()
        now = start
        wall = time.time()
        count = psutil.cpu_count() or 1
        boot_gap = time.clock_gettime(time.CLOCK_BOOTTIME) - now
        if self.topology != count or (self.previous_boot_gap is not None and
                                    abs(boot_gap - self.previous_boot_gap) > .5):
            self.rates.clear()
            self.cpu_previous = None
        self.previous_boot_gap = boot_gap
        self.topology = count
        metrics = {}
        live_keys = set()

        def add(key, title, value, unit, category, detail=""):
            metrics[key] = Metric(key, title, value, unit, category, detail)

        def rate(key, counter):
            live_keys.add(key)
            return self.rates.rate(key, counter, now)

        cores = psutil.cpu_times(percpu=True)
        # Drop Linux guest/guest_nice, which are included in user/nice already.
        raw = [tuple(c)[:8] for c in cores]
        totals = tuple(sum(c[i] for c in raw) for i in range(len(raw[0])))
        old_total = self.cpu_previous[0] if self.cpu_previous else None
        add("cpu.total", "CPU", cpu_delta(old_total, totals), "%", "CPU",
            f"{len(raw)} logical CPUs · whole-machine capacity")
        for i, c in enumerate(raw):
            old = self.cpu_previous[1][i] if self.cpu_previous and i < len(self.cpu_previous[1]) else None
            add(f"cpu.core.{i}", f"Logical CPU {i + 1}", cpu_delta(old, c), "%", "CPU")
        self.cpu_previous = (totals, raw)
        memory = psutil.virtual_memory()
        for name, value in (("used", memory.total - memory.available), ("available", memory.available),
                            ("cache", getattr(memory, "cached", 0)), ("total", memory.total)):
            add(f"memory.{name}", f"RAM {name}", Value.ok(value), "bytes", "Memory")
        add("memory.percent", "Memory", Value.ok((memory.total - memory.available) / memory.total * 100),
            "%", "Memory", "Used = total − available; cache is separately reclaimable")
        swap = psutil.swap_memory()
        add("swap.used", "Swap used", Value.ok(swap.used), "bytes", "Memory", f"Total {swap.total} bytes")
        if now - self.disk_at > 10:
            self.disk_info = physical_disks()
            self.disk_at = now
        counters = psutil.disk_io_counters(perdisk=True, nowrap=False) or {}
        for name, identity in self.disk_info.items():
            c = counters.get(name)
            for attr, title, unit in (("read_bytes", "read", "bytes/s"), ("write_bytes", "write", "bytes/s"),
                                      ("read_count", "reads", "ops/s"), ("write_count", "writes", "ops/s")):
                key = f"disk.{name}.{title}"
                value = rate(("disk", identity, attr), getattr(c, attr)) if c else Value(None, "Disconnected")
                add(key, f"{name} {title}", value, unit, "Storage", "Physical device · excludes partition totals")
        if now - self.fs_at > 15:
            filesystems = []
            for part in psutil.disk_partitions(all=False):
                # Reading capacity on a network/FUSE mount can block; local block filesystems only.
                if not part.device.startswith("/dev/") or part.fstype in ("squashfs", "iso9660"):
                    continue
                usage, status = attempt(lambda part=part: psutil.disk_usage(part.mountpoint))
                filesystems.append((part.device, part.mountpoint, usage, status))
            self.cached_filesystems = tuple(filesystems)
            self.fs_at = now
        # Link metadata uses ioctl sockets on Linux. A restricted socket policy
        # must not discard readable traffic counters or the whole system frame.
        stats, _ = attempt(psutil.net_if_stats)
        stats = stats or {}
        interfaces = []
        for name, c in (psutil.net_io_counters(pernic=True, nowrap=False) or {}).items():
            path = Path("/sys/class/net") / name
            try:
                identity = (int((path / "ifindex").read_text()), str(path.resolve()))
            except (OSError, ValueError):
                identity = (name,)
            kind = "Loopback" if name == "lo" else "Physical" if (path / "device").exists() else "Virtual"
            stat = stats.get(name)
            state = ("Connected" if stat.isup else "Disconnected") if stat else "Link state unknown"
            speed = f"{stat.speed:,} Mbit/s link" if stat and stat.speed > 0 else "Link speed unknown"
            detail = f"{kind} · {state} · {speed}"
            interfaces.append((name, kind, bool(stat and stat.isup)))
            self.interface_seen[name] = (now, kind)
            for attr, label in (("bytes_recv", "receive"), ("bytes_sent", "send")):
                add(f"net.{name}.{label}", f"{name} {label}", rate(("net", identity, attr), getattr(c, attr)),
                    "bytes/s", "Network", detail)
                add(f"net.{name}.{label}.total", f"{name} {label} total", Value.ok(getattr(c, attr)),
                    "bytes", "Network", "Cumulative interface counters; not per-app bandwidth")
        current_names = {n for n, _, _ in interfaces}
        for name, (last_seen, kind) in list(self.interface_seen.items()):
            if name in current_names:
                continue
            if now - last_seen > 30:
                del self.interface_seen[name]
                continue
            interfaces.append((name, kind, False))
            for direction in ("receive", "send"):
                add(f"net.{name}.{direction}", f"{name} {direction}", Value(None, "Disconnected"),
                    "bytes/s", "Network", f"{kind} · Disconnected · awaiting adapter")
        # Prevent a burst of ephemeral interfaces from retaining unbounded names.
        if len(self.interface_seen) > 128:
            self.interface_seen = dict(sorted(self.interface_seen.items(), key=lambda item: item[1][0], reverse=True)[:128])
        temperatures, _ = attempt(psutil.sensors_temperatures)
        for source, readings in (temperatures or {}).items():
            for i, reading in enumerate(readings):
                key = f"sensor.{source}.{i}"
                add(key, f"{source} · {reading.label or 'Temperature'}", Value.ok(reading.current), "°C", "Sensors")
        if not temperatures:
            add("sensor.unavailable", "Temperature sensors", Value(None, "Unavailable"), "°C", "Sensors")
        processes = self._processes(now, count, live_keys)
        self.rates.retain(live_keys)
        frame = Frame(now, wall, metrics, processes, tuple(interfaces), self.cached_filesystems,
                      (time.monotonic() - start) * 1000)
        self.last = frame
        return frame


class NvidiaCollector:
    def __init__(self):
        self.nv = None

    def _value(self, call):
        try:
            return Value.ok(call())
        except self.nv.NVMLError_NotSupported:
            return Value(None, "Unsupported")
        except self.nv.NVMLError_NoPermission:
            return Value(None, "Permission denied")
        except self.nv.NVMLError:
            return Value(None, "Unavailable")

    def collect(self):
        start = time.monotonic()
        if self.nv is None:
            import pynvml
            pynvml.nvmlInit()
            self.nv = pynvml
        nv = self.nv
        metrics, process_vram = {}, {}
        for i in range(nv.nvmlDeviceGetCount()):
            h = nv.nvmlDeviceGetHandleByIndex(i)
            uuid = nv.nvmlDeviceGetUUID(h)
            name = nv.nvmlDeviceGetName(h)
            for suffix, title, unit, call in (
                ("util", "GPU utilization", "%", lambda: nv.nvmlDeviceGetUtilizationRates(h).gpu),
                ("used", "VRAM used", "bytes", lambda: nv.nvmlDeviceGetMemoryInfo(h).used),
                ("total", "VRAM total", "bytes", lambda: nv.nvmlDeviceGetMemoryInfo(h).total),
                ("temperature", "GPU temperature", "°C", lambda: nv.nvmlDeviceGetTemperature(h, 0)),
                ("power", "GPU power", "W", lambda: nv.nvmlDeviceGetPowerUsage(h) / 1000),
            ):
                key = f"gpu.{uuid}.{suffix}"
                metrics[key] = Metric(key, title, self._value(call), unit, "GPU", name)
            # Graphics and compute lists overlap; deduplicate each device/PID.
            query_wall = time.time()
            device_processes = {}
            for call in (nv.nvmlDeviceGetComputeRunningProcesses, nv.nvmlDeviceGetGraphicsRunningProcesses):
                try:
                    for proc in call(h):
                        value = proc.usedGpuMemory
                        if isinstance(value, int) and 0 <= value < (1 << 63):
                            device_processes[proc.pid] = max(device_processes.get(proc.pid, 0), value)
                except nv.NVMLError:
                    pass
            for pid, amount in device_processes.items():
                try:
                    identity = (pid, psutil.Process(pid).create_time())
                    if identity[1] <= query_wall:
                        process_vram[identity] = process_vram.get(identity, 0) + amount
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        if not metrics:
            return Frame(start, time.time(), status="Unsupported")
        return Frame(start, time.time(), metrics, duration_ms=(time.monotonic() - start) * 1000,
                     process_vram=process_vram)

    def close(self):
        if self.nv:
            self.nv.nvmlShutdown()
