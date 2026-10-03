# Decision recording and partial-write recovery

### 10. Record atomically (re-check, then idempotent write)

On D's answer — for a single A-ticket, or for each ticket surviving the confirmed-cohort preflight in a confirmed D1/D2
cohort — **FIRST re-fetch** the ticket's state and scan for an existing `[triage-decision]` marker; D (or the confirmed-cohort
preflight) may have taken minutes, and an agent may have moved the ticket meanwhile. Resolve the pre-write check by
cases, so a partial write from a prior interrupted attempt is repaired rather than orphaned:

Capture the ticket's **pre-decision state** before the first write attempt, so "partial write" and "drift" are
decided by an actual comparison rather than by a catch-all that swallows both.

- **Marker present AND state already matches this decision** → fully done; skip with a note.
- **Marker present for THIS decision AND current state still equals the captured pre-decision state** (comment
  landed, state write did not, on a prior attempt) → partial write, NOT a conflict: skip the comment op and
  complete only the missing state write.
- **Marker present for a DIFFERENT decision, or current state is neither the pre-decision state nor this
  decision's target** → genuine drift; abort and re-surface the ticket rather than writing stale.
- **No marker AND current state still equals the captured pre-decision state** → proceed with a fresh write.
- **No marker but current state has moved** → drift; abort and re-surface. A missing marker is not permission to
  write: another path may have advanced the ticket without leaving one, and writing here posts a stale comment and
  sets a target D's answer was never about.

The state check is re-run immediately before the state write as well, not only before the comment — the two ops are
not atomic, and the window between them is exactly when another path lands.

Then post the decision comment using the template below, THEN set the ticket state. Make both writes **idempotent**:
before (re)trying either, re-scan for the exact marker/state and treat an existing match as success for that
operation only — never let a completed comment op suppress a still-missing state op. Verify both writes; retry up to
3×. On unrecoverable partial failure, report exactly what landed and **halt** — never advance the queue on an
unverified write. A lost or duplicated decision is worse than a stall.

**Bucket B bounces** get the same record-and-repair contract, keyed on a distinct `[triage-bounce: <ISO-8601
timestamp>]` marker (never bare `[triage-bounce]`, and never `[triage-decision]` — a ticket can be bounced more than
once over its life and bounced now / formally decided later, so the marker must identify _this_ bounce operation,
not just the bucket). Immediately before each bounce write, re-fetch the ticket and scan for `[triage-bounce`,
since the gap between the table render and D's reply is enough time for another path to touch the ticket:

Capture the ticket's **pre-bounce state** and mint this operation's timestamped marker before the first write
attempt; the branches below compare against both, so "partial write" and "drift" stay distinguishable rather than
collapsing into a single catch-all, and a stale marker from an _earlier_ bounce can never be read as this one:

- **Exact marker for THIS operation present AND state already `Todo`** → fully done; skip with a note.
- **Exact marker for THIS operation present AND current state still equals the captured pre-bounce state** (comment
  landed, state write did not, on a prior attempt) → partial write; skip the comment op and complete only the
  missing state write.
- **Exact marker for THIS operation present AND current state is anything else** (e.g., already moved to
  `Done`/`Canceled` by another path) → drift; skip the write and report — never force a ticket another path has
  already advanced back to `Todo`.
- **No exact marker for THIS operation, AND current state still equals the captured pre-bounce state** (whether or
  not an _earlier_ `[triage-bounce: ...]` marker exists on the ticket) → proceed with a fresh write: post the "not
  a D-decision; execute or re-block" note under the new timestamped marker, then set state to `Todo`. An earlier
  bounce's marker is never read as evidence of a prior attempt for this operation — it is either drift from an
  unrelated past bounce (leave it, don't touch it) or simply irrelevant history.
- **No exact marker for THIS operation, but current state has moved off the captured pre-bounce state** → drift;
  skip and report. A missing marker is not permission to write: another path can advance a ticket without leaving
  one, and writing here sets `Todo` over a state change someone else made deliberately.

The state comparison is re-run immediately before the state write as well, not only before the comment — the two
ops are not atomic, and the window between them is exactly when another path lands.

Same write discipline as the A/D1/D2 path: verify each write, retry up to 3×, and on unrecoverable partial failure
report exactly what landed and halt that ticket rather than guessing.

### 11. Cascade lightly + collapse keystones

Comment on **direct** dependents to note the unblock. Give each cascade note a **deterministic marker** that names the
blocker, e.g. lead with `[unblock: <blocker-id>]` then "blocker resolved: `<decision>`". Before posting, scan the dependent
for that exact marker referencing this blocker and **skip if already present** — so reruns and later sessions never
duplicate the note (same idempotency contract as the decision comment, keyed on the blocker ID). When the ticket was a
**keystone**, also drop its now-resolved dependents out of the remaining walk (re-derive the A-queue) so you never ask
a question a prior answer already settled. Do NOT auto-transition downstream tickets — the agents own those;
auto-transitioning shared state is an irreversibility trap and is out of scope. These dependent comments are
**best-effort**: verify and retry once — but before that retry, re-scan for the exact marker and skip the retry if
it's already present, since the first attempt may have landed even though its verification response was lost (same
idempotency contract as this recording contract). On failure log the miss in the recap rather than halting — a failed
courtesy-comment must never block D's decisions.


The comment and state operations are not a transaction. Verify each separately; on drift or unrecoverable partial failure stop that ticket and report exactly what landed.
