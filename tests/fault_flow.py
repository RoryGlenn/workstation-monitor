"""Provider failures and recovery through the actual native session and UI."""

import os
os.environ.setdefault('GSK_RENDERER','cairo')
os.environ.setdefault('GDK_DEBUG','gl-disable,vulkan-disable')
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from workstation_monitor.native import Gio
from workstation_monitor.model import Frame, Metric, Value
from workstation_monitor.session import Session
from workstation_monitor.ui import MonitorApplication
from native_flow import pump
from test_core import proc


class Basic:
    def collect(self):
        p=proc(read=Value(None,'Permission denied'))
        now=time.monotonic()
        metric=Metric('cpu.total','CPU',Value.ok(25),'%','CPU')
        return Frame(now,time.time(),{metric.key:metric},{p.identity:p})


class GPU:
    def __init__(self):
        self.block=threading.Event()
        self.slow=False
        self.fail=False
    def collect(self):
        if self.slow:self.block.wait(10)
        if self.fail:raise RuntimeError('PRIVATE_FIXTURE_EXCEPTION')
        metric=Metric('gpu.fixture.util','GPU utilization',Value.ok(20),'%','GPU')
        return Frame(time.monotonic(),time.time(),{metric.key:metric},process_vram={(1001,1.0):512*1024**2})


with tempfile.TemporaryDirectory() as directory:
    os.environ['WORKSTATION_MONITOR_CONFIG_DIR']=directory
    (Path(directory)/'preferences.json').write_text('corrupt fixture')
    gpu=GPU()
    with patch('workstation_monitor.ui.Session',lambda _:Session(system=Basic(),gpu=gpu)):
        app=MonitorApplication();app.set_flags(Gio.ApplicationFlags.NON_UNIQUE);app.register();app.activate()
        w=app.window;pump(.7)
        assert w.banner.get_visible() and 'Safe defaults' in w.banner.get_label()
        old=w.display_frame.timestamp
        gpu.slow=True;pump(3.2)
        assert w.display_frame.timestamp>old
        assert 'Stale' in w.provider_state(w.display_gpu)
        w.open_resource('GPU');pump(.2)
        assert any('Stale' in card.detail.get_label() for card in w.resource_cards.values())
        w.navigate('processes');pump(.1)
        p=next(iter(w.display_frame.processes.values()))
        assert p.read.status=='Permission denied'
        assert w.processes.store.get_n_items()==1
        w.show_details(p);pump(.1)
        assert 'GPU memory 512.0 MiB · Stale' in w.detail_text.get_label()
        w.dialog.close();pump(.1)
        assert w.detail_data is None and w.member_box is None
        gpu.slow=False;gpu.block.set();pump(1.3)
        assert w.provider_state(w.display_gpu)=='Live'
        assert any(value is None for stamp,value in w.session.history.series['gpu.fixture.util'])
        gpu.fail=True;pump(1.2)
        assert w.display_gpu.status=='Unavailable'
        w.open_resource('CPU');pump(.1)
        assert w.resource_cards['cpu.total'].metric.value.number==25
        w.close();pump(.3)
        assert all(not t.is_alive() for t in w.session.threads)
        app.quit()
        print('Corrupt preferences, denied field, slow/failed GPU, recovery and responsive navigation: PASS')
