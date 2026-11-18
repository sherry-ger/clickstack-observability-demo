"""Read-only trainer preflight: dependencies, private config presence and ports.

This does not start containers, query telemetry, approve hooks or send content.
A pass establishes prerequisites only; use check_readiness.py after stack startup.
"""
import argparse
import json
import platform
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def command_output(arguments):
    """Keep command diagnostics private: a failed check names the operation only."""
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def version_tuple(value):
    match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', value or '')
    return tuple(int(part or 0) for part in match.groups()) if match else None


def configured_keys(path):
    """Inspect template-style KEY=value files without executing them or printing values."""
    if not path.is_file():
        return set()
    keys = set()
    try:
        lines = path.read_text().splitlines()
        for line in lines:
            key, separator, value = line.strip().partition('=')
            if not separator or key.startswith('#'):
                continue
            parts = shlex.split(value, comments=True)
            if len(parts) == 1 and parts[0]:
                keys.add(key)
    except (OSError, ValueError):
        return set()
    return keys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', action='store_true', help='Check app/ClickStack setup without Codex, Node, MCP or Langfuse')
    args = parser.parse_args()
    checks = []

    def record(name, passed, detail):
        checks.append({'check': name, 'passed': passed, 'detail': detail})

    record('host_os', platform.system() in {'Darwin', 'Linux'}, platform.system() + '; supported targets: macOS/Linux')
    record('host_architecture', platform.machine().lower() in {'arm64', 'aarch64', 'amd64', 'x86_64'},
           platform.machine() + '; supported targets: ARM64/AMD64')
    record('python', sys.version_info >= (3, 11), platform.python_version() + '; require 3.11+')
    tools = [('git', None)] if args.core else [('git', None), ('node', (22, 0, 0)), ('codex', (0, 143, 0))]
    for executable, minimum in tools:
        if not shutil.which(executable):
            record(executable, False, executable + ' is missing from PATH; install/enable it in this terminal')
            continue
        output = command_output([executable, '--version'])
        version = version_tuple(output)
        passed = version is not None and (minimum is None or version >= minimum)
        # Display only the parsed version, never arbitrary command output.
        detail = '.'.join(map(str, version)) if version else 'version check failed'
        if minimum:
            detail += '; require ' + '.'.join(map(str, minimum)) + '+'
        record(executable, passed, detail)

    docker_ready = False
    if not shutil.which('docker'):
        record('docker', False, 'Docker CLI is missing from PATH')
    else:
        output = command_output(['docker', 'version', '--format', '{{.Server.Version}} {{.Server.Os}} {{.Server.Arch}}'])
        fields = (output or '').split()
        docker_ready = len(fields) == 3 and fields[1] == 'linux' and fields[2].lower() in {'arm64', 'aarch64', 'amd64', 'x86_64'}
        record('docker', docker_ready, output if docker_ready else 'Supported Linux ARM64/AMD64 Docker engine is unavailable; check Docker/context')
        compose = command_output(['docker', 'compose', 'version', '--short'])
        version = version_tuple(compose)
        record('compose', version is not None and version >= (2, 24, 4),
               ('.'.join(map(str, version)) if version else 'version check failed') + '; require 2.24.4+ for !override')

    required_files = {
        '.env': {'HYPERDX_API_KEY', 'POSTGRES_PASSWORD', 'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT',
                 'CLICKHOUSE_USER', 'CLICKHOUSE_PASSWORD', 'CLICKHOUSE_DATABASE',
                 'LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY'},
        '.env.mcp': {'CLICKSTACK_MCP_API_KEY'},
    }
    if args.core:
        required_files['.env'] -= {'LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY'}
        del required_files['.env.mcp']
    for name, required in required_files.items():
        missing = sorted(required - configured_keys(ROOT / name))
        record(name, not missing, 'required nonempty settings present; values/authentication not tested' if not missing
               else 'missing/unreadable file or missing settings: ' + ', '.join(missing))
    record('demo_source', (ROOT / 'demo/docker-compose.all-in-one.yml').is_file(),
           'upstream Compose file present' if (ROOT / 'demo/docker-compose.all-in-one.yml').is_file()
           else 'obtain the pinned upstream demo checkout before stack validation')

    local = {}
    if (ROOT / '.env').is_file():
        for line in (ROOT / '.env').read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and not key.startswith('#'):
                local[key.strip()] = value.strip()

    # Existing demo ports are legitimate during rehearsal. Unknown ownership fails
    # rather than asking the trainer to kill an unrelated container or host app.
    demo_ports = set()
    ownership_known = docker_ready
    if docker_ready:
        for project in (local.get('COMPOSE_PROJECT_NAME') or 'kubecon-training',
                        local.get('KUBECON_INVESTIGATOR_PROJECT') or 'kubecon-investigator'):
            ports = command_output(['docker', 'ps', '--filter', 'label=com.docker.compose.project=' + project,
                                    '--format', '{{.Ports}}'])
            if ports is None:
                ownership_known = False
                break
            # Docker may collapse adjacent published ports into 4317-4318.
            for start, end in re.findall(r'127\.0\.0\.1:(\d+)(?:-(\d+))?->', ports):
                demo_ports.update(range(int(start), int(end or start) + 1))
    port_settings = {'KUBECON_APP_PORT': 8000, 'KUBECON_DOCS_PORT': 8001, 'KUBECON_UI_PORT': 8080,
                     'CLICKHOUSE_PORT': 8123, 'KUBECON_OTLP_GRPC_PORT': 4317, 'KUBECON_OTLP_HTTP_PORT': 4318}
    ports = [int(local.get(key) or default) for key, default in port_settings.items()]
    if not args.core:
        ports += [int(local.get('KUBECON_INVESTIGATOR_OTLP_PORT') or 14318),
                  int(local.get('KUBECON_INVESTIGATOR_HEALTH_PORT') or 14333)]
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(('127.0.0.1', port))
            record('port_' + str(port), True, 'available on loopback')
        except OSError:
            owned = ownership_known and port in demo_ports
            record('port_' + str(port), owned,
                   'already bound by this demo; health checked separately' if owned
                   else 'unavailable or ownership unknown; check the listener without stopping unrelated workloads')

    report = {
        'passed': all(check['passed'] for check in checks),
        'mode': 'core' if args.core else 'full',
        'host': {'system': platform.system(), 'architecture': platform.machine(),
                 'checkout_free_gib': round(shutil.disk_usage(ROOT).free / 1024**3, 1)},
        'checks': checks,
        'scope': 'Prerequisites only. No authentication, ingestion, plugin trust, model access, image architecture, or runtime readiness is certified.',
    }
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
