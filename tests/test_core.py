from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import io
import json
import os
import tempfile
import threading
import time
import unittest

import psutil
from workstation_monitor.collectors import SystemCollector, NvidiaCollector, app_scope, physical_disks
from workstation_monitor.model import Frame, History, Metric, Process, Rates, Value, cpu_delta, groups, stale
from workstation_monitor.session import Session
from workstation_monitor.settings import Settings


def proc(pid=1001, **kw):
    data = dict(pid=pid, started=1.0, name="Fixture app", owner="fixture", uid=os.getuid(),
                state="running", parent=1, threads=1, cpu=Value.ok(5), rss=Value.ok(1024),
                read=Value.ok(12), write=Value.ok(8))
    data.update(kw)
    return Process(**data)


class MeasurementTests(unittest.TestCase):
    def test_first_zero_reset_and_real_elapsed(self):
        rates = Rates()
        self.assertIsNone(rates.rate("a", 100, 1).number)
        self.assertEqual(rates.rate("a", 100, 2).number, 0)
        self.assertEqual(rates.rate("a", 200, 7).number, 20)
        self.assertIsNone(rates.rate("a", 2, 8).number)
        self.assertIsNone(rates.rate("a", None, 9).number)
        self.assertIsNone(rates.rate("a", 4, 10).number)
        self.assertIsNone(rates.rate(("pid", 1, 2), 500, 11).number)
        rates.clear()
        self.assertFalse(rates.previous)

    def test_cpu_topology_and_negative_counters(self):
        self.assertIsNone(cpu_delta(None, (0, 0, 0, 0)).number)
        self.assertEqual(cpu_delta((0, 0, 0, 0, 0), (1, 0, 0, 19, 0)).number, 5)
        self.assertIsNone(cpu_delta((2, 0, 0, 0), (1, 0, 0, 1)).number)
        self.assertIsNone(cpu_delta((0, 0), (0, 0, 0)).number)

    def test_history_ages_out_process_churn_and_selection(self):
        history = History()
        p = proc()
        history.select(p.identity)
        for i in range(1000):
            metric = Metric("cpu.total", "CPU", Value.ok(i % 100), "%", "CPU")
            history.add(Frame(i, i, {metric.key: metric}, {p.identity: p}))
        self.assertLessEqual(len(history.series["cpu.total"]), 302)
        self.assertGreaterEqual(history.series["cpu.total"][0][0], 699)
        self.assertIn("selected.cpu", history.series)
        history.select((p.pid, 999))
        self.assertNotIn("selected.cpu", history.series)
        history.add(Frame(2000, 2000))
        self.assertFalse(history.series)

    def test_groups_partial_same_name_and_pid_reuse(self):
        a, b = proc(), proc(1002)
        self.assertEqual(len(groups({a.identity:a, b.identity:b})), 2)
        a = replace(a, app_id="scope-one", app_name="App")
        b = replace(b, app_id="scope-one", read=Value(None, "Permission denied"))
        g = groups({a.identity:a, b.identity:b})[0]
        self.assertEqual(len(g.members), 2)
        self.assertEqual(g.rss.number, 2048)
        self.assertEqual(g.read.number, 12)
        self.assertTrue(g.partial)
        c = replace(b, app_id="scope-two")
        self.assertEqual(len(groups({a.identity:a,c.identity:c})), 2)
        self.assertNotEqual(a.identity, replace(a, started=2).identity)

    def test_scope_requires_desktop_match(self):
        names = {"org.example.App.desktop":"Example"}
        scope, name = app_scope("0::/user.slice/app-org.example.App-123.scope", names)
        self.assertEqual((scope,name),("app-org.example.App-123.scope","Example"))
        self.assertEqual(app_scope("/unknown-app.scope",names),("",""))
        self.assertEqual(app_scope("/app-org.example.AppOther-123.scope",names),("",""))
        nested={"org.example.Parent.desktop":"Parent","org.example.Child.desktop":"Child"}
        self.assertEqual(app_scope('/app-org.example.Parent-1.scope/app-org.example.Child-2.scope',nested),
                         ('app-org.example.Child-2.scope','Child'))

    def test_freshness_threshold(self):
        self.assertFalse(stale(10, 11.99, 1))
        self.assertTrue(stale(10, 12, 1))
        self.assertFalse(stale(10, 15, 5))

    def test_history_preserves_missed_intervals_after_recovery(self):
        h=History()
        p=proc()
        h.select(p.identity)
        metric=Metric('cpu.total','CPU',Value.ok(25),'%','CPU')
        h.add(Frame(1,1,{metric.key:metric},{p.identity:p}),1)
        h.add(Frame(2,2,{metric.key:metric},{p.identity:p}),1)
        h.add(Frame(6,6,{metric.key:metric},{p.identity:p}),1)
        self.assertEqual([point[1] for point in h.series['cpu.total']],[25,25,None,25])
        self.assertEqual([point[1] for point in h.series['selected.cpu']],[5,5,None,5])


class LinuxTests(unittest.TestCase):
    def test_field_denial_preserves_cpu_memory_and_normalizes(self):
        class FakeProcess:
            pid = 1001
            seconds = 0
            def oneshot(self):return nullcontext()
            def create_time(self):return 1
            def uids(self):return NS(real=os.getuid())
            def name(self):return "Fixture"
            def cpu_times(self):return NS(user=self.seconds,system=0)
            def memory_info(self):return NS(rss=4096)
            def io_counters(self):raise psutil.AccessDenied(self.pid)
            def status(self):return "running"
            def ppid(self):return 1
            def num_threads(self):return 1
        p=FakeProcess()
        c=SystemCollector()
        with patch("psutil.process_iter",return_value=[p]):
            first=c._processes(1,20,set())
            p.seconds=1
            second=c._processes(2,20,set())
        row=next(iter(second.values()))
        self.assertEqual(row.cpu.number,5)
        self.assertEqual(row.rss.number,4096)
        self.assertEqual(row.read.status,"Permission denied")
        self.assertEqual(len(second),1)

    def test_physical_disks_exclude_partitions_and_loops(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ("nvme0n1","nvme0n1p1","loop0","sda"):
                p=root/name;p.mkdir();(p/"device").mkdir();(p/"dev").write_text("1:1")
            (root/"nvme0n1p1/partition").touch()
            self.assertEqual(set(physical_disks(root)),{"nvme0n1","sda"})

    def test_live_memory_and_storage_accounting(self):
        collector=SystemCollector()
        frame=collector.collect()
        self.assertGreater(len(frame.processes),0)
        self.assertEqual(frame.metrics["memory.used"].value.number,
                         frame.metrics["memory.total"].value.number-frame.metrics["memory.available"].value.number)
        self.assertFalse(any(k.startswith("disk.loop") for k in frame.metrics))
        self.assertTrue(any(m.value.status == "Permission denied" for p in frame.processes.values() for m in [NS(value=p.read)]))

    def test_suspend_and_topology_reset(self):
        collector=SystemCollector()
        collector.collect()
        with patch("workstation_monitor.collectors.time.clock_gettime",return_value=time.monotonic()+100):
            f=collector.collect()
        self.assertIsNone(f.metrics["cpu.total"].value.number)
        self.assertTrue(all(p.cpu.number is None for p in f.processes.values()))
        collector.topology=999
        f=collector.collect()
        self.assertIsNone(f.metrics["cpu.total"].value.number)


class SettingsTests(unittest.TestCase):
    def test_allowlist_atomic_permissions_and_readback(self):
        with tempfile.TemporaryDirectory() as path:
            s=Settings(path)
            s.values={"interval":2,"appearance":"dark","secret_runtime_snapshot":"PRIVATE"}
            s.save()
            self.assertEqual(Settings(path).values,{"interval":2,"appearance":"dark"})
            self.assertNotIn("PRIVATE",s.path.read_text())
            self.assertEqual(s.path.stat().st_mode & 0o777,0o600)
            self.assertEqual(s.directory.stat().st_mode & 0o777,0o700)
            self.assertEqual(len(list(Path(path).iterdir())),1)

    def test_corrupt_and_unsupported_preferences(self):
        with tempfile.TemporaryDirectory() as path:
            p=Path(path)/"preferences.json"
            for text in ("broken",'[]','{"interval":true,"appearance":"dark"}',
                         '{"interval":3,"appearance":"dark"}'):
                p.write_text(text)
                s=Settings(path)
                self.assertEqual(s.values["interval"],1)
                self.assertTrue(s.warning)


class WorkerTests(unittest.TestCase):
    def test_slow_gpu_does_not_stall_system_or_build_queue(self):
        release=threading.Event()
        class Basic:
            def collect(self):return Frame(time.monotonic(),time.time())
        class Slow:
            def collect(self):
                release.wait(3)
                return Frame(time.monotonic(),time.time())
        session=Session(system=Basic(),gpu=Slow())
        session.start()
        try:
            time.sleep(.1)
            first=session.latest["system"].timestamp
            time.sleep(1.05)
            self.assertGreater(session.latest["system"].timestamp,first)
            self.assertIsNone(session.latest["gpu"])
            self.assertEqual(len(session.latest),2)
            self.assertEqual(len(session.threads),2)
            session.hidden=True
            self.assertEqual(session.period,5)
            session.interval=2
            session.hidden=False
            self.assertEqual(session.period,2)
        finally:
            release.set();session.close()
        self.assertTrue(all(not t.is_alive() for t in session.threads))

    def test_private_provider_failure_is_not_logged(self):
        class Broken:
            def collect(self):raise RuntimeError("PRIVATE_FIXTURE_NAME_AND_ARGUMENT")
        session=Session(system=Broken(),gpu=Broken())
        output=io.StringIO()
        with patch("sys.stderr",output),patch("sys.stdout",output):
            session.start();time.sleep(.05);session.close()
        self.assertEqual(output.getvalue(),"")
        self.assertEqual(session.latest["gpu"].status,"Unavailable")


if __name__ == "__main__":
    unittest.main()
