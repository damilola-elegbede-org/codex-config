# Review before publication

Use for the pre-PR stage in pr and ship-it, or when explicitly asked to review
and repair before publishing. This adapts upstream codex-review to the current
Codex session: use the available reviewer, not a second CLI login or copied
credentials. Prefer an independent reviewer when delegation is permitted. If
only a direct review is possible, disclose that limitation; never label it
independent. Review stays read-only; the implementing agent owns repairs.

Record the verified target base, merge-base, branch, HEAD, and intended file set.
Review the full branch change plus staged/unstaged task changes and task-owned
new files. Untracked files are not in a normal git diff: read those files
explicitly or use an isolated review index, preserving the real index. Exclude
temporary artifacts and unrelated files, and report exclusions. A reviewer
must see the content that the eventual PR will contain.

Use the shared review artifact schema in
../../resolve-comments/references/schemas.md. For reuse, record a fingerprint of
the verified merge-base, full tracked diff, and sorted names/content hashes of
the task-owned new files. A matching HEAD alone is insufficient when worktree
changes exist. Reuse only a complete result for the same base and content; a
commit with identical reviewed content can reuse that result after equivalence
is verified. Keep the original reviewer evidence and record the published SHA
separately. Never overwrite another active review's artifacts or treat its
pending result as a pass.

Focus on parsing/selection edge cases; missing-input or swallowed-error passes;
retry, concurrency, and partial-write state; registrations outside the diff;
identity and untrusted input reaching a shell/path/prompt; worktree and runtime
assumptions; pagination/timeouts/buffer bounds; tests that would pass with the
bug restored; and instructions made stale by the change. Every finding needs
its concrete trigger, wrong outcome, and the files a fix must touch. Severity
comes from impact, not from a fixed category or a mechanical complexity limit.

Validate findings against the current code using resolve-comments in file mode.
Repair within existing authorization and repeat the affected gates and review
after changes, for at most three repair/review rounds. Retain skipped findings
with evidence across rounds. Unresolved HIGH/CRITICAL findings block
publication; lower-severity findings require an explicit disposition under the
task's scope. Missing, stale, malformed, or interrupted review output is
incomplete, never an empty pass. At the bound, report remaining findings and
stop the publication step.

Before publishing, independently inspect the current state even if a cached
review passed: all intended fixes must be in the commit being pushed. After
publishing, verify that the remote branch and any PR head equal that commit.
Uncommitted task files or unpushed fix commits are incomplete publication. Keep
unrelated local work out of the commit. If the intended content or base changed,
invalidate the old review evidence and repeat the affected checks. This workflow
does not grant permission to commit, push, merge, or post comments beyond the
user's scope.
