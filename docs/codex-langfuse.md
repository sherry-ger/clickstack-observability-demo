# Codex and demo-only Langfuse setup

Run all commands from the repository root. Install Codex CLI using the official distribution if needed. In the same terminal check `node --version`, `npm --version`, `codex --version` and `codex login status`; use `codex login` if necessary. Node must be 22+. A second terminal works when it uses this checkout's launcher and its own valid PATH.

## Connect MCP

Save the local ClickStack personal API access key using the root README setup. The project launcher reads this checkout's UI port and `.env.mcp` key, without editing global MCP configuration:

```sh
sh config/mcp/codex-clickstack -a on-request
```

Trust your project when prompted. Check `/mcp` and the printed local endpoint. The general launcher exposes broader capabilities, including writes; use the narrower tool override in [the investigation guide](investigation.md) for the live exercise.

Prepare a source catalog without native preview scans:

```sh
python3 scripts/configure_local.py --source-catalog
```

This reads authenticated source metadata. Native `list_sources`/`describe_source` and metric builders can sample telemetry outside the bounded SQL protections. Use the supplied catalog and [connection-check prompt](../config/mcp/verify-connection.prompt.txt), replacing its endpoint, recent two-minute window and exact resource name. Never paste API keys into the conversation.

## Install the pinned official content integration

```sh
codex plugin marketplace add ./config/tracing/langfuse-marketplace
codex plugin add tracing@codex-observability-plugin --json
codex plugin list --marketplace codex-observability-plugin --json
```

The included catalog pins the official `@langfuse/codex-observability-plugin` package to 0.4.3. If already installed, inspect its version before changing another project's setup. An untested version needs separate validation.

Installation can enable the plugin at user level. To keep enablement project-only, set only its entry to false in your own `~/.codex/config.toml`, preserving other settings:

```toml
[plugins."tracing@codex-observability-plugin"]
enabled = false
```

This repository's `.codex/config.toml` enables the plugin/hooks for this project; `.codex/langfuse.json` keeps ordinary capture disabled. In `/hooks`, review the expected **Stop** hook: `node "${PLUGIN_ROOT}/dist/index.mjs"`, timeout 30 seconds. Zero PostToolUse hooks is expected. Review your own installed definition; never copy trust state or bypass approval.

## Supply regional keys privately

```sh
python3 scripts/configure_langfuse.py
```

At the hidden prompts enter your Langfuse Cloud origin, public key and secret key. US origin: `https://us.cloud.langfuse.com`; EU origin: `https://cloud.langfuse.com`. Use the project’s actual region, with no `/api` suffix. Values are stored privately in `.env`. They are separate from both ClickStack keys.

Do not set `TRACE_TO_LANGFUSE` globally or save credentials in tracked JSON. Only the dedicated launcher supplies opt-in and keys to its child process.

## Start native timing and a fresh demo session

```sh
sh config/tracing/stack config --quiet
sh config/tracing/stack up -d --no-build --wait --wait-timeout 60
curl --fail http://127.0.0.1:14333/
```

Use the configured health port if changed. This collector has a separate Compose project and joins the selected application network. Native spans go to ClickStack; the official Stop hook sends conversation content directly to Langfuse. Trace IDs differ between exporters.

Start the bounded dedicated session using [investigation.md](investigation.md). Keep it fresh and demo-only; resume/fork is rejected. Record the launcher's run tag and actual execution window. Complete the response, then inspect actual content/export rather than accepting a model answer as proof of delivery. For an interactive rehearsal, a second short message in that same fresh demo session can help inspect the latest completed turn.

## Verify both destinations

In Langfuse, filter environment/tag `kubecon-demo`, then the unique run tag. Open **Codex Turn → Preview → Formatted**, inspect Input/Output, a generation and a tool result. Tool observations may be exec wrappers containing multiple MCP calls.

In local ClickStack Traces, use the investigator execution window, service `codex_exec` and `demo.run_id`. Where populated, `conversation.id` matches the Langfuse session UUID. Do not use the older application-incident window or expect matching trace IDs. Cost and exactly-once delivery are not certified.
