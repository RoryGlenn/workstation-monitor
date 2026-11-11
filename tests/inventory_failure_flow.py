"""A failed sample is not evidence that running processes have exited."""

import os
os.environ.setdefault("GSK_RENDERER", "cairo")
os.environ.setdefault("GDK_DEBUG", "gl-disable,vulkan-disable")
import tempfile
import time
from dataclasses import replace
from unittest.mock import patch

from workstation_monitor.native import Gio
from workstation_monitor.model import Frame, Metric, Value
from workstation_monitor.session import Session
from workstation_monitor.ui import MonitorApplication
from native_flow import pump
from test_core import proc
from capture_window import capture


class System:
    def __init__(self):
        self.fail = False

    def collect(self):
        if self.fail:
            raise RuntimeError("synthetic provider failure")
        process = proc()
        cpu = Metric("cpu.total", "CPU", Value.ok(25), "%", "CPU")
        return Frame(time.monotonic(), time.time(), {cpu.key: cpu}, {process.identity: process})


class GPU:
    def collect(self):
        metric = Metric("gpu.fixture.util", "GPU", Value.ok(20), "%", "GPU")
        return Frame(time.monotonic(), time.time(), {metric.key: metric})


with tempfile.TemporaryDirectory() as config:
    os.environ["WORKSTATION_MONITOR_CONFIG_DIR"] = config
    source = System()
    with patch("workstation_monitor.ui.Session", lambda _: Session(system=source, gpu=GPU())):
        app = MonitorApplication()
        app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        app.register(); app.activate(); pump(.6)
        w = app.window
        try:
            process = next(iter(w.display_frame.processes.values()))
            group = w.top_groups[0]
            observed_at = w.display_frame.wall_time
            w.top_buttons[0].grab_focus()
            w.show_details(process); pump(.1)
            source.fail = True; pump(1.2)
            assert w.display_frame.status == "Unavailable"
            assert "Exited" not in w.top_buttons[0].name.get_label()
            assert w.top_buttons[0].cpu.get_label() == "Unavailable"
            assert "0 processes" not in w.footer.get_label()
            assert "inventory unavailable" in w.footer.get_label().lower()
            assert w.cards["gpu"].metric.value.number == 20
            assert "Exited" not in w.detail_text.get_label()
            assert w.detail_seen_at == observed_at
            for data in (process, group):
                w.show_details(data); pump(.1)
                text = w.detail_text.get_label().lower()
                assert "exited" not in text
                assert "last observed values" in text
                assert w.detail_seen_at == observed_at
                w.dialog.close(); pump(.1)
            w.navigate("processes"); pump(.1)
            assert "unavailable" in w.processes.count.get_label().lower()
            w.navigate("apps"); pump(.1)
            assert "unavailable" in w.apps.count.get_label().lower()
            w.navigate("overview"); pump(.1)
            assert w.top_buttons[0].get_visible()
            assert "Exited" not in w.top_buttons[0].name.get_label()
            requested_width, requested_height = 600, 700
            for _ in range(4 if os.environ.get("MONITOR_VIRTUAL_DISPLAY") else 1):
                w.set_default_size(requested_width, requested_height); pump(.6)
                if (w.get_width(), w.get_height()) == (600, 700):
                    break
                requested_width += 600-w.get_width()
                requested_height += 700-w.get_height()
            assert (w.get_width(), w.get_height()) == (600, 700)
            horizontal = w.overview_scroll.get_hadjustment()
            assert horizontal.get_upper() <= horizontal.get_page_size()+1
            output = f"/tmp/workstation-monitor-inventory-unavailable-{w.get_scale_factor()}x.png"
            capture(w, output); print(output, flush=True)
            # Feed the next successful snapshot without waiting for the real
            # 30-second retry delay. Worker retry behavior has separate tests.
            source.fail = False
            w.session.latest["system"] = source.collect(); pump(.3)
            assert "Live" in w.live_status.get_label()
            assert w.top_buttons[0].cpu.get_label() == "5.0%"
            w.top_buttons[0].emit("clicked"); pump(.1)
            newer = replace(process, cpu=Value.ok(9))
            successful = Frame(time.monotonic(), time.time(), processes={newer.identity: newer})
            w.session.latest["system"] = successful; pump(.3)
            assert w.detail_data.cpu.number == 9
            w.top_buttons[0].grab_focus()
            w.session.latest["system"] = Frame(time.monotonic(), time.time())
            pump(.3)
            assert "Exited" in w.top_buttons[0].name.get_label()
            w.member_box.get_first_child().emit("clicked"); pump(.1)
            assert "Exited" in w.detail_text.get_label()
            assert "CPU 9.0%" in w.detail_text.get_label()
            assert w.detail_seen_at == successful.wall_time
            w.dialog.close(); pump(.1)
            w.top_buttons[0].emit("clicked"); pump(.1)
            assert "has exited" in w.detail_text.get_label()
            assert w.detail_seen_at == successful.wall_time
            w.dialog.close(); pump(.1)
            print("Worker failure, unknown counts, observed timestamps, recovery and confirmed exit: PASS", flush=True)
        finally:
            w.close(); pump(.3)
            assert all(not worker.is_alive() for worker in w.session.threads)
            app.quit()
