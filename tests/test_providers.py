from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import os
import tempfile
import socket
import subprocess
import threading
import time
import unittest

import psutil
from workstation_monitor.collectors import NvidiaCollector, SystemCollector


class ProviderTests(unittest.TestCase):
    def test_nvml_unsupported_and_process_memory_deduplication(self):
        import pynvml as nv
        p=psutil.Process()
        calls={
            'nvmlDeviceGetCount':1,'nvmlDeviceGetHandleByIndex':'handle',
            'nvmlDeviceGetUUID':'fixture-gpu','nvmlDeviceGetName':'Fixture GPU',
            'nvmlDeviceGetUtilizationRates':NS(gpu=25),
            'nvmlDeviceGetMemoryInfo':NS(used=1024,total=8192),
            'nvmlDeviceGetTemperature':45,'nvmlDeviceGetPowerUsage':50000,
            'nvmlDeviceGetComputeRunningProcesses':[NS(pid=p.pid,usedGpuMemory=512)],
            'nvmlDeviceGetGraphicsRunningProcesses':[NS(pid=p.pid,usedGpuMemory=512)]}
        with patch.multiple(nv,**{name:__import__('unittest.mock',fromlist=['Mock']).Mock(return_value=value)
                                 for name,value in calls.items()}):
            c=NvidiaCollector();c.nv=nv
            f=c.collect()
            self.assertEqual(f.process_vram[(p.pid,p.create_time())],512)
            self.assertEqual(f.metrics['gpu.fixture-gpu.power'].value.number,50)
            with patch.object(nv,'nvmlDeviceGetPowerUsage',side_effect=nv.NVMLError_NotSupported()):
                f=c.collect()
                self.assertEqual(f.metrics['gpu.fixture-gpu.power'].value.status,'Unsupported')
                self.assertEqual(f.metrics['gpu.fixture-gpu.util'].value.number,25)

    def test_live_gpu_readback(self):
        c=NvidiaCollector()
        try:
            f=c.collect()
            text=subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,temperature.gpu,power.draw',
                                          '--format=csv,noheader,nounits'],text=True)
            total,temp,power=map(float,text.strip().split(','))
            metrics={key.rsplit('.',1)[-1]:m.value.number for key,m in f.metrics.items()}
            self.assertEqual(metrics['total'],total*1024**2)
            self.assertLessEqual(abs(metrics['temperature']-temp),3)
            self.assertLessEqual(abs(metrics['power']-power),25)
        finally:c.close()

    def test_actual_single_thread_cpu_workload(self):
        workload=subprocess.Popen(['/usr/bin/python3','-c',
            'import time; end=time.monotonic()+2;\nwhile time.monotonic()<end: pass'])
        collector=SystemCollector()
        try:
            a=collector.collect()
            identity=next(key for key,p in a.processes.items() if p.pid==workload.pid)
            time.sleep(.7)
            b=collector.collect()
            value=b.processes[identity].cpu.number
            count=psutil.cpu_count()
            self.assertGreater(value,30/count)
            self.assertLessEqual(value,120/count)
        finally:workload.wait(timeout=4)

    def test_loopback_transfer_matches_counter_delta(self):
        collector=SystemCollector()
        first=collector.collect()
        c0=psutil.net_io_counters(pernic=True,nowrap=False)['lo'].bytes_recv
        server=socket.socket()
        server.bind(('127.0.0.1',0));server.listen(1)
        received=[]
        def receive():
            with server.accept()[0] as stream:
                total=0
                while data:=stream.recv(65536):total+=len(data)
                received.append(total)
        thread=threading.Thread(target=receive);thread.start()
        try:
            with socket.create_connection(server.getsockname()) as client:
                client.sendall(b'x'*(4*1024**2))
            thread.join(timeout=3)
            second=collector.collect()
            c1=psutil.net_io_counters(pernic=True,nowrap=False)['lo'].bytes_recv
            self.assertEqual(received,[4*1024**2])
            rate=second.metrics['net.lo.receive'].value.number
            measured=rate*(second.timestamp-first.timestamp)
            self.assertGreaterEqual(measured,c1-c0-65536)
            self.assertGreater(rate,0)
        finally:server.close()

    def test_interface_disappearance_and_counter_reset(self):
        c=SystemCollector()
        counter=NS(bytes_recv=100,bytes_sent=50)
        with patch('psutil.net_io_counters',return_value={'fixture0':counter}),patch.object(c,'_processes',return_value={}):
            c.collect()
            counter.bytes_recv=200
            second=c.collect()
            self.assertGreater(second.metrics['net.fixture0.receive'].value.number,0)
            counter.bytes_recv=1
            third=c.collect()
            self.assertIsNone(third.metrics['net.fixture0.receive'].value.number)
        with patch('psutil.net_io_counters',return_value={}),patch.object(c,'_processes',return_value={}):
            fourth=c.collect()
            self.assertEqual(fourth.metrics['net.fixture0.receive'].value.status,'Disconnected')

    def test_denied_link_metadata_keeps_system_and_traffic(self):
        c=SystemCollector()
        with patch('psutil.net_if_stats',side_effect=OSError(101,'Network unreachable')):
            f=c.collect()
            self.assertTrue(f.processes)
            self.assertIn('cpu.total',f.metrics)
            self.assertIn('net.lo.receive',f.metrics)
            self.assertIn('Link state unknown',f.metrics['net.lo.receive'].detail)

    def test_disk_removal_and_absent_sensors(self):
        c=SystemCollector()
        with patch('psutil.sensors_temperatures',return_value={}),patch('psutil.disk_io_counters',return_value={}),\
             patch.object(c,'_processes',return_value={}):
            f=c.collect()
            self.assertEqual(f.metrics['sensor.unavailable'].value.status,'Unavailable')
            self.assertTrue(all(m.value.status=='Disconnected' for k,m in f.metrics.items() if k.startswith('disk.')))

    def test_live_local_disk_write_and_counter_window(self):
        c=SystemCollector()
        first=c.collect()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'disposable-io-fixture'
            with path.open('wb') as stream:
                stream.write(b'x'*(8*1024**2));stream.flush();os.fsync(stream.fileno())
            second=c.collect()
        writes=[m.value.number for key,m in second.metrics.items()
                if key.startswith('disk.') and key.endswith('.write') and m.value.number is not None]
        self.assertTrue(writes)
        self.assertGreater(sum(writes),0)
        self.assertGreater(second.timestamp-first.timestamp,0)


if __name__=='__main__':unittest.main()
