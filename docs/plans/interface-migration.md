# Interface migration: the LifeKit app into desktop Gradio

This plan governs the frontend of the `reversely/lifekit` Space. It transfers the literal
interface of the flux app (Expo Router, React Native, Skia shaders) into a desktop Gradio
app, screen by screen. The companion plan `lifekit-space.md` keeps the dataset, licensing,
and model phases; where the two describe the frontend, this document wins.

## Substrate decision

The interface renders inside one custom Gradio component (`lifekit_shell`), built with
`gradio cc` (Svelte + TypeScript + Vite), with three.js compiled in for the shader
backdrops. The alternatives and why they lose:

- Restyled native Gradio widgets reproduce neither the shader field, the stack
  navigation, nor the component chrome; the first attempt proved it.
- A `gr.HTML` shell with a hand-rolled esbuild bundle can carry the same DOM, but every
  screen's reactivity (interview state, chat threads, camera loops) gets re-implemented in
  vanilla JS, and the Python-to-JS bridge gets hand-rolled through hidden widgets. Svelte
  templates sit close to the source JSX, Svelte keeps the sources in TypeScript, and the
  custom-component protocol provides the typed props/events bridge.
- An Expo web export in a Docker Space carries perfect fidelity but loses ZeroGPU, which
  only Gradio-SDK Spaces get.

Costs accepted with this choice: the `gradio cc` toolchain pins a Gradio version range,
the component ships as a wheel committed to the Space repo, and JSX-to-Svelte template
conversion remains hand work per screen (the classes below bound how much).

Routing: the shell owns navigation with hash-based History API routing
(`#/encyclopedia/3`), which preserves the app's stack push/pop semantics, gives the
browser back button the back-chevron role, and keeps deep links shareable without
server-side routes. Desktop layout starts at two columns (navigation/context left,
screen content right) and reconfigures on request.

Python's role: serve the Space, hold the `@spaces.GPU` functions, expose named API
endpoints (`/gradio_api/call/*`) the shell calls directly, and serve pack assets and
fonts through static paths.

## Transfer classes

Every source file falls in one class; the class sets the method and the cost.

- **C1, verbatim TypeScript.** No React, no react-native imports. Transfers with import-path
  edits only, staying TypeScript inside the shell. Files: `data/vss.ts` (sessions and the
  finding matcher), `data/encyclopedia.ts`, `data/reference.ts` + `reference.generated.ts`,
  `data/coach.ts`, `data/synoptic.ts`, `data/guide.ts`, `data/guides/`, `data/widgets.ts`
  (the surface registry), `theme/biome.ts`, `theme/tokens.ts`, `api/types.ts`,
  `lib/route.ts` helpers.
- **C2, SKSL to GLSL.** `HomeBackdrop.tsx` (animated: biome gradient, god rays, three
  parallax terrain ridges keyed to scroll, motes, grain) and `PageBackdrop.tsx` (static
  variant). Port the shader strings to GLSL fragment shaders on a full-screen quad in
  three.js: `half4` to `vec4`, `float2/3` to `vec2/3`, helper functions unchanged.
  Uniforms keep their names; scroll binds to the shell's scroll position; reduced motion
  maps to `prefers-reduced-motion`; the freeze-when-unfocused rule maps to route
  visibility. Palette values keep coming from `biome.ts` (C1), so both sides read one
  source.
- **C3, RN components to Svelte components.** Same names, same structure, StyleSheet
  objects re-expressed as scoped CSS over the token variables. `TopBar`, `Directory`
  (cream paper, italic serif numerals, gold rules), `References` (numbered sources with
  license lines), `Tag` (honest-state badge), `WidgetDirectory` (home shelves),
  `ChatMessage`, `AnswerText`, `StubScreen`. Feather icons transfer glyph-for-glyph via
  the `feather-icons` package (same set the app uses through `@expo/vector-icons`).
- **C4, platform API swaps.** `expo-camera` to `getUserMedia` + `MediaRecorder`;
  `expo-speech` to Web `speechSynthesis`; `expo-location` to browser geolocation (feeds
  `localBaseline`); `expo-device` and haptics drop. Each swap sits behind the same
  function signature the screens already call.
- **C5, transport replacement.** `api/client.ts` becomes a bridge module with the same
  exported functions, fetching `/gradio_api/call/{endpoint}` instead of the flux server;
  `api/uploadQueue.ts` maps to Gradio file upload; `live/watch.ts` (server-sent progress)
  maps to Gradio streaming events. `api/types.ts` stays as the contract.
- **C6, state stores.** zustand stores (`chat`, `session`, `observations`, `traces`,
  `conditions`) become Svelte stores, a mechanical conversion since their logic is plain
  TS over the C5 bridge.

## Screens, one row each

Fidelity = the screen's chrome and behavior as the app source defines them today (dark
biome throughout, per `PageBackdrop`). Capability = which backend phase lights it up;
until then the screen ships its chrome with the app's own honest-badge pattern.

| Route | Src lines | Transfer notes | Capability |
|---|---|---|---|
| `_layout` | 25 | Shell frame: font faces (Aeonik, Argent Pixel, committed per decision), router, backdrop mount | M0 |
| `/` home | 376 | Animated backdrop (C2), wordmark, question pills, ask input, shelves from `widgets.ts`; scroll drives the shader uniform | M2 |
| `/chat`, `/chats` | 227 | Thread + history over chat store (C6); voice out via C4 speech | M2; quotes phase 1, model phase 2 |
| `/encyclopedia` | 44 | `Directory` (C3) over `encyclopedia.ts` | M2 |
| `/encyclopedia/[tile]`, `section/[section]` | 605 | Tile and section content; chapter text extracted from the pack PDF replaces the flux server's `/v1/content` | M2 |
| `/reference` | 71 | pdf.js viewer (vendored), chapter jump table, deep-link targets for findings and tiles | M2 |
| `/vss/[id]` walks | 483 | Full session: capture card (Record via C4 camera, Skip the clip), interview chips, result card with figure, quote block, Again, the 15-minute shadow-tip timer, `localBaseline` via geolocation | M2; clip read phase 2 |
| `/guide/[id]` | 259 | Synoptic guide pages (clouds gallery, fire) from `guide.ts`; cloud images need attribution traced before shipping | M2 |
| `/capture` hub | 167 | Card list with per-card honest badges | M3 chrome |
| `/sky` | 202 | Auto-loop camera read | M3 chrome; phase 2 capability |
| `/capture/trail` | 462 | MediaRecorder chunking to upload queue, ask-over-clips | M3 chrome; phase 2 capability |
| `/coach/[knot]` | 518 | Step screen, camera watch loop, voice | M3 chrome; phase 3 capability |
| `/traces` | 158 | Dev harness over traces store; doubles as the bridge's own test surface | M1, dev flag |
| `/about` | 245 | Static transfer | M3 |
| `/conditions` | 96 | No desktop sensors: honest empty state | M3 chrome |
| `/library` | 155 | Needs the box worker: honest state | M3 chrome |
| `/map` | 819 | maplibre-gl + pmtiles could run in-browser; excluded for now per scope decision, revisit with archive sizing | out |
| `/connect` | 117 | Server pairing has no Space meaning; drop from the router | out |
| `/walkthrough`, `/mushrooms` | 1449 | Edibility surfaces, excluded | out |

## Milestones

- **M0, architecture spike.** `gradio cc` scaffold; the `PageBackdrop` GLSL port on a
  quad; fonts served and rendering; hash router with two stub screens; one bridge
  round-trip (shell calls a named endpoint, renders the reply); a `@spaces.GPU` no-op
  called from shell JS to prove ZeroGPU reachability from the component. Everything
  after this reuses proven parts.
- **M1, foundations.** C1 transfers land as-is; tokens to CSS variables; C3 component
  library; C6 stores; the traces screen as the bridge's test surface.
- **M2, reading surfaces.** Home (with the animated backdrop), encyclopedia, reference,
  guide, walks, chat.
- **M3, camera surfaces and the rest.** Hub, sky, trail, coach chrome with honest
  badges; about, conditions, library. Capability arrives with backend phases 2 and 3
  from `lifekit-space.md`.

Validation per milestone: a screenshot pass against the app's reference shots
(`flux/app/docs/progress/`) for every migrated screen, plus the existing walk-engine
pytest suite, which stays valid because the Python engine remains the server-side twin
of the C1-transferred `vss.ts`.
