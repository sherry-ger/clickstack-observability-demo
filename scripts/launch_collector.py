"""Run the investigator collector in its own project on the selected app network."""
import os
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    if shutil.which('docker') is None:
        raise SystemExit('Docker is required on PATH.')
    settings = {}
    # Read only deployment metadata here. Compose reads the private env file;
    # the wrapper never sources it or exports Langfuse/database credentials.
    wanted = {'COMPOSE_PROJECT_NAME', 'KUBECON_APP_NETWORK',
              'KUBECON_INVESTIGATOR_PROJECT', 'KUBECON_INVESTIGATOR_CONTAINER'}
    for line in (ROOT / '.env').read_text().splitlines():
        key, separator, value = line.strip().partition('=')
        if separator and key in wanted:
            parts = shlex.split(value, comments=True)
            settings[key] = parts[0] if parts else ''

    def selected(name, default):
        return os.environ.get(name) or settings.get(name) or default

    project = selected('KUBECON_INVESTIGATOR_PROJECT', 'kubecon-investigator')
    # COMPOSE_PROJECT_NAME takes precedence over YAML name. Capture its app
    # value separately so --project-name cannot redirect this external network.
    network = selected('KUBECON_APP_NETWORK', selected('COMPOSE_PROJECT_NAME', 'kubecon-training'))
    child = os.environ.copy()
    child['KUBECON_APP_NETWORK'] = network
    child['KUBECON_INVESTIGATOR_PROJECT'] = project
    child['KUBECON_INVESTIGATOR_CONTAINER'] = selected('KUBECON_INVESTIGATOR_CONTAINER', project + '-collector')
    arguments = ['docker', 'compose', '--project-name', project,
                 '--env-file', str(ROOT / '.env')]
    if (ROOT / '.runtime/images.env').is_file():
        arguments += ['--env-file', str(ROOT / '.runtime/images.env')]
    arguments += ['-f', str(ROOT / 'config/tracing/compose.yml')]
    os.chdir(ROOT)
    os.execvpe(arguments[0], arguments + sys.argv[1:], child)


if __name__ == '__main__':
    main()
