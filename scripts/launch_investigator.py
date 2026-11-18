"""Launch a fresh, explicitly opted-in demo conversation; leave ordinary Codex off."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def prepare_launch():
    env = os.environ.copy()
    wanted = {'LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY',
              'KUBECON_INVESTIGATOR_OTLP_PORT'}
    settings = {}
    for line in (ROOT / '.env').read_text().splitlines():
        key, sep, value = line.strip().partition('=')
        if sep and key in wanted:
            parts = shlex.split(value, comments=True)
            settings[key] = parts[0] if parts else ''
    if not all(settings.get(key) for key in ('LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY')):
        raise SystemExit('Set the three canonical Langfuse values privately in .env first.')
    collector_port = settings.get('KUBECON_INVESTIGATOR_OTLP_PORT') or '14318'
    if not collector_port.isdigit() or not 1 <= int(collector_port) <= 65535:
        raise SystemExit('KUBECON_INVESTIGATOR_OTLP_PORT must be a valid local port number.')
    # GUI/terminal shells may have different PATHs. Require the launching shell's
    # runtime rather than guessing a trainer-specific Node installation directory.
    node = shutil.which('node')
    if node is None:
        raise SystemExit('Node.js 22+ is required on PATH. Run node --version in this terminal, then retry.')
    try:
        node_version = subprocess.check_output([node, '--version'], text=True, timeout=10).strip()
        node_major = int(node_version.lstrip('v').split('.')[0])
    except (subprocess.SubprocessError, ValueError, OSError):
        raise SystemExit('Could not verify Node.js. Run node --version in this terminal, then retry.') from None
    if node_major < 22:
        raise SystemExit('Node.js 22+ is required on PATH for the Langfuse plugin.')
    if shutil.which('codex') is None:
        raise SystemExit('Codex CLI is required on PATH. Run codex --version in this terminal, then retry.')
    run_id = 'kubecon-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid())
    env.update({
        'TRACE_TO_LANGFUSE': 'true',
        'LANGFUSE_CODEX_PUBLIC_KEY': settings['LANGFUSE_PUBLIC_KEY'],
        'LANGFUSE_CODEX_SECRET_KEY': settings['LANGFUSE_SECRET_KEY'],
        'LANGFUSE_CODEX_BASE_URL': settings['LANGFUSE_HOST'].rstrip('/'),
        'LANGFUSE_CODEX_ENVIRONMENT': 'kubecon-demo',
        'LANGFUSE_CODEX_TAGS': json.dumps(['kubecon-demo', 'demo-content', run_id]),
        'LANGFUSE_CODEX_METADATA': json.dumps({'demo_run_id': run_id, 'capture_route': 'official-codex-plugin'}),
        'LANGFUSE_CODEX_TRACE_SEED': run_id,
        'LANGFUSE_CODEX_USER_ID': 'kubecon-demo-presenter',
    })
    args = ['sh', str(ROOT / 'config/mcp/codex-clickstack'),
            '-c', 'features.hooks=true',
            '-c', 'plugins.tracing@codex-observability-plugin.enabled=true',
            '-c', 'otel.exporter="none"', '-c', 'otel.metrics_exporter="none"',
            '-c', 'otel.trace_exporter={otlp-http={endpoint="http://127.0.0.1:' + collector_port + '/v1/traces",protocol="json"}}',
            '-c', 'otel.environment="kubecon-investigator"',
            '-c', 'otel.log_user_prompt=false',
            '-c', 'otel.span_attributes=' + json.dumps({'demo.run_id': run_id}).replace(':', '=')]
    # Deterministic first-turn trace ID follows the official plugin's trace_seed.
    trace_id = hashlib.sha256((run_id + ':1').encode()).hexdigest()[:32]
    return args, env, {'run_id': run_id, 'first_turn_trace_id': trace_id,
                       'langfuse_environment': 'kubecon-demo', 'tag': 'kubecon-demo'}


def main():
    # Resuming an arbitrary older thread would let the hook upload its old turns.
    # The demo command deliberately starts a fresh conversation instead.
    if any(arg in {'resume', 'fork'} for arg in sys.argv[1:]):
        raise SystemExit('Start a fresh demo session; this launcher does not resume or fork earlier conversations.')
    args, env, identity = prepare_launch()
    print('Investigator run ID: ' + identity['run_id'], flush=True)
    print('Langfuse filter: environment=kubecon-demo, tag=kubecon-demo', flush=True)
    print('First Langfuse trace ID: ' + identity['first_turn_trace_id'], flush=True)
    print('Conversation capture is ON for this fresh demo session only.', flush=True)
    os.chdir(ROOT)
    os.execvpe(args[0], args + sys.argv[1:], env)


if __name__ == '__main__':
    main()
