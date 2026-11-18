# ClickStack observability demo

Investigate a subscription application's failure using ClickStack logs, traces and metrics; repeat the investigation with Codex over MCP; then inspect that investigator's content in Langfuse and native timing in ClickStack. The demo illustrates how retained context and wide events help troubleshooting, and why efficient analytical storage matters for full-fidelity observability. It uses the subscription form, not Astronomy Shop.

```text
Browser → subscription-app → docs-loader
                  │               │
               Postgres     application telemetry
                                  ↓
              ClickStack: ingestion → ClickHouse → UI/API
                                  ↑
Docker → socat → infrastructure collector / native event forwarder

Codex ── MCP ───────────────────────────────→ ClickStack
   ├── native timing → investigator collector → ClickStack
   └── demo-only official Stop hook ─────────→ Langfuse Cloud
```

This is an experimental demo, not a certified release. Build recipes target Linux ARM64/AMD64; runtime checks have been performed on macOS ARM64 with OrbStack. Independent clean-checkout and native AMD64 runtime checks remain pending. Docker is required; OrbStack is optional. See [publication scope](PUBLICATION.md).

## Requirements

- macOS or Linux, Docker running Linux containers, and Compose 2.24.4+ (`!override` support).
- Python 3.11+, Git, a browser and internet for initial downloads. Host helpers use Python's standard library.
- For the AI segment: Node 22+, Codex CLI with login/model access, and a Langfuse Cloud project. Tested: Codex 0.167.0, Node 24.14.1, official Langfuse plugin 0.4.3.
- Free default ports: app 8000, docs 8001, UI 8080, SQL 8123, OTLP 4317/4318; separate investigator health/OTLP 14333/14318. Configure alternatives before starting if another stack uses these ports.

The demo mounts the Docker socket through a local proxy for infrastructure observation. Run it on a development host with synthetic data. There is no certified universal RAM/disk minimum. Internet is needed for hosted Codex and Langfuse; this is not a fully offline agent.

## Set up

Clone the repository and run commands from its root. Keep any existing demo running elsewhere on separate project names, container prefixes and ports.

```sh
git clone https://github.com/sherry-ger/clickstack-observability-demo.git
cd clickstack-observability-demo
```

```sh
python3 scripts/configure_local.py
python3 scripts/build_images.py
sh scripts/stack.sh bootstrap
```

The build helper clones the public upstream at the revision in [config/build.lock.json](config/build.lock.json), applies the included patches in a temporary build tree, and generates this Docker daemon's image references under ignored `.runtime/`. Do not copy another machine's generated image IDs.

Open **http://localhost:8080** and create a local ClickStack account. In **Team Settings → API & Agents**, copy:

- **Ingestion API key:** lets the application/collectors send telemetry.
- **Personal API access key:** lets the investigator use API/MCP tools.

Save both at hidden terminal prompts, then start the core stack:

```sh
python3 scripts/configure_local.py --keys
python3 scripts/check_prerequisites.py --core
sh scripts/stack.sh up -d --no-build --wait --wait-timeout 180
python3 scripts/check_readiness.py
```

Expected readiness: seven healthy services; app/root/UI HTTP 200; authenticated SQL `1`; unauthenticated SQL HTTP 401; published ports loopback-only; automatic traffic generator off. Prerequisites alone do not verify authentication or ingestion.

Private `.env` and `.env.mcp` are generated locally and ignored by Git. Initialization refuses to overwrite existing files; use `--keys` only when intentionally updating the API keys. Never paste credentials into chat or commit resolved secret-bearing Compose output.

## Check normal behavior

1. Open **http://localhost:8000/#subscribe** and submit synthetic input. **Thank you for subscribing!** is the expected completion state. Leave **Docs** untouched until preparing the incident.
2. In ClickStack Traces, select a recent window and filter `ServiceName='subscription-backend' AND SpanName='POST /api/subscribe'`. Find the request and inspect HTTP status 200. `StatusCode=Unset` alone does not mean failure or success.
3. Open Trace Logs, or search Logs by the observed TraceId and the same time. Verify a correlated access record; it may have no container ID.
4. In Metrics, inspect `container.memory.percent`, grouped by `ResourceAttributes['container.id']`. Verify the intended docs-loader's name/prefix. Host metrics can contain other stacks. Sampling can miss brief peaks.

## Prepare one incident privately

This deliberately causes a docs-loader memory failure and verifies automatic recovery. It is not a readiness command. Keep its output/manifest off screen until after the investigation:

```sh
incident_dir=".runtime/incident-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/run_incident.py "$incident_dir"
```

Require exit 0 and `checks_passed=true` in the private `run.json`: HTTP 500, native OOM/die-137/start retrieved in ClickStack, exactly one healthy restart of the same container, docs health 200 and three normal subscription requests returning 200. No manual kill is needed. A SIGKILL or exit 137 alone does not establish OOM.

Give the investigator only `GET /load-docs`, the absolute UTC window (include 30 seconds around the captured window for sampled metrics) and deployment prefix. Withhold trace/container IDs and cause. Follow [the investigation guide](docs/investigation.md): symptom → dependency → metric-derived identity → resource logs. Clear TraceId for the resource pivot because daemon events have no application TraceId.

If only final readback failed after a completed capture/recovery, fix that issue and use `python3 scripts/run_incident.py "$incident_dir" --verify-existing`. It reads the saved run without triggering another request. It cannot repair a failed trigger/recovery.

## Add Codex and Langfuse

Follow [Codex/Langfuse setup](docs/codex-langfuse.md), then [the bounded investigation](docs/investigation.md). Content capture is opt-in for a fresh demo conversation. Ordinary capture stays disabled; do not resume unrelated conversations.

The live segment investigates read-only. Prepare dashboard/search artifacts offstage using [the authoring prompt](config/mcp/dashboard/create.prompt.txt). There are no preconfigured alerts or Slack destinations. Saving an alert can start evaluation and send notifications; treat that as a separate explicit action.

## Stop or recover

```sh
sh config/tracing/stack stop
sh scripts/stack.sh stop
```

Restart with the corresponding `up -d --no-build --wait` commands and run readiness. These commands preserve volumes/accounts/data. Never use `down -v`, global prune or blanket deletion for routine recovery. See [troubleshooting](docs/troubleshooting.md).

## Contents and provenance

- [Demo flow](docs/demo-flow.md): screen preparation and a deck-independent story.
- [Saved example results](docs/saved-results.md): Markdown fallback, with no private account links.
- [Copy manifest](COPY_MANIFEST.json): exact copied runtime/configuration files and hashes.
- [Upstream license](licenses/upstream-demo-LICENSE): retained from the pinned upstream demo. A license for newly authored files must be chosen before public release.

The private development area retains presenter evidence and future Claude/Cursor work. This repository contains no private deck, staging account, runtime data or raw conversations. Newly authored files have no license grant yet; the included upstream license applies only to the upstream work.
