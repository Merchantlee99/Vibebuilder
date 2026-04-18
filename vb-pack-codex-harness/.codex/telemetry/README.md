# Telemetry Logs

This directory stores append-only runtime logs created by the harness.

- `events.jsonl`: operational event trail.
- `learnings.jsonl`: reusable failure and recovery patterns.
- The log files are created by `bootstrap.py` and are usually gitignored in downstream projects.
