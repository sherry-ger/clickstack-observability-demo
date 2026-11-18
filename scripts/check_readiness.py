"""Check local demo readiness without printing credentials or querying telemetry."""
import base64
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def main():
    # Parse the generated simple KEY=value file; do not execute it as shell code.
    env = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
               if line and not line.startswith('#') and '=' in line)
    raw = subprocess.check_output([str(ROOT / 'scripts/stack.sh'), 'ps', '--format', 'json'], text=True)
    containers = [json.loads(line) for line in raw.splitlines() if line.strip()]
    expected = {'clickstack', 'postgres-db', 'socat', 'docs-loader', 'subscription-app', 'otel-collector', 'docker-events'}
    assert {c['Service'] for c in containers} == expected, 'Missing or unexpected active services'
    for c in containers:
        assert c['State'] == 'running' and c['Health'] == 'healthy', c['Service'] + ' is not ready'
    results = {'services': {c['Service']: c['Health'] for c in containers}}
    app_port = int(env.get('KUBECON_APP_PORT') or 8000)
    ui_port = int(env.get('KUBECON_UI_PORT') or 8080)
    sql_port = int(env.get('CLICKHOUSE_PORT') or 8123)
    for name, url in [('application', f'http://localhost:{app_port}/health'), ('application_root', f'http://localhost:{app_port}'), ('ui', f'http://localhost:{ui_port}')]:
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.status == 200
            results[name + '_http'] = response.status
    credentials = base64.b64encode((env['CLICKHOUSE_USER'] + ':' + env['CLICKHOUSE_PASSWORD']).encode()).decode()
    request = urllib.request.Request(f'http://127.0.0.1:{sql_port}/?max_execution_time=5',
                                    data=b'SELECT 1 FORMAT TabSeparated',
                                    headers={'Authorization': 'Basic ' + credentials})
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200 and response.read().strip() == b'1'
        results['authenticated_sql'] = '1'
    try:
        urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{sql_port}/', data=b'SELECT 1'), timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 401
        results['unauthenticated_sql_http'] = error.code
    else:
        raise AssertionError('SQL accepted an unauthenticated request')
    for c in containers:
        binding = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .HostConfig.PortBindings}}', c['Name']], text=True))
        assert all(b['HostIp'] == '127.0.0.1' for group in (binding or {}).values() for b in group)
    results['published_ports'] = 'loopback only'
    results['traffic_generator'] = 'not running'
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
