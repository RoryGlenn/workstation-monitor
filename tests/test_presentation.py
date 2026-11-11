from types import SimpleNamespace
import unittest

from workstation_monitor.model import Frame, Metric, Value
from workstation_monitor.presentation import cpu_temperature, filesystem_summary, gpu_summary


class DashboardSources(unittest.TestCase):
    def test_root_capacity_keeps_mount_and_failure_identity(self):
        usage = SimpleNamespace(percent=68, free=164 * 1024**3)
        frame = Frame(1, 1, filesystems=(("/dev/backup", "/backup", usage, "Available"),
                                        ("/dev/root", "/", None, "Permission denied")))
        metric, free, mount = filesystem_summary(frame)
        self.assertEqual(mount, "/")
        self.assertIsNone(free)
        self.assertIsNone(metric.value.number)
        self.assertEqual(metric.value.status, "Permission denied")
        metric, free, mount = filesystem_summary(Frame(1, 1, filesystems=(("/dev/root", "/", usage, "Available"),)))
        self.assertEqual((metric.value.number, free, mount), (68, usage.free, "/"))
        self.assertIsNone(filesystem_summary(Frame(1, 1))[0].value.number)

    def test_gpu_fields_never_cross_device_identity(self):
        metrics = [Metric("gpu.first.util", "GPU", Value(None, "Unsupported"), "%", "GPU"),
                   Metric("gpu.first.temperature", "Temperature", Value.ok(46), "°C", "GPU"),
                   Metric("gpu.second.util", "GPU", Value.ok(90), "%", "GPU"),
                   Metric("gpu.second.used", "VRAM", Value.ok(999), "bytes", "GPU")]
        result = gpu_summary(Frame(1, 1, metrics={m.key: m for m in metrics}))
        self.assertEqual(result["util"].value.status, "Unsupported")
        self.assertEqual(result["temperature"].value.number, 46)
        self.assertIsNone(result["used"].value.number)
        self.assertTrue(all(m.key.startswith("gpu.first.") for m in result.values()))

    def test_temperature_uses_identifiable_cpu_not_other_sensors(self):
        def sensor(key, title, value):
            return Metric(key, title, value, "°C", "Sensors")
        acpi = sensor("sensor.acpitz.0", "ACPI Temperature", Value.ok(28))
        disk = sensor("sensor.nvme.0", "NVMe Temperature", Value.ok(40))
        core = sensor("sensor.coretemp.1", "coretemp · Core 0", Value.ok(48))
        package = sensor("sensor.coretemp.0", "coretemp · Package id 0", Value(None, "Unavailable"))
        frame = Frame(1, 1, metrics={m.key: m for m in (acpi, disk)})
        self.assertIsNone(cpu_temperature(frame).value.number)
        frame.metrics.update({m.key: m for m in (core, package)})
        self.assertEqual(cpu_temperature(frame), package)
        die = sensor("sensor.k10temp.0", "k10temp · Tdie", Value.ok(54))
        self.assertEqual(cpu_temperature(Frame(1, 1, metrics={die.key: die})), die)
