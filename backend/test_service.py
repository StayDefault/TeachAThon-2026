import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from docx import Document
import pymupdf

import ai
import app
import store
from ingest import chunks_for, extract
from tutor import PlanError, apply_plan, manual_edit
from voice import Segmenter


ROOT = {"id": "root", "parentId": None, "label": "Photosynthesis", "subtitle": "How plants make food",
        "status": "normal", "said": "", "actually": "", "summary": "Plants use light to make sugars.", "sourceId": "c1"}
INIT = {"title": "Photosynthesis", "topic": "Plant biology", "answer": "What do you know about photosynthesis?", "nodes": [ROOT]}
NEXT = {"title": "Photosynthesis", "topic": "Plant biology", "answer": "Light provides the energy.",
        "nodes": [ROOT, {"id": "light", "parentId": "root", "label": "Light energy", "subtitle": "",
                         "status": "new", "said": "", "actually": "", "summary": "Light powers this process.", "sourceId": "c1"}]}


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.auth_env = patch.dict(os.environ, {"DYSCOVER_TEST_EMAIL": "judge@example.com",
                                             "DYSCOVER_TEST_PASSWORD": "judge-pass", "DYSCOVER_SESSION_SECRET": "test-secret"})
        self.auth_env.start()
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db = patch.object(store, "DB_PATH", Path(self.tmp.name) / "sessions.sqlite3")
        self.db.start()
        self.client = TestClient(app.app)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "judge@example.com", "password": "judge-pass"}).status_code, 200)

    def tearDown(self):
        self.client.close()
        self.auth_env.stop()
        self.db.stop()
        self.tmp.cleanup()

    def create(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(app, "plan", return_value=INIT):
            response = self.client.post("/api/sessions", files={
                "files": ("lesson.txt", b"Photosynthesis uses light to make sugars. Plants also need water.", "text/plain")})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]["id"]

    def test_rest_matches_frontend_contract(self):
        sid = self.create()
        listing = self.client.get("/api/sessions").json()
        self.assertEqual(listing[0]["id"], sid)
        self.assertIn("updatedAt", listing[0])
        snap = self.client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(snap["nodes"][0]["id"], "root")
        self.assertEqual(snap["materials"][0]["kind"], "text")
        detail = self.client.get(f"/api/sessions/{sid}/nodes/root").json()
        self.assertEqual(detail["source"]["fileName"], "lesson.txt")
        self.assertIn(detail["source"]["quote"], "Photosynthesis uses light to make sugars. Plants also need water.")

    def test_login_and_browser_isolation(self):
        sid = self.create()
        with TestClient(app.app) as other:
            self.assertEqual(other.get("/api/sessions").status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "other@example.com", "password": "judge-pass"}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "judge@example.com", "password": "wrong"}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "JUDGE@example.com", "password": "judge-pass"}).status_code, 200)
            self.assertEqual(other.get("/api/sessions").json(), [])
            self.assertEqual(other.get(f"/api/sessions/{sid}").status_code, 404)
            with self.assertRaises(Exception):
                with other.websocket_connect(f"/api/sessions/{sid}/live"):
                    pass

    def test_login_without_ai_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), TestClient(app.app) as browser:
            self.assertEqual(browser.post("/api/auth/login", json={"email": "judge@example.com", "password": "judge-pass"}).status_code, 200)
            self.assertEqual(browser.get("/api/auth/status").status_code, 200)
            self.assertFalse(browser.get("/api/health").json()["aiConfigured"])

    def test_serves_built_frontend(self):
        if not app.FRONTEND_DIST.is_dir():
            self.skipTest("Frontend has not been built")
        self.assertIn("text/html", self.client.get("/").headers["content-type"])

    def test_ai_budget_persists(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test", "DYSCOVER_MAX_AI_CALLS": "1"}), patch.object(ai.urllib.request, "urlopen") as call:
            call.return_value.__enter__.return_value.read.return_value = b'{"ok": true}'
            self.assertEqual(ai.request("responses", {}), {"ok": True})
            with self.assertRaises(ai.AIError) as blocked:
                ai.request("responses", {})
        self.assertEqual(blocked.exception.status, 429)
        self.assertEqual(call.call_count, 1)

    def test_live_text_adds_grounded_node_and_saves(self):
        sid = self.create()
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", return_value=NEXT):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                opening = [ws.receive_json() for _ in range(6)]
                self.assertEqual(opening[0]["type"], "map.reset")
                self.assertEqual(opening[-1]["type"], "prompt.choices")
                ws.send_json({"type": "user.text", "text": "Light matters"})
                events = []
                while not any(event["type"] == "map.add" for event in events):
                    events.append(ws.receive_json())
                self.assertEqual(next(event for event in events if event["type"] == "map.add")["node"]["id"], "light")
                ws.send_json({"type": "session.end"})
                while ws.receive_json()["type"] != "voice.status":
                    pass
        snap = self.client.get(f"/api/sessions/{sid}").json()
        self.assertEqual(len(snap["nodes"]), 2)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/nodes/light").json()["source"]["materialId"], "m1")

    def test_rejects_ungrounded_plan(self):
        sid = self.create()
        session = store.get(sid)
        invalid = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], sourceId="missing")])
        with self.assertRaises(PlanError):
            apply_plan(session, invalid)
        self.assertEqual(len(store.get(sid)["nodes"]), 1)

    def test_rejects_unreadable_upload(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            response = self.client.post("/api/sessions", files={"files": ("broken.pdf", b"not a PDF", "application/pdf")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/sessions").json(), [])

    def test_ai_request_uses_structured_source_plan(self):
        sid = self.create()
        response = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(NEXT)}]}]}
        with patch.object(ai, "request", return_value=response) as send:
            result = ai.plan(store.get(sid), "Light matters", "turn")
        self.assertEqual(result, NEXT)
        body = send.call_args.args[1]
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertFalse(body["store"])

    def test_correction_and_manual_edit_events(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        corrected = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected",
                                                said="Light is unnecessary", actually="Light supplies energy.")])
        _, events = apply_plan(session, corrected)
        self.assertEqual([event["type"] for event in events], ["map.update", "map.focus"])
        self.assertEqual(events[0]["patch"]["correction"]["actually"], "Light supplies energy.")
        self.assertEqual(manual_edit(session, {"op": "rename", "nodeId": "light", "label": "Sunlight"})["type"], "map.update")
        self.assertEqual(manual_edit(session, {"op": "remove", "nodeId": "light"})["type"], "map.remove")
        self.assertNotIn("light", session["details"])

    def test_speech_segmenter_detects_utterance(self):
        segmenter = Segmenter()
        loud = (1000).to_bytes(2, "little", signed=True) * 2048
        quiet = b"\0\0" * 2048
        started, _ = segmenter.feed(loud)
        self.assertTrue(started)
        for _ in range(4):
            segmenter.feed(loud)
        segment = None
        for _ in range(8):
            _, segment = segmenter.feed(quiet)
            if segment:
                break
        self.assertIsNotNone(segment)

    def test_pdf_and_docx_keep_source_text(self):
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "Light provides energy to plants.")
        pdf_result = extract("lesson.pdf", pdf.tobytes())
        pdf.close()
        doc = Document()
        doc.add_paragraph("Water is needed for photosynthesis.")
        output = io.BytesIO()
        doc.save(output)
        doc_result = extract("notes.docx", output.getvalue())
        materials = [{"id": "m1", "name": "lesson.pdf"}, {"id": "m2", "name": "notes.docx"}]
        chunks = chunks_for(materials, [pdf_result, doc_result])
        self.assertEqual([chunk["page"] for chunk in chunks], [1, None])
        self.assertIn("Light provides energy", chunks[0]["text"])
        self.assertIn("Water is needed", chunks[1]["text"])


if __name__ == "__main__":
    unittest.main()
