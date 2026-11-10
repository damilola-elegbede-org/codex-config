# Execution and scope

Review every condition and observer before locking. Keep writes in the experiment
directory, use copies of input files and local bare Git remotes, and avoid
credentials in commands or captured output. The runner has the host session's
actual permissions; no instruction here creates a sandbox or approval.

| Class | Meaning | Execution |
| --- | --- | --- |
| `local` | Reviewed commands operate on local scratch data within the authorized task | `python3 scripts/run.py <dir> --execute-local` |
| `external` | A real service, model call, paid quota, or write outside scratch storage is necessary | Use authorized host tools; record actual evidence |
| `refuse` | The proposed design is outside scope or prohibited | Locking/execution refuses; revise the design |

Existing user authorization continues to apply. Ask only for a missing material
permission or spending constraint; do not repeat an approval already given.
Experiment setup never grants external-write authority. A model trial is an
actual model/tool invocation with captured evidence, not your prediction of what
the model would do. A mocked service tests the mock; label it `simulated` when
the hypothesis concerns real service behavior.

Local runs have a clean environment, scratch cwd, isolated HOME/TMPDIR, and one
process group per command. Ordinary background children in that group are
terminated; deliberately detached children, absolute paths, and network calls
are not contained. Use host-supported isolation for commands that need enforced
containment; otherwise do not run them through this helper. A timeout is an
invalid observation. Parent process failures do not justify guessed values.

One writer owns `.runner-lock`. Normal completion releases it; after an abrupt
kill, verify the old process stopped before removing the stale lock. Recorded
condition/repetition pairs are skipped on resume. Unrecorded interrupted trials
can run again, so local conditions must tolerate that repetition. Changing inputs
or rules after data collection requires a new experiment.

To record an external or manual trial, save the real tool result in the experiment
directory, then run:

```sh
python3 scripts/run.py <dir> --record treatment 1 true --evidence runs/tool-result.json
```

The helper checks that the evidence file exists within the directory and marks
the row `manual`; it cannot verify that the observation faithfully reflects the
file. Review that connection before scoring. Copy no tokens or private service
data beyond what the task requires.
