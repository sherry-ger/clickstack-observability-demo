"""Build pinned source for one Docker platform; never recreate the running demo."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def prepare_source(directory, lock):
    checkout = ROOT / 'demo'
    if not (checkout / '.git').exists():
        if checkout.exists():
            raise SystemExit('demo exists without Git provenance; move it aside explicitly before setup.')
        run(['git', 'clone', '--no-checkout', lock['source']['repository'], str(checkout)])
        run(['git', '-C', str(checkout), 'checkout', '--detach', lock['source']['revision']])
    revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != lock['source']['revision']:
        raise SystemExit('demo HEAD differs from config/build.lock.json. Use a separate checkout of the recorded revision; no files were reset.')
    # Runtime mounts come from the working tree, not the scratch build archive.
    # Reject drift there while allowing the existing deliberate Go source patch.
    for name in ['docker-compose.all-in-one.yml', 'postgresql-db/init.sql',
                 'otel-collector/otel-collector-config.yaml']:
        expected = subprocess.check_output(['git', '-C', str(checkout), 'show', revision + ':' + name])
        if (checkout / name).read_bytes() != expected:
            raise SystemExit('Runtime source differs from the pinned revision: demo/' + name + '. Preserve your edits and use a clean checkout.')
    # Build the recorded commit, ignoring local edits; never patch the trainer's tree.
    archive = directory / 'source.tar'
    run(['git', '-C', str(checkout), 'archive', '--format=tar',
         '--output=' + str(archive), lock['source']['revision']])
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if member.name.startswith('/') or '..' in Path(member.name).parts:
                raise SystemExit('Unsafe source archive path.')
            if member.isdir():
                (directory / member.name).mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target = directory / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as content:
                    target.write_bytes(content.read())
            else:
                raise SystemExit('Unexpected non-file source archive entry.')
    archive.unlink()
    for name in lock['patches']:
        patch = ROOT / name
        run(['git', 'apply', '--check', str(patch)], cwd=directory)
        run(['git', 'apply', str(patch)], cwd=directory)
    config = directory / 'config'
    config.mkdir()
    for name in [entry['dockerfile'] for entry in lock['components'].values()] + [lock['python_dependencies']['path']]:
        shutil.copy2(ROOT / name, config / Path(name).name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=['linux/arm64', 'linux/amd64'],
                        help='Default: the current Docker server architecture.')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'config/build.lock.json').read_text())
    info = json.loads(subprocess.check_output(['docker', 'version', '--format', '{{json .Server}}'], text=True))
    native_platform = info['Os'] + '/' + info['Arch']
    target_platform = args.platform or native_platform
    if target_platform not in lock['platforms']:
        raise SystemExit('Only linux/arm64 and linux/amd64 are supported build targets.')
    architecture = target_platform.split('/')[1]
    recipe_files = ['config/build.lock.json', lock['python_dependencies']['path']] + lock['patches']
    recipe_files += [entry['dockerfile'] for entry in lock['components'].values()]
    hasher = hashlib.sha256()
    for name in sorted(recipe_files):
        hasher.update(name.encode())
        hasher.update((ROOT / name).read_bytes())
    recipe = hasher.hexdigest()
    result = {'source': lock['source'], 'recipe_sha256': recipe,
              'platform': target_platform, 'builder_platform': native_platform,
              'built_at_utc': datetime.now(timezone.utc).isoformat(), 'images': {}}
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='kubecon-image-build-') as scratch:
        context = Path(scratch)
        prepare_source(context, lock)
        for component, entry in lock['components'].items():
            tag = f'kubecon-training/{component}:{recipe[:16]}-{architecture}'
            print(f'Building {component} for {target_platform}', flush=True)
            run(['docker', 'buildx', 'build', '--platform', target_platform, '--load',
                 '--provenance=false', '--tag', tag, '--file', str(context / entry['dockerfile']),
                 '--label', 'org.opencontainers.image.revision=' + lock['source']['revision'],
                 '--label', 'io.clickhouse.training.recipe=' + recipe, str(context)])
            inspected = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], text=True))[0]
            actual = inspected['Os'] + '/' + inspected['Architecture']
            if actual != target_platform:
                raise SystemExit('Built image architecture differs from requested platform.')
            result['images'][component] = {'tag': tag, 'id': inspected['Id'], 'platform': actual,
                                            'env': entry['env']}
    manifest = runtime / f'images-{architecture}.json'
    manifest.write_text(json.dumps(result, indent=2) + '\n')
    # Generated dotenv holds only validated local content IDs, never credentials.
    assignments = ['KUBECON_IMAGE_PLATFORM=' + target_platform]
    assignments += [entry['env'] + '=' + entry['id'] for entry in result['images'].values()]
    values = '\n'.join(assignments) + '\n'
    (runtime / f'images-{architecture}.env').write_text(values)
    if target_platform == native_platform:
        (runtime / 'images.env').write_text(values)
        print('Selected native images in .runtime/images.env; running containers were not changed.')
    else:
        print('Cross-platform build recorded only; native image selection was preserved.')
    print('Provenance: ' + str(manifest.relative_to(ROOT)))


if __name__ == '__main__':
    try:
        main()
    except FileNotFoundError as error:
        raise SystemExit('Required build tool or source file is missing: ' + str(error.filename)) from None
    except subprocess.CalledProcessError as error:
        # Docker/Git already emit the real diagnostic; avoid a second traceback.
        print('Image preparation failed. Review the tool error above; running containers and native selection were not changed.', file=sys.stderr)
        raise SystemExit(error.returncode) from None
