# Review artifact schema

```json
{"schema_version":"1.0","branch":"feature/example","source_sha":"verified SHA","source":"local-review","issues":[{"id":"R1","file":"src/example.py","line":12,"severity":"high","category":"correctness","description":"trigger and wrong outcome","recommendation":"specific fix"}],"walkthrough":[]}
```

issue_count is derived from issues, never trusted independently. A skipped-issues artifact uses the same schema_version, branch, and source_sha plus ignored_issues containing location, description, and reason. If schema/source mismatches, preserve the original and report that it is unusable; do not delete it or silently treat its findings as resolved.
