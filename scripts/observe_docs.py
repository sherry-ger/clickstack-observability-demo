"""Observe docs-loader lifecycle without executing extra processes in that container."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import shlex
import time


ROOT = Path(__file__).resolve().parent.parent


def deployment():
    """Read only incident target metadata; never source/export private settings."""
    wanted = {'KUBECON_CONTAINER_PREFIX', 'KUBECON_APP_PORT', 'KUBECON_DOCS_PORT'}
    settings = {}
    for line in (ROOT / '.env').read_text().splitlines():
        key, separator, value = line.strip().partition('=')
        if separator and key in wanted:
            parts = shlex.split(value, comments=True)
            settings[key] = parts[0] if parts else ''
    return {'prefix': settings.get('KUBECON_CONTAINER_PREFIX') or 'kubecon',
            'app_port': int(settings.get('KUBECON_APP_PORT') or 8000),
            'docs_port': int(settings.get('KUBECON_DOCS_PORT') or 8001)}


def snapshot():
    value = json.loads(subprocess.check_output(['docker', 'inspect', deployment()['prefix'] + '-docs-loader'], text=True))[0]
    return {'utc': datetime.now(timezone.utc).isoformat(), 'id': value['Id'],
            'restarts': value['RestartCount'], 'memory_limit_bytes': value['HostConfig']['Memory'],
            'state': {key: value['State'][key] for key in ['Status', 'OOMKilled', 'ExitCode', 'StartedAt', 'FinishedAt']},
            'health': value['State'].get('Health', {}).get('Status')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--seconds', type=int, default=360)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    # Filter events at the daemon; do not collect container env or arbitrary logs.
    event_file = (args.directory / 'events.jsonl').open('w')
    events = subprocess.Popen(['docker', 'events', '--filter', 'container=kubecon-docs-loader',
                              '--filter', 'event=oom', '--filter', 'event=die', '--filter', 'event=start',
                              '--format', '{"time":{{.TimeNano}},"action":"{{.Action}}","exit_code":"{{index .Actor.Attributes "exitCode"}}"}'], stdout=event_file, stderr=subprocess.PIPE, text=True)
    initial = snapshot()
    (args.directory / 'initial.json').write_text(json.dumps(initial, indent=2) + '\n')
    print('Observation started; baseline restarts:', initial['restarts'], flush=True)
    started = time.monotonic()
    try:
        with (args.directory / 'samples.jsonl').open('w') as samples:
            while time.monotonic() - started < args.seconds:
                point = snapshot()
                point['docker_stats'] = subprocess.check_output(['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}} | {{.CPUPerc}}', deployment()['prefix'] + '-docs-loader'], text=True).strip()
                samples.write(json.dumps(point) + '\n')
                samples.flush()
                if point['restarts'] != initial['restarts']:
                    print('Restart observed:', point['restarts'], flush=True)
                    break
                time.sleep(5)
    finally:
        events.terminate()
        _, errors = events.communicate(timeout=10)
        event_file.close()
        (args.directory / 'event-stderr.txt').write_text(errors)
        final = snapshot()
        (args.directory / 'final.json').write_text(json.dumps(final, indent=2) + '\n')
        print('Observation finished after', round(time.monotonic() - started, 1), 'seconds; restarts:', final['restarts'], flush=True)


if __name__ == '__main__':
    main()
