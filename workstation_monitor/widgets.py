"""Small native widgets shared by Overview and the detailed resource views."""

import time

from .native import GObject, Gtk, Pango
from .model import Value, formatted


def label(text="", css=None, xalign=0):
    widget = Gtk.Label(label=text, xalign=xalign)
    widget.set_wrap(True)
    if css:
        widget.add_css_class(css)
    return widget


def margins(widget, value):
    for side in ("top", "bottom", "start", "end"):
        getattr(widget, f"set_margin_{side}")(value)


def symbolic_icon(name):
    image = Gtk.Image()
    theme = Gtk.IconTheme.get_for_display(image.get_display())
    image.set_from_icon_name(name if theme.has_icon(name) else "system-run-symbolic")
    return image


def number_text(widget, text, unavailable=False):
    widget.set_label(text)
    (widget.add_css_class if unavailable else widget.remove_css_class)("metric-unavailable")


def state_text(widget, state):
    widget.set_label(state.split(" · ")[0])
    widget.set_tooltip_text(state)
    widget.set_visible(bool(state))


class Chart(Gtk.DrawingArea):
    def __init__(self, axes=False, compact=False):
        super().__init__()
        self.set_content_height(74)
        self.set_hexpand(True)
        self.axes, self.compact = axes, compact
        self.points = self.secondary = ()
        self.unit = "%"
        self.scale = 100
        self.now = time.monotonic()
        self.set_draw_func(self.draw)
        self.draw_ms = 0

    def update(self, points, unit, now, secondary=()):
        self.points, self.secondary = tuple(points), tuple(secondary)
        self.unit, self.now = unit, now
        self.scale = 100 if unit == "%" else max(
            [p[1] for p in self.points + self.secondary if p[1] is not None] + [1]) * 1.15
        self.set_tooltip_text(f"Last five minutes · scale 0–{formatted(Value.ok(self.scale), unit)}. Gaps are missing data.")
        self.queue_draw()

    def color(self, name, fallback):
        found, rgba = self.get_style_context().lookup_color(name)
        return (rgba.red, rgba.green, rgba.blue) if found else fallback

    def draw(self, area, cr, width, height):
        started = time.perf_counter()
        left = (42 if self.unit == "%" else 56) if self.axes else 0
        top, bottom = (16, 24) if self.axes else (0, 0)
        plot_width, plot_height = max(1, width-left-6), max(1, height-top-bottom)
        grid = self.color("monitor_border", (.25, .29, .34))
        accent = self.color("monitor_accent", (.57, .94, .84))
        secondary = self.color("monitor_secondary", (.55, .74, .91))
        cr.set_source_rgba(*grid, .65)
        cr.set_line_width(1)
        fractions = (0, .5, 1) if self.compact else (0, .2, .4, .6, .8, 1)
        for fraction in fractions:
            y = top + plot_height * (1-fraction)
            cr.move_to(left, y)
            cr.line_to(left+plot_width, y)
        if self.axes:
            for i in range(6):
                x = left + plot_width * i / 5
                cr.move_to(x, top)
                cr.line_to(x, top+plot_height)
        cr.stroke()
        if self.axes:
            muted = self.color("monitor_muted", (.67, .70, .75))
            cr.set_source_rgba(*muted, 1)
            cr.select_font_face("Sans")
            cr.set_font_size(10 if self.compact else 11)
            divisor, unit = 1, "B/s"
            if self.unit == "bytes/s":
                for candidate, name in ((1024**3, "GiB/s"), (1024**2, "MiB/s"), (1024, "KiB/s")):
                    if self.scale >= candidate:
                        divisor, unit = candidate, name
                        break
                cr.move_to(0, 10)
                cr.show_text(unit)
            for fraction in fractions:
                value = self.scale * fraction / divisor
                text = f"{value:.0f}%" if self.unit == "%" else f"{value:.1f}"
                extent = cr.text_extents(text)
                cr.move_to(left-8-extent.width, top+plot_height*(1-fraction)+4)
                cr.show_text(text)
            ticks = (0, 2, 5) if self.compact else range(6)
            for i in ticks:
                text = "Now" if i == 5 else f"-{5-i}m"
                extent = cr.text_extents(text)
                x = left+plot_width*i/5
                x -= extent.width if i == 5 else 0 if i == 0 else extent.width/2
                cr.move_to(x, height-5)
                cr.show_text(text)
        for points, color, second in ((self.points, accent, False), (self.secondary, secondary, True)):
            segments, segment, previous = [], [], None
            for stamp, number in points:
                if number is None or stamp < self.now-300 or (previous is not None and stamp-previous > 12):
                    if segment:
                        segments.append(segment)
                    segment, previous = [], None
                if number is None or stamp < self.now-300:
                    continue
                x = left+plot_width*max(0, min(1, 1-(self.now-stamp)/300))
                y = top+plot_height*(1-max(0, min(1, number/self.scale)))
                segment.append((x, y))
                previous = stamp
            if segment:
                segments.append(segment)
            for segment in segments:
                if self.axes and not second and len(segment) > 1:
                    cr.set_source_rgba(*color, .10)
                    cr.move_to(segment[0][0], top+plot_height)
                    for x, y in segment:
                        cr.line_to(x, y)
                    cr.line_to(segment[-1][0], top+plot_height)
                    cr.close_path()
                    cr.fill()
                cr.set_source_rgba(*color, 1)
                cr.set_line_width(1.5 if second else 2)
                if second:
                    cr.set_dash((4, 3))
                cr.move_to(*segment[0])
                for point in segment[1:]:
                    cr.line_to(*point)
                cr.stroke()
                if second:
                    cr.set_dash(())
        self.draw_ms = (time.perf_counter()-started)*1000


class MetricCard(Gtk.Box):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_LAST, None, ())}

    def __init__(self, title, clicked=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("card")
        self.add_css_class("metric-card")
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        margins(self.box, 14)
        self.heading = label(title, "heading")
        self.number = label("Measuring…", "title-2")
        self.detail = label("", "dim-label")
        self.chart = Chart()
        self.scale_label = label("0–100% · last 5 min", "caption")
        for widget in (self.heading, self.number, self.detail, self.chart, self.scale_label):
            self.box.append(widget)
        if clicked:
            self.add_css_class("clickable")
            action = Gtk.Button()
            action.add_css_class("flat")
            action.add_css_class("metric-action")
            action.set_child(self.box)
            action.connect("clicked", lambda _: self.emit("clicked"))
            self.append(action)
            self.connect("clicked", lambda _: clicked())
        else:
            self.append(self.box)
        self.metric = None

    def update(self, metric, history, now, status=""):
        self.metric = metric
        self.heading.set_label(metric.title)
        self.number.set_label(formatted(metric.value, metric.unit))
        self.detail.set_label(status or metric.detail)
        self.chart.update(history, metric.unit, now)
        self.scale_label.set_label(f"0–{formatted(Value.ok(self.chart.scale), metric.unit)} · last 5 min")


class Panel(Gtk.Box):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_LAST, None, ())}

    def __init__(self, title, clicked):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.add_css_class("monitor-panel")
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7, hexpand=True)
        margins(self.content, 14)
        self.heading = label(title, "panel-heading")
        self.content.append(self.heading)
        self.action = Gtk.Button(hexpand=True, vexpand=True)
        self.action.add_css_class("flat")
        self.action.add_css_class("monitor-panel-action")
        self.action.set_child(self.content)
        self.action.set_tooltip_text(f"Open {title} measurements")
        self.action.connect("clicked", lambda _: self.emit("clicked"))
        self.connect("clicked", lambda _: clicked())
        self.append(self.action)
        self.state = label("", "metric-state")
        self.state.set_visible(False)
        self.metric = None


class SummaryPanel(Panel):
    def __init__(self, title, clicked):
        super().__init__(title, clicked)
        row = Gtk.Box(spacing=10)
        self.number = label("Measuring…", "metric-number")
        self.number.add_css_class("numeric")
        self.detail = label("", "monitor-muted", 1)
        self.detail.set_hexpand(True)
        row.append(self.number)
        row.append(self.detail)
        self.content.append(row)
        self.source = label("", "monitor-caption")
        self.content.append(self.source)
        self.bar = Gtk.ProgressBar()
        self.bar.add_css_class("capacity-bar")
        self.content.append(self.bar)
        self.content.append(self.state)

    def update(self, metric, detail="", source="", state="", suffix=""):
        self.metric = metric
        text = formatted(metric.value, metric.unit)
        number_text(self.number, text+suffix if metric.value.number is not None else text,
                    metric.value.number is None)
        self.detail.set_label(detail)
        self.source.set_label(source)
        self.bar.set_visible(metric.value.number is not None)
        if metric.value.number is not None:
            self.bar.set_fraction(max(0, min(1, metric.value.number/100)))
        self.action.update_property([Gtk.AccessibleProperty.LABEL],
                                    [f"{self.heading.get_label()}: {text}. {detail}. {source}. {state}"])
        state_text(self.state, state)


class CpuPanel(Panel):
    def __init__(self, clicked):
        super().__init__("CPU", clicked)
        self.content.remove(self.heading)
        row = Gtk.Box(spacing=18)
        values = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        values.set_size_request(120, -1)
        values.append(self.heading)
        self.number = label("Measuring…", "cpu-number")
        self.number.add_css_class("numeric")
        values.append(self.number)
        values.append(label("Whole-machine %", "monitor-caption"))
        row.append(values)
        self.chart = Chart(axes=True)
        self.chart.set_content_height(145)
        row.append(self.chart)
        self.content.append(row)
        self.content.append(self.state)

    def update(self, metric, history, now, status=""):
        self.metric = metric
        text = formatted(metric.value, metric.unit)
        number_text(self.number, text, metric.value.number is None)
        self.chart.update(history, metric.unit, now)
        self.action.update_property([Gtk.AccessibleProperty.LABEL], [f"CPU {text}, whole-machine capacity. {status}"])
        state_text(self.state, status)


class NetworkPanel(Panel):
    def __init__(self, clicked):
        super().__init__("Network", clicked)
        row = Gtk.Box(spacing=12)
        self.receive = label("Measuring…", "network-rate")
        self.send = label("Measuring…", "network-rate")
        for title, widget, css in (("↓ Receive", self.receive, "receive"), ("↑ Send", self.send, "send")):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True)
            box.append(label(title, css))
            widget.add_css_class(css)
            widget.add_css_class("numeric")
            box.append(widget)
            row.append(box)
        self.content.append(row)
        self.chart = Chart(axes=True, compact=True)
        self.chart.set_content_height(100)
        self.content.append(self.chart)
        self.source = label("", "monitor-caption")
        self.content.append(self.source)
        self.content.append(self.state)

    def update(self, receive, send, receive_history, send_history, now, source, state=""):
        self.metric = receive
        number_text(self.receive, formatted(receive.value, receive.unit), receive.value.number is None)
        number_text(self.send, formatted(send.value, send.unit), send.value.number is None)
        self.chart.update(receive_history, "bytes/s", now, send_history)
        self.source.set_label(source+" · last 5 min")
        self.action.update_property([Gtk.AccessibleProperty.LABEL],
            [f"Network {source}. Receive {self.receive.get_label()}. Send {self.send.get_label()}. {state}"])
        state_text(self.state, state)


class TemperaturePanel(Gtk.Box):
    def __init__(self, cpu_clicked, gpu_clicked):
        super().__init__(hexpand=True)
        self.add_css_class("monitor-panel")
        self.values, self.states = {}, {}
        for i, (key, title, callback) in enumerate((("cpu", "CPU temperature", cpu_clicked),
                                                  ("gpu", "GPU temperature", gpu_clicked))):
            if i:
                self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, hexpand=True)
            margins(content, 12)
            content.append(label(title, "monitor-caption"))
            value = label("Measuring…", "temperature-number")
            value.add_css_class("numeric")
            content.append(value)
            state = label("", "metric-state")
            state.set_visible(False)
            content.append(state)
            action = Gtk.Button(hexpand=True)
            action.add_css_class("flat")
            action.add_css_class("temperature-action")
            action.set_tooltip_text(f"Open {'Sensors' if key == 'cpu' else 'GPU'} measurements")
            action.set_child(content)
            action.connect("clicked", lambda _, callback=callback: callback())
            self.append(action)
            self.values[key], self.states[key] = value, state

    def update(self, cpu, gpu, cpu_state="", gpu_state=""):
        for key, metric, state in (("cpu", cpu, cpu_state), ("gpu", gpu, gpu_state)):
            number_text(self.values[key], formatted(metric.value, metric.unit), metric.value.number is None)
            state_text(self.states[key], state)


def app_columns(name, cpu, memory, icon=False):
    row = Gtk.Box(spacing=12, hexpand=True)
    if icon:
        row.append(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
    name.set_hexpand(True)
    name.set_wrap(False)
    name.set_ellipsize(Pango.EllipsizeMode.END)
    name.set_width_chars(8)
    row.append(name)
    for widget, width in ((cpu, 82), (memory, 116)):
        widget.set_xalign(1)
        widget.set_size_request(width, -1)
        widget.add_css_class("numeric")
        row.append(widget)
    return row


class AppSummaryRow(Gtk.Button):
    def __init__(self, clicked):
        super().__init__()
        self.add_css_class("flat")
        self.add_css_class("overview-app-row")
        self.name, self.cpu, self.memory = label(), label(), label()
        self.set_child(app_columns(self.name, self.cpu, self.memory, icon=True))
        self.data = None
        self.observed_at = None
        self.connect("clicked", lambda _: clicked(self.data, observed_at=self.observed_at) if self.data else None)

    def update(self, group, exited=False, unavailable=False, observed_at=None):
        self.data = group
        if not exited and not unavailable:
            self.observed_at = observed_at
        self.name.set_label(group.name+(" · Unavailable" if unavailable else " · Exited" if exited else ""))
        for widget, value, unit in ((self.cpu, group.cpu, "%"), (self.memory, group.rss, "bytes")):
            if unavailable:
                value = Value(None, "Unavailable")
            partial = value.status == "Partial"
            widget.set_label(formatted(value, unit)+(" · partial" if partial else ""))
            (widget.add_css_class if partial else widget.remove_css_class)("partial")
        description = f"{self.name.get_label()}. CPU {self.cpu.get_label()}. Memory RSS {self.memory.get_label()}. Open details."
        self.update_property([Gtk.AccessibleProperty.LABEL], [description])
        self.set_tooltip_text(description)
