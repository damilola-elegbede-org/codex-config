---
name: "higgsfield-soul-id"
description: "Train and manage a Higgsfield Soul identity from supplied face photos when the user requests Higgsfield Soul training."
license: "MIT"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/higgsfield-soul-id/SKILL.md", "vendor-version": "0.13.0"}
---

# Higgsfield Soul Character

Train a face-faithful identity model. Reusable across all Soul-powered generations.

## Runtime prerequisites

Run these checks only for an invoked Higgsfield workflow, never during configuration sync.

1. Check `command -v higgsfield`. If missing, report the dependency; install only when the user's workflow authorizes installation, using current official instructions after inspecting the installer. Do not pipe downloaded scripts into a shell.
2. Check `higgsfield account status`. If authentication is missing or expired, have the user complete the interactive `higgsfield auth login` flow. Never copy credential files or request tokens in chat.
3. Inspect the live command/model schema before submitting jobs. Bundled model names, pricing, limits, and platform contracts are a v0.13.0 reference snapshot, not a guarantee of current availability.
4. Generation consumes service credits; local `--image` paths are uploaded. Submit only the requested assets, within the user's authorized scope and budget. A config install/sync authorizes no service jobs, uploads, login, deployment, or publication.

Follow host tools and policies. In particular, use the host image tool for image generation/editing unless an explicit user request permits Higgsfield; use host question tools only when available and allowed in the active mode, otherwise ask plainly. Honor existing answers and authorizations, and maintain required progress updates during long jobs.


## UX Rules

1. Be concise. Report the character name, actual training state, and reusable reference when useful.
2. Detect language and respond in it. CLI flags stay English.
3. Ask for the smallest set of inputs: name + photos. Pick a sensible model variant.
4. Training takes minutes; maintain host-required progress updates without repeating raw polling details.

## Workflow

1. **Get name.** One word, used for later reference. Ask if missing.
2. **Get photos.** 5–20 face photos, varied angles and lighting. Local paths or already-uploaded IDs both work — `--image` accepts either.
3. **Pick variant.**
   - `--soul-2` — for image generation (default)
   - `--soul-cinematic` — for cinematic / video work
   Choose based on user's stated downstream use. Default to `--soul-2`.
4. **Submit.**
   ```bash
   higgsfield soul-id create --name "<name>" --soul-2 --image ./photo1.png --image ./photo2.png ...
   higgsfield soul-id create --name "<name>" --soul-2 --image <upload_id> --image <upload_id> ...
   ```
   CLI auto-uploads paths. Captures returned reference id.
5. **Wait.** `higgsfield soul-id wait <id>`. Use resumable waits so long training does not block progress updates. Upstream default timeout is 30m.
6. **Deliver.** "Soul `<name>` ready. Use in generate with `--soul-id <id>`."

## Use the Soul

Once trained, pass to `higgsfield-generate`:

```bash
higgsfield generate create text2image_soul_v2 --prompt "..." --soul-id <ref_id> --quality 2k --wait
higgsfield generate create soul_cinematic --prompt "..." --soul-id <ref_id> --quality 2k --wait
```

`--soul-id` is sent as the model's `custom_reference_id`. For a curated Soul style, list styles with `higgsfield preset list soul-v2` and pass the chosen id as `--style_id` on `text2image_soul_v2`. `--style_id` cannot be combined with `--image`.

## Listing existing Souls

```bash
higgsfield soul-id list                   # all references
higgsfield soul-id get <id>               # one by id
```

## Errors

- `Minimum Basic plan required` — user is on free plan; tell them.
- `Training failed` — check photos quality (5+ distinct photos of the same person, well-lit).
- `Session expired` → `higgsfield auth login`.

## Reference docs

- `references/photo-guide.md` — what photos work best
- `references/troubleshooting.md` — common training failures

## License

Adapted from Higgsfield skills v0.13.0. See [LICENSE.txt](LICENSE.txt) for the complete MIT notice.
