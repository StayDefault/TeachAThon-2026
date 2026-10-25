"""OpenAI calls used by the local tutor service."""

import base64
import json
import logging
import os
import urllib.error
import urllib.request
import uuid

from state import ensure

log = logging.getLogger("uvicorn.error.dyscover.ai")

TEXT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.1-sol")
TUTOR_MODEL = os.environ.get("OPENAI_TUTOR_MODEL", os.environ.get("OPENAI_MODEL", "gpt-6-astra"))
TRANSCRIBE_MODEL = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe")
# shortcut: the Speech endpoint is deprecated in 2027; move to Realtime before then.
SPEECH_MODEL = os.environ.get("OPENAI_SPEECH_MODEL", "gpt-4o-mini-tts")

NODE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "parentId": {"type": ["string", "null"]},
        "label": {"type": "string"},
        "subtitle": {"type": "string"},
        "status": {"type": "string", "enum": ["normal", "new", "corrected"]},
        "said": {"type": "string"},
        "actually": {"type": "string"},
        "summary": {"type": "string"},
        "sourceId": {"type": "string"},
        "review": {"type": "string", "enum": ["none", "agree", "remove"]},
        "reviewReason": {"type": "string"},
    },
    "required": ["id", "parentId", "label", "subtitle", "status", "said", "actually", "summary", "sourceId", "review", "reviewReason"],
}
LESSON_ITEM = {
    "type": "object", "additionalProperties": False,
    "properties": {key: {"type": "string"} for key in ("id", "title", "summary", "sourceId", "parentId")},
    "required": ["id", "title", "summary", "sourceId", "parentId"],
}
INIT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "topic": {"type": "string"},
        "answer": {"type": "string"},
        "nodes": {"type": "array", "items": NODE_SCHEMA},
        "lesson": {"type": "array", "items": LESSON_ITEM},
    },
    "required": ["title", "topic", "answer", "nodes", "lesson"],
}


class AIError(Exception):
    def __init__(self, message, status=502):
        self.message = message
        self.status = status


def request(path, body, content_type="application/json", binary=False):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise AIError("Set OPENAI_API_KEY to use Dyscover", 503)
    from store import reserve
    if not reserve("ai_calls", int(os.environ.get("DYSCOVER_MAX_AI_CALLS", "250"))):
        raise AIError("The judging demo has reached its AI usage limit", 429)
    if not isinstance(body, bytes):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.openai.com/v1/{path}", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
        return data if binary else json.loads(data)
    except urllib.error.HTTPError as exc:
        try:
            error_code = json.loads(exc.read()).get("error", {}).get("code")
        except (ValueError, AttributeError, TypeError):
            error_code = None
        if not isinstance(error_code, str) or len(error_code) > 80 or not error_code.replace("_", "").replace("-", "").isalnum():
            error_code = None
        log.warning("OpenAI request failed endpoint=%s status=%s code=%s", path, exc.code, error_code)
        if exc.code == 401:
            raise AIError("OpenAI rejected the API key. Check OPENAI_API_KEY and restart Dyscover") from None
        if exc.code == 429:
            raise AIError("OpenAI rate or spending limit reached. Check the project limits before retrying", 429) from None
        if exc.code in (403, 404):
            raise AIError("OpenAI could not access the configured model. Check project access and model settings") from None
        if exc.code == 400:
            raise AIError("OpenAI rejected the request. Check the configured model and server logs") from None
        if 500 <= exc.code < 600:
            raise AIError("OpenAI is temporarily unavailable. Please try again later") from None
        raise AIError(f"OpenAI request failed (HTTP {exc.code}). Check the Render logs") from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise AIError("AI service unavailable or returned an invalid response") from None


def response_text(result):
    try:
        if result.get("status") != "completed":
            raise ValueError
        return next(part["text"] for item in result["output"] if item.get("type") == "message"
                    for part in item.get("content", []) if part.get("type") == "output_text")
    except (KeyError, StopIteration, TypeError, ValueError):
        raise AIError("AI returned no usable answer") from None


def base_payload():
    payload = {"model": TUTOR_MODEL, "store": False}
    if TUTOR_MODEL.startswith("gpt-6"):
        payload["reasoning"] = {"effort": "low"}
    return payload


def plan(session, message, mode, validation_feedback=None, review_node_id=None):
    from context import prompt, sources_message
    ensure(session)
    if mode != "init":
        from agent import run
        return run(session, message, mode, base_payload(), request, AIError, review_node_id, validation_feedback)
    instructions = prompt("plan")
    if validation_feedback:
        instructions += f"\n\nYour previous plan was rejected by the server: {validation_feedback}. Fix that in this attempt."
    payload = dict(base_payload(), instructions=instructions, input=sources_message(session),
                   text={"format": {"type": "json_schema", "name": "dyscover_lesson", "strict": True, "schema": INIT_SCHEMA}})
    try:
        return json.loads(response_text(request("responses", payload)))
    except (ValueError, TypeError):
        raise AIError("AI returned an invalid study plan") from None


def summarize(session, messages):
    from context import lesson_view, prompt
    payload = dict(base_payload(), instructions=prompt("summary"), input=json.dumps({
        "previous_summary": session.get("summary", ""), "lesson": lesson_view(session),
        "messages": [{"role": m["role"], "text": m["text"][-800:]} for m in messages]}, ensure_ascii=False))
    return response_text(request("responses", payload)).strip()[:1200]


def ocr_image(data, mime):
    image_url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    payload = {
        "model": TEXT_MODEL,
        "instructions": "Transcribe the visible study material faithfully. Return only the text, preserving useful line breaks. If unreadable, return an empty string.",
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": "Read this page or photo."},
            {"type": "input_image", "image_url": image_url, "detail": "high"},
        ]}],
        "store": False,
    }
    if TEXT_MODEL.startswith("gpt-6"):
        payload["reasoning"] = {"effort": "low"}
    result = request("responses", payload)
    return response_text(result).strip()


def transcribe(wav_bytes, vocabulary=""):
    boundary = f"dyscover-{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{TRANSCRIBE_MODEL}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"prompt\"\r\n\r\n{vocabulary[:1500]}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"speech.wav\"\r\n"
        "Content-Type: audio/wav\r\n\r\n"
    ).encode() + wav_bytes + f"\r\n--{boundary}--\r\n".encode()
    result = request("audio/transcriptions", body, f"multipart/form-data; boundary={boundary}")
    text = result.get("text")
    if not isinstance(text, str):
        raise AIError("Speech transcription failed")
    return text.strip()


def speak(text):
    return request("audio/speech", {
        "model": SPEECH_MODEL, "voice": "marin", "input": text[:4096], "response_format": "pcm",
        "instructions": "Speak clearly and calmly for a student. Use a natural pace.",
    }, binary=True)
