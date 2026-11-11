"""Native GTK views. All objects in this module are used on the main thread."""

from datetime import datetime
import os
import time

from .native import Adw, Gdk, Gio, GLib, Gtk, Pango
from .model import AppGroup, Metric, Value, formatted, groups, size, stale
from .session import Session
from .theme import Theme
from .presentation import cpu_temperature, filesystem_summary, gpu_summary, missing
from .widgets import (AppSummaryRow, Chart, CpuPanel, MetricCard, NetworkPanel, SummaryPanel,
                      TemperaturePanel, app_columns, label, margins, symbolic_icon)
from .settings import Settings


CPU_HELP = "CPU uses whole-machine capacity: one busy logical CPU on a 20-CPU machine is about 5%."
RSS_HELP = "RSS is resident memory. Group totals sum process RSS; shared pages can be counted more than once."


class Row:
    def __init__(self, key, data, child=False):
        self.key, self.data, self.child = key, data, child


class VisibleRows:
    def __init__(self, table):
        self.table = table

    def get_n_items(self):
        return len(self.table.model)

    def get_item(self, position):
        return self.table.model[position][6] if 0 <= position < len(self.table.model) else None


class TableSelection:
    def __init__(self, table):
        self.table = table

    def get_selected_item(self):
        model, iterator = self.table.view.get_selection().get_selected()
        return model.get_value(iterator, 6) if iterator is not None else None

    def get_selected(self):
        model, iterator = self.table.view.get_selection().get_selected()
        return model.get_path(iterator).get_indices()[0] if iterator is not None else 2**32-1

    def set_selected(self, position):
        if position < len(self.table.model):
            self.table.view.get_selection().select_path(Gtk.TreePath.new_from_indices([position]))


class ProcessTable(Gtk.Box):
    def __init__(self, window, app_view=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window, self.app_view = window, app_view
        self.frame = None
        self.rows = {}
        self.order = []
        self.visible_order = []
        self.rendered_cache = {}
        self.expanded = set()
        self.force_sort = True
        controls = Gtk.Box(spacing=8)
        self.search = Gtk.SearchEntry(placeholder_text="Search name or PID", hexpand=True)
        self.search.update_property([Gtk.AccessibleProperty.LABEL], ["Search apps or processes by name or PID"])
        self.search.connect("search-changed", self.refilter)
        self.sort = Gtk.DropDown.new_from_strings(["CPU", "Memory (RSS)", "Name", "PID", "Disk read", "Disk write"])
        self.sort.update_property([Gtk.AccessibleProperty.LABEL], ["Sort apps or processes by"])
        self.sort.set_tooltip_text("Sort by this measurement. Choose a column heading to re-sort explicitly.")
        self.sort.connect("notify::selected", self.refilter)
        self.mine = Gtk.CheckButton(label="My processes")
        self.mine.connect("toggled", self.refilter)
        controls.append(self.search)
        controls.append(self.sort)
        self.append(controls)
        self.append(self.mine)
        self.append(label("CPU: whole-machine % · Memory: RSS (shared pages may count twice)\n"
                          "Partial totals exclude unreadable fields. Row order holds while the table has focus.", "caption"))
        # Shared native cell renderers avoid thousands of per-cell Python widgets.
        self.model = Gtk.ListStore(str, str, str, str, str, str, object)
        self.view = Gtk.TreeView(model=self.model, headers_visible=True, vexpand=True)
        self.view.update_property([Gtk.AccessibleProperty.LABEL], ["Applications" if app_view else "Running processes"])
        self.view.set_activate_on_single_click(False)
        self.view.connect("row-activated", lambda view, path, col: self.activate(view, path.get_indices()[0]))
        self.selection = TableSelection(self)
        self.store = VisibleRows(self)
        self.columns = []
        for i, (title, field) in enumerate((("App / process" if app_view else "Process", "name"),
                ("CPU", "cpu"), ("Memory · RSS", "rss"), ("Disk read", "read"), ("Disk write", "write"), ("PID", "pid"))):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            if field != "name":
                renderer.set_property("xalign", 1.0)
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_fixed_width({"name":240,"cpu":86,"rss":130,"read":138,"write":138,"pid":80}[field])
            column.set_expand(field == "name")
            column.set_resizable(True)
            column.set_clickable(True)
            column.connect("clicked", lambda _, f=field: self.resort(f))
            self.view.append_column(column)
            self.columns.append((field, column))
        self.view.set_tooltip_text(CPU_HELP + "\n" + RSS_HELP + "\nUse arrow keys on app groups to expand members; Enter opens details.")
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", self.refilter)
        self.view.add_controller(focus)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.key_pressed)
        self.view.add_controller(keys)
        click = Gtk.GestureClick()
        click.connect("pressed", self.clicked)
        self.view.add_controller(click)
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scroll.set_child(self.view)
        self.append(self.scroll)
        footer = Gtk.Box(spacing=8)
        self.count = label("Waiting for process inventory…", "caption")
        self.count.set_hexpand(True)
        details = Gtk.Button(label="View details")
        details.connect("clicked", lambda _: self.activate(self.view, self.selection.get_selected()))
        footer.append(self.count)
        footer.append(details)
        self.append(footer)

    def resort(self, field):
        self.sort.set_selected(("cpu", "rss", "name", "pid", "read", "write").index(field))
        self.refilter()

    def key_pressed(self, controller, key, code, state):
        row = self.selection.get_selected_item()
        if row and isinstance(row.data, AppGroup) and key in (Gdk.KEY_Right, Gdk.KEY_Left):
            expanded = row.key in self.expanded
            if (key == Gdk.KEY_Right and not expanded) or (key == Gdk.KEY_Left and expanded):
                self.toggle(row)
            return True
        return False

    def clicked(self, gesture, count, x, y):
        hit = self.view.get_path_at_pos(int(x), int(y))
        if hit and hit[1] == self.columns[0][1] and hit[2] < 26:
            row = self.store.get_item(hit[0].get_indices()[0])
            if row and isinstance(row.data, AppGroup) and len(row.data.members) > 1:
                self.toggle(row)

    def refilter(self, *_):
        self.force_sort = True
        if self.frame:
            self.update(self.frame)

    def toggle(self, row):
        if row:
            if row.key in self.expanded:
                self.expanded.remove(row.key)
            else:
                self.expanded.add(row.key)
            self.refilter()

    def activate(self, view, position):
        row = self.store.get_item(position)
        if row:
            self.window.show_details(row.data, observed_at=self.frame.wall_time)

    def update(self, frame):
        started = time.perf_counter()
        self.frame = frame
        query = self.search.get_text().strip().casefold()
        data = groups(frame.processes) if self.app_view else list(frame.processes.values())

        def matches(p):
            members = p.members if isinstance(p, AppGroup) else (p,)
            return ((not self.mine.get_active() or members[0].uid == os.getuid()) and
                    (not query or query in p.name.casefold() or any(query in str(m.pid) for m in members)))
        data = [p for p in data if matches(p)]
        field = ("cpu", "rss", "name", "pid", "read", "write")[self.sort.get_selected()]

        def key(p):
            if field == "name":
                return p.name.casefold()
            if field == "pid":
                return p.members[0].pid if isinstance(p, AppGroup) else p.pid
            value = getattr(p, field).number
            return -(value if value is not None else -1)

        focus = self.window.get_focus()
        held = focus is not None and (focus == self.view or focus.is_ancestor(self.view))
        if held and not self.force_sort:
            rank = {identity: i for i, identity in enumerate(self.order)}
            data.sort(key=lambda p: rank.get(p.identity, len(rank)))
        else:
            data.sort(key=key)
        self.force_sort = False
        self.order = [p.identity for p in data]
        flattened = []
        for p in data:
            flattened.append((p.identity, p, False))
            if isinstance(p, AppGroup) and p.identity in self.expanded:
                flattened.extend((("member", *m.identity), m, True) for m in p.members)
        selected = self.selection.get_selected_item()
        selected_key = selected.key if selected else None
        old_order = self.visible_order
        fresh, rendered = {}, []
        for identity, p, child in flattened:
            row = self.rows.get(identity) or Row(identity, p, child)
            row.data = p
            name = ("↳ " if child else "") + p.name
            if isinstance(p, AppGroup):
                name = (("▾ " if identity in self.expanded else "▸ ") +
                        ("Partial · " if p.partial else "") + name + f" ({len(p.members)})")
            values = [name]
            for attr in ("cpu", "rss", "read", "write"):
                value = getattr(p, attr)
                text = formatted(value, "%" if attr == "cpu" else "bytes" if attr == "rss" else "bytes/s")
                values.append(text + (" · partial" if value.status == "Partial" else ""))
            values.append(str(p.pid) if not isinstance(p, AppGroup) else "—")
            rendered.append((values, row))
            fresh[identity] = row
        new_order = [row.key for _, row in rendered]
        adjustment = self.scroll.get_vadjustment()
        scroll_value = adjustment.get_value()
        if set(old_order) == set(new_order):
            if old_order != new_order:
                ranks = {identity: i for i, identity in enumerate(old_order)}
                self.model.reorder([ranks[identity] for identity in new_order])
            for i, (values, row) in enumerate(rendered):
                if self.rendered_cache.get(row.key) != values:
                    iterator = self.model.get_iter(Gtk.TreePath.new_from_indices([i]))
                    self.model.set(iterator, list(range(6)), values)
        else:
            self.model.clear()
            for values, row in rendered:
                self.model.append(values + [row])
        if selected_key in new_order:
            self.selection.set_selected(new_order.index(selected_key))
        adjustment.set_value(scroll_value)
        self.rows = fresh
        self.visible_order = new_order
        self.rendered_cache = {row.key: values for values, row in rendered}
        self.expanded.intersection_update(fresh)
        self.count.set_label(f"{len(data):,} {'apps / groups' if self.app_view else 'processes'} · read-only"
                             if frame.status == "Available" else "Process inventory unavailable · read-only")
        self.model_ms = (time.perf_counter() - started) * 1000

    def narrow(self, value):
        for field, column in self.columns:
            column.set_visible(not value or field in ("name", "cpu", "rss"))


class MonitorWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Workstation Monitor")
        self.set_default_size(1220, 820)
        self.set_size_request(560, 520)
        self.settings = Settings()
        self.apply_appearance()
        desktop_names = {app.get_id(): app.get_display_name() for app in Gio.AppInfo.get_all() if app.get_id()}
        self.session = Session(desktop_names)
        self.session.interval = self.settings.values["interval"]
        self.paused = False
        self.frozen_history = {}
        self.display_frame = None
        self.display_gpu = None
        self.inventory_observed_at = None
        self.presented = None
        self.dialog = None
        self.detail_identity = None
        self.render_ms = 0
        self.model_ms = 0
        self.last_layout = None
        self.last_performance = None
        self.cards = {}
        self.resource_cards = {}
        self.network_choice = ""
        self.build()
        self.session.start()
        self.timer = GLib.timeout_add(200, self.tick)
        self.connect("close-request", self.close_monitor)

    def build(self):
        self.add_css_class("workstation-monitor")
        self.theme = Theme(self.get_display())
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Box())
        brand = Gtk.Box(spacing=10)
        brand.append(symbolic_icon("utilities-system-monitor-symbolic"))
        brand.append(label("Workstation Monitor", "brand"))
        header.pack_start(brand)
        root.append(header)
        body = Gtk.Box(vexpand=True)
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.set_size_request(180, -1)
        self.sidebar.add_css_class("monitor-sidebar")
        self.nav_buttons = {}
        for name, title, icon in (("overview", "Overview", "view-grid-symbolic"),
                                  ("apps", "Apps", "application-x-executable-symbolic"),
                                  ("processes", "Processes", "view-list-symbolic"),
                                  ("performance", "Performance", "utilities-system-monitor-symbolic")):
            button = Gtk.ToggleButton()
            button.add_css_class("flat")
            button.add_css_class("monitor-nav")
            content = Gtk.Box(spacing=12)
            content.append(symbolic_icon(icon))
            content.append(label(title))
            button.set_child(content)
            button.update_property([Gtk.AccessibleProperty.LABEL], [title])
            button.connect("clicked", lambda _, name=name: self.navigate(name))
            self.sidebar.append(button)
            self.nav_buttons[name] = button
        body.append(self.sidebar)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        page_header = Gtk.Box(spacing=10)
        margins(page_header, 16)
        self.page_heading = label("Overview", "page-heading")
        self.page_heading.set_wrap(False)
        self.page_heading.set_hexpand(True)
        page_header.append(self.page_heading)
        self.live_status = label("Measuring…", "monitor-status")
        self.live_status.set_wrap(False)
        self.live_status.set_valign(Gtk.Align.CENTER)
        page_header.append(self.live_status)
        self.pause_button = Gtk.ToggleButton(label="Pause display")
        self.pause_button.set_valign(Gtk.Align.CENTER)
        self.pause_button.set_tooltip_text("Freeze visible values. Collection continues until the app closes.")
        self.pause_button.connect("toggled", self.toggle_pause)
        page_header.append(self.pause_button)
        self.preferences_button = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Settings")
        self.preferences_button.set_valign(Gtk.Align.CENTER)
        self.preferences_button.update_property([Gtk.AccessibleProperty.LABEL], ["Settings"])
        self.preferences_button.connect("clicked", self.show_settings)
        page_header.append(self.preferences_button)
        main.append(page_header)
        self.banner = label(self.settings.warning, "monitor-banner")
        self.banner.set_visible(bool(self.settings.warning))
        main.append(self.banner)
        self.nav_dropdown = Gtk.DropDown.new_from_strings(["Overview", "Apps", "Processes", "Performance"])
        self.nav_dropdown.update_property([Gtk.AccessibleProperty.LABEL], ["Destination"])
        self.nav_dropdown.set_margin_start(16)
        self.nav_dropdown.set_margin_end(16)
        self.nav_dropdown.set_margin_bottom(12)
        self.nav_dropdown.connect("notify::selected", lambda *_: self.navigate(
            ("overview", "apps", "processes", "performance")[self.nav_dropdown.get_selected()]))
        self.nav_dropdown.set_visible(False)
        main.append(self.nav_dropdown)
        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        main.append(self.stack)
        footer = Gtk.Box(spacing=16)
        footer.add_css_class("monitor-footer")
        footer.append(Gtk.Image.new_from_icon_name("computer-symbolic"))
        footer.append(label("Local monitoring"))
        self.footer = label("Starting collectors…", xalign=1)
        self.footer.set_hexpand(True)
        footer.append(self.footer)
        main.append(footer)
        body.append(main)
        root.append(body)
        self.set_content(root)
        self.build_overview()
        self.apps = ProcessTable(self, True)
        self.processes = ProcessTable(self)
        for name, title, widget in (("apps", "Apps", self.apps), ("processes", "Processes", self.processes)):
            margins(widget, 16)
            self.stack.add_titled(widget, name, title)
        self.build_performance()
        self.stack.connect("notify::visible-child-name", self.page_changed)
        self.page_changed()
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.key_pressed)
        self.add_controller(keys)

    def build_overview(self):
        self.overview_grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        margins(self.overview_grid, 16)
        self.overview_grid.set_margin_top(0)
        self.cards = {
            "cpu": CpuPanel(lambda: self.open_resource("CPU")),
            "memory": SummaryPanel("Memory", lambda: self.open_resource("Memory")),
            "gpu": SummaryPanel("GPU", lambda: self.open_resource("GPU")),
            "disk": SummaryPanel("Storage", lambda: self.open_resource("Storage")),
            "network": NetworkPanel(lambda: self.open_resource("Network")),
        }
        self.cards["cpu"].set_tooltip_text(CPU_HELP)
        self.temperatures = TemperaturePanel(lambda: self.open_resource("Sensors"), lambda: self.open_resource("GPU"))
        self.app_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.app_panel.add_css_class("monitor-panel")
        top_header = Gtk.Box(spacing=12)
        top_header.add_css_class("apps-heading-row")
        title = label("Apps using resources", "panel-heading")
        title.set_hexpand(True)
        top_header.append(title)
        self.top_sort = Gtk.DropDown.new_from_strings(["Highest CPU", "Highest memory"])
        self.top_sort.update_property([Gtk.AccessibleProperty.LABEL], ["Rank high-usage apps by"])
        self.top_sort.connect("notify::selected", lambda *_: self.update_overview() if self.display_frame else None)
        top_header.append(self.top_sort)
        self.view_all_apps = Gtk.Button(label="View all apps")
        self.view_all_apps.add_css_class("flat")
        self.view_all_apps.add_css_class("monitor-link")
        self.view_all_apps.connect("clicked", lambda _: self.navigate("apps"))
        top_header.append(self.view_all_apps)
        self.app_panel.append(top_header)
        name = label("App")
        name.set_margin_start(28)
        columns = app_columns(name, label("CPU"), label("Memory (RSS)"))
        columns.add_css_class("apps-column-heading")
        columns.set_tooltip_text(CPU_HELP+"\n"+RSS_HELP)
        self.app_panel.append(columns)
        self.top_buttons = []
        self.top_groups = []
        for _ in range(3):
            button = AppSummaryRow(self.show_details)
            self.top_buttons.append(button)
            self.app_panel.append(button)
        self.apps_empty = label("Waiting for app measurements…", "monitor-caption")
        margins(self.apps_empty, 12)
        self.app_panel.append(self.apps_empty)
        self.overview_scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        # Allow a wide grid to shrink first; the next layout tick stacks it.
        # NEVER would turn the three-column grid into the window's minimum width.
        self.overview_scroll.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.AUTOMATIC)
        self.overview_scroll.set_child(self.overview_grid)
        self.layout_overview(False)
        self.stack.add_titled(self.overview_scroll, "overview", "Overview")

    def layout_overview(self, narrow):
        widgets = list(self.cards.values())+[self.temperatures, self.app_panel]
        for widget in widgets:
            if widget.get_parent() == self.overview_grid:
                self.overview_grid.remove(widget)
        if narrow:
            for i, widget in enumerate(widgets):
                self.overview_grid.attach(widget, 0, i, 1, 1)
        else:
            for key, x, y, width, height in (("cpu", 0, 0, 3, 1), ("memory", 0, 1, 1, 1),
                    ("gpu", 1, 1, 1, 1), ("disk", 0, 2, 1, 1), ("network", 2, 1, 1, 2)):
                self.overview_grid.attach(self.cards[key], x, y, width, height)
            self.overview_grid.attach(self.temperatures, 1, 2, 1, 1)
            self.overview_grid.attach(self.app_panel, 0, 3, 3, 1)

    def build_performance(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        margins(page, 16)
        controls = Gtk.Box(spacing=10)
        self.resource = Gtk.DropDown.new_from_strings(["CPU", "Memory", "GPU", "Storage", "Network", "Sensors"])
        self.resource.update_property([Gtk.AccessibleProperty.LABEL], ["Hardware resource"])
        self.resource.connect("notify::selected", lambda *_: self.update_performance(True))
        controls.append(label("Resource", "heading"))
        controls.append(self.resource)
        page.append(controls)
        self.network_dropdown = Gtk.DropDown.new_from_strings(["Waiting for interfaces…"])
        self.network_dropdown.update_property([Gtk.AccessibleProperty.LABEL], ["Network interface"])
        self.network_dropdown.connect("notify::selected", self.interface_changed)
        self.network_dropdown.set_visible(False)
        self.interface_names = []
        page.append(self.network_dropdown)
        self.resource_note = label("", "resource-note")
        page.append(self.resource_note)
        self.perf_grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        self.filesystems_label = label("", "caption")
        self.perf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.perf_box.append(self.perf_grid)
        self.perf_box.append(self.filesystems_label)
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(self.perf_box)
        page.append(scroll)
        self.stack.add_titled(page, "performance", "Performance")

    def navigate(self, name):
        self.stack.set_visible_child_name(name)
        for key, button in self.nav_buttons.items():
            button.set_active(key == name)

    def page_changed(self, *_):
        name = self.stack.get_visible_child_name()
        index = ("overview", "apps", "processes", "performance").index(name)
        self.page_heading.set_label(("Overview", "Apps", "Processes", "Performance")[index])
        for key, button in self.nav_buttons.items():
            button.set_active(key == name)
        if self.nav_dropdown.get_selected() != index:
            self.nav_dropdown.set_selected(index)
        self.presented = None
        self.render(force=True)

    def open_resource(self, category):
        self.resource.set_selected(("CPU", "Memory", "GPU", "Storage", "Network", "Sensors").index(category))
        self.navigate("performance")

    def interface_changed(self, *_):
        pos = self.network_dropdown.get_selected()
        if pos < len(self.interface_names):
            self.network_choice = self.interface_names[pos]
            self.update_performance(True)

    def tick(self):
        self.session.hidden = not self.get_mapped() or bool(self.get_surface() and
            self.get_surface().get_state() & Gdk.ToplevelState.MINIMIZED)
        self.session.consume()
        width = self.get_width()
        narrow = width < 850
        if self.last_layout != narrow:
            self.last_layout = narrow
            self.sidebar.set_visible(not narrow)
            self.nav_dropdown.set_visible(narrow)
            self.apps.narrow(narrow)
            self.processes.narrow(narrow)
            self.layout_overview(narrow)
            self.update_performance(True)
        if not self.paused and not self.session.hidden:
            self.render()
        return GLib.SOURCE_CONTINUE

    def render(self, force=False):
        if self.paused and not force:
            return
        system = self.display_frame if self.paused else self.session.latest["system"]
        gpu = self.display_gpu if self.paused else self.session.latest["gpu"]
        if system is None:
            return
        token = (system.timestamp, gpu.timestamp if gpu else None, self.stack.get_visible_child_name(),
                 stale(system.timestamp, time.monotonic(), self.session.period),
                 stale(gpu.timestamp, time.monotonic(), self.session.period) if gpu else False)
        if token == self.presented:
            return
        started = time.perf_counter()
        self.display_frame, self.display_gpu = system, gpu
        if system.status == "Available":
            self.inventory_observed_at = system.wall_time
        self.presented = token
        names = [n for n, _, _ in system.interfaces]
        if names != self.interface_names:
            previous = self.network_choice
            self.interface_names = names
            chosen = previous if previous in names else next(
                (n for n, k, up in system.interfaces if k == "Physical" and up), names[0] if names else "")
            self.network_dropdown.set_model(Gtk.StringList.new(names or ["No interfaces"]))
            self.network_choice = chosen
            if chosen in names:
                self.network_dropdown.set_selected(names.index(chosen))
        name = self.stack.get_visible_child_name()
        if name == "overview":
            self.update_overview()
        elif name in ("apps", "processes"):
            getattr(self, name).update(system)
        elif name == "performance":
            self.update_performance()
        if self.dialog is not None:
            self.update_details()
        state = self.provider_state(system)
        gpu_state = self.provider_state(gpu)
        badge = "Paused" if self.paused else state.split(" · ")[0]
        self.live_status.set_label(("● " if badge == "Live" else "")+badge)
        self.live_status.set_tooltip_text(f"{'Paused snapshot · ' if self.paused else ''}System {state} · GPU {gpu_state}")
        (self.live_status.remove_css_class if badge == "Live" else self.live_status.add_css_class)("warning")
        display_state = "Paused snapshot" if self.paused else state
        gpu_display_state = "snapshot" if self.paused and gpu_state == "Live" else gpu_state
        count = f"{len(system.processes):,} processes" if system.status == "Available" else "Process inventory unavailable"
        sample_label = "Last sample" if system.status == "Available" else "Last attempt"
        self.footer.set_label(f"{count} · {display_state} · {sample_label} "
                              f"{datetime.fromtimestamp(system.wall_time):%H:%M:%S} · GPU {gpu_display_state}")
        self.render_ms = (time.perf_counter() - started) * 1000

    def provider_state(self, frame):
        if frame is None:
            return "Measuring…"
        if frame.status != "Available":
            return frame.status
        now = self.chart_now()
        if stale(frame.timestamp, now, self.session.period):
            return f"Stale · last success {datetime.fromtimestamp(frame.wall_time):%H:%M:%S}"
        return "Live"

    def chart_now(self):
        return self.display_frame.timestamp if self.paused and self.display_frame else time.monotonic()

    def history_points(self, key):
        return self.frozen_history.get(key, ()) if self.paused else self.session.history.series.get(key, ())

    def all_metrics(self):
        metrics = dict(self.display_frame.metrics) if self.display_frame else {}
        if self.display_gpu:
            metrics.update(self.display_gpu.metrics)
        return metrics

    def update_overview(self):
        if not self.display_frame:
            return
        frame, gpu = self.display_frame, self.display_gpu
        metrics = frame.metrics
        system_state = self.provider_state(frame)
        gpu_state = self.provider_state(gpu)
        system_state = "" if system_state == "Live" else system_state
        gpu_state = "" if gpu_state == "Live" else gpu_state
        now = self.chart_now()
        cpu = metrics.get("cpu.total", missing("cpu.total", "CPU", "%", "CPU"))
        self.cards["cpu"].update(cpu, self.history_points(cpu.key), now, system_state)
        memory = metrics.get("memory.percent", missing("memory.percent", "Memory", "%", "Memory"))
        used, total = metrics.get("memory.used"), metrics.get("memory.total")
        memory_detail = (f"{formatted(used.value, 'bytes')} / {formatted(total.value, 'bytes')}"
                         if used and total else "Capacity unavailable")
        self.cards["memory"].update(memory, memory_detail, "Used / total RAM", system_state)
        device = gpu_summary(gpu)
        vram = f"{formatted(device['used'].value, 'bytes')} / {formatted(device['total'].value, 'bytes')}"
        self.cards["gpu"].update(device["util"], vram, "GPU utilization · VRAM used / total", gpu_state)
        storage, free, mount = filesystem_summary(frame)
        self.cards["disk"].update(storage, f"{size(free)} free" if free is not None else "Free space unavailable",
                                  f"Filesystem {mount}" if mount.startswith("/") else mount,
                                  system_state, suffix=" used")
        (self.cards["disk"].bar.add_css_class if storage.value.number is not None and storage.value.number >= 90
            else self.cards["disk"].bar.remove_css_class)("warning")
        receive_key = f"net.{self.network_choice}.receive"
        send_key = f"net.{self.network_choice}.send"
        receive = metrics.get(receive_key, missing(receive_key, "Receive", "bytes/s", "Network"))
        send = metrics.get(send_key, missing(send_key, "Send", "bytes/s", "Network"))
        self.cards["network"].update(receive, send, self.history_points(receive_key), self.history_points(send_key),
                                     now, self.network_choice or "No interface", system_state)
        self.temperatures.update(cpu_temperature(frame), device["temperature"], system_state, gpu_state)
        field = "cpu" if self.top_sort.get_selected() == 0 else "rss"
        model_started = time.perf_counter()
        ranked = sorted(groups(frame.processes), key=lambda group: -(getattr(group, field).number or 0))
        self.model_ms = (time.perf_counter()-model_started)*1000
        focus = self.get_focus()
        held = focus is not None and any(focus == button or focus.is_ancestor(button) for button in self.top_buttons)
        inventory_available = frame.status == "Available"
        if not inventory_available:
            chosen = self.top_groups
        elif held and self.top_groups:
            by_identity = {group.identity: group for group in ranked}
            chosen = [by_identity.get(group.identity, group) for group in self.top_groups]
        else:
            chosen = ranked[:3]
        self.top_groups = chosen
        live = {group.identity for group in ranked}
        for i, button in enumerate(self.top_buttons):
            button.set_visible(i < len(chosen))
            if i < len(chosen):
                button.update(chosen[i], exited=inventory_available and chosen[i].identity not in live,
                              unavailable=not inventory_available, observed_at=frame.wall_time)
        self.apps_empty.set_visible(not chosen)
        self.apps_empty.set_label("No readable processes in this snapshot." if inventory_available
                                  else "App inventory unavailable.")

    def update_performance(self, force=False):
        if not self.display_frame:
            return
        category = ("CPU", "Memory", "GPU", "Storage", "Network", "Sensors")[self.resource.get_selected()]
        self.network_dropdown.set_visible(category == "Network")
        notes = {"CPU": CPU_HELP, "Memory": "Used RAM = total − available. App RSS totals can count shared pages twice.",
                 "GPU": "Device utilization and VRAM are separate. Per-app GPU utilization is not inferred.",
                 "Storage": "Physical-device throughput excludes partition totals. Filesystem capacity is separate.",
                 "Network": "Interface throughput, not internet speed. No per-app bandwidth or combined interface total.",
                 "Sensors": "Only sensors reported by the hardware are shown; unavailable readings are not zero."}
        self.resource_note.set_label(notes[category])
        metrics = [m for m in self.all_metrics().values() if m.category == category and
                   (category != "Network" or m.key.startswith(f"net.{self.network_choice}."))]
        if not metrics:
            metrics = [Metric("missing", category, Value(None, self.provider_state(self.display_gpu)
                              if category == "GPU" else "Unavailable"), "", category)]
        signature = (category, tuple(m.key for m in metrics), self.last_layout)
        if signature != self.last_performance:
            for card in self.resource_cards.values():
                self.perf_grid.remove(card)
            self.resource_cards = {}
            columns = 1 if self.last_layout else 2
            for i, metric in enumerate(metrics):
                card = MetricCard(metric.title)
                self.resource_cards[metric.key] = card
                self.perf_grid.attach(card, i % columns, i // columns, 1, 1)
            self.last_performance = signature
        state = self.provider_state(self.display_gpu if category == "GPU" else self.display_frame)
        for metric in metrics:
            self.resource_cards[metric.key].update(metric, self.history_points(metric.key),
                self.chart_now(), state if state != "Live" else "")
        self.filesystems_label.set_visible(category == "Storage")
        self.filesystems_label.set_label("Filesystem capacity\n" + "\n".join(
            f"{mount}: {size(usage.used)} used / {size(usage.total)} total · {size(usage.free)} available"
            if usage else f"{mount}: {status}"
            for dev, mount, usage, status in self.display_frame.filesystems))

    def toggle_pause(self, button):
        self.paused = button.get_active()
        button.set_label("Resume display" if self.paused else "Pause display")
        if self.paused:
            self.live_status.set_label("Paused")
            self.live_status.add_css_class("warning")
        self.banner.set_visible(self.paused or bool(self.settings.warning))
        if self.paused:
            self.frozen_history = {key: tuple(points) for key, points in self.session.history.series.items()}
            stamp = self.display_frame.wall_time if self.display_frame else time.time()
            self.banner.set_label(f"Display paused at {datetime.fromtimestamp(stamp):%H:%M:%S}. Collection continues.")
            self.presented = None
            self.render(force=True)
        else:
            self.frozen_history = {}
            self.banner.set_label(self.settings.warning)
            self.presented = None
            self.render()

    def show_details(self, data, observed_at=None):
        if self.dialog:
            self.dialog.close()
        dialog = Adw.Window(transient_for=self, modal=True, title="App details" if isinstance(data, AppGroup) else "Process details")
        dialog.set_default_size(560, 600)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        margins(box, 20)
        self.detail_text = label("", "body")
        self.detail_chart = Chart()
        self.member_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(self.detail_text)
        box.append(self.detail_chart)
        box.append(label("Selected process CPU · 0–100% of this machine · last 5 min", "caption"))
        box.append(self.member_box)
        close = Gtk.Button(label="Close details")
        close.connect("clicked", lambda _: dialog.close())
        box.append(close)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(box)
        dialog.set_content(scroll)
        self.dialog, self.detail_data = dialog, data
        self.detail_seen_at = (observed_at if observed_at is not None else self.display_frame.wall_time
                               if self.display_frame and self.display_frame.status == "Available"
                               else self.inventory_observed_at)
        self.member_identities = None
        self.detail_identity = data.identity
        if not isinstance(data, AppGroup):
            if self.session.history.selected != data.identity:
                self.frozen_history.pop("selected.cpu", None)
            self.session.history.select(data.identity)
        dialog.connect("close-request", self.close_details)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", lambda _, key, *args: (dialog.close() or True) if key == Gdk.KEY_Escape else False)
        dialog.add_controller(keys)
        self.update_details()
        dialog.present()

    def close_details(self, *_):
        self.dialog = None
        self.detail_data = None
        self.detail_text = None
        self.detail_chart = None
        self.member_box = None
        self.session.history.select(None)
        return False

    def show_member_details(self, identity):
        if isinstance(self.detail_data, AppGroup):
            member = next((p for p in self.detail_data.members if p.identity == identity), None)
            if member:
                self.show_details(member, observed_at=self.detail_seen_at)

    def update_details(self):
        if not self.dialog or not self.display_frame:
            return
        data = self.detail_data
        inventory_available = self.display_frame.status == "Available"
        snapshot_state = "Paused snapshot" if self.paused else self.provider_state(self.display_frame)
        if isinstance(data, AppGroup):
            group = next((g for g in groups(self.display_frame.processes) if g.identity == data.identity),
                         None) if inventory_available else None
            if group:
                data = group
                self.detail_data = data
                self.detail_seen_at = self.display_frame.wall_time
            observed = datetime.fromtimestamp(self.detail_seen_at).strftime("%H:%M:%S") if self.detail_seen_at is not None else "Unknown"
            self.detail_text.set_label(f"{data.name}\n{snapshot_state} · Last observed {observed}\n"
                f"{len(data.members)} member processes\n"
                f"CPU {formatted(data.cpu, '%')} · RSS {formatted(data.rss, 'bytes')}\n"
                f"Read {formatted(data.read, 'bytes/s')} · Write {formatted(data.write, 'bytes/s')}\n"
                f"{'Partial totals: some member measurements are unavailable.' if data.partial else 'Readable member totals.'}\n"
                f"{RSS_HELP}\nRead-only. Per-app network bandwidth is outside this release."
                + ("\nThis app group has exited." if group is None and inventory_available else
                   "\nApp membership unavailable. Showing last observed values." if not inventory_available else ""))
            identities = tuple(m.identity for m in data.members)
            if getattr(self, "member_identities", None) != identities:
                while child := self.member_box.get_first_child():
                    self.member_box.remove(child)
                for p in data.members:
                    button = Gtk.Button(label=f"{p.name} · PID {p.pid}")
                    button.connect("clicked", lambda _, identity=p.identity: self.show_member_details(identity))
                    self.member_box.append(button)
                self.member_identities = identities
            self.detail_chart.set_visible(False)
        else:
            current = self.display_frame.processes.get(data.identity) if inventory_available else None
            data = current or data
            if current:
                self.detail_data = current
                self.detail_seen_at = self.display_frame.wall_time
            gpu_amount = self.display_gpu.process_vram.get(data.identity) if current and self.display_gpu else None
            gpu_text = size(gpu_amount) if gpu_amount is not None else "Unavailable / unsupported"
            gpu_state = self.provider_state(self.display_gpu)
            if gpu_amount is not None and gpu_state != "Live":
                gpu_text += f" · {gpu_state}"
            process_state = (data.state if current else "Exited — this PID will not be followed if reused."
                             if inventory_available else "Process state unavailable. Showing last observed values.")
            observed = datetime.fromtimestamp(self.detail_seen_at).strftime("%H:%M:%S") if self.detail_seen_at is not None else "Unknown"
            self.detail_text.set_label(f"{data.name} · PID {data.pid}\n"
                f"{snapshot_state} · Last observed {observed}\n"
                f"{process_state}\n"
                f"Owner {data.owner} · Parent PID {data.parent} · Threads {data.threads}\n"
                f"Started {datetime.fromtimestamp(data.started):%Y-%m-%d %H:%M:%S}\n\n"
                f"CPU {formatted(data.cpu, '%')}\nRSS {formatted(data.rss, 'bytes')}\n"
                f"Disk read {formatted(data.read, 'bytes/s')}\nDisk write {formatted(data.write, 'bytes/s')}\n"
                f"GPU memory {gpu_text}\n\n{CPU_HELP}\n{RSS_HELP}\n"
                "Read-only. Command arguments and environment are not collected. Per-app network bandwidth is outside this release.")
            self.detail_chart.set_visible(True)
            self.detail_chart.update(self.history_points("selected.cpu"), "%", self.chart_now())

    def apply_appearance(self):
        Adw.StyleManager.get_default().set_color_scheme({"system": Adw.ColorScheme.DEFAULT,
            "light": Adw.ColorScheme.FORCE_LIGHT, "dark": Adw.ColorScheme.FORCE_DARK}[self.settings.values["appearance"]])

    def show_settings(self, *_):
        dialog = Adw.Window(transient_for=self, modal=True, title="Settings")
        dialog.set_default_size(380, 330)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        margins(box, 22)
        box.append(label("Refresh interval", "heading"))
        interval = Gtk.DropDown.new_from_strings(["1 second", "2 seconds", "5 seconds"])
        interval.update_property([Gtk.AccessibleProperty.LABEL], ["Refresh interval"])
        interval.set_selected((1, 2, 5).index(self.settings.values["interval"]))
        box.append(interval)
        box.append(label("Appearance", "heading"))
        appearance = Gtk.DropDown.new_from_strings(["System", "Light", "Dark"])
        appearance.update_property([Gtk.AccessibleProperty.LABEL], ["Appearance"])
        appearance.set_selected(("system", "light", "dark").index(self.settings.values["appearance"]))
        box.append(appearance)
        box.append(label("Only these preferences are saved. Measurements remain in memory.", "caption"))
        save = Gtk.Button(label="Save settings")
        save.add_css_class("suggested-action")

        def persist(_):
            self.settings.values = {"interval": (1, 2, 5)[interval.get_selected()],
                                    "appearance": ("system", "light", "dark")[appearance.get_selected()]}
            try:
                self.settings.save()
                self.settings.warning = ""
            except OSError:
                self.settings.warning = "Preferences could not be saved. Current choices apply for this session."
            self.session.interval = self.settings.values["interval"]
            self.apply_appearance()
            if not self.paused:
                self.banner.set_label(self.settings.warning)
                self.banner.set_visible(bool(self.settings.warning))
            dialog.close()

        save.connect("clicked", persist)
        box.append(save)
        dialog.set_content(box)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", lambda _, key, *args: (dialog.close() or True) if key == Gdk.KEY_Escape else False)
        dialog.add_controller(keys)
        dialog.present()
        # Kept for native integration tests; not a runtime remote-control interface.
        self.settings_dialog, self.interval_control, self.appearance_control, self.save_control = dialog, interval, appearance, save

    def key_pressed(self, controller, key, code, state):
        if key == Gdk.KEY_f and state & Gdk.ModifierType.CONTROL_MASK:
            page = self.stack.get_visible_child_name()
            if page in ("apps", "processes"):
                getattr(self, page).search.grab_focus()
                return True
        return False

    def close_monitor(self, *_):
        GLib.source_remove(self.timer)
        self.session.close()
        for child in Gtk.Window.list_toplevels():
            if child.get_transient_for() == self:
                child.close()
        self.theme.close(self.get_display())
        return False


class MonitorApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="local.workstation.Monitor", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = MonitorWindow(self)
        self.window.present()
