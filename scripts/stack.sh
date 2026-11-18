#!/bin/sh
# Resolve from the wrapper, so checkout paths with spaces work from any directory.
set -eu
project_root=$(CDPATH= cd -P "$(dirname "$0")/.." && pwd)
command -v docker >/dev/null 2>&1 || { echo 'Docker is required on PATH.' >&2; exit 1; }
cd "$project_root"
# First-run account setup precedes obtaining an ingestion key. This placeholder
# only satisfies interpolation for services that bootstrap does not start.
if [ "${1:-}" = "bootstrap" ]; then
    shift
    [ "$#" -eq 0 ] || { echo 'Usage: sh scripts/stack.sh bootstrap' >&2; exit 1; }
    export HYPERDX_API_KEY=bootstrap-only-not-an-ingestion-key
    set -- up -d --no-build --wait --wait-timeout 180 clickstack
fi
if [ -f "$project_root/.runtime/images.env" ]; then
    exec docker compose --env-file "$project_root/.env" --env-file "$project_root/.runtime/images.env" -f "$project_root/demo/docker-compose.all-in-one.yml" -f "$project_root/config/compose.local.yml" "$@"
fi
exec docker compose --env-file "$project_root/.env" -f "$project_root/demo/docker-compose.all-in-one.yml" -f "$project_root/config/compose.local.yml" "$@"
