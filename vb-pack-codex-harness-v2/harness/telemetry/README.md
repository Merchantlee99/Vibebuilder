# Harness Telemetry

Append-only telemetry belongs here.

Do not store telemetry under `.codex`; `.codex` is reserved for Codex control-plane configuration.

Runtime files are intentionally gitignored:

- `events.jsonl`
- `learnings.jsonl`
- `events.manifest.json`
- `segments/*.jsonl`
- `*.lock`

Use `python3 scripts/harness/event_log.py verify` to validate the hash chain and segment manifest. Use `python3 scripts/harness/event_log.py rotate --max-bytes 1048576` to archive the active event log into `segments/` while keeping the chain continuous.
