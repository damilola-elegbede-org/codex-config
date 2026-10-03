# File mode

Read the requested review JSON under .tmp/. Validate schema_version 1.0, branch, current source/diff, issue IDs, severity, locations, and descriptions before acting. Missing, stale, or malformed output is not a clean review.

Use triage.md, apply authorized fixes, and run appropriate checks. Commit only if included in scope; file mode does not create a PR, push, or send review replies without authorization. Preserve skipped findings with reasons and report actual changed files and results.
