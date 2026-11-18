"""Create private local settings or save ClickStack keys using hidden prompts."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import urllib.request

from launch_mcp import local_configuration

ROOT = Path(__file__).resolve().parent.parent


def write_setting(path, key, value):
    # Keys are pasted privately, never passed as CLI arguments or printed.
    if not value or not re.fullmatch(r'[A-Za-z0-9_./:+=-]+', value):
        raise SystemExit('Paste only the API key, without spaces, quotes or newlines.')
    lines = path.read_text().splitlines()
    replacement = key + '=' + value
    matches = [index for index, line in enumerate(lines) if line.startswith(key + '=')]
    if len(matches) != 1:
        raise SystemExit('Expected exactly one ' + key + ' setting in ' + path.name)
    lines[matches[0]] = replacement
    path.chmod(0o600)
    path.write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keys', action='store_true', help='Privately save ingestion and personal MCP keys')
    parser.add_argument('--source-catalog', action='store_true',
                        help='Read source metadata without native MCP metric-name preview queries')
    args = parser.parse_args()
    if args.source_catalog:
        config = local_configuration()
        # The UI proxies /api to the API service; this v2 route is Mongo metadata
        # only, unlike MCP list_sources which also samples metric names.
        url = f"http://localhost:{config['port']}/api/api/v2/sources"
        request = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + config['personal_key']})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = json.load(response)
        fields = {'id', 'name', 'kind', 'connection', 'from', 'metricTables',
                  'timestampValueExpression'}
        catalog = [{key: value for key, value in source.items() if key in fields}
                   for source in raw['data']]
        print(json.dumps({'endpoint': url, 'sources': catalog}, indent=2))
        return
    if args.keys:
        if not (ROOT / '.env').is_file() or not (ROOT / '.env.mcp').is_file():
            raise SystemExit('Run python3 scripts/configure_local.py first.')
        ui_port = next((line.split('=', 1)[1].strip() for line in (ROOT / '.env').read_text().splitlines()
                        if line.startswith('KUBECON_UI_PORT=')), '8080') or '8080'
        print('Open http://localhost:' + ui_port + ' → Team Settings → API & Agents.')
        print('First: Ingestion API key sends app/collector telemetry into this ClickStack.')
        print('Second: Personal API access key authorizes API/MCP access for the investigator.')
        ingestion = getpass.getpass('ClickStack Ingestion API key (hidden): ').strip()
        personal = getpass.getpass('ClickStack Personal API access key (hidden): ').strip()
        write_setting(ROOT / '.env', 'HYPERDX_API_KEY', ingestion)
        write_setting(ROOT / '.env.mcp', 'CLICKSTACK_MCP_API_KEY', personal)
        print('Saved both keys privately. No service was started or notification sent.')
        return
    targets = [('.env.example', '.env'), ('config/mcp/env.mcp.example', '.env.mcp')]
    if any((ROOT / target).exists() for _, target in targets):
        raise SystemExit('Private settings already exist; initialization will not overwrite them. To save copied API keys, rerun the same helper command with --keys.')
    previous_mask = os.umask(0o077)
    try:
        for template, target in targets:
            content = (ROOT / template).read_text()
            if target == '.env':
                content = content.replace('POSTGRES_PASSWORD=replace-with-random-local-password',
                                          'POSTGRES_PASSWORD=' + secrets.token_hex(24))
                content = content.replace('CLICKHOUSE_PASSWORD=replace-with-random-local-password',
                                          'CLICKHOUSE_PASSWORD=' + secrets.token_hex(24))
            with (ROOT / target).open('x') as output:
                output.write(content)
    finally:
        os.umask(previous_mask)
    print('Created .env and .env.mcp with private permissions and generated local database passwords.')
    print('Next: build images, bootstrap ClickStack, create its local account, then run this helper with --keys.')


if __name__ == '__main__':
    main()
