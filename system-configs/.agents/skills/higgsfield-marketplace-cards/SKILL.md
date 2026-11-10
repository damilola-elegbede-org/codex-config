---
name: "higgsfield-marketplace-cards"
description: "Create marketplace listing image sets with the Higgsfield marketplace-cards service when Higgsfield is explicitly requested or already selected."
license: "MIT"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/higgsfield-marketplace-cards/SKILL.md", "vendor-version": "0.13.0"}
---

# Marketplace Cards

Create product visuals for marketplace listings with `higgsfield marketplace-cards create`.
The CLI first calls the backend enhancer, where marketplace rules and templates are kept private, then creates `nano_banana_2` jobs and prints result URLs.

## Runtime prerequisites

Run these checks only for an invoked Higgsfield workflow, never during configuration sync.

1. Check `command -v higgsfield`. If missing, report the dependency; install only when the user's workflow authorizes installation, using current official instructions after inspecting the installer. Do not pipe downloaded scripts into a shell.
2. Check `higgsfield account status`. If authentication is missing or expired, have the user complete the interactive `higgsfield auth login` flow. Never copy credential files or request tokens in chat.
3. Inspect the live command/model schema before submitting jobs. Bundled model names, pricing, limits, and platform contracts are a v0.13.0 reference snapshot, not a guarantee of current availability.
4. Generation consumes service credits; local `--image` paths are uploaded. Submit only the requested assets, within the user's authorized scope and budget. A config install/sync authorizes no service jobs, uploads, login, deployment, or publication.

Follow host tools and policies. In particular, use the host image tool for image generation/editing unless an explicit user request permits Higgsfield; use host question tools only when available and allowed in the active mode, otherwise ask plainly. Honor existing answers and authorizations, and maintain required progress updates during long jobs.


## UX Rules

1. Respond in the user's language.
2. Ask only for missing choices that materially change the result; do not reconfirm an already authorized request.
3. Prefer a product image. If the user provides only text or a URL, proceed only when the product details are clear.
4. Do not write final image-generation prompts yourself. Backend enhancement owns that.
5. Deliver ready image URLs and short labels, plus any material limitation. Follow the host response format.

## Scope Selection

Use `--scope` when the user asks for a common bundle:

| Scope | Creates |
|---|---|
| `main` | 1 marketplace main image |
| `product-images` | main image + 5 secondary images |
| `aplus` | main image + 7 A+ modules |
| `full-set` | main image + 5 secondary images + 7 A+ modules |

Use repeated `--asset` only for custom subsets:

- `main_image`
- `infographic`
- `multi_angle`
- `detail_shot`
- `lifestyle`
- `whats_in_box`
- `aplus_hero_banner`
- `aplus_pain_points`
- `aplus_features`
- `aplus_ingredients`
- `aplus_efficacy`
- `aplus_how_to_use`
- `aplus_endorsement`

## Command

Build and run one `higgsfield marketplace-cards create` command from the user's request.

For common bundles, use `--scope <main|product-images|aplus|full-set>`, `--prompt "<short product and listing intent>"`, optional repeated `--image <path-or-upload-id>`, and optional context flags: `--product_context`, `--brand_context`, `--category`, `--visual_style`.

Examples to mirror when choosing arguments:

- Product images: `higgsfield marketplace-cards create --scope product-images --prompt "sparkling peach lemonade can for marketplace listing" --image ./can.png --category "beverage"`
- Full set: `higgsfield marketplace-cards create --scope full-set --prompt "premium skincare serum, clean clinical marketplace visual system" --image ./serum.jpg --brand_context "minimal white and sage palette"`
- Custom subset: repeat `--asset`, for example `--asset main_image --asset infographic --asset lifestyle`.
- Existing completed main image job: use `--main-job <completed_main_job_id>` with the requested secondary or A+ `--asset` values.

## Delivery

Print URLs with labels:

```text
Marketplace cards ready:
- Main image: https://...
- Infographic: https://...
- Lifestyle: https://...
```

Avoid JSON, job IDs, internal model names, or enhanced prompt text unless the user explicitly asks.

## License

Adapted from Higgsfield skills v0.13.0. See [LICENSE.txt](LICENSE.txt) for the complete MIT notice.
