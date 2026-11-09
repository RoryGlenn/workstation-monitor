"""Drive real GTK widgets and assertions on the local desktop; no remote test API."""

import os
os.environ.setdefault("GSK_RENDERER","cairo")
os.environ.setdefault("GDK_DEBUG","gl-disable,vulkan-disable")
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import statistics
import sys
if os.environ.get('MONITOR_SWITCH_INTERVAL'):
    sys.setswitchinterval(float(os.environ['MONITOR_SWITCH_INTERVAL']))
import faulthandler
import signal
faulthandler.register(signal.SIGUSR2)

from workstation_monitor.native import Adw, Gio, GLib
from workstation_monitor.model import Frame, Value
from workstation_monitor.settings import Settings
from workstation_monitor.ui import MonitorApplication
from test_core import proc


def pump(seconds=.1):
    end=time.monotonic()+seconds
    ctx=GLib.MainContext.default()
    while time.monotonic()<end:
        while ctx.pending() and time.monotonic()<end:ctx.iteration(False)
        time.sleep(.01)


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['WORKSTATION_MONITOR_CONFIG_DIR']=directory
        app=MonitorApplication()
        app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        app.register()
        start=time.monotonic()
        app.activate()
        w=app.window
        pump(2.5)
        assert w.get_mapped()
        assert w.display_frame and w.display_frame.processes
        assert w.cards['cpu'].metric.value.number is not None
        assert w.network_choice != 'lo',w.network_choice
        assert w.display_gpu and len(w.display_gpu.metrics)>=5
        print('Live overview and independent GPU provider: PASS',flush=True)
        w.cards['gpu'].emit('clicked');pump()
        print('GPU navigation: PASS',flush=True)
        assert w.stack.get_visible_child_name()=='performance'
        assert w.resource.get_selected()==2
        assert len(w.resource_cards)>=5
        w.navigate('processes');pump()
        print('Process navigation: PASS',flush=True)
        own=next(p for p in w.display_frame.processes.values() if p.pid==os.getpid())
        w.processes.search.set_text(str(own.pid));pump(.4)
        assert w.processes.store.get_n_items()>=1
        w.processes.selection.set_selected(0)
        w.processes.activate(w.processes.view,0);pump()
        assert w.dialog and str(own.pid) in w.detail_text.get_label()
        w.dialog.close();pump()
        w.navigate('overview');pump()
        stamp=w.display_frame.timestamp
        w.pause_button.set_active(True);pump(1.5)
        assert w.display_frame.timestamp==stamp
        assert w.session.latest['system'].timestamp>stamp
        assert w.banner.get_visible() and 'Collection continues' in w.banner.get_label()
        w.open_resource('CPU');pump(.2)
        assert w.resource_cards['cpu.total'].metric.value==w.display_frame.metrics['cpu.total'].value
        assert all(timestamp<=stamp for timestamp,value in w.resource_cards['cpu.total'].chart.points)
        assert w.resource_cards['cpu.total'].chart.now==stamp
        w.navigate('processes');pump(.2)
        assert w.processes.frame.timestamp==stamp
        w.navigate('overview');pump(.1)
        w.pause_button.set_active(False);pump(.2)
        assert w.display_frame.timestamp>stamp
        w.show_settings();pump()
        w.interval_control.set_selected(1)
        w.appearance_control.set_selected(2)
        w.save_control.emit('clicked');pump()
        assert Settings(directory).values=={'interval':2,'appearance':'dark'}
        assert w.session.interval==2
        w.set_default_size(600,700);pump(.8)
        assert w.nav_dropdown.get_visible()
        assert not w.sidebar.get_visible()
        assert w.get_width()<=650,w.get_width()
        print('Native overview → details → pause/resume → saved settings → narrow layout: PASS',flush=True)
        # Fixtures use the same real native table and model as the live inventory.
        w.pause_button.set_active(True)
        w.navigate('processes')
        w.processes.search.set_text('');pump(.3)
        data=[proc(10000+i,started=100+i,name=f'Fixture {i}',cpu=Value.ok(i%100),rss=Value.ok(i)) for i in range(2000)]
        frame=Frame(time.monotonic(),time.time(),processes={p.identity:p for p in data})
        timings=[]
        if os.environ.get('MONITOR_PROFILE'):
            import cProfile
            profile=cProfile.Profile()
            profile.enable()
        for i in range(2 if os.environ.get('MONITOR_PROFILE') else 10):
            print('Fixture iteration',i,flush=True)
            before=time.perf_counter()
            w.processes.force_sort=True
            w.processes.update(frame)
            w.processes.search.set_text('Fixture 19' if i%2 else '')
            w.processes.refilter()
            timings.append((time.perf_counter()-before)*1000)
            print('Fixture model ms',round(timings[-1],2),flush=True)
            pump(.02)
        if os.environ.get('MONITOR_PROFILE'):
            profile.disable()
            import pstats
            pstats.Stats(profile).sort_stats('cumtime').print_stats(18)
        p95=sorted(timings)[-1]
        assert p95<200,timings
        w.processes.search.set_text('');w.processes.refilter()
        w.processes.selection.set_selected(10)
        key=w.processes.selection.get_selected_item().key
        w.processes.sort.set_selected(1);pump(.1)
        assert w.processes.selection.get_selected_item().key==key
        assert w.processes.store.get_item(0).data.rss.number==1999
        p=data[0]
        w.show_details(p);pump(.1)
        changed=replace(p,cpu=Value.ok(9))
        w.display_frame=Frame(time.monotonic(),time.time(),processes={p.identity:changed})
        w.update_details()
        w.display_frame=Frame(time.monotonic(),time.time(),processes={(p.pid,999):replace(p,started=999)})
        w.update_details()
        assert 'Exited' in w.detail_text.get_label()
        assert 'CPU 9.0%' in w.detail_text.get_label()
        w.dialog.close();pump()
        print('2,000-process native search/sort p95_ms:',round(p95,2),'PID reuse: PASS',flush=True)
        w.close();pump(.3)
        assert all(not t.is_alive() for t in w.session.threads)
        assert not w.get_mapped()
        app.quit()
        print('Clean native close: PASS',flush=True)
        # A restart is a fresh process; GApplication objects cannot re-export
        # the same application path twice on one process's shared bus connection.
        import subprocess
        subprocess.run([sys.executable,str(Path(__file__).with_name('restart_flow.py'))],check=True)
        print('Native application restart preference readback: PASS',flush=True)


if __name__=='__main__':main()
