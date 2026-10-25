"""Dyscover backend. Run: uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000"""

import asyncio
import copy
import io
import json
import logging
import mimetypes
import os
import re
import time
import uuid
import wave
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from ai import AIError, plan, speak, transcribe
from agent import edit_scope
from auth import COOKIE, MAX_AGE, check_credentials, configured, issue, owner
from ingest import IngestError, chunks_for, extract
from store import delete_session, get, get_material, list_sessions, save, save_materials
from tutor import PlanError, apply_plan, manual_edit, message
from voice import Segmenter


app = FastAPI(title="Dyscover local API")
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
PUBLIC_ORIGIN = (os.environ.get("DYSCOVER_PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")
ALLOWED_ORIGINS = [PUBLIC_ORIGIN] if PUBLIC_ORIGIN else LOCAL_ORIGINS + ["http://localhost:8000", "http://127.0.0.1:8000"]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])
log = logging.getLogger("uvicorn.error.dyscover")


async def checked_plan(session, text, mode, initial=False, review_node_id=None):
    feedback = None
    for attempt in range(2):
        before_review = None
        if review_node_id:
            target = next((node for node in session["nodes"] if node["id"] == review_node_id), None)
            before_review = (target["label"], session["details"][review_node_id]["summary"]) if target else None
            if before_review:
                text = f"Review only node {review_node_id}. Its saved label is {before_review[0]!r}; its saved description is {before_review[1]!r}. Check this exact content against the material."
        snapshot = copy.deepcopy(session)
        started = time.monotonic()
        proposal = await asyncio.to_thread(plan, snapshot, text, mode, feedback)
        try:
            if session["nodes"] != snapshot["nodes"] or session["details"] != snapshot["details"]:
                raise PlanError("The map changed while the tutor was thinking. Please retry.", "use the current saved map; the previous map changed during processing")
            if review_node_id:
                items = proposal.get("nodes", []) if isinstance(proposal, dict) else []
                if not isinstance(items, list) or not all(isinstance(item, dict) and isinstance(item.get("id"), str) for item in items):
                    raise PlanError("Invalid review response", "return the complete map with valid node IDs")
                reviewed = next((item for item in items if item.get("id") == review_node_id), None)
                if not reviewed or (reviewed.get("review") not in ("agree", "remove") and reviewed.get("status") != "corrected"):
                    raise PlanError("The tutor did not review the edited node", "return an explicit agree, corrected, or remove decision for the requested node")
                existing = {node["id"]: node for node in session["nodes"]}
                target = existing.get(review_node_id)
                if target is None or before_review != (target["label"], session["details"][review_node_id]["summary"]):
                    raise PlanError("The node changed during review", "review the current saved label and description again")
                if reviewed.get("review") == "agree":
                    reviewed["label"], reviewed["summary"] = before_review
                for item in items:
                    before = existing.get(item["id"])
                    correction = {"said": item.get("said"), "actually": item.get("actually")}
                    if before is None or (item["id"] != review_node_id and (item.get("review", "none") != "none" or (item.get("status") == "corrected" and correction != before.get("correction")))):
                        raise PlanError("The tutor changed another node during review", "review only the requested node and leave every other node unchanged")
            result = apply_plan(session, proposal, initial=initial, allow_restructure=mode in ("rename", "move", "restructure"))
            log.info("Tutor plan mode=%s elapsed_ms=%s", mode, round((time.monotonic() - started) * 1000))
            return result
        except PlanError as exc:
            log.warning("Rejected AI map for %s: %s", mode, exc.reason)
            if attempt:
                raise
            feedback = exc.reason


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
    return {"status": "ok", "aiConfigured": bool(os.environ.get("OPENAI_API_KEY")), "authConfigured": configured(), "publicOrigin": PUBLIC_ORIGIN or None,
            "voiceMode": os.environ.get("DYSCOVER_VOICE_MODE", "chained").lower()}


@app.post("/api/sessions")
async def create_session(request: Request, files: list[UploadFile] = File(...)):
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Set OPENAI_API_KEY to use Dyscover")
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, "Upload one to five files")
    if len(list_sessions()) >= 30:
        raise HTTPException(429, "The judging demo has reached its 30-session limit")
    materials, extracted, originals = [], [], []
    try:
        for index, file in enumerate(files, 1):
            name = file.filename or f"material-{index}"
            data = await file.read(10 * 1024 * 1024 + 1)
            result = await asyncio.to_thread(extract, name, data)
            materials.append({"id": f"m{index}", "name": name, "kind": result["kind"], "label": result["label"]})
            extracted.append(result)
            originals.append((materials[-1], data))
        chunks = chunks_for(materials, extracted)
        session = {"owner": request.state.owner,
                   "session": {"id": uuid.uuid4().hex, "title": "", "topic": "", "updatedAt": ""},
                   "materials": materials, "chunks": chunks, "nodes": [], "details": {}, "messages": [], "turns": 0}
        await checked_plan(session, "", "init", initial=True)
        save(session)
        save_materials(session["session"]["id"], originals)
        return {"session": session["session"], "materials": [dict(item, originalAvailable=True) for item in materials]}
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
    return {"session": session["session"], "nodes": session["nodes"],
            "messages": [{key: value for key, value in item.items() if key != "nodeId"} for item in session["messages"]],
            "materials": [dict(item, originalAvailable=get_material(session_id, item["id"]) is not None)
                          for item in session["materials"]]}


@app.delete("/api/sessions/{session_id}", status_code=204)
def remove_session(session_id: str, request: Request):
    if not delete_session(session_id, request.state.owner):
        raise HTTPException(404, "Session not found")
    return Response(status_code=204)


@app.get("/api/sessions/{session_id}/history")
def conversation_history(session_id: str, request: Request):
    session = required_session(session_id, request.state.owner)
    return [{key: value for key, value in item.items() if key != "nodeId"} for item in session["messages"]]


@app.get("/api/sessions/{session_id}/materials/{material_id}")
def original_material(session_id: str, material_id: str, request: Request):
    required_session(session_id, request.state.owner)
    material = get_material(session_id, material_id)
    if material is None:
        raise HTTPException(404, "Original file unavailable for this session")
    name, kind, data = material
    media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    disposition = "inline" if kind in ("pdf", "image", "text") else "attachment"
    return Response(data, media_type=media_type,
                    headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(name, safe='')}",
                             "X-Content-Type-Options": "nosniff"})


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
    return {"nodeId": node_id, "title": nodes[node_id]["label"], "breadcrumb": breadcrumb,
            "source": detail["source"], "summary": detail["summary"],
            "correction": nodes[node_id].get("correction"),
            "userEdited": detail.get("userEdited", False)}


@app.websocket("/api/sessions/{session_id}/live")
async def live(websocket: WebSocket, session_id: str):
    await websocket.accept()
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        log.warning("Rejected live connection origin %s; allowed origins: %s", origin, ALLOWED_ORIGINS)
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
    if os.environ.get("DYSCOVER_VOICE_MODE", "chained").lower() == "live":
        from live_voice import serve
        await serve(websocket, session, checked_plan)
        return
    send_lock = asyncio.Lock()
    segmenter = Segmenter()
    ended = False
    task = None
    speaking = False
    review_parents = {}
    selected_node_id = None

    async def emit(event):
        async with send_lock:
            await websocket.send_json(event)

    async def say(text):
        nonlocal speaking
        saved_message = message("assistant", text)
        session["messages"].append(saved_message)
        save(session)
        await emit({"type": "voice.status", "status": "speaking"})
        speaking = True
        try:
            started = time.monotonic()
            pcm = await asyncio.to_thread(speak, text)
            log.info("Speech audio_ready_ms=%s", round((time.monotonic() - started) * 1000))
            words = text.split()
            if not pcm:
                await emit({"type": "caption", "caption": {"role": "assistant", "text": text, "final": True}, "message": saved_message})
            last_count = 0
            for start in range(0, len(pcm), 8192):
                if ended:
                    break
                part = pcm[start:start + 8192]
                count = max(1, min(len(words), round((start + len(part)) / len(pcm) * len(words))))
                if count != last_count:
                    await emit({"type": "caption", "caption": {"role": "assistant", "text": " ".join(words[:count]), "final": count == len(words)}, "message": saved_message})
                    last_count = count
                async with send_lock:
                    await websocket.send_bytes(part)
                await asyncio.sleep(len(part) / 48000)
            if pcm and last_count < len(words):
                await emit({"type": "caption", "caption": {"role": "assistant", "text": text, "final": True}, "message": saved_message})
        except AIError as exc:
            await emit({"type": "error", "message": exc.message})
            await emit({"type": "caption", "caption": {"role": "assistant", "text": text, "final": True}, "message": saved_message})
        finally:
            speaking = False
        await emit({"type": "voice.status", "status": "ended" if ended else "listening"})

    async def turn(text):
        text = text.strip()
        if not text or len(text) > 2000:
            await emit({"type": "error", "message": "Use a shorter message"})
            return
        if session["turns"] >= 25:
            await emit({"type": "error", "message": "This session has reached its judging limit"})
            return
        saved_message = message("user", text)
        session["messages"].append(saved_message)
        save(session)
        await emit({"type": "caption", "caption": {"role": "user", "text": text, "final": True}, "message": saved_message})
        await emit({"type": "voice.status", "status": "thinking"})
        try:
            session["selectedNodeId"] = selected_node_id
            action, _ = edit_scope(session, text)
            mode = action or "turn"
            answer, events = await checked_plan(session, text, mode)
            session["turns"] += 1
            save(session)
            for event in events:
                await emit(event)
            await say(answer)
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
            started = time.monotonic()
            vocabulary = ", ".join([session["session"]["topic"]] + [node["label"] for node in session["nodes"]])
            text = await asyncio.to_thread(transcribe, output.getvalue(), vocabulary)
            log.info("Transcription elapsed_ms=%s", round((time.monotonic() - started) * 1000))
            if text:
                await turn(text)
            else:
                await emit({"type": "voice.status", "status": "listening"})
        except AIError as exc:
            await emit({"type": "error", "message": exc.message})
            await emit({"type": "voice.status", "status": "listening"})

    async def queued_turn(review_task, text):
        # Shielded so a later message cancels only this turn, never the pending review.
        try:
            await asyncio.shield(review_task)
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling():
                raise
        await turn(text)

    async def review_edit(previous_task, node_id):
        if previous_task and not previous_task.done():
            try:
                await previous_task
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise
        node = next((item for item in session["nodes"] if item["id"] == node_id), None)
        if not node or not node.get("userEdited") or node.get("pendingRemoval"):
            return
        await emit({"type": "voice.status", "status": "thinking"})
        try:
            answer, events = await checked_plan(session, f"Review node {node_id}", "review", review_node_id=node_id)
            save(session)
            for event in events:
                await emit(event)
            node = next(item for item in session["nodes"] if item["id"] == node_id)
            outcome = "Proposed deletion" if node.get("pendingRemoval") else "Corrected" if node["status"] == "corrected" else "Agreed"
            answer = re.sub(r"^(?:Agreed|Corrected|Proposed deletion)\s*:\s*", "", answer, flags=re.I)
            answer = f"{outcome}: {answer}"
            if ended:
                saved_message = message("assistant", answer)
                session["messages"].append(saved_message)
                save(session)
                await emit({"type": "caption", "caption": {"role": "assistant", "text": answer, "final": True}, "message": saved_message})
                await emit({"type": "voice.status", "status": "ended"})
            else:
                await say(answer)
        except (AIError, PlanError) as exc:
            await emit({"type": "error", "message": getattr(exc, "message", str(exc))})
            await emit({"type": "voice.status", "status": "ended" if ended else "listening"})

    async def opening():
        await emit({"type": "map.reset", "nodes": session["nodes"]})
        await emit({"type": "voice.status", "status": "listening"})
        if session["turns"] == 0:
            await say(f"I've read your files. Tell me what you know about {session['session']['title']}, or ask me to explain it.")
        else:
            await say("Welcome back. Tell me what you know, or ask what you'd like to explore next.")

    task = asyncio.create_task(opening())
    try:
        while True:
            packet = await websocket.receive()
            if packet["type"] == "websocket.disconnect":
                break
            if packet.get("bytes") is not None:
                if ended or (task and not task.done() and not speaking):
                    continue
                started, pcm = segmenter.feed(packet["bytes"])
                if started:
                    if speaking and task and not task.done():
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
                voice_task = task
                while voice_task in review_parents:
                    voice_task = review_parents[voice_task]
                if voice_task and not voice_task.done():
                    voice_task.cancel()
                await emit({"type": "voice.status", "status": "ended"})
            elif kind == "session.resume":
                ended = False
                segmenter = Segmenter()
                await emit({"type": "voice.status", "status": "listening"})
            elif ended and kind != "user.map_edit":
                continue
            elif kind == "user.text":
                text = event.get("text")
                if not isinstance(text, str):
                    await emit({"type": "error", "message": "Text is required"})
                    continue
                if task in review_parents:
                    task = asyncio.create_task(queued_turn(task, text))
                else:
                    if task and not task.done():
                        task.cancel()
                    task = asyncio.create_task(turn(text))
            elif kind == "user.node_opened":
                node_id = event.get("nodeId")
                selected_node_id = node_id if any(node["id"] == node_id for node in session["nodes"]) else None
                continue
            elif kind == "user.map_edit":
                try:
                    update = manual_edit(session, event)
                    save(session)
                    await emit(update)
                    if event.get("op") in ("add", "update", "rename"):
                        node_id = update["node"]["id"] if update["type"] == "map.add" else update["nodeId"]
                        previous_task = task
                        task = asyncio.create_task(review_edit(previous_task, node_id))
                        review_parents[task] = previous_task
                        task.add_done_callback(lambda completed: review_parents.pop(completed, None))
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
