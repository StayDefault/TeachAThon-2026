# DysCover

**Most AI study tools explain to the student. DysCover asks the student to explain.**

DysCover is a voice-first study companion for university students, designed with dyslexic learners in mind. Students upload their own course material and talk it through with an AI tutor. As they talk, a concept map grows on a calm, uncluttered board. When a student explains a concept correctly, its node turns green and quotes their own words. Every node links back to the passage in the uploaded material it came from, so students can check what the AI says.

Submitted to **TeachAThon 2026** (University of Edinburgh) by Brian Qian, King Jin and Yirou Dong.

| | |
|---|---|
| Online prototype | https://dyscover.onrender.com (sign-in details are in our submission report) |
| Demo video (3 min) | [Google Drive](https://drive.google.com/file/d/16gesh-yH-jq7YnjkeWVjmo9y821zf0kt/view?usp=sharing) |

## What it does

- **Study your own material.** Upload slides, notes, documents or photos. DysCover extracts the text and plans a short lesson from it.
- **Talk it through.** Ask questions or explain ideas by voice, or type instead. Captions show every spoken word.
- **See the map grow.** Concepts appear one at a time as the conversation reaches them. Expand a topic, or ask to be taught any node, with one click.
- **Your understanding, in your words.** Correct explanations turn a node green and quote the student. Misconceptions are corrected beside the student's own words, quoted rather than crossed out.
- **Check the source.** Opening a node shows the passage or image it comes from. The server rejects any node that does not cite the uploaded material.
- **No labels.** DysCover needs no diagnosis, never mentions dyslexia, and never comments on spelling or grammar.

It is a working prototype. It has not yet been evaluated with learners.

## Repository layout

| Path | Contents |
|---|---|
| [`Dyscover/`](Dyscover/) | React + TypeScript frontend, including a scripted demo mode |
| [`backend/`](backend/) | Python FastAPI service: file extraction, tutor agent, prompts, GPT-Live voice bridge, SQLite storage, evaluation harness |
| [`docs/`](docs/) | Prototype guide, design architecture, workflow, demo script |
| [`docs/research/`](docs/research/) | Background reading behind the design |
| [`testing/`](testing/) | Manual test pack and the fixture files used by the evaluation harness |
| [`competition/`](competition/) | TeachAThon 2026 brief and submission template |

## Run it locally

You need Python 3.12+, Node.js and an OpenAI API key.

```bash
python -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
cd Dyscover && npm ci && cd ..
```

Start the backend. Set the variables yourself; never commit them.

```bash
export OPENAI_API_KEY=... DYSCOVER_TEST_EMAIL=... DYSCOVER_TEST_PASSWORD=... DYSCOVER_SESSION_SECRET=...
backend/.venv/bin/python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend and open http://localhost:5173:

```bash
cd Dyscover && VITE_USE_MOCK=false npm run dev
```

To see the interface without an API key, run `VITE_USE_MOCK=true npm run dev` instead. This scripted demo mode plays a fixed lesson and does not analyse uploaded files.

## Documentation

- [Prototype overview and user guide](docs/PROTOTYPE_OVERVIEW.md): features, node states, limits, setup on Windows, troubleshooting
- [Design architecture](docs/DESIGN_ARCHITECTURE.md): interaction loops, the tutor agent, context management, voice delegation
- [Workflow](docs/WORKFLOW.md): the learner's path through a session
- [Demo script](docs/DEMO_SCRIPT.md): a 3-minute live demonstration with backup plans
- [Backend guide](backend/README.md): tutor tools, prompts, GPT-Live voice mode, evaluations, deployment
- [API contract](Dyscover/docs/API.md): REST and WebSocket events between frontend and backend
- [Notes for coding agents](Dyscover/AGENTS.md)

## Tests

```bash
backend/.venv/bin/python -m unittest discover -s backend
cd Dyscover && npm run build && npm test
```
