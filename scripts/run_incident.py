"""Capture one existing docs-loader failure and verify non-destructive automatic recovery."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

from observe_docs import deployment, snapshot


def request(url, *, data=None, trace_id=None):
    headers = {}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if trace_id:
        # A CLI request has no browser SDK; provide valid remote trace context explicitly.
        headers['traceparent'] = '00-' + trace_id + '-' + uuid.uuid4().hex[:16] + '-01'
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return {'status': response.status, 'body': response.read().decode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--verify-existing', action='store_true',
                        help='Verify a saved run without issuing any application request')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    manifest = args.directory / 'run.json'
    if args.verify_existing:
        record = json.loads(manifest.read_text())
        assert record['response']['status'] == 500
        assert record['docs_status']['status'] == 200
        assert len(record['normal_requests']) == 3
        assert all(r['status'] == 200 for r in record['normal_requests'])
        assert record['after']['health'] == 'healthy'
        assert record['after']['restarts'] == record['before']['restarts'] + 1
        verify_lifecycle(args.directory, record)
        return
    # Fail before causing a failure when packaging is incomplete.
    lifecycle_query = Path(__file__).resolve().parent.parent / 'queries/task05/lifecycle-events.sql'
    assert lifecycle_query.is_file(), 'Lifecycle verification SQL is missing; restore queries/ first'
    if manifest.exists():
        raise SystemExit('Use a fresh directory to preserve the previous run evidence.')
    target = deployment()
    prefix = target['prefix']
    app_url = f"http://localhost:{target['app_port']}"
    docs_url = f"http://localhost:{target['docs_port']}"
    label = args.directory.name
    # Do not create an incident while its external event observer is unavailable.
    event_health = subprocess.check_output(['docker', 'inspect', '--format',
                                            '{{.State.Health.Status}}', prefix + '-docker-events'], text=True).strip()
    assert event_health == 'healthy', 'Docker event forwarding is not ready'
    before = snapshot()
    assert before['health'] == 'healthy', 'Docs-loader is not ready'
    assert before['memory_limit_bytes'] == 10485760, 'Intentional memory limit changed'
    trace_id = uuid.uuid4().hex
    event_file = (args.directory / 'events.jsonl').open('w')
    events = subprocess.Popen(['docker', 'events', '--filter', 'container=' + before['id'],
                              '--filter', 'event=oom', '--filter', 'event=die', '--filter', 'event=start',
                              '--format', '{"time":{{.TimeNano}},"action":"{{.Action}}","exit_code":"{{index .Actor.Attributes "exitCode"}}"}'],
                             stdout=event_file, stderr=subprocess.PIPE, text=True)
    # Keep one second of pre-trigger capture and allow the event subscription to establish.
    time.sleep(1)
    record = {'run': label, 'start': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
              'trace': trace_id, 'before': before, 'trigger': 'GET ' + app_url + '/load-docs',
              'run_label_location': 'manifest only; trace ID propagated in traceparent', 'checks_passed': False}
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    try:
        started = time.monotonic()
        record['response'] = request(app_url + '/load-docs', trace_id=trace_id)
        record['request_elapsed_seconds'] = round(time.monotonic() - started, 3)
        assert record['response']['status'] == 500, 'Failure signature changed; inspect saved response'
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            after = snapshot()
            if after['restarts'] > before['restarts'] and after['health'] == 'healthy':
                break
            time.sleep(1)
        else:
            raise AssertionError('Automatic recovery did not reach healthy within 60 seconds')
        record['after'] = after
        assert after['id'] == before['id'], 'Container was replaced during the run'
        assert after['restarts'] == before['restarts'] + 1, 'More than one restart; baseline is not controlled'
        record['docs_status'] = request(docs_url + '/')
        assert record['docs_status']['status'] == 200
        assert json.loads(record['docs_status']['body'])['status'] == 'ok'
        # Use synthetic data; the same email exercises the app's existing upsert behavior.
        email = label.lower() + '@example.invalid'
        record['recovery_email'] = email
        record['normal_requests'] = []
        for index in range(3):
            body = json.dumps({'name': 'Training Presenter', 'company': 'Training Demo',
                               'email': email, 'source': 'in-person-event'}).encode()
            result = request(app_url + '/api/subscribe', data=body)
            record['normal_requests'].append(result)
            assert result['status'] == 200 and json.loads(result['body'])['success'] is True
        # This is a local demo identifier, not arbitrary user SQL input.
        assert all(c.isalnum() or c in '-_@.' for c in email)
        query = "SELECT count(email) FROM users WHERE email = '" + email + "';"
        count = subprocess.check_output(['docker', 'exec', prefix + '-postgres-db', 'psql', '-U', 'postgres',
                                         '-d', 'postgres', '-Atc', query], text=True).strip()
        record['postgres_matching_rows'] = int(count)
        assert record['postgres_matching_rows'] == 1
        record['end'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    finally:
        events.terminate()
        _, errors = events.communicate(timeout=10)
        event_file.close()
        (args.directory / 'event-stderr.txt').write_text(errors)
        manifest.write_text(json.dumps(record, indent=2) + '\n')
    verify_lifecycle(args.directory, record)


def verify_lifecycle(directory, record):
    """Finish read-only verification of an already captured incident; never retrigger it."""
    manifest = directory / 'run.json'
    captured = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
    assert any(event['action'] == 'oom' for event in captured), 'No OOM event captured'
    assert any(event['action'] == 'die' and event['exit_code'] == '137' for event in captured), 'No exit-137 death event captured'
    assert any(event['action'] == 'start' for event in captured), 'No restart event captured'
    # The exercise also requires the native Docker events to be retrievable in ClickStack.
    # Match the immutable source event identity, not just a nearby timestamp/HTTP error.
    root = Path(__file__).resolve().parent.parent
    command = [sys.executable, str(root / 'scripts/sql.py'),
               str(root / 'queries/task05/lifecycle-events.sql'),
               '--param', 'start=' + record['start'], '--param', 'end=' + record['end'],
               '--param', 'container=' + record['before']['id']]
    expected_ids = {hashlib.sha256(f"{record['before']['id']}:{e['action']}:{e['time']}".encode()).hexdigest()
                    for e in captured}
    deadline = time.monotonic() + 30
    while True:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        found = json.loads(result.stdout)['data']
        if expected_ids <= {row['event_id'] for row in found}:
            break
        if time.monotonic() >= deadline:
            raise AssertionError('Docker events were captured locally but are not yet proven in ClickStack')
        time.sleep(1)
    (directory / 'clickstack-events.json').write_text(result.stdout)
    record['clickstack_lifecycle_actions'] = [row['action'] for row in found]
    record['clickstack_container_id'] = record['before']['id']
    record['clickstack_events_verified'] = True
    record['checks_passed'] = True
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'run': record['run'], 'status': record['response']['status'], 'trace': record['trace'],
                      'restart_delta': record['after']['restarts'] - record['before']['restarts'],
                      'normal_statuses': [r['status'] for r in record['normal_requests']],
                      'lifecycle_events': [e['action'] for e in captured],
                      'clickstack_events_verified': record['clickstack_events_verified']}, indent=2))


if __name__ == '__main__':
    main()
