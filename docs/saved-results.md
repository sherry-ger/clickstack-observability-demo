# Saved example results

**SAVED RESULTS — historical example, not a new live investigation.** This Markdown is a teaching fallback, not a screen recording or public account link. The observations below come from the original local demo; identifiers and private account references are omitted. A fresh run must derive its own evidence.

## Application investigation

A failed `GET /load-docs` SERVER request returned HTTP 500. Its trace identified a docs-loader dependency; metric resource attributes established that instance's container identity. Clearing application TraceId while preserving the same resource/time scope exposed native `oom → die (137) → start` events.

Observed counts: one failed server request, two error spans. Memory samples missed the failure instant. Exit 137 alone would not establish OOM; the native event supplied that evidence.

Later observed requests returned HTTP 200: 28 health checks, three normal subscriptions and one root request. These 32 successes establish bounded route/window recovery, not universal recovery or a successful retry of the allocating route.

## Investigator observation

One explicitly opted-in demo run had actual prompt/response content, generation observations and exec-wrapper tool results in Langfuse. Its native timing was recorded in ClickStack. Run metadata and conversation UUID connected the views; exporter trace IDs differed.

Observed run duration was approximately 152 seconds, with 15 generation and 14 exec observations. These are one run's measurements, not latency/cost guarantees. A wrapper may contain several MCP calls. No raw conversation or hidden reasoning is included here.

## Teaching limit

This summary cannot prove current telemetry retention, authenticate a service or run a new investigation. Use your own fresh evidence for the live exercise. Already-running local UI/SQL may still work during an internet outage; hosted Codex and Langfuse need their services.
