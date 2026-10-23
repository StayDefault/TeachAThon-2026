# DysCover API contract (frontend ⇄ backend)

The frontend already implements the client side of everything below (`src/api/http.ts`).
TypeScript source of truth for every shape: `src/types.ts`. **If you change a shape, change it in both places.**

Base path: `/api`. All JSON is UTF-8. Timestamps are ISO 8601 strings.

The backend requires `POST /api/auth/login` with JSON `{ "email": "…", "password": "…" }`. It sets a 24-hour HttpOnly cookie. `GET /api/auth/status` checks that cookie. All other session REST calls and the live WebSocket require the cookie; sessions are isolated per browser. A hosted scripted mock can use the same login with `VITE_REQUIRE_LOGIN=true`.

---

## 1. REST

### `POST /api/sessions` — upload materials, create a session

`multipart/form-data`, one or more `files` fields (PDF, images, docx/pptx, txt/md).

Response `200`:

```json
{
  "session":   { "id": "s_123", "title": "Backpropagation", "topic": "Neural networks", "updatedAt": "2026-10-21T14:03:00Z" },
  "materials": [
    { "id": "m1", "name": "Lecture3_Backprop.pdf", "kind": "pdf", "label": "Lecture slides" }
  ]
}
```

- `title` = short topic name the backend infers from the files (shown under the material box and in the sidebar).
- `kind` ∈ `pdf | image | doc | text`. `label` is a short human description.
- The backend should parse/extract text **per page/slide** here (OCR for images), so later answers can cite `page` + `quote`.

### `GET /api/sessions` — sidebar list

Response: `SessionSummary[]`, newest first.

```json
[{ "id": "s_123", "title": "Backpropagation", "topic": "Neural networks", "updatedAt": "…", "durationMin": 23 }]
```

The UI groups them into Today / This week / Earlier using `updatedAt`.

### `GET /api/sessions/:id` — reopen a session

```json
{ "session": { … }, "materials": [ … ], "nodes": [ MapNode, … ] }
```

### `GET /api/sessions/:id/nodes/:nodeId` — node panel content

```json
{
  "nodeId": "chain",
  "title": "Chain rule",
  "breadcrumb": ["Backpropagation"],
  "source": {
    "materialId": "m1",
    "fileName": "Lecture3_Backprop.pdf",
    "page": 14,
    "context": "Lecture 3 · Backpropagation",
    "quote": "Each layer's error = the error from the layer after × its own local gradient."
  },
  "summary": "One or two plain-language sentences.",
  "messages": [
    { "id": "c1", "role": "user", "text": "Why does it go backwards?", "at": "…" },
    { "id": "c2", "role": "assistant", "text": "Each layer needs…", "at": "…", "audioUrl": "/api/audio/c2.mp3" }
  ]
}
```

- `quote` must be **verbatim** from the material — it is shown highlighted as "from your slides".
- `audioUrl` is optional. Without it, the "play" buttons fall back to browser text-to-speech.

---

## 2. Live session — WebSocket `GET /api/sessions/:id/live`

Opened as soon as a session starts. Voice is **always on**: there is no push-to-talk.

| Frame type | Direction | Content |
|---|---|---|
| binary | client → server | microphone audio, **PCM16 mono 16 kHz**, ~2048-sample chunks, continuous |
| binary | server → client | assistant speech, **PCM16 mono 24 kHz**, any chunk size; the client queues them gap-free |
| text   | both | one JSON event per frame (below) |

### 2.1 Server → client events (`ServerEvent`)

| `type` | Payload | UI effect |
|---|---|---|
| `voice.status` | `status`: `connecting \| listening \| thinking \| speaking \| ended` | Dock label + orb state. Sending `listening` while audio is playing **cuts playback** (barge-in). |
| `voice.level` | `level`: 0..1 | Orb size + waveform. Optional — the client already computes levels locally from mic/playback. |
| `caption` | `caption`: `{ role: "user"\|"assistant", text, final }` | Subtitles. Send the **full text so far** each time (not deltas); set `final: true` on the last one. |
| `prompt.choices` | `choices`: `[{ id, title, subtitle? }]` | Quick-reply cards above the captions (e.g. "I'm new to this" / "I know a bit"). |
| `prompt.clear` | — | Hide the cards. |
| `map.reset` | `nodes`: `MapNode[]` | Replace the whole map (e.g. the first seed node). |
| `map.add` | `node`: `MapNode` | Add (or replace by id) one node. It slides in; layout re-flows. |
| `map.update` | `nodeId`, `patch`: partial `MapNode` | e.g. mark a node `corrected`, clear `new`, rename. |
| `map.remove` | `nodeId` | Removes the node **and its subtree**. |
| `map.focus` | `nodeId` | Scroll to the node and pulse it for ~2 s. |
| `error` | `message` | Logged; shown nowhere yet. |

`MapNode`:

```json
{
  "id": "update",
  "parentId": "root",
  "label": "Weight update",
  "status": "corrected",
  "correction": { "said": "backprop updates weights", "actually": "Backprop finds gradients. The optimiser (SGD) updates weights." },
  "hiddenChildren": 0,
  "order": 3
}
```

Rules the UI relies on:

- Exactly **one** node has `parentId: null` (the root/thesis). Root may have a `subtitle`.
- `label` ≤ ~5 words. Details are **spoken**, not written on the map.
- `status`: `normal`, `new` (just added — set back to `normal` after the next turn or two), `corrected` (needs `correction`).
- Start with **5–8 nodes max**; expand only on request. `hiddenChildren > 0` shows a "+N" badge.
- `order` sorts siblings (ascending).

### 2.2 Client → server events (`ClientEvent`)

| `type` | Payload | When |
|---|---|---|
| `user.text` | `text` | Learner typed in text mode. Treat exactly like a spoken turn. |
| `user.choice` | `choiceId` | Learner tapped a quick-reply card. |
| `user.node_opened` | `nodeId` | Learner opened a node panel. The tutor may briefly explain it. |
| `user.map_edit` | `op`: `rename\|remove\|add`, `nodeId?`, `parentId?`, `label?` | Learner edited the map by hand (UI applies it optimistically). |
| `session.end` | — | Learner tapped the voice area to end. Stop listening and speaking. The client also stops sending mic audio. |
| `session.resume` | — | Learner tapped again to resume. |

### 2.3 A typical turn

```
client  ── binary mic audio (continuous) ──────────────────────────►
server  ◄─ {"type":"voice.status","status":"listening"}
server  ◄─ {"type":"caption","caption":{"role":"user","text":"I think backprop","final":false}}
server  ◄─ {"type":"caption","caption":{"role":"user","text":"I think backprop updates the weights.","final":true}}
server  ◄─ {"type":"voice.status","status":"thinking"}
server  ◄─ {"type":"map.update","nodeId":"update","patch":{"status":"corrected","correction":{…}}}
server  ◄─ {"type":"map.focus","nodeId":"update"}
server  ◄─ {"type":"voice.status","status":"speaking"}
server  ◄─ binary assistant audio …  +  {"type":"caption","caption":{"role":"assistant","text":"Nearly! …","final":false}} …
server  ◄─ {"type":"voice.status","status":"listening"}
```

---

## 3. Suggested map tools for the LLM

The easiest backend: give the tutor model these **tools** and forward each call as the matching `map.*` event (plus store it so `GET /sessions/:id` can return the map).

```json
[
  { "name": "add_node", "description": "Add one idea to the learner's map. Keep labels ≤ 5 words.",
    "parameters": { "type": "object", "required": ["id", "parentId", "label"], "properties": {
      "id": { "type": "string" }, "parentId": { "type": "string" }, "label": { "type": "string" },
      "sourcePage": { "type": "integer" }, "sourceQuote": { "type": "string", "description": "verbatim sentence from the materials" } } } },
  { "name": "correct_node", "description": "The learner has a misconception about this node.",
    "parameters": { "type": "object", "required": ["id", "said", "actually"], "properties": {
      "id": { "type": "string" }, "said": { "type": "string" }, "actually": { "type": "string" } } } },
  { "name": "rename_node", "parameters": { "type": "object", "required": ["id", "label"], "properties": { "id": { "type": "string" }, "label": { "type": "string" } } } },
  { "name": "remove_node", "parameters": { "type": "object", "required": ["id"], "properties": { "id": { "type": "string" } } } },
  { "name": "focus_node",  "parameters": { "type": "object", "required": ["id"], "properties": { "id": { "type": "string" } } } },
  { "name": "offer_choices", "parameters": { "type": "object", "required": ["choices"], "properties": {
      "choices": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string" }, "title": { "type": "string" }, "subtitle": { "type": "string" } } } } } } }
]
```
