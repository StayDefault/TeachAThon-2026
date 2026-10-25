# Dyscover backend

For current feature descriptions, node states, demo instructions, and learner guidance, see the [prototype overview and user guide](../PROTOTYPE_OVERVIEW.md).

On Render, set `DYSCOVER_PUBLIC_ORIGIN` to the exact public HTTPS origin. If omitted, the backend falls back to Render's `RENDER_EXTERNAL_URL`. `/api/health` reports the resolved `publicOrigin` to help diagnose rejected live connections. Configure the explicit origin when using a custom domain.

This service implements the contract in [`../Dyscover/docs/API.md`](../Dyscover/docs/API.md). It accepts PDF, DOCX, PPTX, TXT, MD, PNG, JPEG, and WEBP files; extracts short source passages; creates a grounded concept map; and stores sessions and original uploads in SQLite. A WebSocket carries typed turns, voice-mode microphone audio, rolling captions, map changes, and assistant PCM audio.

## Temporary judge access

The backend requires a shared judge email, password, and a separate session secret. The login issues a 24-hour HttpOnly browser cookie; each browser sees only its own study sessions. Set credentials on the server, never in Vite or the submission repository. Build the frontend in real mode and serve it from this FastAPI app so REST, WebSocket, and cookies use one origin:

```powershell
$env:OPENAI_API_KEY = 'your-api-key'
$env:DYSCOVER_TEST_EMAIL = 'judge@example.com'
$env:DYSCOVER_TEST_PASSWORD = 'a-strong-judge-password'
$env:DYSCOVER_SESSION_SECRET = 'a-long-random-secret-different-from-the-password'
$env:DYSCOVER_PUBLIC_ORIGIN = 'https://your-public-domain.example'
$env:DYSCOVER_DB = 'backend/dyscover.sqlite3'
cd Dyscover
$env:VITE_USE_MOCK = 'false'
npm ci
npm run build
cd ..
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000
```

Use an HTTPS host or reverse proxy that supports WebSockets, and persist `DYSCOVER_DB` on a private volume. Point the public domain at port 8000; FastAPI serves the built frontend. The public origin must exactly match the browser origin, with no trailing slash. Do not publish the judge password in the frontend bundle. The default safety caps are 30 sessions total, 25 tutor turns per session, 250 OpenAI request attempts total, and 50 login attempts total. These are lifetime caps in SQLite; `DYSCOVER_MAX_AI_CALLS` and `DYSCOVER_MAX_LOGINS` can change the latter two before launch. Keep the OpenAI account's own spending limit enabled. Old sessions remain on the private volume after cookies expire; remove the volume after judging if it contains disposable demo data.

For a hosted scripted demo without an OpenAI key, build with `VITE_USE_MOCK=true VITE_REQUIRE_LOGIN=true npm run build`. Keep the FastAPI service running for sign-in and set `DYSCOVER_TEST_EMAIL`, `DYSCOVER_TEST_PASSWORD`, `DYSCOVER_SESSION_SECRET`, and `DYSCOVER_PUBLIC_ORIGIN`; `OPENAI_API_KEY` is not needed. A local mock build without `VITE_REQUIRE_LOGIN=true` still runs without the server.

## Run locally

Tutoring and concept-map generation default to `gpt-6-astra`. Set `OPENAI_TUTOR_MODEL` in the backend environment to override it. Image text extraction uses `OPENAI_MODEL` (default `gpt-6.1-sol`); an explicitly set `OPENAI_MODEL` also remains the tutor fallback when `OPENAI_TUTOR_MODEL` is unset. Speech models are configured separately. Restart the backend after changing model settings.

From the project root, open two PowerShell terminals. First, start the backend (the leading `. ` loads your local credentials into this terminal):

```powershell
. .\backend\.env.local.ps1
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

In the second terminal, start the frontend in live mode:

```powershell
cd Dyscover
$env:VITE_USE_MOCK = 'false'
npm run dev
```

Open `http://localhost:5173` and sign in with `DYSCOVER_TEST_EMAIL` and `DYSCOVER_TEST_PASSWORD` from your local file. Keep both terminals open. The Vite proxy sends `/api` REST and WebSocket traffic to port 8000. The real backend needs actual files; the mock-only demo button is hidden in live mode. `/api/health` reports whether an API key is configured, but does not validate it.

For first-time setup, use Python 3.12 or later and run these commands from the project root before launching:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd Dyscover
npm ci
```

Create `backend/.env.local.ps1` with `OPENAI_API_KEY`, `DYSCOVER_TEST_EMAIL`, `DYSCOVER_TEST_PASSWORD`, and `DYSCOVER_SESSION_SECRET` assignments. Keep this Git-ignored file private. After changing it, stop and restart the backend so the new values load.

Uploads and recent conversation are sent to OpenAI for OCR, map generation, transcription, and speech. Do not upload material you cannot send to that service. Node quotes are taken directly from extracted passages; OCR can misread images, and a cited quote does not by itself prove an AI explanation is correct. Review the source panel before relying on a correction.

The local voice segmenter detects utterances by loudness and silence. It is suitable for a prototype but needs calibration with real microphones and noisy rooms. The current Speech API model is scheduled for retirement in 2027; migrate the voice path to OpenAI Realtime before then.

## Tests

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend -v
```

The tests mock the external AI requests and cover the REST shape, WebSocket map events, source validation, and speech segmentation. Set `DYSCOVER_DB` to choose a different SQLite path; otherwise data stays in `backend/dyscover.sqlite3`.

## Backend tutor agent

No separate agent server, SDK, dependency, or database migration is required. Restart the backend using the commands above; the real API automatically uses `agent.py` after initial root creation. The existing tutor model setting applies. The mock frontend stays scripted.

The agent can search uploaded passages and stage individual additions, reviews, removal proposals, renames, and parent changes. It returns only the spoken answer; server code constructs the map plan. Source search is required before ordinary explanations and content-changing tools. Automatic reviews must perform a source lookup and record an explicit decision before answering. All changes are validated before saving. An ordinary turn is limited to six model responses (at most five tool rounds, followed by a reserved final answer) and three changed nodes; explicit branch expansion adds one complete immediate level in a single validated batch; each response counts toward `DYSCOVER_MAX_AI_CALLS`. Search ranks local passages by word overlap and returns up to six per call; this is a prototype retrieval strategy, not semantic search.

Explicit rename and move commands grant only their corresponding tool and exact target. Delete commands expose only removal proposals; they never permit renaming. Unrecognized or duplicate node names require clarification. Selecting a node provides context for commands such as “delete this node” without triggering speech. Actual deletion remains a user-confirmed action. Source-supported ideas explained by the tutor become New nodes immediately; learner repetition is not required. Explicit requests such as “expand the map structure” add all relevant missing immediate subtopics of the target branch in one batch. Global map expansion targets the root; an explicit node ID or named topic targets that branch; a generic “expand further” uses the selected node. Existing nodes and positions remain intact. The branch panel opens with all children and **Expand subtopics** / **Learn this topic** actions. Selecting a child is silent; invoking an action starts a tutor turn. Expansion reads all accepted source passages, rather than only six search results. The shared map safety capacity is 200 nodes; an oversized batch is rejected as a whole with a capacity explanation, never silently truncated.

Tools stage operations against a snapshot. A concurrent map change causes a retry against current state; exhausting the retry leaves the newer map intact. No new schema is needed for saved sessions. Automatic reviews retain their existing per-connection queue; disconnect recovery is not a durable job system.

Run regression checks from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend -p 'test*.py' -q
cd Dyscover
npm run build
node scripts/check-node-markers.mjs
node scripts/check-layout.mjs
node scripts/check-live-audio.mjs
```

To inspect timing, run Uvicorn with `--log-level info`. Logs record transcription time, tutor/agent time, speech audio-ready time, tool names, and target IDs; they do not log credentials or raw audio. Audio-ready time measures server generation, not the moment sound reaches the listener.

Deploy to a separate staging Render service before updating the public demo. Use the existing build/start commands and separate credentials/database, verify session reopening, source uploads, silent selection, edits and deletion confirmation, then deploy the tested commit to the public service. Keep the previous release available for rollback. Free-tier ephemeral storage remains temporary. Choose GPT-Live using the voice-mode configuration below; the chained pipeline remains available for rollback.

## GPT-Live voice mode

Install the updated requirements, then load your existing credentials and select Live:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
. .\backend\.env.local.ps1
$env:DYSCOVER_VOICE_MODE = 'live'
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

The local environment file now selects `live`. Restart the backend and reload the browser. Keep `VITE_USE_MOCK=false` for the real service. `/api/health` reports `voiceMode`. Use `DYSCOVER_VOICE_MODE=chained` and restart to restore the previous speech pipeline. When unset, the server retains the chained default so deploying code alone does not activate paid continuous voice on Render.

Live defaults to `OPENAI_LIVE_MODEL=gpt-live-1` and `OPENAI_LIVE_VOICE=marin`; the existing `OPENAI_API_KEY` stays on the server. The backend agent keeps its separate `OPENAI_TUTOR_MODEL`. The only additional dependency is `websockets`.

The browser connects to the same authenticated Dyscover WebSocket. FastAPI opens a primary GPT-Live WebSocket, streams paced PCM16 at 16 kHz in both directions, and handles client delegation. No API key or provider session credential is sent to the browser. Direct text input uses the same backend agent without needing microphone permission. Node selection stays within the application and never starts a voice turn.

The server builds delegated requests from timestamped input transcripts; the delegation event itself has no task text. It preserves delegation IDs, ignores repeated IDs, validates/stages map changes, discards results superseded by newer learner input, and returns verified results through Live commentary. Actual spoken transcripts populate Conversation, including partial speech on interruption. Stable message IDs let subsequent fragments update their existing history entry. Live has no transcript turn-completed event: the prototype groups a speaker's fragments using a 0.8-second quiet interval. This is approximate grouping, not word-aligned caption timing.

Live mode bypasses local utterance segmentation, the separate transcription request, the speech synthesis request, and proportional caption simulation. The chained implementation remains available. The browser uses playback completion to update speaking state; input transcript activity clears queued speech for interruption. Device/network testing is still needed to assess real-world interruption latency and echo handling.

**Usage:** Live is a continuously running paid voice connection, including silence. Switching to text stops microphone capture but keeps Live connected to speak responses. Pause/end voice closes the provider connection; typing and edit reviews continue as text. `DYSCOVER_LIVE_MAX_SECONDS` defaults to 600 seconds per connection (maximum 1,800); reaching it closes voice while leaving text available. Resume creates a new connection with recent saved history. Starting a provider connection consumes one existing AI-request allowance; backend agent calls consume their own allowances. Request counts do not measure voice duration or replace provider spending controls.

For Render, install the updated requirements and deploy the updated frontend/backend together, then set `DYSCOVER_VOICE_MODE=live` in the service environment. Keep the existing origin, authentication and API-key settings. Test on staging before enabling the public demo. Roll back with `DYSCOVER_VOICE_MODE=chained`. No public deployment is performed by editing this configuration locally.

Protocol references: [GPT-Live WebSockets](https://developers.openai.com/api/docs/guides/voice-websockets?api=live), [client delegation](https://developers.openai.com/api/docs/guides/live-delegation), and [session/transcript handling](https://developers.openai.com/api/docs/guides/live-conversations).

The tutor/image upgrade uses `gpt-6-astra` for tutoring and `gpt-6.1-sol` for image text extraction, both with low reasoning effort for responsiveness. Set both `OPENAI_TUTOR_MODEL` and `OPENAI_MODEL` explicitly on Render if older environment values exist. Existing sessions retain their previously extracted text; re-upload an image or scanned PDF to process it with the upgraded model. GPT-Live remains `gpt-live-1`. Model quality on your own course materials still needs comparison; this upgrade increases token costs.

Submitted text now stays in an expandable You row inside the input dock while the tutor thinks or replies. It remains available after a tutor error; a disconnected transport explicitly reports that the message was not sent. Tool work reserves the last response for a final answer instead of treating tool-budget exhaustion as a request-length problem.

For explicit expansion, source search supplies every accepted passage so the tutor can construct the complete relevant next level. Ordinary explanation searches retain relevance ranking and a six-passage result window.
