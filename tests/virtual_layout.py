"""Test real 200% GTK scaling on a roomy disposable X11 display, not host settings."""

import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
env=dict(os.environ,LD_LIBRARY_PATH=str(root/'.native/usr/lib/x86_64-linux-gnu'))
server=subprocess.Popen([str(root/'.native/usr/bin/Xvfb'),'-displayfd','1','-screen','0','3200x2200x24',
                         '-nolisten','tcp'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
try:
    number=server.stdout.readline().strip()
    if not number.isdigit():
        raise SystemExit('Virtual X11 display failed: '+server.stderr.read())
    result=subprocess.run([sys.executable,str(root/'tests/layout_flow.py')],
        env=dict(env,DISPLAY=':'+number,GDK_SCALE='2',MONITOR_VIRTUAL_DISPLAY='1',
                 PYTHONPATH=str(root)+':'+str(root/'tests')))
    raise SystemExit(result.returncode)
finally:
    server.terminate()
    server.wait(timeout=5)
