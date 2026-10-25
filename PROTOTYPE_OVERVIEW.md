# Dyscover — prototype overview and user guide

**Status snapshot: 24 October 2026**  
**Audience:** learners, judges, demonstrators, and developers maintaining the prototype.

Dyscover is a study prototype for university students, with particular attention to learners who find dense written material difficult to process. It combines uploaded course material, a conversational tutor, and an editable concept map. Learners can speak, type, inspect a source, or change the map themselves.

**Interaction is the core design idea:** learner actions influence the tutor and the shared map, and every result can lead to another question, source check, revision, or decision. See the [interactive design architecture](DESIGN_ARCHITECTURE.md) for the feedback loops, component responsibilities, and distinction between implemented behavior and future design directions.

This document describes the implementation currently in this repository. It distinguishes working features from prototype limitations. It is a development snapshot, not evidence of educational or clinical effectiveness.

## 1. What the prototype currently does

| Area | Current capability |
|---|---|
| Material handling | Select or drop study files; inspect and remove selections before starting; retain original uploads with live sessions. |
| Study conversation | Ask questions by voice or text, explain an understanding, request help, or ask for uncovered material. |
| Concept mapping | Start from a root concept; map source-supported tutor explanations immediately, or expand a complete immediate branch level on request; preserve the existing structure during ordinary turns. |
| Manual editing | Change labels and descriptions, add connected ideas, move nodes, and confirm removal of nodes and their branches. |
| Automatic review | Review created or edited content automatically and return Agreed, Corrected, or Proposed deletion feedback. |
| Source inspection | Show a short explanation, an extracted source quotation or original image, and a reference to the original upload. |
| Conversation history | Display a separate, session-wide transcript, including saved tutor feedback. |
| Session management | List, reopen, and delete saved sessions within the current browser's authenticated session ownership. |
| Accessibility features | Lexend typography, an off-white board, short labels, keyboard controls, visible focus, and rolling speech captions. |

### Live mode and scripted demo mode

**Live mode** connects the interface to the Python backend and OpenAI. It processes actual uploads, generates tutor responses, reviews content edits, and stores sessions in SQLite. It requires a working API key and the configured shared sign-in credentials.

**Scripted demo mode** runs the prepared backpropagation demonstration without an AI key. It demonstrates the interface and simulated conversation. Its replies do not analyse the learner's files, and it does not provide genuine automatic AI review of arbitrary edits. Mock session and conversation changes are held in application memory and are not a durable alternative to the live backend.

Check the mode indicator on the screen when testing. A successful scripted demonstration does not establish that the live API connection works.

## 2. Starting a study session

1. Sign in when prompted, using the email and password supplied for the demonstration.
2. Drop study files onto the home board, or click the empty study box to select files.
3. Click the populated study box to inspect the selected files. Use **Remove** for an unwanted file, or **Add files** to select more.
4. Click **Start studying**. In live mode, the backend extracts readable passages and prepares the initial concept.
5. The study screen opens with a root node. The tutor invites you to explain what you know or ask for help.
6. Speak in voice mode, or select the keyboard control to type.

For a first demonstration, use a short, readable lesson containing a few related ideas. This makes source checking and map changes easier to observe.

### Supported material

| Format | What is processed |
|---|---|
| PDF | Text is extracted page by page. Pages without extracted text are sent for image-based text extraction. |
| DOCX | Paragraph text and table text. |
| PPTX | Text from text-bearing slide shapes, with slide references. |
| TXT and MD | UTF-8 text notes. |
| PNG, JPG/JPEG, WEBP | Image-based text extraction; the original image remains available in a live session. |

The former 30-page PDF restriction has been removed. Other size limits remain; see section 10. Embedded diagrams and image-only content inside DOCX or PPTX files are not comprehensively extracted. Upload an important image separately if its content is needed for the discussion.

## 3. Talking to the tutor

### Voice input

Select voice mode and allow microphone access when the browser asks. Capture is hands-free while voice is active. Speak a short statement or question, then leave a brief pause so the prototype can detect the end of the utterance.

The voice area of the bottom dock pauses or resumes voice. The status label indicates connecting, listening, thinking, speaking, or an ended voice session. Microphone segmentation uses loudness and silence, so noise and microphone quality can affect it.

### Text input

Select the keyboard control to open the text field. Type a question or explanation, then press Enter or the send arrow. Typing works with microphone capture off. Switching to typing after pausing voice resumes message handling without restarting the microphone.

Select the small orb to return to voice mode. Text input and microphone capture are separate; the tutor may still speak a response to a typed question.

### When you do not know what to ask

You do not need to choose an interaction category. The tutor infers the intent from your message and the recent conversation.

Useful prompts include:

- “Explain this topic with an example.”
- “I don't understand that part.”
- “Expand on content we haven't covered yet.”
- “What components are missing from this map?”
- “I don't know how to proceed.”

Requests for missing material direct the tutor to identify a few important uncovered components, explain them, and ask the learner to explain one back. If the supplied material is already covered, it should say so rather than inventing additional content. This behavior depends on model output and remains subject to source validation and retry handling.

### Captions and waiting feedback

Captions use **one rolling line total**, showing the active speaker. Longer speech rolls to its most recent words. **Thinking…** appears while the tutor is processing. The tutor's last line stays on screen until the next reply, so slower readers can finish it.

The learner's own captions can be toggled from Past sessions. Open **Conversation** to read the complete saved dialogue beyond the rolling captions.

## 4. Reading the concept map

The root is on the left, with related concepts arranged in columns to the right. Separate curved connectors make each parent-child relationship easier to trace. Wider gaps separate major branches.

| Appearance | Meaning | What happens next |
|---|---|---|
| Default frame; dark styling for the root | An ordinary concept without an outstanding marker. | Open it to inspect its explanation and source. |
| Blue frame and **New** | A system-created concept that has not yet been opened. | Clicking the node clears New silently and saves that state. |
| Red frame and **Edited** | Learner-created content or a saved label/description change awaiting agreement. | Automatic review checks it against the uploaded material. |
| Orange **Corrected** styling | The tutor identifies a misconception in an actual learner statement or edited note. | Read the quoted claim, correction, and source. |
| Dashed frame, crosslines, and **Review removal** | A proposed deletion. The node still exists. | Open it and choose **Keep node** or **Confirm deletion**. |

Opening a node does not request an explanation or start speech. Audio replay requires an explicit replay control.

### Arranging the map

- Drag an existing non-root node to change its visual position.
- With a non-root node focused, use **Alt + arrow keys** to move it by keyboard.
- Use zoom controls or **Fit map to screen** to navigate a larger map.
- Use **Arrange branches** to rebuild the automatic tree arrangement. Manually positioned nodes retain their saved positions.

Dragging changes position only: it does not mark content Edited, start an AI review, or change the node's parent. Ordinary map expansion preserves existing positions. To request a semantic hierarchy change, be explicit, for example: “Move the Exceptions node under Java Refresher.”

The legend shows only node-state style indicators. New content can make the map larger; arranging or fitting the view is a deliberate user action.

## 5. Inspecting and editing a node

Click a node to open its details panel. The panel contains its short explanation, source material when available, correction information when applicable, and editing controls. Conversation is available separately from the top-bar Conversation option.

### Change content

1. Click **Edit this node**.
2. Update the short label and/or brief description.
3. Click **Save changes**.

Labels are limited to one to five words and 60 characters; descriptions are limited to 600 characters. Root content can also be edited. A content edit receives a red Edited marker and automatically queues a tutor review.

### Create a connected idea

1. Open the node that should be its parent.
2. Enter a short label in **Add a connected idea**.
3. Click **Add node**.

The new node is initially learner-authored, rather than a blue system-created node. Its initial description is the supplied label. You can expand its description through Edit this node. Creating it also queues automatic review.

### Automatic review and feedback

You do not need to send another question after creating or editing content. The backend queues the review after any current tutor response, checks the specific node against the uploaded material, and saves brief feedback in Conversation.

| Review result | Effect |
|---|---|
| **Agreed** | Clears the red marker and retains the learner's saved wording. The review supplies a source reference. |
| **Corrected** | Replaces the content-edit marker with the orange correction style and gives a supported explanation. |
| **Proposed deletion** | Preserves the node and its content, adds crosslines, and waits for the learner's decision. |

Reviews continue with voice paused; in that case feedback is delivered as text and saved without playing audio. Opening and moving nodes never trigger review. If content changes while a review is running, the backend retries against the current saved version. If review fails, it reports the error and leaves the edit marker in place.

A review is an AI judgment, not independent proof of correctness. Check its cited material, particularly when accepting a correction.

## 6. Reviewing and confirming deletion

A removal proposal and a correction are different actions. The tutor should propose removal for an unsupported system-created node instead of claiming that the learner made a misconception. Conflicting removal/correction output is handled as a removal proposal, preserving the node's content.

To respond to a proposal:

1. Open the crossed-out node.
2. Read the removal reason.
3. Choose **Keep node** to clear the proposal, or **Confirm deletion** to remove it.

Confirmed deletion also removes that node's connected child branches. The panel states this before confirmation. A learner-initiated Delete action also presents confirmation. The root cannot be deleted. There is currently no undo control for a confirmed deletion.

## 7. Sources and original files

The node panel shows short source text with a filename and a PDF page or slide number where available. Image sources can display the original image. Text citations are taken from extracted passages; OCR text can contain recognition errors.

Use the source link, or open the materials box at the top of the study screen, to access an original upload. PDF, image, and text files can open in the browser; Office documents may download. Originals are available for live uploads stored by the current implementation; some older sessions or scripted demo materials may not have a corresponding original file.

Learner-created ideas are not assigned a fabricated citation. Until reviewed, they can show **No verified source citation**. An edited description may retain the concept's previous citation, with an indication that the edit has not yet been checked.

The prototype does not currently provide comprehensive diagram interpretation, fine-grained visual highlighting on PDF pages, or independent verification of every generated explanation.

## 8. Conversation and saved sessions

### Session-wide conversation

Select **Conversation** beside Past sessions. It shows the full saved dialogue for the current session, across topics, including automatic review feedback. Node panels do not keep separate chat threads.

Live sessions store complete user and assistant messages with stable message IDs. Messages are included when a session reopens and are delivered alongside live captions, so the full transcript does not depend on the short caption display. The history panel combines saved and live messages without duplicating streamed caption fragments.

Replay controls read an individual assistant reply. When no saved audio URL is available, replay uses browser text-to-speech; it is not a recording of the original microphone audio.

### Reopening and deleting sessions

Select **Past sessions** to reopen a saved study map or delete a session. Deleting a session removes its map, dialogue, and original uploads from the live database. It does not reset the cumulative AI request counter.

The prototype uses shared sign-in credentials but gives each login a browser cookie identifying its session ownership. It is not a full account system: the same email/password in another browser does not provide a shared library of sessions. A new login or expired cookie can also change which stored sessions are accessible.

## 9. Suggested demonstration sequence

1. Sign in and upload a short lesson with several related concepts.
2. Start studying and ask for a plain-language explanation.
3. Request “missing content” and observe the existing structure expand.
4. Open a New node and observe its marker disappear without speech.
5. Inspect its source and open the original file.
6. Move a node; observe that its content marker does not change.
7. Save a supported edit and observe automatic Agreed feedback.
8. Try an incorrect or unrelated idea and inspect the resulting correction or removal proposal. Outcomes depend on the source and model judgment.
9. For a removal proposal, demonstrate Keep or explicitly confirm deletion after checking its child branches.
10. Open Conversation, then reopen the session from Past sessions to inspect saved progress.

Use sample material and disposable sessions when demonstrating deletion. Before a public demonstration, check the live connection, credentials, microphone, and remaining request allowance.

## 10. Current prototype limits

| Limit | Current implementation |
|---|---|
| Files per new live session | One to five. |
| Size per file | Up to 10 MB; empty files are rejected. |
| Extracted source text | Up to 40,000 characters across the session's extracted passages. |
| PDF pages | No fixed 30-page limit; file size and extracted-text limits still apply. |
| Uploaded images | Up to 20 million pixels, then resized for text extraction. |
| Concept map | Up to 200 nodes; complete branch batches are never silently truncated. |
| Stored sessions | Up to 30 across the backend database; deleting a session frees a slot. |
| Successful tutor turns | Up to 25 per session. Automatic content reviews do not increment this learner-turn counter, but do consume AI requests. |
| AI requests | Default service cap: 250 attempts. Current local startup setting: **5,000 attempts**. |
| Login attempts | Default cumulative cap: 50, configurable through `DYSCOVER_MAX_LOGINS`. |
| Sign-in cookie | Approximately 24 hours; it also identifies ownership of sessions. |

The AI cap counts API attempts, not conversations. Tutor generation, transcription, speech generation, OCR, automatic reviews, and retries can each consume requests. Failed requests count too. Counts are stored in SQLite and survive a normal backend restart. A spoken interaction can therefore use several attempts.

`DYSCOVER_MAX_AI_CALLS=5000` is configured in the private local startup file. That does not automatically change a hosted service's environment or the code's default. Increasing the cap permits more paid API usage; it is not a monetary budget or an OpenAI account quota.

## 11. Local setup and launch

Run the following commands from the repository root in PowerShell. Initial setup requires Python 3.12 or later and a working Node.js/npm installation.

### First-time dependency setup

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd Dyscover
npm ci
cd ..
```

### Private backend configuration

Create or edit `backend/.env.local.ps1`. It is ignored by Git. Use your own values in place of these placeholders; never commit actual credentials.

```powershell
$env:OPENAI_API_KEY = 'your-api-key'
$env:DYSCOVER_TEST_EMAIL = 'your-demo-email@example.com'
$env:DYSCOVER_TEST_PASSWORD = 'your-demo-password'
$env:DYSCOVER_SESSION_SECRET = 'a-separate-long-random-secret'
$env:OPENAI_TUTOR_MODEL = 'gpt-6-astra'
$env:DYSCOVER_MAX_AI_CALLS = '5000'
```

`DYSCOVER_SESSION_SECRET` signs the login cookie; it is separate from the sign-in password. Changing it invalidates existing signed cookies. `DYSCOVER_DB` can optionally select another private SQLite location; otherwise the database is `backend/dyscover.sqlite3`.

### Start the live backend

In the first terminal:

```powershell
. .\backend\.env.local.ps1
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

The leading `. ` loads the environment file into that terminal. After changing the file, stop the backend, load it again, and restart. Editing the file alone does not change the environment of an already running process.

### Start the live frontend

In a second terminal, from the repository root:

```powershell
cd Dyscover
$env:VITE_USE_MOCK = 'false'
npm run dev
```

Open `http://localhost:5173`, sign in, and keep both terminals running. The development frontend proxies API and WebSocket requests to port 8000.

For a built frontend served by the backend instead of Vite:

```powershell
cd Dyscover
$env:VITE_USE_MOCK = 'false'
npm run build
cd ..
```

Start the backend as above and open `http://localhost:8000`. The live/mock setting is applied during the frontend build; changing it requires rebuilding.

### Run the scripted demo without an API key

```powershell
cd Dyscover
$env:VITE_USE_MOCK = 'true'
npm run dev
```

Open the frontend and choose **Use demo files → Start studying**. This normally runs without the backend. A build explicitly configured with `VITE_REQUIRE_LOGIN=true` still requires server-backed sign-in.

## 12. Hosting and data durability

The backend can serve a built frontend from the same origin. A hosted live demo needs HTTPS, WebSocket support, the sign-in configuration, an API key, and an exact `DYSCOVER_PUBLIC_ORIGIN` value without a trailing slash. On Render, an omitted origin falls back to the service's `RENDER_EXTERNAL_URL`; set an explicit origin for a custom domain. `/api/health` reports the resolved public origin. Set the desired AI request cap in the host's environment as well.

Maps, transcripts, and original uploads are stored in SQLite. A host must retain that database to retain session data. If the host uses ephemeral storage, replacing or redeploying an instance can lose the database. The prototype has no automatic remote backup or local-to-host synchronization.

A private copy of the local database protects local progress only; it is not a backup of subsequent activity on a separate hosted database. For a simple local backup, stop the backend and copy its SQLite file to a private location before restarting it. Backups include original uploads and transcripts.

Hosted deployment behavior has not been revalidated as part of this documentation update. See the backend README for the service launch configuration.

## 13. Troubleshooting

| Symptom | Suggested action |
|---|---|
| Sign-in unavailable | Check that the backend is running and all three sign-in/session-secret variables are loaded. |
| API key rejected | Correct `OPENAI_API_KEY`, reload the private environment file, and restart the backend. |
| AI usage limit reached | Check the saved attempt count and the backend's loaded cap. Restarts do not reset the count; load the intended cap before restarting. |
| Session limit reached | Delete an unwanted stored session. This does not reset AI or login counts. |
| Connection lost | Restart the backend if necessary, refresh the frontend, and reopen the saved session. |
| Upload rejected | Check the extension, file size, readable content, and combined extracted-text limit. Split a large lesson into smaller sessions. |
| Edit remains red | Read any review error, confirm the live API connection, and try a clear, source-supported description. Failed reviews leave the edit marked. |
| Unexpected correction or removal | Inspect the cited source and Conversation. Keep a proposed node if appropriate; deletion requires your confirmation. |
| Dialogue is no longer in captions | Open Conversation; captions show only the latest line. |
| Map becomes difficult to trace | Use Arrange branches and Fit map to screen, or move individual nodes. Arrangement does not reclassify their saved parents. |
| Speech is not detected | Select voice mode, check browser microphone permission, reduce background noise, and leave a short pause after speaking. Typing remains an alternative. |
| Old behavior after an update | Restart the backend and hard-refresh the page. Rebuild the frontend when using the backend-served production build. |

## 14. Technical implementation

The architecture serves the interaction loop. Inspection uses a silent read path, movement updates presentation only, content edits trigger automatic review, and dialogue connects explanations to the evolving map. The [design architecture](DESIGN_ARCHITECTURE.md) describes these paths and their learner-control guarantees in detail.

```text
React / TypeScript frontend
  ├─ Upload and session requests ──────────────┐
  ├─ Typed turns and PCM microphone audio ────┤
  └─ Map, captions, history, and audio UI     │
                                             ▼
Python / FastAPI backend
  ├─ Shared sign-in and browser ownership
  ├─ File extraction and source passages
  ├─ Tutor plans and automatic edit reviews ───► OpenAI
  ├─ Source/schema validation and map events
  └─ SQLite: sessions, uploads, dialogue, usage
```

After initial root creation, the tutor runs a bounded backend agent with source-search and individual map-operation tools. Tools stage changes against a session snapshot; the existing source and map validator checks them before the backend saves and emits map events. Explicit deletion, renaming and movement have separate target permissions. Ambiguous spoken node names require clarification. This is one tutor agent inside FastAPI. Voice is configurable: the chained path uses transcription → tutor → speech generation; `DYSCOVER_VOICE_MODE=live` uses GPT-Live for streaming conversation and delegates grounded tutoring/map work to the same backend agent. The local environment enables Live; hosted services retain the chained default until explicitly changed.

| Workload | Configured model / override |
|---|---|
| Tutor and concept-map generation; automatic reviews | `gpt-6-astra`, controlled by `OPENAI_TUTOR_MODEL`. |
| Image text extraction | `gpt-6.1-sol`, controlled by `OPENAI_MODEL`. An explicitly set `OPENAI_MODEL` also remains the tutor fallback if `OPENAI_TUTOR_MODEL` is absent. |
| Transcription | Configured identifier `gpt-transcribe`, overridable with `OPENAI_TRANSCRIBE_MODEL`. |
| Speech generation | `gpt-4o-mini-tts`, overridable with `OPENAI_SPEECH_MODEL`; voice `marin`. |

These are configuration values, not a guarantee of availability for every API account. Tutor access and selected live review paths have been checked with the development account. The overview does not independently verify every speech model identifier or account permission.

The current implementation sends the extracted passages and recent conversation to the tutor directly. It does not yet implement an embedding-based retrieval service for large course collections.

### Code and documentation map

| Location | Responsibility |
|---|---|
| `Dyscover/src/screens/` | Upload/home workflow and study-screen composition. |
| `Dyscover/src/components/map/` | Tree layout, connectors, node styles, movement, and map controls. |
| `Dyscover/src/components/NodePanel.tsx` | Concept explanations, citations, editing, and deletion confirmation. |
| `Dyscover/src/components/ConversationHistory.tsx` | Session-wide transcript and explicit reply playback. |
| `Dyscover/src/components/Captions.tsx` | One-line rolling captions. |
| `Dyscover/src/api/` | Real API/WebSocket client and scripted demo implementation. |
| `Dyscover/src/state/store.tsx` | Live UI state, saved/live messages, and map updates. |
| `backend/app.py` | HTTP/WebSocket endpoints, speech loop, review scheduling, and persistence flow. |
| `backend/live_voice.py` | GPT-Live audio bridge, transcript persistence, delegation, and voice lifecycle. |
| `backend/agent.py` | Bounded tool loop, source search, explicit edit permissions, and staged operations. |
| `backend/ai.py` | Model configuration, structured requests, OCR, transcription, and speech requests. |
| `backend/tutor.py` | Map validation, content-review outcomes, correction provenance, and manual edits. |
| `backend/ingest.py` | File extraction, OCR routing, source passages, and upload limits. |
| `backend/store.py` | SQLite session, original-file, history, and usage storage. |
| `backend/auth.py` | Shared credentials and signed ownership cookies. |
| [Backend README](backend/README.md) | Service setup and launch commands. |
| [API contract](Dyscover/docs/API.md) | Endpoint, message, and map data contracts. |
| [Interactive design architecture](DESIGN_ARCHITECTURE.md) | Interaction loops, learner control, component responsibilities, and design evaluation. |

## 15. Progress and verification

Recent completed work includes the tutor model upgrade; local 5,000-request setting; file-selection management; removal of the fixed PDF page cap; independent text input; silent node inspection; explicit waiting feedback; one-line rolling captions; session-wide persistent dialogue; clearer hierarchy and legend; editable nodes; automatic edit review; and confirmation-based removal proposals.

Backend checks cover authentication/ownership, uploads, grounded plans, message persistence and reload, edit review outcomes, stale-review retries, voice-paused review completion, deletion confirmation behavior, and Render origin configuration. Frontend checks cover layout, markers, history rendering, message deduplication, and caption persistence. The backend-agent implementation passed **65 backend tests**, the frontend production build, and node-marker/layout checks. Live API smoke checks verified a deletion proposal without renaming, agreement with a correct user note, and a source-backed explanation that preserved the existing map.

Selected real-model checks have exercised grounded map generation, a removal proposal, and an automatic Agreed review triggered by saving an edit. Browser checks have inspected sample map styles, hierarchy/legend changes, and the conversation panel. These checks are not a complete evaluation of arbitrary course materials or real microphone conditions.

### Remaining prototype work

- Broader end-to-end testing with representative uploads, microphones, and assistive technology.
- Formal user evaluation of readability, learning usefulness, and the tutor's source interpretation.
- Durable hosted storage and a verified backup/restore procedure for hosted sessions.
- Full account management, shared cross-browser session access, and production administration.
- Retrieval for larger material collections and stronger handling of diagrams and embedded images.
- More detailed operational visibility for request consumption and review failures.
- Recovery or undo for confirmed destructive actions.

When changing a feature, update its user-facing description and limitations here alongside the implementation and API contract. Record validation scope accurately rather than treating a scripted demo as a live-service test.

### GPT-Live integration update

The current codebase supports `gpt-live-1` through an authenticated server WebSocket bridge. Speech, captions and the global transcript use Live events; the existing agent controls source checking and map changes. Text works without microphone audio and remains usable after voice failure or pause. Node inspection stays silent. Newer requests supersede stale pending map results.

Enable with `DYSCOVER_VOICE_MODE=live`, restart the backend, and reload the frontend. The local environment file has this setting. Render needs the setting separately after deployment. `chained` restores the previous pipeline. See the [backend guide](backend/README.md#gpt-live-voice-mode) for limits, rollout and protocol details.

A synthetic-audio live API check exercised transcription, delegation to the tutor, returned spoken audio and captions. Real microphone, device echo, and network interruption behaviour still require hands-on testing. Voice has a separate duration cost; switching to text keeps the voice connection alive, while pausing closes it. The default per-connection voice time limit is ten minutes.

GPT-Live verification passed **78 backend tests**, the frontend production build, Live audio protocol checks, and existing marker/layout checks. The Live tests cover transcript updates, delegation deduplication, bounded context and audio, startup failure, paused reviews, duration expiry, and superseded requests.

Tutor/image model upgrade: `gpt-6-astra` now handles tutoring and `gpt-6.1-sol` handles image text extraction, with low reasoning effort on GPT-6 requests. Local overrides and code defaults are updated; GPT-Live remains unchanged. Verification passed **80 backend tests** and live tutor tool-call/image-transcription smoke checks. This does not establish improved learning outcomes or accuracy across arbitrary course materials. Restart to apply; previously extracted materials require re-upload for fresh OCR.

### Interaction fixes

Explicit map-expansion requests now add the complete relevant immediate level of a branch in one batch, independently of explain-back. Existing structure, labels and manual positions remain intact; these additions do not certify understanding. Source-supported tutor explanations are also mapped immediately; learner repetition is optional, not a prerequisite. The agent reserves its sixth response for a final answer, and stops tool work after a complete expansion batch, an explicit edit, or three ordinary changes. Submitted text stays in an expandable You row inside the input dock during thinking, replies and errors. Network failures explicitly indicate when text was not sent.

Verification for these interaction fixes passed **86 backend tests**, the frontend production build, node/dock checks, Live audio protocol checks, and layout checks. A live Astra check added two cited outline nodes on an expansion request while preserving existing nodes and manual positions; a follow-up returned a clear response when the small source was exhausted. The latest expansion path reads all accepted source passages and uses a shared 200-node safety capacity.

### Complete branch expansion and immediate explanation mapping

“Expand the map structure” reveals all relevant missing immediate children of the root together. A named branch or **Expand subtopics** reveals that branch’s complete next level. Existing labels, structure, descriptions and manual positions remain intact. Expansion opens the branch panel, where choosing a child only inspects it; **Expand subtopics** goes one level deeper and **Learn this topic** returns to explanation and optional comprehension questions. The tutor does not recursively exhaust the whole tree without the learner choosing a branch.

Ordinary source-supported explanations now create their matching New nodes immediately. Asking the learner a question remains useful for interaction, but it does not gate map visibility or imply that merely viewing a node proves understanding.

Verification of complete-level expansion and immediate explanation mapping passed **93 backend tests**, the frontend production build, branch-action/node checks, Live audio protocol checks, and a 200-node layout check. Live Astra checks added all five supplied lifecycle topics, then all four Design subtopics, and mapped a tutor explanation without learner repetition. Existing nodes and manual positions were preserved. Manual browser/device QA and broad completeness evaluation on arbitrary courses remain outstanding.

### Lesson plan, learner progress and an open tutor agent

**What the learner sees.** Uploading material now produces a short lesson plan (three to ten concepts in teaching order). A row of steps under the legend shows each concept's state and the concept being studied; pressing a step asks the tutor to teach it. The tutor explains the current concept, invites the learner to say it in their own words, and moves on. On the map:

| Appearance | Meaning |
|---|---|
| White card | Explained by the tutor, not yet shown to be understood. |
| Green card with ✓ and quoted words | The learner explained it correctly; the quote is their own wording. |
| Dotted amber frame and **Review** | Not understood after a couple of tries, or skipped; revisit later. |
| Dashed purple line with a short label | A cross-link between branches, for example “feeds”. |

The legend lists only the states currently on the map. Nodes can be dragged with a finger or mouse, and the empty background can be dragged with a mouse to pan.

**How the tutor decides.** Keyword routing has been removed; the model decides what the learner wants from their words and the context. All map tools are available every turn, including a resolver that matches misheard names (“face” → Phase). Removal still waits for on-screen confirmation, corrections and “understood” must quote the learner, and every change is validated before saving. The prompt tells the tutor not to end two replies in a row with a question, never to repeat a question, and to give the answer and move on after a second unsuccessful attempt or when the learner says “I don't know”, “skip” or “next”. Prompts are in `backend/prompts/`; see the [backend guide](backend/README.md#backend-tutor-agent) for tools and context.

**GPT-Live.** Live now follows OpenAI's recommended structure (backchannel, interruption and delegation policies) and receives the current concept's source passage, so it can answer questions about that concept itself and delegates explanations, topic changes and map edits to the tutor.

**Measuring it.** `backend/evals/run.py` runs learner personas (steady, confused, stuck, speech errors, map editor) against the real tutor and reports progress, question loops, misheard-deletion accuracy, grounding, latency and API calls. See [Evaluations](backend/README.md#evaluations).

**Verification status.** 94 backend tests, the frontend production build and the layout/marker/audio checks pass, and the scripted demo was checked in a browser at desktop and phone widths. The new prompts, the lesson planner and GPT-Live behaviour have **not** yet been run against a real model in this change: run the evaluation and a manual session before a public demonstration.
