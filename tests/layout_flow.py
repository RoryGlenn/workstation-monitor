"""Visual QA with fixture process names and real local hardware values."""

import os
os.environ.setdefault('GSK_RENDERER','cairo')
os.environ.setdefault('GDK_DEBUG','gl-disable,vulkan-disable')
from dataclasses import replace
from pathlib import Path
import tempfile
import time

from workstation_monitor.native import Gio, Gdk, Gtk, Adw
from workstation_monitor.ui import MonitorApplication, Chart
from workstation_monitor.model import groups, Value
from native_flow import pump
from test_core import proc
from capture_window import capture


with tempfile.TemporaryDirectory() as config:
    os.environ['WORKSTATION_MONITOR_CONFIG_DIR']=config
    app=MonitorApplication();app.set_flags(Gio.ApplicationFlags.NON_UNIQUE);app.register();app.activate()
    w=app.window;pump(2.5)
    class Recorder:
        def __init__(self):self.data=False;self.operations=[]
        def set_source_rgba(self,*color):self.data=color[0]==.24
        def set_line_width(self,*args):pass
        def move_to(self,*point):
            if self.data:self.operations.append('move')
        def line_to(self,*point):
            if self.data:self.operations.append('line')
        def stroke(self):pass
    chart=Chart();now=time.monotonic()
    chart.update([(now-3,10),(now-2,None),(now-1,20),(now,30)],'%',now)
    recorder=Recorder();chart.draw(chart,recorder,300,74)
    assert chart.scale==100 and recorder.operations==['move','move','line']
    w.pause_button.set_active(True)
    members=[proc(20000+i,started=time.time()-100,name=f'Demo app {i+1}',
                  cpu=Value.ok(2+i),rss=Value.ok((i+1)*100*1024**2),
                  app_id='demo-scope' if i<2 else '',app_name='Demo browser' if i<2 else '') for i in range(5)]
    fixture=replace(w.display_frame,processes={p.identity:p for p in members})
    w.display_frame=fixture
    for appearance in ('light','dark'):
        w.settings.values['appearance']=appearance;w.apply_appearance()
        w.set_default_size(1280,800);w.navigate('overview');w.update_overview();pump(.8)
        if os.environ.get('MONITOR_VIRTUAL_DISPLAY'):
            # A display without a window manager includes a small CSD border
            # in default_size. Match the actual content allocation explicitly.
            w.set_default_size(1280+(1280-w.get_width()),800+(800-w.get_height()));pump(.4)
        assert w.get_width()==1280,w.get_width()
        assert w.get_height()==800,w.get_height()
        assert w.get_scale_factor()==int(os.environ.get('GDK_SCALE','1'))
        output=f'/tmp/workstation-monitor-{appearance}-{os.environ.get("GDK_SCALE","1")}x-wide.png'
        print(output,capture(w,output),flush=True)
    w.navigate('apps');w.apps.update(fixture);pump(.2)
    group=next(g for g in groups(fixture.processes) if len(g.members)>1)
    row=w.apps.rows[group.identity]
    before=w.apps.store.get_n_items();w.apps.toggle(row);pump(.2)
    assert w.apps.store.get_n_items()==before+2
    w.show_details(group);pump(.2)
    assert w.member_box.get_first_child() is not None
    w.dialog.close();pump(.1)
    # The same key controller that receives a real Escape event dismisses details.
    w.show_details(members[0]);pump(.1)
    controllers=w.dialog.observe_controllers()
    handled=False
    for i in range(controllers.get_n_items()):
        controller=controllers.get_item(i)
        if isinstance(controller,Gtk.EventControllerKey):
            handled=controller.emit('key-pressed',Gdk.KEY_Escape,0,Gdk.ModifierType(0)) or handled
            if handled:break
    pump(.1)
    assert handled and w.dialog is None
    w.show_details(group);pump(.1)
    assert w.member_box.get_first_child() is not None
    w.dialog.close();pump(.1)
    w.apps.view.grab_focus();w.apps.selection.set_selected(0);pump(.1)
    selected=w.apps.selection.get_selected_item().key
    order=list(w.apps.visible_order)
    changed=replace(fixture,processes={p.identity:replace(p,cpu=Value.ok(9.9-i)) for i,p in enumerate(members)})
    w.apps.force_sort=False;w.apps.update(changed);pump(.1)
    assert w.apps.visible_order==order
    assert w.apps.selection.get_selected_item().key==selected
    print('App expansion, repeat detail, focus and selection stability: PASS',flush=True)
    w.set_default_size(600,700);pump(.7)
    if os.environ.get('MONITOR_VIRTUAL_DISPLAY'):
        w.set_default_size(600+(600-w.get_width()),700+(700-w.get_height()));pump(.4)
    assert (w.get_width(),w.get_height())==(600,700)
    assert w.nav_dropdown.get_visible() and not w.sidebar.get_visible()
    assert all(column.get_visible()==(field in ('name','cpu','rss')) for field,column in w.apps.columns)
    output=f'/tmp/workstation-monitor-dark-{os.environ.get("GDK_SCALE","1")}x-narrow.png'
    print(output,capture(w,output),flush=True)
    # Exercise ordinary minimize/restore rather than restarting collectors.
    (w.set_visible(False) if os.environ.get('MONITOR_VIRTUAL_DISPLAY') else w.minimize())
    pump(.7);assert w.session.hidden
    w.present();pump(.7);assert not w.session.hidden
    w.show_settings();pump(.1)
    w.close();pump(.3);assert all(not t.is_alive() for t in w.session.threads)
    assert not w.settings_dialog.get_visible()
    app.quit()
    print('Layouts, scaling, minimize/restore and close: PASS',flush=True)
