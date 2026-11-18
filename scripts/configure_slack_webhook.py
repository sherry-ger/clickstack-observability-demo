"""Register the demo Slack destination without putting its URL in agent context."""
import argparse
import json
from pathlib import Path
import shlex
import urllib.error
import urllib.parse
import urllib.request

from launch_mcp import local_configuration

ROOT = Path(__file__).resolve().parent.parent
WEBHOOK_NAME = 'Demo Slack alerts'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--list', action='store_true', help='List destination IDs/names only')
    action.add_argument('--register', action='store_true', help='Create or reuse the demo destination; sends no Slack message')
    args = parser.parse_args()
    env = {}
    for line in (ROOT / '.env.mcp').read_text().splitlines():
        key, sep, value = line.strip().partition('=')
        if sep and not key.startswith('#'):
            parts = shlex.split(value, comments=True)
            env[key] = parts[0] if parts else ''
    # Reuse the same selected local endpoint/key as the project MCP launcher.
    # Registration still reads only the optional private webhook below.
    config = local_configuration()
    key = config['personal_key']

    # The UI proxy strips its first /api; the backend mounts external routes at /api/v2.
    def request(method, path, payload=None):
        req = urllib.request.Request(f"http://localhost:{config['port']}/api/api/v2/webhooks" + path,
                                     method=method,
                                     data=json.dumps(payload).encode() if payload else None,
                                     headers={'Authorization': 'Bearer ' + key,
                                              'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # API validation errors can echo submitted fields, including secrets.
            raise SystemExit(f'ClickStack webhook request failed: HTTP {error.code}. Check the local UI.') from None
        except urllib.error.URLError:
            raise SystemExit('Cannot reach the local ClickStack webhook API.') from None

    listed = request('GET', '?limit=1000&offset=0')
    destinations = listed['data']
    if args.list:
        print(json.dumps([{'id': x['id'], 'name': x['name'], 'service': x['service']}
                          for x in destinations], indent=2))
        return
    if listed.get('meta', {}).get('total', len(destinations)) > len(destinations):
        raise SystemExit('Destination listing is incomplete; select the existing destination in the UI.')
    existing = next((x for x in destinations
                     if x['name'] == WEBHOOK_NAME and x['service'] == 'slack'), None)
    if existing:
        print(json.dumps({'id': existing['id'], 'name': WEBHOOK_NAME, 'status': 'reused; destination unchanged'}))
        return
    url = env.get('CLICKSTACK_SLACK_WEBHOOK_URL', '')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'hooks.slack.com' or not parsed.path.startswith('/services/'):
        raise SystemExit('Set a valid Slack incoming-webhook URL privately as CLICKSTACK_SLACK_WEBHOOK_URL in .env.mcp.')
    result = request('POST', '', {'name': WEBHOOK_NAME, 'service': 'slack', 'url': url,
                                 'description': 'Presenter demo alert destination'})['data']
    # Return only the identity used by MCP; never print the webhook response or URL.
    print(json.dumps({'id': result['id'], 'name': WEBHOOK_NAME, 'status': 'registered; no test message sent'}))


if __name__ == '__main__':
    main()
