# Investigator exercises

The default live demo investigates only. Dashboard/search authoring is offstage; alert activation is a separate opt-in extension. Use a fresh run and your own environment metadata.

## 1. Select the environment and bootstrap source metadata

Run every command from the repository root. From the selected checkout root (normal default UI: **http://localhost:8080**):

```sh
python3 scripts/configure_local.py --source-catalog
```

This authenticated metadata-only route prints source/connection/table mappings without secrets or ClickHouse preview scans. Paste that JSON after the investigation prompt. Source IDs are setup metadata; request/resource IDs and diagnosis are withheld.

Do not substitute native `list_sources` or `describe_source` for this bounded exercise: these tools also sample telemetry without our scan/memory protections. Native metric discovery/builders likewise remain outside the protected route. Use capped native MCP SQL for discovery and metric values.  This does not change or universally harden the server.

## 2. Start a fresh demo-only investigator

Use the selected checkout's launcher, from that checkout root:

```sh
sh config/tracing/codex-investigator -a on-request \
  -c 'mcp_servers.clickstack_demo.enabled_tools=["clickstack_sql","clickstack_get_dashboard","clickstack_get_dashboard_tile","clickstack_query_tile","clickstack_get_saved_search"]'
```

The collector must already be healthy. The allowlist excludes preview/builders and all artifact/alert/webhook writes for live delivery. Check `/mcp`. Keep the conversation fresh and demo-only; do not resume unrelated work. Record its run tag and execution time for Langfuse/native correlation.

## 3. Paste the investigation-only prompt, then the source catalog

Prepare a fresh incident privately using [incident preparation](../README.md#prepare-one-incident-privately). Replace all three placeholders below with that run’s absolute UTC window and known deployment prefix (normal default: kubecon-). Do not supply trace/container IDs or cause. Never reuse identifiers or times from someone else’s run.

```text
Investigate failed GET /load-docs requests between <UTC_START> and <UTC_END> in the intended local clickstack_demo connection. Deployment container-name prefix: <DEPLOYMENT_PREFIX>. Host metrics also include other stacks. Use the source metadata pasted below; it was obtained from this environment's metadata-only REST endpoint.

Use only native clickstack_sql for schema/keys/metric discovery and telemetry. Discover columns, table engines/keys, metric kinds/units before interpreting values. Independently derive request and resource identities. Do not read files, source code, manifests, instructor answers or prepared artifacts to learn them. No other server or environment. Keep this absolute window; do not widen on empty results.

Every statement, including system metadata/getSetting, must select explicit columns, return at most 10 rows with LIMIT<=10, and include SETTINGS max_execution_time=10, timeout_before_checking_execution_speed=0, max_rows_to_read=1000000, max_bytes_to_read=100000000, max_memory_usage=268435456, max_result_rows=10, result_overflow_mode='throw'. Leave native readonly unchanged. Telemetry reads also need time and relevant sort-key/service/resource/metric filters. Do not remove caps on error. These are statement protections, not a hardened role or universal MCP boundary.

Start with the failed SERVER request, follow its dependency and correlated logs, then use metric resource attributes to verify the correct container instance in this deployment. Clear trace linkage for the resource pivot: initially search that instance's logs by ID and time only, without a predetermined producer, action or exit-code filter. Let returned fields identify the event. Cite at least two retrievable decisive records with timestamps/identities. Explain request versus span counting, sampled-memory limitations, absent IDs/child spans and what bounded recovery actually establishes. Do not turn Unset status into proof of success; use observed HTTP codes/explicit error fields.

Read only. Do not create/update dashboards, searches, webhooks, alerts or services; do not trigger incidents or notifications. After independent investigation, prepared artifacts may be read for comparison only if requested. Finish with observed evidence, hypotheses, missing evidence and actual scan/query statistics.

SOURCE METADATA:
<paste this environment's --source-catalog JSON here>
```

## 4. Review and reuse the result

Require a retrievable failed SERVER request, dependency, metric-derived resource identity and native lifecycle records in the same window. One failed request may contain multiple error spans. Exit 137 alone is not OOM evidence; a native OOM event supplies the missing distinction. Sampled memory can miss the peak. Recovery claims must name the actual tested routes/window.

After independent investigation, create a new dashboard/search offstage using [the authoring prompt](../config/mcp/dashboard/create.prompt.txt). Use your own catalog, findings and unique artifact name. Review each save, read it back and execute SQL tiles sequentially. Fixed replay SQL windows must be labeled; saved-search UI builders do not inherit SQL tile caps. Preserve unrelated resources.

Alerts are optional and unsaved by default. Saving can activate evaluation and notify a destination. Registration, transport, firing, delivery and resolution need separate explicit checks. Never paste a Slack webhook into the conversation. This public package includes no preconfigured destinations or historical account IDs.

## 5. Find the same investigator run

Use the dedicated launcher’s new run tag and actual execution window. In Langfuse filter environment/tag `kubecon-demo`, then that run tag. Open Codex Turn → Preview → Formatted to inspect actual Input/Output, a generation and a tool result. A tool observation can be an exec wrapper containing several MCP calls.

In ClickStack use that execution window, `ServiceName='codex_exec'` and `demo.run_id`. Where populated, `conversation.id` matches the Langfuse session UUID. Different exporters have different trace IDs. Do not search agent activity using the older application incident time.
