# Preservation and conflict workflow

Read-only inspection uses git status, branch, diff, log, and upstream refs. All writes use the repository’s authorized identity tooling. An authorized GitHub connector can integrate remote changes, but does not provide a local stash/rebase command; use an approved local write path if those operations are needed.

1. Record the base/current SHA and any pre-existing changes. Prefer an isolated checkout to stashing a shared tree.
2. If an authorized operation needs a stash, include untracked files and record the exact newly created stash ID. Never pop a prior unrelated stash.
3. Integrate the verified upstream. Do not checkout or reset a production working tree.
4. Capture conflict paths under .tmp/merge/ or .tmp/rebase/. Resolve from both intended behaviors; ours/theirs explicitly discards the other side.
5. Even on “already up to date,” restore the exact workflow-owned stash. A restoration conflict leaves work incomplete; retain the stash and report it.
6. Run relevant checks for changed content and report final SHA, unresolved paths, and outstanding stash. Abort only the requested in-progress operation, never delete unrelated temporary reports or stashes.
