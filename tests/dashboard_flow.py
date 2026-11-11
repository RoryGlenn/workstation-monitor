"""Verify the selected dashboard through real GTK controls and synthetic data."""

import os
os.environ.setdefault("GSK_RENDERER", "cairo")
os.environ.setdefault("GDK_DEBUG", "gl-disable,vulkan-disable")
from dataclasses import replace
import math
import tempfile
import time
from types import SimpleNamespace

from workstation_monitor.native import Adw, Gio
from workstation_monitor.model import Frame, Metric, Value
from workstation_monitor.ui import MonitorApplication
from capture_window import capture
from native_flow import pump
from test_core import proc


def resize(window, width, height):
    requested_width, requested_height = width, height
    for _ in range(4 if os.environ.get("MONITOR_VIRTUAL_DISPLAY") else 1):
        window.set_default_size(requested_width, requested_height); pump(.6)
        if (window.get_width(), window.get_height()) == (width, height):
            break
        # Account for CSD and the next allocation after adaptive reparenting.
        requested_width += width-window.get_width()
        requested_height += height-window.get_height()
    assert (window.get_width(), window.get_height()) == (width, height), (
        (window.get_width(), window.get_height()), window.get_default_size(), window.get_size_request())


with tempfile.TemporaryDirectory() as config:
    os.environ["WORKSTATION_MONITOR_CONFIG_DIR"] = config
    app = MonitorApplication()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(); app.activate(); pump(2.5)
    w = app.window
    assert Adw.StyleManager.get_default().get_dark()
    assert w.nav_buttons["overview"].get_active()
    w.nav_buttons["overview"].emit("clicked")
    assert w.nav_buttons["overview"].get_active()
    assert w.cards["cpu"].metric.value.number is not None
    w.pause_button.set_active(True); pump(.1)
    stamp = w.display_frame.timestamp
    wall = w.display_frame.wall_time
    assert w.live_status.get_label() == "Paused"
    assert "Paused snapshot" in w.footer.get_label()
    assert "GPU snapshot" in w.footer.get_label()
    metrics = [Metric("cpu.total", "CPU", Value.ok(24), "%", "CPU"),
               Metric("memory.percent", "Memory", Value.ok(38), "%", "Memory"),
               Metric("memory.used", "Used", Value.ok(12.2*1024**3), "bytes", "Memory"),
               Metric("memory.total", "Total", Value.ok(32*1024**3), "bytes", "Memory"),
               Metric("net.demo.receive", "Receive", Value.ok(12.4*1024**2), "bytes/s", "Network"),
               Metric("net.demo.send", "Send", Value.ok(1.2*1024**2), "bytes/s", "Network"),
               Metric("sensor.coretemp.0", "coretemp · Package id 0", Value.ok(54), "°C", "Sensors")]
    device_metrics = [Metric(f"gpu.demo.{key}", title, value, unit, "GPU") for key, title, value, unit in (
        ("util", "GPU", Value.ok(18), "%"), ("used", "VRAM used", Value.ok(2.1*1024**3), "bytes"),
        ("total", "VRAM total", Value.ok(8*1024**3), "bytes"), ("temperature", "GPU temperature", Value.ok(46), "°C"))]
    processes = [proc(30001+i, name=name, cpu=Value.ok(cpu), rss=Value.ok(memory*1024**2))
                 for i, (name, cpu, memory) in enumerate((("Web Browser", 5.4, 1638),
                     ("Code Editor", 2.8, 740), ("Terminal", .3, 96), ("Other app", .1, 50)))]
    usage = SimpleNamespace(percent=68, used=348*1024**3, free=164*1024**3, total=512*1024**3)
    fixture = Frame(stamp, wall, {m.key: m for m in metrics}, {p.identity: p for p in processes},
                    (("demo", "Physical", True),), (("/dev/demo", "/", usage, "Available"),))
    gpu = Frame(stamp, time.time(), {m.key: m for m in device_metrics})
    w.display_frame, w.display_gpu = fixture, gpu
    w.network_choice = "demo"
    w.frozen_history = {"cpu.total": [(stamp-300+i, 24+8*math.sin(i/12)) for i in range(301)],
                        "net.demo.receive": [(stamp-300+i, (12+2*math.sin(i/15))*1024**2) for i in range(301)],
                        "net.demo.send": [(stamp-300+i, (1.2+.2*math.sin(i/8))*1024**2) for i in range(301)]}
    w.presented = None; w.render(force=True); pump(.2)
    assert "164.0 GiB free" in w.cards["disk"].detail.get_label()
    assert w.cards["disk"].source.get_label() == "Filesystem /"
    assert w.cards["gpu"].metric.value.number == 18
    assert "2.1 GiB / 8.0 GiB" in w.cards["gpu"].detail.get_label()
    assert w.temperatures.values["cpu"].get_label() == "54.0 °C"
    assert w.cards["network"].send.get_label() == "1.2 MiB/s"
    assert w.cards["network"].chart.secondary
    for key, category in (("cpu", 0), ("memory", 1), ("gpu", 2), ("disk", 3), ("network", 4)):
        w.cards[key].emit("clicked"); pump(.1)
        assert w.stack.get_visible_child_name() == "performance"
        assert w.resource.get_selected() == category
        w.navigate("overview"); pump(.1)
    assert w.display_frame.timestamp == stamp
    assert w.cards["cpu"].chart.now == stamp
    assert all(t <= stamp for t, value in w.cards["cpu"].chart.points)
    w.top_buttons[0].grab_focus(); pump(.1)
    identity = w.top_buttons[0].data.identity
    changed = replace(fixture, processes={p.identity: replace(p, cpu=Value.ok(i*10)) for i, p in enumerate(processes)})
    w.display_frame = changed; w.update_overview()
    assert w.top_buttons[0].data.identity == identity
    w.top_buttons[0].emit("clicked"); pump(.1)
    assert w.detail_data.identity == identity
    w.dialog.close(); pump(.1)
    w.top_buttons[0].grab_focus()
    members = {member.identity for member in w.top_buttons[0].data.members}
    w.display_frame = replace(changed, processes={key: value for key, value in changed.processes.items()
                                                 if key not in members})
    w.update_overview()
    assert w.top_buttons[0].data.identity == identity
    assert "Exited" in w.top_buttons[0].name.get_label()
    w.view_all_apps.emit("clicked"); pump(.1)
    assert w.stack.get_visible_child_name() == "apps"
    w.navigate("overview"); pump(.1)
    w.top_sort.grab_focus()
    partial = [replace(processes[0], app_id="demo-group", app_name="Partial app"),
               replace(processes[3], app_id="demo-group", app_name="Partial app",
                       cpu=Value(None, "Permission denied"), rss=Value(None, "Permission denied"))]
    w.display_frame = replace(fixture, processes={p.identity: p for p in partial})
    w.update_overview()
    assert "partial" in w.top_buttons[0].cpu.get_label()
    assert "partial" in w.top_buttons[0].memory.get_label()
    w.display_frame = fixture; w.update_overview()
    w.display_gpu = replace(gpu, timestamp=stamp-10)
    w.update_overview()
    assert "Stale" in w.cards["gpu"].state.get_label()
    assert "Stale" in w.temperatures.states["gpu"].get_label()
    w.display_gpu = Frame(stamp, time.time(), status="Unavailable")
    w.update_overview()
    assert w.cards["gpu"].number.get_label() == "Unavailable"
    assert not w.cards["gpu"].bar.get_visible()
    assert w.cards["memory"].metric.value.number == 38
    w.display_gpu = gpu
    w.settings.values["appearance"] = "dark"; w.apply_appearance()
    w.presented = None; w.render(force=True)
    resize(w, 1280, 800)
    w.update_overview(); pump(.1)
    scale = w.get_scale_factor()
    output = f"/tmp/workstation-monitor-sleek-fixture-{scale}x-wide.png"
    capture(w, output); print(output, flush=True)
    resize(w, 600, 700)
    assert (w.get_width(), w.get_height()) == (600, 700), (w.get_width(), w.get_height())
    assert w.nav_dropdown.get_visible() and not w.sidebar.get_visible()
    adjustment = w.overview_scroll.get_hadjustment()
    assert adjustment.get_upper() <= adjustment.get_page_size()+1
    for panel in list(w.cards.values())+[w.temperatures, w.app_panel]:
        assert 0 < panel.get_width() <= 568, (type(panel).__name__, panel.get_width())
    output = f"/tmp/workstation-monitor-sleek-fixture-{scale}x-narrow.png"
    capture(w, output); print(output, flush=True)
    scroll = w.overview_scroll.get_vadjustment()
    scroll.set_value(scroll.get_upper()-scroll.get_page_size()); pump(.1)
    before = scroll.get_value()
    w.update_overview(); pump(.1)
    assert scroll.get_value() == before
    output = f"/tmp/workstation-monitor-sleek-fixture-{scale}x-narrow-bottom.png"
    capture(w, output); print(output, flush=True)
    w.pause_button.set_active(False); pump(1.2)
    assert w.display_frame.timestamp > stamp
    assert "Live" in w.live_status.get_label()
    w.close(); pump(.2)
    assert all(not thread.is_alive() for thread in w.session.threads)
    app.quit()
    print("Dashboard summaries, navigation, focus, pause, missing/stale GPU, responsive layout and scroll: PASS", flush=True)
