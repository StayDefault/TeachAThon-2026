# Dyscover backend

This service implements the contract in [`../Dyscover/docs/API.md`](../Dyscover/docs/API.md). It accepts PDF, DOCX, PPTX, TXT, MD, PNG, JPEG, and WEBP files; extracts short source passages; creates a grounded concept map; and stores sessions in SQLite. A WebSocket carries typed turns, continuous microphone audio, captions, map changes, and assistant PCM audio.

## Temporary judge access

The live backend now requires a shared judge password and a separate session secret. The login issues a 24-hour HttpOnly browser cookie; each browser sees only its own study sessions. Set secrets on the server, never in Vite or the submission repository. Build the frontend in real mode and serve it from this FastAPI app so REST, WebSocket, and cookies use one origin:

```powershell
$env:OPENAI_API_KEY = 'your-api-key'
$env:DYSCOVER_JUDGE_PASSWORD = 'a-strong-judge-password'
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

Use an HTTPS host or reverse proxy that supports WebSockets, and persist `DYSCOVER_DB` on a private volume. Point the public domain at port 8000; FastAPI serves the built frontend. The public origin must exactly match the browser origin, with no trailing slash. Do not publish the judge password in the frontend bundle. The default safety caps are 3 sessions per browser, 30 sessions total, 25 tutor turns per session, 250 OpenAI request attempts total, and 50 login attempts total. These are lifetime caps in SQLite; `DYSCOVER_MAX_AI_CALLS` and `DYSCOVER_MAX_LOGINS` can change the latter two before launch. Keep the OpenAI account's own spending limit enabled. Old sessions remain on the private volume after cookies expire; remove the volume after judging if it contains disposable demo data.

## Run locally

Use Python 3.12 or later. From the project root in PowerShell:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
# Set OPENAI_API_KEY in your environment before starting the server.
# Also set DYSCOVER_JUDGE_PASSWORD and DYSCOVER_SESSION_SECRET as above.
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd Dyscover
Copy-Item .env.example .env
# Change VITE_USE_MOCK to false in .env.
npm ci
npm run dev
```

Open `http://localhost:5173`. The Vite proxy sends `/api` REST and WebSocket traffic to port 8000. The real backend needs actual files; the mock-only demo button is hidden in real mode. `/api/health` reports whether an API key is configured.

Uploads and recent conversation are sent to OpenAI for OCR, map generation, transcription, and speech. Do not upload material you cannot send to that service. Node quotes are taken directly from extracted passages; OCR can misread images, and a cited quote does not by itself prove an AI explanation is correct. Review the source panel before relying on a correction.

The local voice segmenter detects utterances by loudness and silence. It is suitable for a prototype but needs calibration with real microphones and noisy rooms. The current Speech API model is scheduled for retirement in 2027; migrate the voice path to OpenAI Realtime before then.

## Tests

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend -v
```

The tests mock the external AI requests and cover the REST shape, WebSocket map events, source validation, and speech segmentation. Set `DYSCOVER_DB` to choose a different SQLite path; otherwise data stays in `backend/dyscover.sqlite3`.
