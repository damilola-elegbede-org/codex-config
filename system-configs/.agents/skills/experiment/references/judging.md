# Blind judgments

Use judgment only when a command cannot measure the outcome. Put the rubric and
score meaning in `protocol.json` notes before locking. Export outputs with:

```sh
python3 scripts/score.py --export-blind <dir>
```

Export uses the recorded stdout artifact for local trials and the `--evidence`
artifact for manual/external trials. It verifies containment and the captured
hash before reading either; absent or changed evidence refuses export.

When independent delegation is allowed, give a fresh judge only
`blind/items.jsonl` and the frozen rubric. It writes `blind/judgments.jsonl`, one
`{"id": "...", "value": true, "reason": "..."}` record per item; ungradable
items use null. The judge must not read `blind/key.json`, condition names, the
hypothesis, or the expected result. Anonymization removes metadata, not clues
inside an output; disclose residual unblinding.

Then score normally. Do not re-export after judgment: it creates different item
IDs. One judge is one assessment, not independent confirmation of the hypothesis.
If delegation is unavailable, report the limitation rather than inventing a
panel or silently calling your own assessment blind.
