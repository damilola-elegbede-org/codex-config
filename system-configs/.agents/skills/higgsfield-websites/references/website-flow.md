# Website flow — Higgsfield standalone websites

Use this flow after the user selects Higgsfield and the `website` product type. The app lives in `app/`, runs React/TanStack Start SSR in a Cloudflare Worker, and has the user's independent brand. Quanta and fnf belong to the Higgsfield `app` template instead. Check the actual scaffold contract before relying on versioned examples below.

## Build workflow

1. Resolve only missing requirements: requested scope, supplied brand assets, animation direction, and any authorization needed for service creation, paid assets, or live deployment. Do not repeat answers already given or infer authorization from silence.
2. Record a concise design brief in `.tmp/plans/` (or the project's required durable location). Capture audience, concept, palette, typography, sections, requested interactions, and asset needs. Preserve explicit user branding and accessibility needs.
3. Read [design-recipe](design-recipe.md) for craft guidance, then [reference-boards](reference-boards.md) when boards would help settle a substantial design. Use [scroll-scrub](scroll-scrub.md) only for an agreed animated film journey; use [wow-catalog](wow-catalog.md) for other requested effects. Artistic defaults are subordinate to the brief and budget.
4. Plan only assets needed by the requested output with [asset-system](asset-system.md). Preserve supplied assets; generate missing ones only within authorized Higgsfield usage. Inspect outputs before implementation. Optional visual kits, films, 3D assets, and cover videos are not automatic scope expansion.
5. Implement real requested behavior using [image-to-code](image-to-code.md), the scaffold, and the platform contracts below. Keep content visible without animation, provide reduced-motion fallbacks, and guard browser-only APIs from SSR. Use `.tmp/` for temporary planning/review artifacts.
6. Verify responsive rendering, interactions, accessibility, and generated media. Use [review-rubric](review-rubric.md) as applicable to the brief, plus the actual project typecheck/build/test commands. Do not substitute a text grep for browser verification when the interface can be tested.
7. Prepare requested launch metadata and a suitable cover using [app-cover](app-cover.md), existing supplied assets, or authorized generation. A feed listing needs nonempty `og_title`, `og_description`, `og_image_url`, and `marketplace_cover_url`.
8. Deploy with `higgsfield website deploy <website_id>` only when deployment is authorized: it immediately updates the live public site. Otherwise deliver the verified local build for review. Inspect status and the live result after an authorized deploy; report the live URL and material limitations.
9. Publish with `higgsfield website publish <website_id>` only when a community-feed listing is authorized. Deployment and listing are separate actions. A prior explicit listing request needs no redundant confirmation.

For small edits, preserve the existing design and scope, run proportionate checks, and deploy only within existing authorization. Do not restart the full design process.

## Reference routing

- Runtime/SSR/storage: [runtime-and-infra](runtime-and-infra.md).
- SEO/metadata: [seo](seo.md).
- Worker security: [security](security.md).
- Advanced design and motion: [wow-maker](wow-maker.md), [design-taste-frontend](design-taste-frontend.md).

## Stack

- **TanStack Start** (file-based routing under `app/src/routes/`, SSR via
  `app/src/server.ts` → a Worker `export default { fetch }`). No Next/Remix/Astro
  conventions, no `app/src/pages`.
- **Vite 7 + bun**. Build emits `dist/server/server.js` (the Worker) +
  `dist/client` (hashed static assets). Tailwind v4 is wired in `app/src/styles.css`
  (it also imports Quanta's Tailwind entry for the template
  bundle — leave that wiring alone even though websites use neither). Legacy
  shadcn/ui files may exist from the scaffold. Websites use custom
  Tailwind/CSS only — never import `@higgsfield/quanta/*`.
- **No separate Hono/Express backend.** Server logic is TanStack **server
  functions** (`createServerFn`) and **server routes**. App-local API routes are
  allowed when a platform contract requires them (for example a webhook
  receiver or a JSON endpoint the site's own client fetches).


## Hard rules

### 0a. Vendored packages and template modules

The `app/packages/` directory contains managed snapshots vendored from the
upstream Higgsfield web app (`@higgsfield/fnf`, `@higgsfield/fnf-react`,
`@higgsfield/quanta`). Websites never use them, but do NOT edit or delete
them. Template-owned infrastructure lives in `app/src/module/**`.

### 0b. Supercomputer Design mode inspector

Generated websites support a Higgsfield design inspector bridge for editing in
Supercomputer Design mode. The split is strict:

- The Higgsfield editor (parent window) owns the iframe UI, hover overlay,
  edit popover, origin/session checks, and edit prompt submission.
- This template owns the child iframe runtime through
  `app/src/module/design-inspector`.
- Agents never manually implement inspector code, refs, source markers, or
  `data-hf-*` attributes.

Local scripts (LOCAL work only — the deploy build is owned by CI):

- `bun run build` is inspector-free by default: no inspector runtime and no
  source metadata. Setting `HF_DESIGN_INSPECTOR=1` in the env turns the same
  build into the inspector-enabled one (this is what platform CI does on
  every deploy).
- `bun run dev:design` is local dev with the inspector enabled.

The platform CI sets `HF_DESIGN_INSPECTOR=1` on every deploy build, so the live
deployed site always carries the inspector and IS the surface Supercomputer
Design mode opens. Exact source metadata is attached with inspector-only
callback refs and a `WeakMap`, not DOM attributes. Keep the guarded
dynamic install in `app/src/routes/__root.tsx` and the Vite integration in
`app/vite.config.ts` wired to `app/src/module/design-inspector/vite`.

For every Supercomputer website-builder task there is ONE deploy —
`higgsfield website deploy <website_id>` — and it ships the live public site
immediately; there is no preview stage or environment choice. Publishing/listing on
the community feed is separate: do NOT run `higgsfield website publish` unless
the user explicitly asks to publish, list, or share the site. Never hard-code
`HF_DESIGN_INSPECTOR=1` into the `build` script and never hand-edit the build
script to toggle it — the deploy build is CI-owned.
### 1. SSR-safe rendering
Every route renders on the server per request. NEVER touch browser-only globals
(`window`, `document`, `localStorage`, `navigator`) at module top level or during
render — only inside `useEffect`/event handlers, or guarded with
`typeof window !== "undefined"`. A top-level `window` reference crashes SSR.

### 2. Server-only code stays server-only
Put server logic in `createServerFn(...).handler(...)` or a `*.server.ts` module
(the `.server.ts` suffix keeps it out of the client bundle). Secrets and
bindings are read **server-side, per request** — never shipped to the browser.

### 3. No Higgsfield integration — but a REAL backend of the site's own
A `type: "website"` product never calls `https://fnf.internal/*`, never shows
"Sign in with Higgsfield", and never imports the fnf SDK. It still gets a real
backend wherever the product needs one: server functions (`createServerFn`),
app-local API routes, sessions, business logic, and real persistence (D1) —
never in-memory arrays, `localStorage`-as-database, or fixture data. In-app
auth for the site's OWN users (accounts, teams, dashboards) is built with the
website's own routes/storage. If the request needs generation or Higgsfield
accounts, it is a `type: "app"` — switch to `references/app-flow.md`.

### 4. Cloudflare bindings via `cloudflare:workers`
Any infra you opt into (D1 `DB`, R2 `STORAGE`, KV `KV`) is read server-side
through `app/src/lib/bindings.server.ts` (`import { env } from "cloudflare:workers"`).
Each binding is present ONLY if declared in `app/app.manifest.json`, so the typed
accessors are optional — guard before use. Do not thread `env` through React
props or read it at module top level.

### 5. Opted-in storage is LIVE — one deploy, one database
If you opt into D1, R2, or KV, each is a SINGLE instance backing the ONE live
deploy. There is no staging copy: every migration and data change hits **live
production data** directly.
- `env.HF_ENV` is always `"production"` on deployed builds; there is no
  separate database/bucket to test against.
- A destructive migration you run "just to test" destroys **production data**.
  Prefer additive migrations (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN`), and
  get explicit user approval before any destructive change.

### 6. `app/app.manifest.json` declares infra — NOTHING is provisioned by default
A new website gets **no D1, no R2, no KV, no Durable Object**. Opt in only when
the website actually needs it:
- `"db": true` → a D1 database, bound `env.DB`
- `"r2": true` → an R2 bucket, bound `env.STORAGE`
- `"kv": true` → a KV namespace, bound `env.KV`
- `"durableObject": "ClassName"` → a Durable Object, bound `env.ROOMS`
- `"container": true` (or `{ "instanceType", "port", "sleepAfter" }`) → a Docker
  container for heavy/long-running work, bound `env.CONTAINER` — see
  `references/containers.md`

Counts are capped (≤1 each) by the platform, which PROVISIONS the resource and
binds it at deploy. The committed `app/wrangler.jsonc` is build/dev input only;
the platform OVERWRITES its `name` + bindings at deploy — declare infra in
`app/app.manifest.json`.

**KV is eventually consistent** (NOT Redis): config, feature flags, cached reads
— NOT counters, locks, or read-after-write. Use a Durable Object for strong
consistency.

For a **Durable Object** you must ALSO `export class ClassName extends
DurableObject {…}` from `app/src/server.ts` (alongside the default `{ fetch }`
export).

For a **container** — heavy or long-running work a Worker can't do: set
`"container"` in the manifest and follow **`references/containers.md`** (exact
Dockerfile, the platform-fixed `AppContainer` class, keep-alive + 3-hour-deadline
pattern, fnf via container token). Containers are **off by default**.

## Editing map
- Pages / routing → `app/src/routes/**` (file-based; `__root.tsx` is the shell).
- Server logic → `createServerFn` (see `app/src/lib/api/example.functions.ts`) or
  `*.server.ts`.
- Bindings access → `app/src/lib/bindings.server.ts`.
- Infra declaration → `app/app.manifest.json`; `app/wrangler.jsonc` = build/dev input.
- Durable Object class → exported from `app/src/server.ts`.
- Components → custom components per the boards; app-local files in
  `app/src/components/**`. Do not start from `app/src/components/ui/*` unless
  migrating a legacy shadcn piece.
- Styles / theme → `app/src/styles.css` wires Tailwind v4. Websites: a custom
  token layer from the design brief — no q-prefixed utilities, no site-wide
  CTA utility classes.
- D1 schema → `app/migrations/000N_*.sql` (additive; see rule 5).
- Pipeline artifacts → `app/design-brief.md` (Phase 0) + `refs/*.png` (Phase 1);
  commit both.

## Verify + deploy

The trusted platform CI builds the website on **every deploy** (always with
`HF_DESIGN_INSPECTOR=1` and `HF_ENV="production"` — the live site carries the
design inspector), so a deploy already gives you the authoritative type +
build result. Do NOT reflexively `bun install` +
`bun run build` just to check your work. The sandbox cannot deploy/migrate (no
Cloudflare token); the trusted platform CI does that.

**Default: run the pipeline, pass the Phase 5 gate, deploy**
(`higgsfield website deploy <website_id>` — this ships the live site
immediately). Never publish/list on the community feed unless the user
explicitly asked to publish.

**Publishing ("show in feed").** When the user asks to publish / share / put the
site on the feed, run `higgsfield website publish <website_id>` — it lists the
site on the Higgsfield community feed. **Publishing no longer deploys**: it
lists whatever is already live, so run `higgsfield website deploy <website_id>`
FIRST — and after ANY later change, deploy again to ship it (re-publishing does
not re-deploy and won't pick up un-deployed changes).

**HARD GATE — the cover is NOT optional. Running `higgsfield website publish` while
`og_image_url` or `marketplace_cover_url` is empty is a BROKEN publish** (the
feed card renders ONLY from `app/src/app-meta.json`; an empty `og_title` makes
the listing INVISIBLE, an empty cover makes it a blank card). The publish
sequence is: (a) READ `app/src/app-meta.json`; (b) if `og_image_url` or
`marketplace_cover_url` is empty → STOP, read `references/app-cover.md` and
generate + upload the cover NOW — do not skip this because the user "only asked
to publish", the cover IS part of publishing; (c) fill ALL fields below with
real values (never placeholders); (d) commit + push; (e) run
`higgsfield website deploy <website_id>` to ship the pushed changes (publish no
longer deploys — it lists what's already live); (f) only then run
`higgsfield website publish`:

1. `og_title` — the card's title (also the browser tab title).
2. `og_description` — the card's one-liner.
3. `og_image_url` — REQUIRED: the cover image, generated per
   `references/app-cover.md` (the branded 3:2 cover + stadium-capsule OG
   mask) if none exists yet; upload the OG file with `higgsfield upload create`
   and set the returned durable URL.
4. `marketplace_cover_url` — REQUIRED: the plain (unmasked) cover, the same
   generation's `<name>_cover.png` from `references/app-cover.md`, uploaded
   with `higgsfield upload create`. One generation fills both this and
   `og_image_url` — there is never a reason to have one without the other.
5. `favicon_url` — the card's logo/icon (generate one if none exists yet).
6. `og_video_url` — the **cover video**, OPTIONAL and permission-gated: OFFER
   it to the user ("want a short cover video for the feed card?") and ASK
   PERMISSION FIRST — generating a video costs credits; never generate it
   unprompted. If they say yes, follow "Cover video" in `references/seo.md`.

Reuse suitable existing assets for fields 1–5; generate/upload missing assets only within the authorized publish workflow and credit budget. Cover video is optional and needs a request that includes it.

`higgsfield website deploy <website_id>` remains the way to ship the live site
WITHOUT a feed listing.

**Run the applicable local checks before claiming the build is ready** — from `app/`:
```bash
cd app
bun install          # only when you changed dependencies / package.json
bun run typecheck    # tsc --noEmit when available
bun run build        # validate the production build
```
Run the repository's required gates; add focused behavior checks for changed functionality.

**Small edits to an existing site** (copy tweak, one component, styling fix): the
pipeline does not restart. Make the edit, verify it, and deploy when authorized.

**Before claiming a build done / deploying, no placeholders may remain** — no
`<...>`-style tokens, `lorem ipsum`, or scaffold blank-page markers
(`REMOVE_THIS` / `blank-app-v1`). This is covered by the mechanical gate (the
grep checklist in `references/review-rubric.md` §A).
