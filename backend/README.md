# Dyscover backend

For current feature descriptions, node states, demo instructions, and learner guidance, see the [prototype overview and user guide](../PROTOTYPE_OVERVIEW.md).

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

Tutoring and concept-map generation default to `gpt-5.4-mini`. Set `OPENAI_TUTOR_MODEL` in the backend environment to override it. Image text extraction keeps using `OPENAI_MODEL` (default `gpt-4o-mini`); an explicitly set `OPENAI_MODEL` also remains the tutor fallback when `OPENAI_TUTOR_MODEL` is unset. Speech models are configured separately. Restart the backend after changing model settings.

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
