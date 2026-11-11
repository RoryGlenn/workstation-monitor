"""Choose dashboard sources from existing snapshots, without new collection."""

from .model import Metric, Value


def missing(key, title, unit, category, status="Unavailable"):
    return Metric(key, title, Value(None, status), unit, category)


def filesystem_summary(frame):
    entries = frame.filesystems if frame else ()
    entry = next((item for item in entries if item[1] == "/"), entries[0] if entries else None)
    if entry is None:
        return missing("filesystem.missing", "Storage", "%", "Storage"), None, "No local filesystem"
    _, mount, usage, status = entry
    metric = Metric(f"filesystem.{mount}", "Storage", Value.ok(usage.percent) if usage else Value(None, status),
                    "%", "Storage", mount)
    return metric, usage.free if usage else None, mount


def gpu_summary(frame):
    metrics = frame.metrics if frame else {}
    # Select one device identity first, including when its utilization is unsupported.
    first = next((m for m in metrics.values() if m.category == "GPU"), None)
    prefix = first.key.rsplit(".", 1)[0] if first else "gpu.missing"
    state = "Measuring…" if frame is None else frame.status if frame.status != "Available" else "Unavailable"
    return {name: metrics.get(f"{prefix}.{name}", missing(f"{prefix}.{name}", title, unit, "GPU", state))
            for name, title, unit in (("util", "GPU", "%"), ("used", "VRAM used", "bytes"),
                                      ("total", "VRAM total", "bytes"), ("temperature", "GPU temperature", "°C"))}


def cpu_temperature(frame):
    metrics = frame.metrics.values() if frame else ()
    candidates = []
    for metric in metrics:
        if metric.category != "Sensors" or metric.unit != "°C":
            continue
        text = (metric.key + " " + metric.title).casefold()
        if "coretemp" in text:
            candidates.append((0 if "package" in text else 2, metric))
        elif "k10temp" in text and ("tdie" in text or "tctl" in text):
            candidates.append((0 if "tdie" in text else 1, metric))
        elif "cpu" in metric.title.casefold() and "temperature" in metric.title.casefold():
            candidates.append((1, metric))
    return min(candidates, key=lambda item: item[0])[1] if candidates else missing(
        "cpu.temperature.missing", "CPU temperature", "°C", "Sensors")
