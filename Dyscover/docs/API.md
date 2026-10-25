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
    { "id": "m1", "name": "Lecture3_Backprop.pdf", "kind": "pdf", "label": "Lecture slides", "originalAvailable": true }
  ]
}
```

- `title` = short topic name the backend infers from the files (shown under the material box and in the sidebar).
- `kind` ∈ `pdf | image | doc | text`. `label` is a short human description.
- `originalAvailable` indicates whether the uploaded file can be opened. Older sessions created before file retention may have `false`.
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

### `GET /api/sessions/:id/materials/:materialId` — open an original upload

Returns the uploaded file with an inline disposition for PDF, images, and text; other documents download. Requires the session owner's cookie. Returns `404` when the file is unavailable.

### `DELETE /api/sessions/:id` — delete a session

Returns `204` and removes its saved map and original uploads. Returns `404` for missing sessions or sessions owned by another browser.

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
  "summary": "Two or three short, source-grounded sentences retained with this concept.",
  "userEdited": false
}
```

- `quote` must be **verbatim** from the material — it is shown highlighted as "from your slides".
- `source` may be `null` for a learner-created node until its claim has been checked. Image sources show the original image; other sources link to the original file.
- `userEdited` marks a learner-authored description so it is shown as their note, not as verified teaching content.

### `GET /api/sessions/:id/history` — session conversation

Returns all saved `ChatMessage` objects in conversation order: `{ id, role, text, at, audioUrl? }`. The session snapshot also includes `messages` so reopening restores the transcript immediately. Requires the session owner's cookie. Historical node associations are omitted; new messages are saved at session scope. Node panels do not include conversation messages. The Conversation option merges stored history with live messages using their saved IDs. Replay is explicit; `audioUrl` is optional and falls back to browser speech.

Dragging only changes `position`; it does not mark a node Edited. Content changes remain marked until tutor agreement. A removal review preserves the node's content and takes precedence over conflicting correction fields; pending removals wait for Keep or confirmed deletion.

Saving a content edit or creating a node automatically queues a tutor review. The tutor reviews only that node and returns Agreed, Corrected, or Proposed deletion feedback, saved in the session conversation. Reviews continue when voice is paused and then return text without audio. Moving or opening nodes never triggers a review. A failed review leaves the edit marker in place and reports the error.

---

## 2. Live session — WebSocket `GET /api/sessions/:id/live`

Opened as soon as a session starts. Voice mode is hands-free; text mode stops microphone capture until voice mode is selected again. Map edits and new-marker acknowledgements remain available while voice is paused. Captions show one rolling line total for the active speaker and the tutor's last line stays until the next reply; the complete transcript remains in Conversation. Caption events may include `message: ChatMessage` with the full saved reply and stable ID, independently of the rolling caption text.

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
| `caption` | `caption`: `{ role: "user"\|"assistant", text, final }` | Subtitles. Send the **full text so far** as speech progresses (not deltas); the UI rolls within one line. Set `final: true` on the last one. |
| `map.reset` | `nodes`: `MapNode[]` | Replace the whole map (e.g. the first seed node). |
| `map.add` | `node`: `MapNode` | Add (or replace by id) one node, preserving existing positions. Arrange branches explicitly rebuilds the automatic tree layout, retaining manually placed nodes. |
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
  "order": 3,
  "position": { "x": 520, "y": 180 },
  "userEdited": true,
  "pendingRemoval": null
}
```

Rules the UI relies on:

- Exactly **one** node has `parentId: null` (the root/thesis). Root may have a `subtitle`.
- `label` ≤ ~5 words. Details are **spoken**, not written on the map.
- `status`: `normal`, `new` (system-created; clears when opened), `corrected` (orange, needs `correction`).
- `userEdited: true` shows a red Edited marker until a source-grounded tutor review agrees. A correction replaces the edit marker with the orange correction style.
- `pendingRemoval` holds a removal reason. Proposed removals show crosslines and remain in the map until the learner confirms deletion; Keep clears the proposal.
- `position` is optional and stores a learner-placed pixel position on the map canvas; AI updates preserve it.
- Source-supported ideas explained by the tutor appear as New nodes without explain-back. Explicit expansion adds all relevant immediate children in one validated batch, preserving existing nodes and positions. `hiddenChildren > 0` shows a "+N" badge.
- `order` sorts siblings (ascending).

### 2.2 Client → server events (`ClientEvent`)

| `type` | Payload | When |
|---|---|---|
| `user.text` | `text` | Learner typed in text mode. Treat exactly like a spoken turn. |
| `user.node_opened` | `nodeId` | Selection context only. Opening a node sends its ID; an empty ID clears selection. This event never starts speech, a tutor turn, or content review. |
| `user.map_edit` | `op`: `rename\|remove\|add\|move\|update\|acknowledge\|keep`, `nodeId?`, `parentId?`, `label?`, `summary?`, `x?`, `y?` | Learner edits the map. `acknowledge` clears New silently; `keep` rejects proposed removal; `remove` confirms deletion of the node and its subtree. Rejected edits receive an error and `map.reset`. |
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

### GPT-Live transport extension

With server environment `DYSCOVER_VOICE_MODE=live`, the same authenticated `/api/sessions/:id/live` endpoint bridges GPT-Live. The chained pipeline remains the default when unset.

- `voice.audio {sampleRate: 16000}` arrives before audio and configures the browser PCM player. Input and output are mono PCM16 at 16 kHz in Live mode; chained output remains 24 kHz.
- `voice.interrupt` flushes queued browser playback. In Live mode, a listening status alone must not discard queued speech.
- Transcript caption events update an existing `message.id` as fragments arrive. The message text is full text so far. The client replaces the matching history entry rather than keeping the first fragment forever.
- Node selections are stored only as silent backend context. Opening a node never sends a provider commentary or tutor request.
- `session.end` closes the provider voice connection while keeping the application WebSocket available for typed turns and edit reviews. `session.resume` starts a fresh provider session with saved context.
- Provider startup failure leaves text available. Backend results are saved as text if voice is unavailable.

GPT-Live delegation metadata stays server-side. Only backend-validated map events are sent to the browser. Captions are actual Live transcripts, grouped approximately by speaker/quiet interval; they are not simulated against generated audio length.

`map.expanded {nodeId}` follows the saved map additions and opens the parent branch panel. Its child list lets the learner inspect a subtopic silently, explicitly expand it, or choose Learn this topic. Explicit expansion uses one `expand_branch` batch against all accepted sources; ordinary turns still use individual tools. The shared node safety capacity is 200.
