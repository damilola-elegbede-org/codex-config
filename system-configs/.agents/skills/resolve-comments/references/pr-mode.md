# PR mode

Resolve repository, PR, verified base, and head SHA. Retrieve all unresolved threads with human and bot authorship. Fetch pagination or explicit completeness information: an empty, failed, or truncated response does not establish a completed review.

Validate findings with triage.md and repair within authorization. Reconcile tracked changes and task-owned new files against the repair list before committing; preserve unrelated work. For commit messages derived from thread locations, replace control characters with spaces and bound each location to 200 characters. Write the message through a structured tool argument or a temporary body file, never by interpolating reviewer text or filenames into shell code.

Before publishing repairs, follow ../../review/references/pre-publish.md against the PR’s actual base. Recheck affected gates after any repair, and verify all intended fixes are committed. If a prior run left unpublished fix commits, inspect those commits and publish them only within the existing scope; do not create a duplicate fix or claim resolution before they are remote. Missing or stale review/check evidence remains incomplete.

After a successful push, verify the remote head contains the fix. Build the commit URL from the actual repository URL and pushed SHA, including the correct host for enterprise installations. Every Fixed reply cites that URL; sanitize and truncate reviewer-derived prose before appending the URL so the link survives. A failed push means no Fixed reply. Reply before resolving eligible bot threads through the available API. Leave human threads open unless D explicitly authorized resolving them; do not rely on an undocumented bot magic comment.

Re-fetch and verify threads acted on, report other unresolved threads and asynchronous review status, and stop after bounded retries if publishing or resolution fails. A local-only fix is not a resolved remote finding. When the task includes getting the PR ready, follow the sibling land workflow for the new exact head; a pushed fix starts new CI and review work.
