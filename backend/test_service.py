import json
import asyncio
import io
import os
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
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
    def test_ai_auth_failure_has_actionable_message_without_status_code(self):
        failure = urllib.error.HTTPError("https://api.openai.com/v1/responses", 401, "Unauthorized", {}, None)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(store, "reserve", return_value=True), \
             patch.object(ai.urllib.request, "urlopen", side_effect=failure):
            with self.assertRaises(ai.AIError) as caught:
                ai.request("responses", {})
        self.assertIn("Check OPENAI_API_KEY", caught.exception.message)
        self.assertNotIn("401", caught.exception.message)

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
        self.assertTrue(snap["materials"][0]["originalAvailable"])
        original = self.client.get(f"/api/sessions/{sid}/materials/m1")
        self.assertEqual(original.content, b"Photosynthesis uses light to make sugars. Plants also need water.")

    def test_delete_session_removes_original_and_respects_owner(self):
        sid = self.create()
        with TestClient(app.app) as other:
            other.post("/api/auth/login", json={"email": "judge@example.com", "password": "judge-pass"})
            self.assertEqual(other.delete(f"/api/sessions/{sid}").status_code, 404)
            self.assertEqual(other.get(f"/api/sessions/{sid}/materials/m1").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/sessions/{sid}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}").status_code, 404)
        self.assertIsNone(store.get_material(sid, "m1"))

    def test_one_browser_can_create_more_than_three_sessions(self):
        for _ in range(4):
            self.create()
        self.assertEqual(len(self.client.get("/api/sessions").json()), 4)

    def test_login_and_browser_isolation(self):
        sid = self.create()
        with TestClient(app.app) as other:
            self.assertEqual(other.get("/api/sessions").status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "other@example.com", "password": "judge-pass"}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "judge@example.com", "password": "wrong"}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"email": "JUDGE@example.com", "password": "judge-pass"}).status_code, 200)
            self.assertEqual(other.get("/api/sessions").json(), [])
            self.assertEqual(other.get(f"/api/sessions/{sid}").status_code, 404)
            with other.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                with self.assertRaises(WebSocketDisconnect) as closed:
                    ws.receive_json()
            self.assertEqual(closed.exception.code, 4404)

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
                opening = [ws.receive_json() for _ in range(5)]
                self.assertEqual(opening[0]["type"], "map.reset")
                self.assertEqual(opening[3]["type"], "caption")
                ws.send_json({"type": "user.text", "text": "What does light do?"})
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

    def test_text_turn_after_paused_session_resumes(self):
        sid = self.create()
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", return_value=NEXT) as generate:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5):
                    ws.receive_json()
                ws.send_json({"type": "session.end"})
                self.assertEqual(ws.receive_json(), {"type": "voice.status", "status": "ended"})
                ws.send_json({"type": "session.resume"})
                self.assertEqual(ws.receive_json(), {"type": "voice.status", "status": "listening"})
                ws.send_json({"type": "user.text", "text": "Explain light energy"})
                events = []
                while not any(event["type"] == "map.add" for event in events):
                    events.append(ws.receive_json())
                self.assertEqual(generate.call_args.args[1], "Explain light energy")

    def test_reopened_session_accepts_text_without_choice(self):
        sid = self.create()
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", return_value=NEXT) as generate:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                opening = [ws.receive_json() for _ in range(5)]
                self.assertEqual(opening[3]["type"], "caption")
                ws.send_json({"type": "user.text", "text": "I think plants need light"})
                self.assertEqual(ws.receive_json()["type"], "caption")
                while ws.receive_json()["type"] != "map.add":
                    pass
                self.assertEqual(generate.call_args.args[2], "turn")
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                reopened = [ws.receive_json() for _ in range(5)]
                self.assertEqual(reopened[0]["type"], "map.reset")
                ws.send_json({"type": "user.text", "text": "Tell me more"})
                self.assertEqual(ws.receive_json()["type"], "caption")

    def test_spoken_caption_rolls_forward_with_audio(self):
        sid = self.create()
        with patch.object(app, "speak", return_value=b"\0" * 16384):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                captions = []
                speaking = False
                while True:
                    packet = ws.receive()
                    if packet.get("text") is None:
                        continue
                    event = json.loads(packet["text"])
                    if event["type"] == "voice.status":
                        if event["status"] == "speaking":
                            speaking = True
                        elif speaking and event["status"] == "listening":
                            break
                    if event["type"] == "caption":
                        captions.append(event["caption"])
        self.assertGreaterEqual(len(captions), 2)
        self.assertLess(len(captions[0]["text"]), len(captions[-1]["text"]))
        self.assertTrue(captions[-1]["final"])

    def test_rejects_ungrounded_plan(self):
        sid = self.create()
        session = store.get(sid)
        invalid = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], sourceId="missing")])
        with self.assertRaises(PlanError):
            apply_plan(session, invalid)
        self.assertEqual(len(store.get(sid)["nodes"]), 1)

    def test_first_added_nodes_are_marked_new(self):
        sid = self.create()
        session = store.get(sid)
        proposal = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="normal")])
        _, events = apply_plan(session, proposal)
        added = next(event["node"] for event in events if event["type"] == "map.add")
        self.assertEqual(added["status"], "new")
        self.assertEqual(session["nodes"][1]["status"], "new")

    def test_ordinary_turn_preserves_map_structure_and_saved_description(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        original = session["details"]["light"]["summary"]
        proposal = dict(NEXT, nodes=[dict(ROOT, label="Rewritten root", summary="Changed"),
                                     dict(NEXT["nodes"][1], parentId="water", label="Moved light", summary="Replacement"),
                                     dict(NEXT["nodes"][1], id="water", label="Water")])
        _, events = apply_plan(session, proposal)
        self.assertEqual(session["nodes"][0]["label"], "Photosynthesis")
        self.assertEqual(session["nodes"][1]["parentId"], "root")
        self.assertEqual(session["nodes"][1]["label"], "Light energy")
        self.assertEqual(session["details"]["light"]["summary"], original)
        store.save(session)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/nodes/light").json()["summary"], original)
        self.assertFalse(any(event["type"] in ("map.remove", "map.reset") for event in events))

        _, events = apply_plan(session, dict(NEXT, nodes=[ROOT]), initial=False)
        self.assertEqual([node["id"] for node in session["nodes"]], ["root", "light", "water"])
        self.assertFalse(any(event["type"] == "map.remove" for event in events))

        changed = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], label="Sunlight")])
        apply_plan(session, changed, allow_restructure=True)
        self.assertEqual(session["nodes"][1]["label"], "Sunlight")

    def test_explicit_map_edit_phrase_is_recognized(self):
        self.assertTrue(app.map_edit_requested("Please move the Light node under Water"))
        self.assertTrue(app.map_edit_requested("Reorganise my concept map"))
        self.assertFalse(app.map_edit_requested("Explain how light helps plants"))

    def test_manual_edits_persist_through_later_ai_turns(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        original_source = session["details"]["light"]["source"]
        manual_edit(session, {"op": "move", "nodeId": "light", "x": 520, "y": 180})
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Sunlight", "summary": "My short explanation."})
        self.assertEqual(session["nodes"][1]["position"], {"x": 520, "y": 180})
        apply_plan(session, NEXT)
        self.assertEqual(session["nodes"][1]["label"], "Sunlight")
        self.assertEqual(session["nodes"][1]["position"], {"x": 520, "y": 180})
        self.assertEqual(session["details"]["light"]["summary"], "My short explanation.")
        self.assertEqual(session["details"]["light"]["source"], original_source)
        store.save(session)
        detail = self.client.get(f"/api/sessions/{sid}/nodes/light").json()
        self.assertTrue(detail["userEdited"])
        self.assertEqual(detail["source"], original_source)
        with self.assertRaises(PlanError):
            manual_edit(session, {"op": "move", "nodeId": "light", "x": -1, "y": 0})

    def test_new_user_node_has_no_unverified_citation(self):
        sid = self.create()
        session = store.get(sid)
        event = manual_edit(session, {"op": "add", "nodeId": "ownidea", "parentId": "root", "label": "My idea"})
        self.assertEqual(event["type"], "map.add")
        store.save(session)
        detail = self.client.get(f"/api/sessions/{sid}/nodes/ownidea").json()
        self.assertIsNone(detail["source"])
        self.assertTrue(detail["userEdited"])

    def test_blank_opening_answer_uses_grounded_topic_question(self):
        sid = self.create()
        session = store.get(sid)
        session["nodes"] = []
        session["session"]["title"] = ""
        session["session"]["topic"] = ""
        answer, events = apply_plan(session, dict(INIT, answer=""), initial=True)
        self.assertIn("Plant biology", answer)
        self.assertEqual(events[0]["type"], "map.reset")
        with self.assertRaises(PlanError):
            apply_plan(session, dict(INIT, answer=""))

    def test_retries_invalid_ai_map_without_accepting_bad_sources(self):
        invalid = dict(INIT, nodes=[dict(ROOT, sourceId="missing")])
        upload = {"files": ("lesson.txt", b"Photosynthesis uses light to make sugars.", "text/plain")}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(app, "plan", side_effect=[invalid, INIT]) as generate:
            response = self.client.post("/api/sessions", files=upload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_count, 2)
        self.assertIn("sourceId", generate.call_args_list[1].args[3])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(app, "plan", return_value=invalid) as generate:
            response = self.client.post("/api/sessions", files=upload)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(generate.call_count, 2)

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
        self.assertEqual(body["model"], ai.TUTOR_MODEL)
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertFalse(body["store"])

    def test_system_agreement_clears_edit_marker_and_keeps_user_content(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        manual_edit(session, {"op": "move", "nodeId": "light", "x": 500, "y": 100})
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Sunlight", "summary": "Light powers this process."})
        agreed = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], label="Sunlight", review="agree", reviewReason="The source supports this explanation.")])
        _, events = apply_plan(session, agreed)
        self.assertFalse(session["nodes"][1]["userEdited"])
        self.assertEqual(session["nodes"][1]["status"], "normal")
        self.assertEqual(session["details"]["light"]["summary"], "Light powers this process.")
        self.assertFalse(session["details"]["light"]["userEdited"])
        self.assertTrue(any(event.get("patch", {}).get("userEdited") is False for event in events))
        store.save(session)
        self.assertFalse(store.get(sid)["nodes"][1]["userEdited"])

    def test_dragging_changes_position_without_editing_content(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        event = manual_edit(session, {"op": "move", "nodeId": "light", "x": 600, "y": 120})
        self.assertNotIn("userEdited", event["patch"])
        self.assertEqual(session["nodes"][1]["status"], "new")
        store.save(session)
        self.assertFalse(store.get(sid)["nodes"][1].get("userEdited"))
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Sunlight", "summary": "My note."})
        manual_edit(session, {"op": "move", "nodeId": "light", "x": 700, "y": 150})
        store.save(session)
        self.assertTrue(store.get(sid)["nodes"][1]["userEdited"])

    def test_layout_coordinates_are_not_sent_as_tutor_feedback(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        manual_edit(session, {"op": "move", "nodeId": "light", "x": 450, "y": 300})
        response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(NEXT)}]}]}
        with patch.object(ai, "request", return_value=response) as send:
            ai.plan(session, "Explain the next topic", "turn")
        supplied = json.loads(send.call_args.args[1]["input"])["current_nodes"]
        self.assertTrue(all("position" not in node for node in supplied))
        self.assertFalse(supplied[1].get("userEdited"))

    def test_live_dialog_is_saved_and_reloaded_with_stable_message_ids(self):
        sid = self.create()
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", return_value=NEXT):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                opening = [ws.receive_json() for _ in range(5)]
                self.assertIn("message", opening[3])
                ws.send_json({"type": "user.text", "text": "What does light do?"})
                user = ws.receive_json()
                self.assertEqual(user["message"]["role"], "user")
                reply = None
                while True:
                    event = ws.receive_json()
                    if event["type"] == "caption" and event["caption"]["role"] == "assistant":
                        reply = event["message"]
                    if reply and event == {"type": "voice.status", "status": "listening"}:
                        break
        snapshot = self.client.get(f"/api/sessions/{sid}").json()
        ids = {item["id"] for item in snapshot["messages"]}
        self.assertIn(user["message"]["id"], ids)
        self.assertIn(reply["id"], ids)
        self.assertEqual(snapshot["messages"], self.client.get(f"/api/sessions/{sid}/history").json())

    def test_deletion_retries_invented_correction_instead_of_showing_it(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        store.save(session)
        invented = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected", said="You suggested a Light energy node here.", actually="This node is unsupported.")])
        removal = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], review="remove", reviewReason="This duplicates another idea.")])
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", side_effect=[invented, removal]) as generate:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5): ws.receive_json()
                ws.send_json({"type": "user.text", "text": "Remove the Light energy node."})
                while True:
                    event = ws.receive_json()
                    if event["type"] == "map.update" and event.get("patch", {}).get("pendingRemoval"):
                        self.assertNotEqual(event["patch"].get("status"), "corrected")
                        break
        self.assertEqual(generate.call_count, 2)
        self.assertTrue(store.get(sid)["nodes"][1]["pendingRemoval"])

    def test_history_is_session_wide_and_owner_scoped(self):
        sid = self.create()
        session = store.get(sid)
        session["messages"] = [{"id": "one", "role": "user", "text": "First topic", "at": "2026-10-24T10:00:00Z", "nodeId": "root"},
                               {"id": "two", "role": "assistant", "text": "Second topic", "at": "2026-10-24T10:00:01Z", "nodeId": "other"}]
        store.save(session)
        history = self.client.get(f"/api/sessions/{sid}/history").json()
        self.assertEqual([item["text"] for item in history], ["First topic", "Second topic"])
        self.assertTrue(all("nodeId" not in item for item in history))
        self.assertNotIn("messages", self.client.get(f"/api/sessions/{sid}/nodes/root").json())
        with TestClient(app.app) as other:
            other.post("/api/auth/login", json={"email": "judge@example.com", "password": "judge-pass"})
            self.assertEqual(other.get(f"/api/sessions/{sid}/history").status_code, 404)

    def test_removal_overrides_conflicting_correction_and_keeps_content(self):
        session = store.get(self.create())
        apply_plan(session, NEXT)
        original = dict(session["details"]["light"])
        removal = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected", said="", actually="", review="remove", reviewReason="A duplicate concept.")])
        apply_plan(session, removal)
        self.assertEqual(session["nodes"][1]["status"], "new")
        self.assertNotIn("correction", session["nodes"][1])
        self.assertEqual(session["details"]["light"], original)
        self.assertTrue(session["nodes"][1]["pendingRemoval"])
        apply_plan(session, dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected", said="Wrong", actually="Correct")]))
        self.assertEqual(session["nodes"][1]["status"], "new")
        self.assertTrue(session["nodes"][1]["pendingRemoval"])

    def test_spoken_removal_claim_requires_a_removal_proposal(self):
        session = store.get(self.create())
        apply_plan(session, NEXT)
        contradictory = dict(NEXT, answer="I suggest removing the Light energy node.", nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected", said="Wrong", actually="Correct")])
        with self.assertRaises(PlanError):
            apply_plan(session, contradictory)

    def test_system_cannot_agree_by_rewriting_the_user_note(self):
        session = store.get(self.create())
        apply_plan(session, NEXT)
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Sunlight", "summary": "My own explanation."})
        rewritten = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], label="Sunlight", review="agree", reviewReason="Agreed")])
        with self.assertRaises(PlanError):
            apply_plan(session, rewritten)
        self.assertTrue(session["nodes"][1]["userEdited"])

    def test_removal_proposal_waits_for_confirmation_and_can_be_kept(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        removal = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], review="remove", reviewReason="This duplicates another idea.")])
        _, events = apply_plan(session, removal)
        self.assertEqual(len(session["nodes"]), 2)
        self.assertEqual(session["nodes"][1]["pendingRemoval"], "This duplicates another idea.")
        self.assertFalse(any(event["type"] == "map.remove" for event in events))
        manual_edit(session, {"op": "acknowledge", "nodeId": "light"})
        self.assertTrue(session["nodes"][1]["pendingRemoval"])
        store.save(session)
        self.assertTrue(store.get(sid)["nodes"][1]["pendingRemoval"])
        manual_edit(session, {"op": "keep", "nodeId": "light"})
        self.assertIsNone(session["nodes"][1]["pendingRemoval"])
        _, events = apply_plan(session, dict(NEXT, nodes=[ROOT]), allow_restructure=True)
        self.assertTrue(session["nodes"][1]["pendingRemoval"])
        self.assertFalse(any(event["type"] == "map.remove" for event in events))
        manual_edit(session, {"op": "remove", "nodeId": "light"})
        self.assertEqual(len(session["nodes"]), 1)
        self.assertNotIn("light", session["details"])

    def test_correcting_a_user_edit_replaces_the_edit_marker(self):
        session = store.get(self.create())
        apply_plan(session, NEXT)
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Light energy", "summary": "Light is unnecessary."})
        corrected = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], status="corrected", said="Light is unnecessary", actually="Light supplies energy.")])
        apply_plan(session, corrected)
        self.assertEqual(session["nodes"][1]["status"], "corrected")
        self.assertFalse(session["nodes"][1]["userEdited"])
        self.assertEqual(session["details"]["light"]["summary"], "Light powers this process.")
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Light energy", "summary": "Light supplies energy."})
        self.assertEqual(session["nodes"][1]["status"], "normal")
        self.assertTrue(session["nodes"][1]["userEdited"])
        self.assertNotIn("correction", session["nodes"][1])

    def test_missing_content_requests_proactively_expand(self):
        sid = self.create()
        response = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(NEXT)}]}]}
        with patch.object(ai, "request", return_value=response) as send:
            for text in ("missing content", "expand on anything we haven't covered yet", "I don't know how to proceed"):
                with self.subTest(text=text):
                    ai.plan(store.get(sid), text, "turn")
                    body = send.call_args.args[1]
                    self.assertTrue(json.loads(body["input"])["explore_uncovered"])
                    self.assertIn("Do not end with a question", body["instructions"])

    def test_viewed_and_edited_markers_survive_ai_updates(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        event = manual_edit(session, {"op": "acknowledge", "nodeId": "light"})
        self.assertEqual(event["patch"]["status"], "normal")
        apply_plan(session, NEXT)
        self.assertEqual(session["nodes"][1]["status"], "normal")
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Sunlight", "summary": "My explanation."})
        apply_plan(session, NEXT)
        store.save(session)
        node = store.get(sid)["nodes"][1]
        self.assertTrue(node["userEdited"])
        self.assertEqual(node["status"], "normal")

    def test_map_markers_can_change_with_voice_paused(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        store.save(session)
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", side_effect=ai.AIError("Review temporarily unavailable")):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5):
                    ws.receive_json()
                ws.send_json({"type": "session.end"})
                self.assertEqual(ws.receive_json()["status"], "ended")
                ws.send_json({"type": "user.map_edit", "op": "acknowledge", "nodeId": "light"})
                self.assertEqual(ws.receive_json()["patch"]["status"], "normal")
                ws.send_json({"type": "user.map_edit", "op": "update", "nodeId": "light", "label": "Sunlight", "summary": "My note."})
                self.assertTrue(ws.receive_json()["patch"]["userEdited"])
                ws.send_json({"type": "user.map_edit", "op": "add", "nodeId": "own", "parentId": "root", "label": "Own idea"})
                event = ws.receive_json()
                while event["type"] != "map.add":
                    event = ws.receive_json()
                added = event["node"]
                self.assertTrue(added["userEdited"])
                self.assertEqual(added["status"], "normal")
        saved = store.get(sid)
        self.assertEqual(saved["nodes"][1]["status"], "normal")
        self.assertEqual(saved["nodes"][1]["label"], "Sunlight")
        self.assertTrue(saved["nodes"][1]["userEdited"])

    def test_content_edits_automatically_receive_each_review_outcome(self):
        for outcome in ("Agreed", "Corrected", "Proposed deletion"):
            with self.subTest(outcome=outcome):
                sid = self.create()
                session = store.get(sid)
                apply_plan(session, NEXT)
                store.save(session)
                note = "Light is unnecessary." if outcome == "Corrected" else "Light powers this process."
                item = dict(NEXT["nodes"][1], summary=note, review="agree", reviewReason="Supported by the material.")
                if outcome == "Agreed":
                    item.update(label="AI rephrasing", summary="A rephrased explanation.")
                if outcome == "Corrected":
                    item.update(status="corrected", said="Light is unnecessary.", actually="Light supplies energy.", summary="Light powers this process.", review="none", reviewReason="")
                elif outcome == "Proposed deletion":
                    item.update(review="remove", reviewReason="This duplicates another idea.")
                reply = dict(NEXT, nodes=[ROOT, item])
                with patch.object(app, "speak", return_value=b"") as speak_call, patch.object(app, "plan", return_value=reply) as generate:
                    with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                        for _ in range(5): ws.receive_json()
                        ws.send_json({"type": "session.end"})
                        self.assertEqual(ws.receive_json()["status"], "ended")
                        ws.send_json({"type": "user.map_edit", "op": "update", "nodeId": "light", "label": "Light energy", "summary": note})
                        feedback = None
                        while True:
                            event = ws.receive_json()
                            if event["type"] == "error": self.fail(event["message"])
                            if event["type"] == "caption": feedback = event["message"]
                            if feedback and event == {"type": "voice.status", "status": "ended"}: break
                self.assertEqual(generate.call_count, 1)
                self.assertEqual(generate.call_args.args[2], "review")
                self.assertTrue(feedback["text"].startswith(outcome + ":"))
                self.assertEqual(speak_call.call_count, 1)
                saved = store.get(sid)
                node = next(node for node in saved["nodes"] if node["id"] == "light")
                if outcome == "Proposed deletion": self.assertTrue(node["pendingRemoval"])
                else: self.assertFalse(node["userEdited"])
                self.assertEqual(node["status"], "corrected" if outcome == "Corrected" else "normal")
                self.assertEqual(saved["messages"][-1]["id"], feedback["id"])
                if outcome == "Agreed":
                    self.assertEqual(saved["details"]["light"]["summary"], note)
                    self.assertEqual(node["label"], "Light energy")

    def test_review_retries_if_the_note_changes_while_pending(self):
        session = store.get(self.create())
        apply_plan(session, NEXT)
        manual_edit(session, {"op": "update", "nodeId": "light", "label": "Light energy", "summary": "Original note."})
        calls = []
        def generate(current, text, mode, feedback):
            calls.append(text)
            if len(calls) == 1:
                current["details"]["light"]["summary"] = "Revised note."
            return dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], review="agree", reviewReason="Supported.")])
        with patch.object(app, "plan", side_effect=generate):
            asyncio.run(app.checked_plan(session, "Review light", "review", review_node_id="light"))
        self.assertEqual(len(calls), 2)
        self.assertIn("Revised note.", calls[1])
        self.assertEqual(session["details"]["light"]["summary"], "Revised note.")

    def test_created_node_is_reviewed_without_a_typed_prompt(self):
        sid = self.create()
        proposal = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], id="own", label="Own idea", summary="Own idea", status="normal", review="remove", reviewReason="This idea is not supported by the lesson.")])
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan", return_value=proposal) as generate:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5): ws.receive_json()
                ws.send_json({"type": "user.map_edit", "op": "add", "nodeId": "own", "parentId": "root", "label": "Own idea"})
                while True:
                    event = ws.receive_json()
                    if event["type"] == "error": self.fail(event["message"])
                    if event["type"] == "caption" and event["caption"]["text"].startswith("Proposed deletion:"): break
        self.assertEqual(generate.call_count, 1)
        self.assertTrue(store.get(sid)["nodes"][1]["pendingRemoval"])

    def test_dragging_does_not_trigger_automatic_review(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        store.save(session)
        with patch.object(app, "speak", return_value=b""), patch.object(app, "plan") as generate:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5): ws.receive_json()
                ws.send_json({"type": "user.map_edit", "op": "move", "nodeId": "light", "x": 600, "y": 200})
                self.assertEqual(ws.receive_json()["type"], "map.update")
                ws.send_json({"type": "session.end"})
                self.assertEqual(ws.receive_json()["status"], "ended")
        generate.assert_not_called()

    def test_pausing_voice_does_not_cancel_a_pending_edit_review(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        store.save(session)
        release = threading.Event()
        reply = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], review="agree", reviewReason="Supported by the source.")])
        def generate(*args):
            release.wait(5)
            return reply
        with patch.object(app, "speak", return_value=b"") as speak_call, patch.object(app, "plan", side_effect=generate):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                for _ in range(5): ws.receive_json()
                ws.send_json({"type": "user.map_edit", "op": "update", "nodeId": "light", "label": "Light energy", "summary": "Light powers this process."})
                self.assertEqual(ws.receive_json()["type"], "map.update")
                self.assertEqual(ws.receive_json()["status"], "thinking")
                ws.send_json({"type": "session.end"})
                self.assertEqual(ws.receive_json()["status"], "ended")
                release.set()
                while True:
                    event = ws.receive_json()
                    if event["type"] == "error": self.fail(event["message"])
                    if event["type"] == "caption":
                        self.assertTrue(event["caption"]["text"].startswith("Agreed:"))
                        break
        self.assertFalse(store.get(sid)["nodes"][1]["userEdited"])
        self.assertEqual(speak_call.call_count, 1)

    def test_direct_help_request_gets_explanation_intent(self):
        sid = self.create()
        session = store.get(sid)
        session["messages"].append({"role": "assistant", "text": "How does light help photosynthesis?"})
        response = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(NEXT)}]}]}
        with patch.object(ai, "request", return_value=response) as send:
            for text in ("how", "don't know much about that", "no idea", "explain for me"):
                with self.subTest(text=text):
                    ai.plan(session, text, "turn")
                    body = send.call_args.args[1]
                    payload = json.loads(body["input"])
                    self.assertTrue(payload["learner_needs_explanation"])
                    self.assertEqual(payload["recent_messages"][-1]["text"], "How does light help photosynthesis?")
                    self.assertIn("directly answer", body["instructions"])
            ai.plan(session, "Plants use light to make sugars", "turn")
            self.assertFalse(json.loads(send.call_args.args[1]["input"])["learner_needs_explanation"])

    def test_correction_and_manual_edit_events(self):
        sid = self.create()
        session = store.get(sid)
        apply_plan(session, NEXT)
        session["messages"].append({"role": "user", "text": "Light is unnecessary"})
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

    def test_pdf_over_thirty_pages_is_accepted(self):
        pdf = pymupdf.open()
        for _ in range(31):
            page = pdf.new_page()
            page.insert_text((72, 72), "A short lesson note.")
        result = extract("long-lecture.pdf", pdf.tobytes())
        pdf.close()
        self.assertEqual(len(result["pages"]), 31)


if __name__ == "__main__":
    unittest.main()
