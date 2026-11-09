"""Read preferences saved by native_flow in a fresh native app process."""

from workstation_monitor.native import Adw, Gio
from workstation_monitor.ui import MonitorApplication
from native_flow import pump

app=MonitorApplication()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register();app.activate();pump(.5)
w=app.window
assert w.settings.values=={'interval':2,'appearance':'dark'}
assert w.session.interval==2
assert Adw.StyleManager.get_default().get_color_scheme()==Adw.ColorScheme.FORCE_DARK
w.close();pump(.3)
assert all(not t.is_alive() for t in w.session.threads)
app.quit()
