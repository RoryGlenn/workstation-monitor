"""Time fresh native app processes, including Python/import/application setup."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


if len(sys.argv)>1 and sys.argv[1]=='--child':
    from workstation_monitor.native import GLib
    from workstation_monitor.ui import MonitorApplication
    app=MonitorApplication()
    ready=False
    def watch():
        global ready
        w=app.window
        if w and w.get_mapped() and w.display_frame:
            if not ready:
                print('READY',flush=True);ready=True
            metric=w.cards['cpu'].metric
            if metric and metric.value.number is not None:
                print('VALID_RATES',flush=True)
                w.close();app.quit();return False
        return True
    GLib.timeout_add(25,watch)
    app.run([])
else:
    import select
    root=Path(__file__).resolve().parents[1]
    results=[]
    with tempfile.TemporaryDirectory() as directory:
        env=dict(os.environ,GSK_RENDERER='cairo',GDK_DEBUG='gl-disable,vulkan-disable',
                 WORKSTATION_MONITOR_CONFIG_DIR=directory)
        for run in range(3):
            started=time.perf_counter()
            p=subprocess.Popen([sys.executable,__file__,'--child'],stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,text=True,env=env)
            values={}
            try:
                while len(values)<2:
                    assert select.select([p.stdout],[],[],5)[0],'Startup timed out'
                    message=p.stdout.readline().strip()
                    assert message in ('READY','VALID_RATES'),message
                    values[message]=time.perf_counter()-started
                assert p.wait(timeout=5)==0,p.stderr.read()
            finally:
                if p.poll() is None:p.terminate();p.wait(timeout=5)
            assert values['READY']<2,values
            assert values['VALID_RATES']<2,values
            results.append(values)
    output=root/'artifacts/startup.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
