# AGENTS.md — read this first

You are working on **DysCover**, a voice-first study tool for **dyslexic university students**.
The learner drops lecture slides / handouts / photos onto a whiteboard; a voice tutor talks with them
and builds a small, editable **concept map** as they talk, correcting misconceptions on the map.
The demo uses University of Edinburgh "Learn" course materials.

The **frontend is finished as a working demo** (with a scripted fake backend).
Your job is most likely the **real backend + logic** behind it. This file tells you what exists,
what the contract is, and what must not be broken.

---

## 1. Run it

```bash
npm install
npm run dev          # http://localhost:5173 — runs the scripted demo, no server needed
npm run build        # type-check + production build
```

`.env` (copy from `.env.example`):

| var | meaning |
|---|---|
| `VITE_USE_MOCK=true` (default) | use `src/api/mock.ts` — scripted demo |
| `VITE_USE_MOCK=false` | use `src/api/http.ts` — real REST + WebSocket client |
| `VITE_REQUIRE_LOGIN=true` | require server-backed email/password sign-in even in mock mode (for hosted demos) |
| `VITE_API_BASE` | backend origin; empty = Vite dev proxy `/api → http://localhost:8000` (see `vite.config.ts`) |

Demo flow to try: **Use demo files → Start studying → "I'm new to this"** and watch (~30 s). Then click any node.

---

## 2. Product rules (do not break these)

1. **Voice is always on.** No push-to-talk, no "tap to talk". Opening a session starts listening.
   The only voice control is *end / resume* (tap the voice area of the dock).
2. **The map shows hints, the voice explains.** Node labels ≤ ~5 words. Start with 5–8 nodes; expand on request.
3. **Corrections are the core feature.** When the learner says something wrong, mark that node `corrected`
   with `said` (struck through) and `actually` (one sentence), focus it, and explain it out loud.
4. **Everything is grounded in the learner's files.** Every node should have a source (`fileName`, `page`, verbatim `quote`).
5. **Every spoken word is also on screen** (captions). The learner's own speech is shown small ("YOU …") so they can see they were heard correctly; it can be turned off in the sidebar.
6. Text mode is optional and secondary (dock ratio 1 : 9 voice-first, flips to 9 : 1 when typing).
7. Dyslexia-friendly UI: Lexend font, off-white board (never pure white page), no italics for body text, short lines, ≥ 44 px touch targets. Keep it.

---

## 3. Architecture (frontend)

```
src/
  types.ts                 ← data model + all live events (source of truth, mirrored in docs/API.md)
  api/
    backend.ts             ← DysCoverBackend interface: the ONLY way the UI talks to a backend
    index.ts               ← picks mock or http via VITE_USE_MOCK
    mock.ts, mockData.ts   ← scripted demo (story about backpropagation)
    http.ts                ← real client: REST + WebSocket + mic/speaker streaming
  lib/
    audio.ts               ← mic capture (PCM16 16 kHz) + gap-free PCM16 playback, both with loudness levels
    speech.ts              ← replay buttons: plays audioUrl or falls back to browser TTS
    useLocalSpeech.ts      ← Home-screen greeting (no backend session exists yet)
  state/
    store.tsx              ← useReducer store; applies ServerEvents; owns the live connection
    level.ts               ← voice loudness (separate tiny store so only the orb re-renders)
  screens/
    HomeScreen.tsx         ← whiteboard, drag & drop, cards fly into the study box
    StudyScreen.tsx        ← map + quick-reply choices + node panel
  components/
    Header.tsx             ← "Past sessions" (left) · logo (right)
    SessionsSidebar.tsx    ← left drawer (~1/6 width), closed by default
    MaterialBox.tsx        ← study box under the logo; flies in from screen centre
    map/layout.ts          ← pure tidy-tree layout (left → right)
    map/ConceptMap.tsx     ← renders nodes/edges, zoom/fit, focus pulse, dimming
    NodePanel.tsx          ← quarter-screen panel: source quote, summary, conversation
    Captions.tsx           ← live subtitles (assistant big, learner small)
    VoiceDock.tsx, Orb.tsx ← glass dock, iridescent orb that scales with loudness
  styles/global.css        ← design tokens (colours, font, radii) — reuse them
```

Data flow: backend → `ServerEvent` → `store.tsx` reducer → React. UI → `send(ClientEvent)` → backend.
The UI never calls `fetch` directly; everything goes through `api` (`src/api/index.ts`).

---

## 4. What the backend must do

Full contract with JSON examples: **`docs/API.md`**. Summary:

| Endpoint | Purpose |
|---|---|
| `POST /api/sessions` (multipart `files`) | parse materials per page (OCR images), infer a short topic title, create session |
| `GET /api/sessions` | list for the sidebar |
| `GET /api/sessions/:id` | session + materials + current map |
| `GET /api/sessions/:id/nodes/:nodeId` | node panel: source quote, summary, messages |
| `WS /api/sessions/:id/live` | always-on voice: binary audio both ways + JSON events |

Suggested backend design (any language; Python FastAPI or Node are both fine):

1. **Ingest**: extract text per page/slide; keep `(materialId, page, text)` chunks; embed them for retrieval.
2. **Live loop**: bridge the WebSocket to a speech pipeline — either a realtime speech-to-speech model, or
   STT → LLM → TTS. Stream both sides' transcripts back as `caption` events (full text so far, `final` at end).
3. **Tutor LLM** with retrieval over the chunks and the **map tools** in `docs/API.md §3`
   (`add_node`, `correct_node`, `rename_node`, `remove_node`, `focus_node`, `offer_choices`).
   Forward every tool call as the matching `map.*` / `prompt.*` event and persist the map.
4. **Opening of a new session** (what the mock does — reproduce it):
   `map.reset` with only the root node → say "I've read your files. How much do you already know about <topic>?" →
   `prompt.choices` ["I'm new to this", "I know a bit"]. New → guide from the start, adding nodes as you go.
   Know a bit → let them explain, add what they mention, **correct** what's wrong.
5. **Barge-in**: when the learner starts speaking, send `voice.status: listening` — the client cuts playback.
6. `session.end` → stop listening/speaking (the client stops sending audio); `session.resume` → continue.

Suggested tutor system-prompt essentials: speak in short sentences; one idea at a time; ask the learner to
explain in their own words; never dump long text onto the map; ground every claim in the uploaded material.

---

## 5. Where to change things

| Want to… | Edit |
|---|---|
| change demo script / content | `src/api/mock.ts`, `src/api/mockData.ts` |
| add a new live event | `src/types.ts` → reducer in `src/state/store.tsx` → `docs/API.md` |
| change map look | `src/components/map/ConceptMap.css`; spacing in `map/layout.ts` (`COL`, `GAP`, `sizeOf`) |
| change colours / font | `src/styles/global.css` tokens |
| real audio formats | `src/lib/audio.ts` + `docs/API.md §2` |

Known gaps / TODO (good next tasks):

- Map editing by hand: `user.map_edit` exists in the contract, but there's no UI for rename/drag/delete yet.
- "+N hidden" nodes: the badge renders, but expanding them needs a `user.expand` event (or reuse `user.node_opened`).
- Home greeting is text-only (no audio) because no session exists yet; add a TTS call in `useLocalSpeech.ts` if wanted.
- Recall practice (hide some labels, learner recalls them) was in the original idea; not built.
- `error` events are only logged.

---

## 6. Conventions

- TypeScript strict; no `any`. React 18 function components; plain CSS files next to components; BEM-ish class names.
- No UI libraries — keep the bundle small and the look custom.
- Keep everything accessible: real `<button>`s, `aria-label` on icon buttons, `aria-live` captions, visible focus.
- Respect `prefers-reduced-motion` (already handled globally).
- After changes: `npm run build` must pass.
