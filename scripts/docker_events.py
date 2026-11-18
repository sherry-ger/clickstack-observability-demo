"""Forward this demo's real Docker lifecycle events as OTLP/HTTP JSON logs."""
from collections import deque
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from queue import Empty, Queue
from threading import Thread
import time
import urllib.parse
import urllib.request


def string_attribute(key, value):
    return {'key': key, 'value': {'stringValue': str(value)}}


def event_resource(event):
    # Allowlist fields: Docker event attributes may otherwise contain commands/labels.
    attrs = event['Actor']['Attributes']
    return {'attributes': [string_attribute('service.name', 'docker-events'),
                           string_attribute('container.id', event['Actor']['ID']),
                           string_attribute('container.name', attrs['name']),
                           string_attribute('container.image.name', attrs.get('image', ''))]}


def event_record(event):
    action = event['Action']
    attrs = event['Actor']['Attributes']
    identity = f"{event['Actor']['ID']}:{action}:{event['timeNano']}"
    attributes = [string_attribute('event.name', 'docker.' + action),
                  string_attribute('event.provider', 'docker'),
                  string_attribute('event.id', hashlib.sha256(identity.encode()).hexdigest()),
                  string_attribute('docker.event.action', action)]
    if 'exitCode' in attrs:
        attributes.append(string_attribute('docker.event.exit_code', attrs['exitCode']))
    error = action == 'oom' or (action == 'die' and attrs.get('exitCode') != '0')
    # Docker supplies no request trace ID. Correlate using container identity and time.
    return {'timeUnixNano': str(event['timeNano']), 'observedTimeUnixNano': str(time.time_ns()),
            'severityNumber': 17 if error else 9, 'severityText': 'ERROR' if error else 'INFO',
            'body': {'stringValue': f"Docker {action}: {attrs['name']}"}, 'attributes': attributes}


def main():
    docker_url = os.environ['DOCKER_EVENTS_URL'].rstrip('/')
    otlp_url = os.environ['OTEL_EXPORTER_OTLP_LOGS_ENDPOINT']
    ingestion_key = os.environ['HYPERDX_API_KEY']
    project = os.environ['DOCKER_DEMO_PROJECT']
    events = Queue(maxsize=512)
    state = {'connected': False, 'export_error': False}

    class Health(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/health':
                self.send_error(404)
                return
            ready = state['connected'] and not state['export_error']
            self.send_response(200 if ready else 503)
            self.end_headers()
            self.wfile.write(json.dumps({'docker_connected': state['connected'],
                                        'export_error': state['export_error'],
                                        'queued_events': events.qsize()}).encode())

        def log_message(self, *_):
            pass

    def read_events():
        # Reconnect to the live daemon after resets. A bounded recent-ID cache
        # removes replay within the same process; this is not durable exactly-once delivery.
        since = int(time.time()) - 1
        seen = set()
        recent = deque()
        while True:
            try:
                with urllib.request.urlopen(docker_url + '/version', timeout=5) as response:
                    version = json.load(response)['ApiVersion']
                filters = {'type': ['container'], 'label': ['com.docker.compose.project=' + project],
                           'event': ['oom', 'die', 'start', 'restart']}
                query = urllib.parse.urlencode({'filters': json.dumps(filters), 'since': since})
                with urllib.request.urlopen(f'{docker_url}/v{version}/events?{query}', timeout=30) as response:
                    state['connected'] = True
                    for line in response:
                        if not line.strip():
                            continue
                        event = json.loads(line)
                        record = event_record(event)
                        identity = record['attributes'][2]['value']['stringValue']
                        if identity in seen:
                            continue
                        events.put({'resource': event_resource(event),
                                    'scopeLogs': [{'scope': {'name': 'kubecon.docker.events', 'version': '1'},
                                                   'logRecords': [record]}]})
                        seen.add(identity)
                        recent.append(identity)
                        if len(recent) > 512:
                            seen.remove(recent.popleft())
                        since = event['timeNano'] // 1_000_000_000
            except (OSError, ValueError, KeyError) as error:
                state['connected'] = False
                print('Docker stream reconnect:', type(error).__name__, flush=True)
                time.sleep(1)

    Thread(target=read_events, daemon=True).start()
    Thread(target=HTTPServer(('127.0.0.1', 13134), Health).serve_forever, daemon=True).start()
    while True:
        batch = [events.get()]
        # Send bursts together; ClickStack's ingestion collector performs DB batching.
        time.sleep(0.5)
        while len(batch) < 64:
            try:
                batch.append(events.get_nowait())
            except Empty:
                break
        payload = json.dumps({'resourceLogs': batch}).encode()
        while True:
            try:
                request = urllib.request.Request(otlp_url, data=payload,
                                                headers={'Content-Type': 'application/json',
                                                         'Authorization': ingestion_key})
                with urllib.request.urlopen(request, timeout=10) as response:
                    result = json.loads(response.read() or '{}')
                if int(result.get('partialSuccess', {}).get('rejectedLogRecords', 0)):
                    raise ValueError('OTLP rejected log records')
                state['export_error'] = False
                print(f'Forwarded {len(batch)} Docker lifecycle events', flush=True)
                break
            except (OSError, ValueError) as error:
                state['export_error'] = True
                print('OTLP export retry:', type(error).__name__, flush=True)
                time.sleep(1)


if __name__ == '__main__':
    main()
