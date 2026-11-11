"""Sanitized real-app benchmark. Stores numbers, never process names/snapshots."""

import os
os.environ.setdefault("GSK_RENDERER", "cairo")
os.environ.setdefault("GDK_DEBUG", "gl-disable,vulkan-disable")
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time
import psutil

from workstation_monitor.native import Gio, GLib
from workstation_monitor.ui import MonitorApplication


def percentile(values, percent):
    return sorted(values)[min(len(values)-1, int((len(values)-1)*percent))] if values else None


def source_hash():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    runtime = root / 'workstation_monitor'
    for path in sorted(runtime.glob('*.py')) + sorted(runtime.glob('*.css')) + [root / 'run.sh']:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=1800, help='Measured duration after warm-up')
    parser.add_argument('--warmup', type=int, default=None, help='Defaults to 300s for long runs, 0 for diagnostics')
    parser.add_argument('--output', default='artifacts/benchmark.json')
    args = parser.parse_args()
    warmup = args.warmup if args.warmup is not None else 300 if args.seconds >= 600 else 0
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    initial_hash = source_hash()
    cpu_count = psutil.cpu_count() or 1
    with tempfile.TemporaryDirectory() as config:
        os.environ['WORKSTATION_MONITOR_CONFIG_DIR'] = config
        app = MonitorApplication()
        app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        app.register()
        started = time.monotonic()
        app.activate()
        w = app.window
        p = psutil.Process()
        p.cpu_percent()
        samples, collections, gpu, models, draws = [], [], [], [], []
        usable = initial_rates = None
        signatures = set()
        last_saved_minute = -1

        def startup_watch():
            nonlocal usable, initial_rates
            elapsed = time.monotonic() - started
            if usable is None and w.get_mapped() and w.display_frame:
                usable = elapsed
            if initial_rates is None and w.cards['cpu'].metric and w.cards['cpu'].metric.value.number is not None:
                initial_rates = elapsed
            return elapsed < 5 and (usable is None or initial_rates is None)
        GLib.timeout_add(50, startup_watch)

        def result(complete):
            warm = [s for s in samples if s['elapsed'] >= warmup] or samples
            ten = []
            if warm:
                for sample in warm:
                    ten.append(sample)
                    if sample['elapsed'] - warm[0]['elapsed'] >= 600:
                        break
            cpu_window = ten[-1]['elapsed'] - ten[0]['elapsed'] if len(ten) > 1 else 0
            cpu_mean = ((ten[-1]['cpu_seconds']-ten[0]['cpu_seconds']) / cpu_window / cpu_count * 100
                        if cpu_window >= 600 else None)
            return {
                'complete': complete, 'elapsed_seconds': samples[-1]['elapsed'] if samples else 0,
                'warmup_seconds': warmup, 'requested_measurement_seconds': args.seconds,
                'usable_window_seconds': usable, 'initial_rates_seconds': initial_rates,
                'logical_cpu_count': cpu_count, 'cpu_window_seconds': cpu_window,
                'mean_cpu_total_percent_10min': cpu_mean,
                'max_rss_mib': max((s['rss_mib'] for s in warm), default=0),
                'system_collection_p95_ms': percentile(collections, .95),
                'gpu_query_p95_ms': percentile(gpu, .95),
                'overview_group_sort_p95_ms': percentile(models, .95),
                'main_thread_update_p95_ms': percentile([s['render_ms'] for s in warm], .95),
                'curve_draw_p95_ms': percentile(draws, .95),
                'process_count_min': min((s['processes'] for s in warm), default=0),
                'process_count_max': max((s['processes'] for s in warm), default=0),
                'runtime_source_sha256': initial_hash, 'source_unchanged': source_hash() == initial_hash,
                'samples': samples,
            }

        def save(data):
            temporary = output.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, indent=2))
            os.replace(temporary, output)

        def sample():
            nonlocal last_saved_minute
            elapsed = time.monotonic() - started
            frame = w.session.latest['system']
            gpu_frame = w.session.latest['gpu']
            if frame and frame.timestamp not in signatures:
                signatures.add(frame.timestamp)
                if elapsed >= warmup:
                    collections.append(frame.duration_ms)
            if gpu_frame and elapsed >= warmup:
                gpu.append(gpu_frame.duration_ms)
            if elapsed >= warmup:
                models.append(w.model_ms)
                draws.extend(card.chart.draw_ms for card in w.cards.values() if hasattr(card, 'chart'))
            samples.append({
                'elapsed': round(elapsed, 3),
                'cpu_total_percent': p.cpu_percent() / cpu_count,
                'cpu_seconds': sum(p.cpu_times()[:2]),
                'rss_mib': p.memory_info().rss / 1024**2,
                'processes': len(frame.processes) if frame else 0,
                'render_ms': w.render_ms,
                'history_points': sum(len(s) for s in w.session.history.series.values()),
                'system_status': frame.status if frame else 'Measuring',
                'gpu_status': gpu_frame.status if gpu_frame else 'Measuring',
            })
            minute = int(elapsed)//60
            complete = elapsed >= warmup + args.seconds
            if minute != last_saved_minute or complete:
                data = result(complete)
                save(data)
                last_saved_minute = minute
                print('Measured seconds', max(0, int(elapsed-warmup)), '/', args.seconds,
                      'RSS MiB', round(samples[-1]['rss_mib'], 1), 'checkpoint saved', flush=True)
            if complete:
                print(json.dumps({k:v for k,v in data.items() if k != 'samples'}, indent=2), flush=True)
                w.close()
                app.quit()
                return False
            return True
        GLib.timeout_add(250 if args.seconds < 60 else 1000, sample)
        loop = GLib.MainLoop()
        w.connect('close-request', lambda *_:loop.quit())
        loop.run()


if __name__ == '__main__':
    main()
