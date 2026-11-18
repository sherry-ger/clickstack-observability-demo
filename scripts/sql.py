"""Run a local demo SQL file with credentials kept out of output and shell history."""
import argparse
import base64
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--param', action='append', default=[], metavar='NAME=VALUE')
    args = parser.parse_args()
    env = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
               if line and not line.startswith('#') and '=' in line)
    # These are request-level limits, not a production role/permissions boundary.
    settings = {'database': env['CLICKHOUSE_DATABASE'], 'default_format': 'JSON',
                'max_execution_time': '10', 'timeout_before_checking_execution_speed': '0',
                'max_rows_to_read': '1000000', 'max_bytes_to_read': '100000000',
                'max_memory_usage': '268435456', 'max_result_rows': '1000',
                'result_overflow_mode': 'throw', 'readonly': '1'}
    for item in args.param:
        name, value = item.split('=', 1)
        settings['param_' + name] = value
    credentials = base64.b64encode((env['CLICKHOUSE_USER'] + ':' + env['CLICKHOUSE_PASSWORD']).encode()).decode()
    url = f"http://{env['CLICKHOUSE_HOST']}:{env['CLICKHOUSE_PORT']}/?" + urllib.parse.urlencode(settings)
    request = urllib.request.Request(url, data=args.file.read_bytes(),
                                    headers={'Authorization': 'Basic ' + credentials})
    with urllib.request.urlopen(request, timeout=15) as response:
        sys.stdout.write(response.read().decode())


if __name__ == '__main__':
    main()
