# Presenter flow

Prepare privately: core readiness, a normal request, one verified incident, source metadata, a fresh demo-only investigator and completed dashboard/search artifacts. Keep keys, manifests, instructor answers and cause-labeled dashboards off screen until the evidence is established. Use your own presentation; this package includes no private deck.

| Segment | Minutes | Starting screen and success check |
|---|---:|---|
| Context and full fidelity | 12 | Slides: retained detail and wide events preserve debugging context. |
| Collection and architecture | 18 | Slides; optionally show checked-in upstream collector configuration with variable references, never resolved secrets. |
| UI orientation | 10 | Normal subscription trace; inspect HTTP outcome, waterfall and correlated log. Thank-you is expected. |
| Manual investigation | 30 | Traces on the chosen incident window; failed request → dependency → metrics/resource identity → resource logs. Clear TraceId before reading native lifecycle records. |
| Why ClickHouse | 20 | Connect evidence to efficient analytical queries, compression and practical retention. Treat external benchmark numbers as workload-specific, never demo guarantees. |
| Break | 10 | Return to the agent-investigation story. |
| MCP investigation and review | 40 | Fresh bounded Codex session; operation/window/prefix only. Challenge the evidence, then show prepared artifacts. Keep alerts separate. |
| Observe the investigator | 15 | Langfuse content and native ClickStack timing for the same new run, using its execution window/run tag/conversation UUID. |
| Operating choices | 10 | Explain what each deployment model requires the team to operate. |
| Recap, Q&A and close | 15 | Reserve 10 minutes for Q&A. |

Total: **180 minutes allocated**, not a measured full rehearsal. No staging module is required or configured in this public copy. Claude/Cursor are not implemented here.

Before leaving slides, state the investigation question. After each demo, return to the relevant explanation: three signal roles after UI orientation, cause/impact after manual investigation, evidence review after MCP, and operating choices after observing the investigator. Rehearse the actual window changes with your own deck.

Questions to practice: Why are error spans not request counts? Why do daemon events lack TraceId? Can sampled memory miss OOM? Does Unset prove success? Does LIMIT bound scanning? Does an exposed save tool authorize a write? Why do Langfuse and native trace IDs differ?
