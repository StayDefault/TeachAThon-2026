"""Dyscover backend. Run: uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000"""

import asyncio
import io
import json
import os
import uuid
import wave
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from ai import AIError, plan, speak, transcribe
from auth import COOKIE, MAX_AGE, check_credentials, configured, issue, owner
from ingest import IngestError, chunks_for, extract
from store import get, list_sessions, save
from tutor import PlanError, apply_plan, manual_edit, message
from voice import Segmenter


app = FastAPI(title="Dyscover local API")
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
PUBLIC_ORIGIN = os.environ.get("DYSCOVER_PUBLIC_ORIGIN", "").rstrip("/")
ALLOWED_ORIGINS = [PUBLIC_ORIGIN] if PUBLIC_ORIGIN else LOCAL_ORIGINS + ["http://localhost:8000", "http://127.0.0.1:8000"]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
CHOICES = [
    {"id": "new", "title": "I'm new to this", "subtitle": "Guide me from the start"},
    {"id": "know", "title": "I know a bit", "subtitle": "Let me explain it first"},
]


@app.middleware("http")
async def require_login(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path not in ("/api/health", "/api/auth/login"):
        try:
            request.state.owner = owner(request.cookies.get(COOKIE))
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


@app.post("/api/auth/login")
async def login(request: Request, response: Response):
    from store import reserve
    if not configured():
        raise HTTPException(503, "Configure judge email, password and session secret")
    if not reserve("login_attempts", int(os.environ.get("DYSCOVER_MAX_LOGINS", "50"))):
        raise HTTPException(429, "The judging demo has reached its login limit")
    if len(await request.body()) > 1024:
        raise HTTPException(413, "Password request is too large")
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(400, "Invalid login request") from None
    if not isinstance(payload, dict) or not check_credentials(payload.get("email"), payload.get("password")):
        raise HTTPException(401, "Incorrect email or password")
    response.set_cookie(COOKIE, issue(), max_age=MAX_AGE, httponly=True,
                        secure=PUBLIC_ORIGIN.startswith("https://") or request.url.scheme == "https",
                        samesite="lax", path="/api")
    return {"ok": True}


@app.get("/api/auth/status")
def auth_status():
    return {"ok": True}


def required_session(session_id, owner_id):
    session = get(session_id, owner_id)
    if session is None or "nodes" not in session:
        raise HTTPException(404, "Session not found")
    return session


@app.get("/api/health")
def health():
    return {"status": "ok", "aiConfigured": bool(os.environ.get("OPENAI_API_KEY")), "authConfigured": configured()}


@app.post("/api/sessions")
async def create_session(request: Request, files: list[UploadFile] = File(...)):
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Set OPENAI_API_KEY to use Dyscover")
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, "Upload one to five files")
    if len(list_sessions(request.state.owner)) >= 3 or len(list_sessions()) >= 30:
        raise HTTPException(429, "The judging demo has reached its session limit")
    materials, extracted = [], []
    try:
        for index, file in enumerate(files, 1):
            name = file.filename or f"material-{index}"
            data = await file.read(10 * 1024 * 1024 + 1)
            result = await asyncio.to_thread(extract, name, data)
            materials.append({"id": f"m{index}", "name": name, "kind": result["kind"], "label": result["label"]})
            extracted.append(result)
        chunks = chunks_for(materials, extracted)
        session = {"owner": request.state.owner,
                   "session": {"id": uuid.uuid4().hex, "title": "", "topic": "", "updatedAt": ""},
                   "materials": materials, "chunks": chunks, "nodes": [], "details": {}, "messages": [], "turns": 0}
        proposal = await asyncio.to_thread(plan, session, "", "init")
        apply_plan(session, proposal, initial=True)
        save(session)
        return {"session": session["session"], "materials": materials}
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AIError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except PlanError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/sessions")
def sessions(request: Request):
    return list_sessions(request.state.owner)


@app.get("/api/sessions/{session_id}")
def session_snapshot(session_id: str, request: Request):
    session = required_session(session_id, request.state.owner)
    return {key: session[key] for key in ("session", "materials", "nodes")}


@app.get("/api/sessions/{session_id}/nodes/{node_id}")
def node_detail(session_id: str, node_id: str, request: Request):
    session = required_session(session_id, request.state.owner)
    nodes = {node["id"]: node for node in session["nodes"]}
    if node_id not in nodes:
        raise HTTPException(404, "Node not found")
    breadcrumb, parent = [], nodes[node_id]["parentId"]
    while parent is not None:
        breadcrumb.insert(0, nodes[parent]["label"])
        parent = nodes[parent]["parentId"]
    detail = session["details"][node_id]
    messages = [{key: value for key, value in item.items() if key != "nodeId"}
                for item in session["messages"] if item.get("nodeId") == node_id]
    return {"nodeId": node_id, "title": nodes[node_id]["label"], "breadcrumb": breadcrumb,
            "source": detail["source"], "summary": detail["summary"], "messages": messages}


@app.websocket("/api/sessions/{session_id}/live")
async def live(websocket: WebSocket, session_id: str):
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return
    try:
        owner_id = owner(websocket.cookies.get(COOKIE))
    except HTTPException:
        await websocket.close(code=4401)
        return
    session = get(session_id, owner_id)
    if session is None or "nodes" not in session:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    send_lock = asyncio.Lock()
    segmenter = Segmenter()
    active_node = "root"
    ended = False
    task = None

    async def emit(event):
        async with send_lock:
            await websocket.send_json(event)

    async def say(text, node_id=None):
        session["messages"].append(message("assistant", text, node_id))
        save(session)
        await emit({"type": "caption", "caption": {"role": "assistant", "text": text, "final": True}})
        await emit({"type": "voice.status", "status": "speaking"})
        try:
            pcm = await asyncio.to_thread(speak, text)
            for start in range(0, len(pcm), 8192):
                async with send_lock:
                    await websocket.send_bytes(pcm[start:start + 8192])
                await asyncio.sleep(0)
            await asyncio.sleep(len(pcm) / 48000)
        except AIError as exc:
            await emit({"type": "error", "message": exc.message})
        await emit({"type": "voice.status", "status": "listening"})

    async def turn(text):
        nonlocal active_node
        text = text.strip()
        if not text or len(text) > 2000:
            await emit({"type": "error", "message": "Use a shorter message"})
            return
        if session["turns"] >= 25:
            await emit({"type": "error", "message": "This session has reached its judging limit"})
            return
        session["messages"].append(message("user", text, active_node))
        save(session)
        await emit({"type": "caption", "caption": {"role": "user", "text": text, "final": True}})
        await emit({"type": "voice.status", "status": "thinking"})
        try:
            proposal = await asyncio.to_thread(plan, session, text, "turn")
            answer, events = apply_plan(session, proposal)
            session["turns"] += 1
            save(session)
            for event in events:
                await emit(event)
                if event["type"] == "map.focus":
                    active_node = event["nodeId"]
            await say(answer, active_node)
        except (AIError, PlanError) as exc:
            await emit({"type": "error", "message": getattr(exc, "message", str(exc))})
            await emit({"type": "voice.status", "status": "listening"})

    async def heard(pcm):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm)
        await emit({"type": "voice.status", "status": "thinking"})
        try:
            text = await asyncio.to_thread(transcribe, output.getvalue())
            if text:
                await turn(text)
            else:
                await emit({"type": "voice.status", "status": "listening"})
        except AIError as exc:
            await emit({"type": "error", "message": exc.message})
            await emit({"type": "voice.status", "status": "listening"})

    async def opening():
        await emit({"type": "map.reset", "nodes": session["nodes"]})
        await emit({"type": "voice.status", "status": "listening"})
        if session["turns"] == 0:
            await say(f"I've read your files. How much do you already know about {session['session']['title']}?", "root")
            await emit({"type": "prompt.choices", "choices": CHOICES})
        else:
            await say("Welcome back. What would you like to explore next?", "root")

    task = asyncio.create_task(opening())
    try:
        while True:
            packet = await websocket.receive()
            if packet["type"] == "websocket.disconnect":
                break
            if packet.get("bytes") is not None:
                if ended:
                    continue
                started, pcm = segmenter.feed(packet["bytes"])
                if started:
                    if task and not task.done():
                        task.cancel()
                    await emit({"type": "voice.status", "status": "listening"})
                if pcm:
                    task = asyncio.create_task(heard(pcm))
                continue
            try:
                event = packet.get("text")
                event = json.loads(event) if event else {}
                kind = event.get("type")
            except (ValueError, AttributeError):
                await emit({"type": "error", "message": "Invalid live event"})
                continue
            if kind == "session.end":
                ended = True
                if task and not task.done():
                    task.cancel()
                await emit({"type": "voice.status", "status": "ended"})
            elif kind == "session.resume":
                ended = False
                segmenter = Segmenter()
                await emit({"type": "voice.status", "status": "listening"})
            elif ended:
                continue
            elif kind in ("user.text", "user.choice"):
                if task and not task.done():
                    task.cancel()
                if kind == "user.choice":
                    choice = event.get("choiceId")
                    if choice not in ("new", "know"):
                        await emit({"type": "error", "message": "Unknown choice"})
                        continue
                    text = "I'm new to this; guide me from the start." if choice == "new" else "I know a bit; let me explain what I know first."
                    await emit({"type": "prompt.clear"})
                else:
                    text = event.get("text")
                    if not isinstance(text, str):
                        await emit({"type": "error", "message": "Text is required"})
                        continue
                task = asyncio.create_task(turn(text))
            elif kind == "user.node_opened":
                node_id = event.get("nodeId")
                if node_id in session["details"]:
                    active_node = node_id
                    if not task or task.done():
                        task = asyncio.create_task(say(session["details"][node_id]["summary"], node_id))
            elif kind == "user.map_edit":
                try:
                    update = manual_edit(session, event)
                    save(session)
                    await emit(update)
                except PlanError as exc:
                    await emit({"type": "error", "message": str(exc)})
                    await emit({"type": "map.reset", "nodes": session["nodes"]})
            else:
                await emit({"type": "error", "message": "Unknown live event"})
    except WebSocketDisconnect:
        pass
    finally:
        if task and not task.done():
            task.cancel()


# Serve the production frontend from the same origin so browser cookies cover REST and WebSocket.
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "Dyscover" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
