# PR mode

Resolve repository/PR/head SHA and retrieve all unresolved threads, including human and bot authors. Fetch pagination or explicit completeness information: an empty/failed/truncated response does not establish a completed review.

Validate findings with triage.md, apply authorized fixes, run checks, commit and publish through the authorized interface. Reply with commit and evidence after the remote head contains the fix. Resolve eligible bot threads using the available API; leave human threads open unless explicitly authorized to resolve them. Do not rely on an undocumented bot magic comment.

Re-fetch and verify threads acted on, report other unresolved threads and asynchronous review status, and stop after bounded retries if publishing or resolution fails. A local-only fix is not a resolved remote finding.
