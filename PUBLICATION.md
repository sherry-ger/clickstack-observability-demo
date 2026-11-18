# Publication staging

This repository is an explicitly selected standalone public copy of the demo, published as an experimental project at https://github.com/sherry-ger/clickstack-observability-demo. It has its own Git history, separate from the larger private development workspace. Never stage/push the parent workspace.

Included: pinned build recipes, runtime helpers, empty credential templates, project-scoped Codex/Langfuse configuration, bounded prompts and public-facing Markdown instructions. Runtime files are unchanged copies; COPY_MANIFEST.json records their hashes. Documentation is adapted to remove presenter accounts, private deck/staging links and historical identifiers.

Excluded: `.env`, `.env.mcp`, `.runtime`, existing Docker data, generated image IDs, upstream working checkout, private/raw evidence, conversations, screenshots, slide exports, presenter script/plan/spec history, legacy hardcoded dashboards/alerts and Slack destinations. The build fetches the pinned public upstream source instead.

Remaining certification checks: independent clean-checkout pilot and native AMD64 runtime; full presenter rehearsal. A license for newly authored code/docs has not been selected, and no license grant for those files is implied by publication. The upstream Apache license is preserved under licenses/ and applies to that upstream work; it does not assign a license to newly authored files.

Codex is the supported client. Claude/Cursor work remains in the original private development area until separately implemented/tested. Publication includes only this selected tree; it is not a certified release.

## Copy checks

- 37 copied runtime/configuration files match their source hashes; 47 files total including adapted docs and provenance.
- Python 3.11 syntax, shell syntax, JSON parsing and all 17 local Markdown links passed.
- Compared known private credential values against every selected file: no matches. No private settings, runtime trees, symlinks or Git history were included.
- Initialized a throwaway copy in a path with spaces; private settings were created with mode 0600. Core and investigator Compose configuration parsed using pinned upstream fixture files and disposable placeholder values.
- The original staging checks started no containers, image builds, incidents, model calls or cloud uploads. The selected files were subsequently committed and published with the owner's authorization. Configuration checks do not establish clean-checkout runtime readiness.
