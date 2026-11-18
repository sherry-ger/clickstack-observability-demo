"""Launch project-scoped Codex against this checkout's local ClickStack."""
import os
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
ENABLED_TOOLS = (
    'clickstack_list_sources', 'clickstack_describe_source',
    'clickstack_list_metrics', 'clickstack_describe_metric',
    'clickstack_search', 'clickstack_sql', 'clickstack_table',
    'clickstack_timeseries', 'clickstack_trace_waterfall',
    'clickstack_get_dashboard', 'clickstack_get_dashboard_tile',
    'clickstack_save_dashboard', 'clickstack_patch_dashboard',
    'clickstack_search_dashboards', 'clickstack_query_tile',
    'clickstack_query_tiles', 'clickstack_get_saved_search',
    'clickstack_save_saved_search', 'clickstack_get_webhook',
    'clickstack_save_webhook', 'clickstack_get_alert', 'clickstack_save_alert',
)


def read_settings(path, names):
    values = {}
    if not path.is_file():
        raise SystemExit('Missing ' + path.name + '; follow the private configuration setup first.')
    try:
        for line in path.read_text().splitlines():
            key, separator, value = line.strip().partition('=')
            if separator and key in names:
                parts = shlex.split(value, comments=True)
                values[key] = parts[0] if parts else ''
    except (OSError, ValueError):
        raise SystemExit('Cannot parse ' + path.name + '; check its KEY=value format privately.') from None
    return values


def local_configuration(root=ROOT):
    settings = read_settings(root / '.env', {'KUBECON_UI_PORT', 'KUBECON_CONTAINER_PREFIX'})
    personal = read_settings(root / '.env.mcp', {'CLICKSTACK_MCP_API_KEY'})
    key = personal.get('CLICKSTACK_MCP_API_KEY', '')
    if not key:
        raise SystemExit('Set CLICKSTACK_MCP_API_KEY privately in .env.mcp; use the Personal API access key, not the ingestion key.')
    try:
        port = int(settings.get('KUBECON_UI_PORT') or 8080)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit('KUBECON_UI_PORT must be a valid local TCP port.') from None
    return {'port': port, 'url': f'http://localhost:{port}/api/mcp',
            'container': (settings.get('KUBECON_CONTAINER_PREFIX') or 'kubecon') + '-clickstack',
            'personal_key': key}


def prepare_launch():
    import json
    config = local_configuration()
    if shutil.which('codex') is None:
        raise SystemExit('Codex CLI is required on PATH. Run codex --version in this terminal.')
    env = os.environ.copy()
    # Export only the MCP credential from the private file. Optional Slack URLs
    # and unrelated settings are not needed in the investigator process.
    env['CLICKSTACK_MCP_API_KEY'] = config['personal_key']
    arguments = ['codex', '-c', 'mcp_servers.clickstack_demo.url=' + json.dumps(config['url']),
                 '-c', 'mcp_servers.clickstack_demo.bearer_token_env_var="CLICKSTACK_MCP_API_KEY"',
                 '-c', 'mcp_servers.clickstack_demo.enabled_tools=' + json.dumps(ENABLED_TOOLS),
                 '-c', 'mcp_servers.clickstack_demo.tool_timeout_sec=40']
    return arguments, env, config['url']


def main():
    arguments, env, url = prepare_launch()
    os.chdir(ROOT)
    print('ClickStack MCP: ' + url, flush=True)
    os.execvpe(arguments[0], arguments + sys.argv[1:], env)


if __name__ == '__main__':
    main()
