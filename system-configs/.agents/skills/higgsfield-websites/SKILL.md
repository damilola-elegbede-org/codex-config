---
name: "higgsfield-websites"
description: "Build, edit, or deploy websites, apps, games, and their assets on the Higgsfield platform when Higgsfield is explicitly selected; ordinary website requests use the host website workflow."
license: "MIT"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "06fcb1349e93860a779c14c5ac47b9bf0cbe2aa4", "source-path": "system-configs/.claude/skills/higgsfield-websites/SKILL.md", "vendor-version": "0.13.0"}
---

# Higgsfield websites, apps, and games

Use this workflow only for a requested Higgsfield project. Existing repository contracts and host tools remain authoritative; ordinary website requests belong to the host website workflow. These resources describe the upstream v0.13.0 platform snapshot. Inspect the installed CLI and actual scaffold before relying on versioned APIs.

## Runtime prerequisites

Run these checks only for an invoked Higgsfield workflow, never during configuration sync.

1. Check `command -v higgsfield`. If missing, report the dependency; install only when the user's workflow authorizes installation, using current official instructions after inspecting the installer. Do not pipe downloaded scripts into a shell.
2. Check `higgsfield account status`. If authentication is missing or expired, have the user complete the interactive `higgsfield auth login` flow. Never copy credential files or request tokens in chat.
3. Inspect the live command/model schema before submitting jobs. Bundled model names, pricing, limits, and platform contracts are a v0.13.0 reference snapshot, not a guarantee of current availability.
4. Generation consumes service credits; local `--image` paths are uploaded. Submit only the requested assets, within the user's authorized scope and budget. A config install/sync authorizes no service jobs, uploads, login, deployment, or publication.

Follow host tools and policies. In particular, use the host image tool for image generation/editing unless an explicit user request permits Higgsfield; use host question tools only when available and allowed in the active mode, otherwise ask plainly. Honor existing answers and authorizations, and maintain required progress updates during long jobs.


## Choose the project type

The Higgsfield scaffold is a React/TanStack Start app in one Cloudflare Worker. Run package and build commands inside its `app/` directory. Read the scaffold's `app/AGENTS.md` before editing.

`higgsfield website create` requires `--type`. Infer it from a clear brief; ask if materially ambiguous:

| Type | Meaning | Workflow |
| --- | --- | --- |
| `website` | Standalone brand, without Higgsfield generation/sign-in or Quanta UI | [website-flow](references/website-flow.md) |
| `app` | Higgsfield sign-in and generation through fnf, using Quanta | [app-flow](references/app-flow.md) |
| `game` | Game template with realtime rooms and six pure game-logic functions | [game-flow](references/game-flow.md) |

The template's separation of standalone websites and generation apps is a Higgsfield platform contract, not a restriction on projects using other platforms. Preserve the user's chosen stack and provider.

Set a meaningful DNS-safe `--subdomain` derived from the product when creating a requested project. Check live categories for games; games require `--category` and take no `--template`. Project creation changes service state, so it belongs to the authorized build workflow, never configuration sync.

## Assets, launch, and verification

- Preserve supplied branding and useful existing assets. Generate missing assets only within the user's requested Higgsfield workflow and credit budget; optional cover videos and extra variations require scope that includes them.
- Match the requested animation direction. Ask about animation only when unresolved and material; an unanswered question does not authorize an animated film or extra paid assets. [scroll-scrub](references/scroll-scrub.md) applies to an agreed animated website.
- For a requested feed listing, fill `app/src/app-meta.json`: `og_title`, `og_description`, `favicon_url`, `og_image_url`, `marketplace_cover_url`. Use a suitable supplied cover or an authorized new one; see [app-cover](references/app-cover.md). Cover video is optional.
- Run the project's real type, build, and test gates as applicable. Inspect generated media and the rendered interface; fix material defects before claiming success. Batch independent operations without suppressing verification or progress updates.
- `higgsfield website deploy <website_id>` immediately changes the **live public site**. Deploy only when the user has authorized deployment; otherwise finish and verify the local build for review.
- `higgsfield website publish <website_id>` separately lists it in the community feed. Publish only when listing is requested or already authorized; do not repeat an existing approval. Contest entry also publishes automatically: verify current terms and act only on an explicit contest request.
- Report the actual state and URL: a deployment is live, not a private preview. Never expose or commit scoped git credentials.

## Reference routing

Read one matching flow first, then only relevant resources:

- Shared infrastructure and security: [runtime-and-infra](references/runtime-and-infra.md), [security](references/security.md).
- Website design and implementation: [design-recipe](references/design-recipe.md), [reference-boards](references/reference-boards.md), [asset-system](references/asset-system.md), [image-to-code](references/image-to-code.md), [review-rubric](references/review-rubric.md), [seo](references/seo.md). Specialized motion: [wow-catalog](references/wow-catalog.md), [wow-maker](references/wow-maker.md), [design-taste-frontend](references/design-taste-frontend.md).
- Apps: [app-quickstart](references/app-quickstart.md), [quanta-design](references/quanta-design.md), [app-layouts](references/app-layouts.md), [fnf-sdk](references/fnf-sdk.md), [fnf-react](references/fnf-react.md), [auth](references/auth.md), [containers](references/containers.md).
- Optional launch assets and contest: [app-cover](references/app-cover.md), [cover-animator](references/cover-animator.md), [contest](references/contest.md).
- Game assets: start with [game-design-system](references/game-design-system.md) and [game-stylization](references/game-stylization.md). The [game flow](references/game-flow.md) routes animation, textures, 3D, audio, and bundled scripts. The actual scaffold supplies game implementation and multiplayer contracts; upstream `build-game` and `multiplayer` documents are not bundled.

## License

Adapted from Higgsfield skills v0.13.0. See [LICENSE.txt](LICENSE.txt) for the complete MIT notice.
