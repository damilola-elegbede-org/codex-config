# Review artifact schema

All review producers use schema_version 1.0 with uppercase severity and suggestion. Native pre-publish review uses the same artifact; no separate Claude or CLI-specific producer is required.

```json
{"schema_version":"1.0","branch":"feature/example","source_sha":"verified SHA","created_at":"2026-10-03T00:00:00Z","source":"code-reviewer","summary":"Brief overall assessment","issues":[{"id":"R1","file":"src/example.py","line":12,"severity":"HIGH","type":"bugs","description":"trigger and wrong outcome","suggestion":"specific fix"}],"walkthrough":[]}
```

Required issue fields: id, file, line (integer or null), severity
(LOW/MEDIUM/HIGH/CRITICAL), type, description, suggestion. Type is one of
security, bugs, performance, best-practices, code-quality, accessibility.
issue_count is derived from issues, never trusted independently.

Single-pass source is code-reviewer. Independent deep passes use code-reviewer,
security-reviewer, and a11y-reviewer in their separate artifacts. All include the
verified source_sha, branch, created_at, summary, issues, and walkthrough.

After all three deep outputs are validated, write the combined review-local.json
with source=deep-review and sources listing the three producer labels. Qualify
issue IDs with the producer label, retain each issue's source and original_id,
and add source to each walkthrough entry. Preserve differing judgments instead
of silently deleting them. Missing/invalid input, branch mismatch, or source_sha
mismatch makes aggregation incomplete; never publish a clean empty review.

A skipped-issues artifact uses the same schema_version, branch, and source_sha
plus ignored_issues containing location, description, and reason. If schema or
source mismatches, preserve the original and report that it is unusable; do not
delete it or silently treat its findings as resolved.

For pre-publish reuse, also record base_sha (the verified merge-base) and a
content_fingerprint covering the tracked diff and task-owned new files as
described in ../../review/references/pre-publish.md. The fingerprint supplements
source_sha; a matching HEAD does not prove unchanged worktree content. Preserve
the review's original source_sha when committing identical reviewed content,
and record the verified published_sha separately. Never rewrite the reviewer’s
findings to imply that changed content was reviewed.
