# File mode

Read the requested review JSON under .tmp/. Validate schema_version 1.0, branch, current source/diff, issue IDs, severity, locations, and descriptions before acting. Missing, stale, or malformed output is not a clean review.

Use triage.md, apply authorized fixes, and run appropriate checks. Commit only if included in scope; file mode does not create a PR, push, or send review replies without authorization. Preserve skipped findings with reasons across review rounds and report actual changed files and results. When committing, reconcile the repair list with tracked diffs and the task-owned untracked files that triage actually created. Never stage other untracked files merely because they are present.
