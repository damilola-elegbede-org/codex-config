# Locked experiment format

The helpers require Bash, jq, and Python 3.11 or newer. They make no model or
service requests themselves. Resolve every helper from the loaded skill folder.

`new.sh <slug>` scaffolds an experiment under the repository's `.tmp/experiments`;
`EXPERIMENTS_DIR` can select another authorized temporary directory. Fill both
JSON files before `lock.sh <dir>`; leaving scaffold question text refuses locking.

`protocol.json` holds the hypothesis and decision rule. The runner's model
context must not read it; the helper reads it to validate its lock.

| Field | Contract |
| --- | --- |
| `question`, `hypothesis`, `prediction`, `if_false` | Nonempty descriptions of the claim and its falsifying outcome |
| `evidence_kind` | `observed` for actual behavior; `simulated` for a stand-in or model of it |
| `side_effects` | `local`, `external`, or `refuse`; see execution.md |
| `controls` | Conditions with `expect: "pass"` or `"fail"`; at least one negative control |
| `pass_rule` | One of the rules below |
| `notes` | Frozen rubric, cost authorization/budget, relevant limits, and source revisions |

```json
{"type": "rate", "condition": "treatment", "op": ">=", "value": 0.9}
{"type": "mean", "condition": "treatment", "op": "<", "value": 2.5}
{"type": "compare", "stat": "rate", "a": "treatment", "b": "baseline", "op": ">", "margin": 0.2}
```

Operators: `>=`, `>`, `<=`, `<`, `==`. A comparison margin increases the required
gap: compare `a` to `b + margin` for greater-than operators and `b - margin` for
less-than operators. Equality ignores margin. For rates, true, a nonzero number,
or the strings `pass`, `true`, `yes`, `1` count as passes. Mean rules require a
numeric observation for every planned trial; booleans count as 1/0.

`plan.json` is the runner's input:

| Field | Contract |
| --- | --- |
| `reps` | Integer 1–1000 per condition, at most 10000 planned trials total |
| `timeout_s` | Per-command time limit, 1–3600 seconds; default 120 |
| `budget_s` | Total recorded local runtime budget, 1–86400 seconds; enforced on resume too |
| `seed` | Integer for deterministic per-repetition condition shuffling |
| `conditions` | Unique lowercase/digit/hyphen `name`, Bash `cmd`, optional `observe` |

`observe: null` measures successful exit; `"judge"` defers to a blind rubric.
An observer command prints one JSON value or a string and sees `RUN_OUT`,
`RUN_ERR`, and `RUN_EXIT`. Empty or whitespace-only observer output is missing
evidence; explicit JSON `false`, `0`, or `""` is an observation. A failed observer, timed out command, or absent value
is invalid, not a failing measurement. Observers share the budget and have a
60-second maximum. Process cleanup may take several extra seconds.

The scorer requires all planned observations used by the rule and controls.
Missing/invalid observations or a control behaving incorrectly yield
INCONCLUSIVE. Otherwise the locked rule yields SUPPORTED or REFUTED. Duplicate
pairs and out-of-range repetitions do not add evidence. The 95% Wilson interval
describes observed pass rates, not a hypothesis probability or mean interval.
For example, 5/5 gives roughly 0.57–1.00; small samples remain uncertain.

`verdict.json` records the protocol/plan hash, evidence kind, observation-file
hashes, and per-condition statistics. Preserve the directory for reproduction;
hashes reveal changes when compared with a retained verdict, not authenticity.
Score exits: 0 SUPPORTED, 1 REFUTED, 2 INCONCLUSIVE, 3 malformed/unlocked input.
