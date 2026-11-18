# Targeted troubleshooting

Start with `python3 scripts/check_prerequisites.py --core` and `python3 scripts/check_readiness.py` from this repository root. Read the failure before changing anything. Prerequisites do not certify authentication/ingestion; readiness does not certify model/plugin/export paths.

| Symptom | Check and targeted response |
|---|---|
| Port occupied | Identify its owner. Change this demo's project name, container prefix and conflicting ports in its private settings before startup, or explicitly stop only your own identified demo service. Never stop unrelated workloads. |
| Images absent | Run `python3 scripts/build_images.py` for this Docker daemon. Do not reuse another machine's content IDs. |
| Initialization refuses to overwrite settings | Expected protection. Use `--keys` only to intentionally save copied API keys. Do not delete working private files to bypass it. |
| UI healthy, telemetry missing | Check source, time and actual signal ingestion independently. Use `--source-catalog` for metadata. Confirm exporter/ingestion credentials privately; UI HTTP 200 does not prove ingestion. |
| MCP points elsewhere | Exit and launch this checkout's wrapper. Confirm endpoint/catalog/account match; do not search another tenant for the incident. |
| Metric multi-select unsupported | Use bounded SQL after schema/kind/unit discovery. Native metric builders have different input shapes and do not inherit this exercise's SQL caps. |
| No HTTP 500 | Select the chosen incident window and correct Traces source. This app uses `SpanAttributes['http.status_code']='500'`. Remove unrelated stale chips. Do not widen to all history. |
| Container logs empty after trace pivot | Clear TraceId, retain the same observed container ID and absolute window. Native resource events have no application TraceId. Confirm the dependency's identity from metrics first. |
| Below-limit memory samples | Sampling may miss a brief peak. Native OOM evidence is decisive; exit 137 alone is insufficient. Do not invent a measured 100% sample. |
| Node works only in another terminal | Activate your own runtime/PATH in the launching terminal. Do not copy a presenter's installation path. |
| No prompt/response in Langfuse | Check fresh dedicated opt-in, Stop-hook review, correct regional host/project and current run tag/execution window. Native OTel timing alone does not include conversation content. Never backfill unrelated conversations. |
| Query hits a scan cap | Inspect schema/sorting keys and narrow relevant predicates within the same window. Keep budgets; do not silently remove caps or widen time. |

## Targeted application recovery

For an application process issue, recover only that service:

```sh
sh scripts/stack.sh stop subscription-app
sh scripts/stack.sh up -d --no-build --no-deps --wait --wait-timeout 60 subscription-app
python3 scripts/check_readiness.py
```

The equivalent targeted recovery was exercised in the original isolated environment and preserved source metadata, recorded telemetry, private files and volume names. This copied directory has not yet had an independent clean-checkout runtime pilot. Restarting the application is not a fix for every database/ingestion issue.

Normal shutdown uses `sh config/tracing/stack stop` then `sh scripts/stack.sh stop`. Preserve named volumes. Never use `down -v` or global prune for routine recovery.

## Fallback and cleanup

Open [saved-results.md](saved-results.md) in an editor or Markdown preview. It needs no hosted model or cloud API. Already-running local UI/SQL may inspect retained telemetry without internet; new hosted-model/Langfuse work needs connectivity. Browser instrumentation has a CDN dependency.

Core delivery creates no live alert. If you separately activated one, identify and disable only the demo-owned evaluator before cleaning up its artifacts. Read back exact names/IDs and destination ownership first. Do not delete shared dashboards, sources or destinations. A saved alert does not prove transport, firing, delivery or resolution.
