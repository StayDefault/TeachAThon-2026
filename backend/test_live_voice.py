import asyncio
import base64
import json
import os
import threading
import unittest
from unittest.mock import AsyncMock, patch

import app
import live_voice
import store
import test_agent as agent_tests
import test_service as service_tests
from test_service import NEXT, ROOT


class Connection:
    def __init__(self):
        self.events = asyncio.Queue()
        self.sent = []
        self.closed = False

    async def send(self, packet):
        event = json.loads(packet)
        self.sent.append(event)
        if event["type"] == "session.start":
            await self.events.put(json.dumps({"type": "session.started", "session": {"id": "live_test"}}))
        elif event["type"] == "session.close":
            await self.events.put(json.dumps({"type": "session.closed", "usage": {}}))

    async def recv(self):
        return await self.events.get()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.recv()

    async def close(self):
        self.closed = True


class LiveVoiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture = agent_tests.AgentTest()
        fixture.setUp()
        self.session = fixture.session
        self.emit, self.audio, self.delegate = AsyncMock(), AsyncMock(), AsyncMock()
        self.voice = live_voice.LiveVoice(self.session, self.emit, self.audio, self.delegate)
        self.saved = patch.object(live_voice, "save")
        self.saved.start()

    async def asyncTearDown(self):
        await self.voice.close()
        self.saved.stop()

    def test_configuration_keeps_private_tools_and_key_on_backend(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "private-test-key"}):
            config = live_voice.configuration(self.session)
        self.assertEqual(config["delegation"], {"type": "client"})
        self.assertEqual(config["audio"]["format"]["rate"], 16000)
        self.assertNotIn("tools", config)
        self.assertNotIn("private-test-key", json.dumps(config))
        self.assertIn("Phase", json.dumps(config["input"]))

    def test_startup_history_has_a_bounded_utf8_budget(self):
        self.session["messages"] = [{"role": "user", "text": "概念" * 3000}] * 20
        config = live_voice.configuration(self.session)
        self.assertLess(sum(len(item["content"][0]["text"].encode()) for item in config["input"]), 6500)

    async def test_transcript_deltas_update_one_saved_message_without_losing_spaces(self):
        await self.voice.transcript("user", {"delta": "Delete", "start_ms": 0, "end_ms": 200})
        await self.voice.transcript("user", {"delta": " Phase", "start_ms": 200, "end_ms": 500})
        self.assertEqual(len(self.session["messages"]), 1)
        self.assertEqual(self.session["messages"][0]["text"], "Delete Phase")
        self.assertEqual(self.voice.revision, 2)
        captions = [c.args[0] for c in self.emit.call_args_list if c.args[0]["type"] == "caption"]
        self.assertEqual(captions[0]["message"]["id"], captions[1]["message"]["id"])
        self.assertEqual(captions[0]["message"]["text"], "Delete")

    async def test_delegation_uses_transcript_before_its_offset_and_consumes_once(self):
        self.voice.fragments = [{"text": "Delete Phase", "start": 0, "end": 500}, {"text": "Explain design", "start": 1000, "end": 1500}]
        text, revision = await self.voice.request_text(600)
        self.assertEqual(text, "Delete Phase")
        self.assertEqual(self.voice.consumed, 1)
        text, revision = await self.voice.request_text(1600)
        self.assertEqual(text, "Explain design")

    async def test_receiver_routes_audio_and_deduplicates_delegation_ids(self):
        connection = Connection()
        self.voice.connection = connection
        self.voice.stopped = False
        for event in [
            {"type": "session.delegation.created", "offset_ms": 300, "delegation": {"id": "task_one", "target": "client"}},
            {"type": "session.delegation.created", "offset_ms": 300, "delegation": {"id": "task_one", "target": "client"}},
            {"type": "session.output_audio.delta", "delta": base64.b64encode(b"\x01\x00" * 10).decode()},
            {"type": "session.closed", "usage": {}},
        ]:
            await connection.events.put(json.dumps(event))
        await self.voice.receive()
        self.delegate.assert_awaited_once_with("task_one", 300)
        self.audio.assert_awaited_once_with(b"\x01\x00" * 10)

    async def test_append_preserves_non_english_text_and_delegation_id_within_budget(self):
        self.voice.connection = Connection()
        text = "概念 feedback " * 200
        await self.voice.append(text, "task_one")
        sent = self.voice.connection.sent
        self.assertEqual("".join(item["content"] for item in sent), text)
        self.assertTrue(all(len(item["content"].encode()) <= 450 and item["delegation_id"] == "task_one" for item in sent))

    async def test_failed_start_is_sanitized_and_leaves_text_possible(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(live_voice, "reserve", return_value=True), \
             patch.object(live_voice, "connect", new=AsyncMock(side_effect=OSError("private detail"))):
            await self.voice.start()
        self.assertFalse(self.voice.ready)
        errors = [c.args[0]["message"] for c in self.emit.call_args_list if c.args[0]["type"] == "error"]
        self.assertIn("Text remains available", errors[0])
        self.assertNotIn("private detail", errors[0])

    async def test_audio_is_bounded_and_start_waits_for_provider_ready(self):
        connection = Connection()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(live_voice, "reserve", return_value=True), \
             patch.object(live_voice, "connect", new=AsyncMock(return_value=connection)):
            await self.voice.start()
        self.assertTrue(self.voice.ready)
        self.assertEqual(connection.sent[0]["type"], "session.start")
        self.voice.feed(b"\0" * 64000)
        self.voice.feed(b"\0" * 64000)
        self.assertLessEqual(len(self.voice.buffer), 64000)
        await self.voice.close()
        self.assertTrue(connection.closed)
        self.assertFalse(self.voice.ready)
        self.assertEqual(self.voice.tasks, [])

    async def test_voice_duration_limit_closes_provider_and_keeps_text_path_open(self):
        self.voice.connection = Connection()
        connection = self.voice.connection
        self.voice.ready = True
        self.voice.stopped = False
        self.voice.max_seconds = .001
        await self.voice.expire()
        self.assertTrue(connection.closed)
        self.assertFalse(self.voice.ready)
        self.assertEqual(self.emit.call_args.args[0], {"type": "voice.status", "status": "ended"})


class LiveServiceTest(unittest.TestCase):
    create = service_tests.ServiceTest.create

    def setUp(self):
        service_tests.ServiceTest.setUp(self)
        self.environment = patch.dict(os.environ, {"DYSCOVER_VOICE_MODE": "live", "OPENAI_API_KEY": "test"})
        self.environment.start()
        self.connection = Connection()
        self.connector = patch.object(live_voice, "connect", new=AsyncMock(return_value=self.connection))
        self.connector.start()

    def tearDown(self):
        self.connector.stop()
        self.environment.stop()
        service_tests.ServiceTest.tearDown(self)

    def ready(self, ws):
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event.get("status") in ("listening", "ended"):
                return events

    def test_selection_is_silent_and_text_reaches_agent_without_microphone(self):
        sid = self.create()
        with patch.object(app, "plan", return_value=NEXT) as agent, patch.object(app, "speak") as old_speech:
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                events = self.ready(ws)
                self.assertEqual(events[0], {"type": "voice.audio", "sampleRate": 16000})
                ws.send_json({"type": "user.node_opened", "nodeId": "root"})
                ws.send_json({"type": "user.map_edit", "op": "acknowledge", "nodeId": "root"})
                self.assertEqual(ws.receive_json()["type"], "map.update")
                agent.assert_not_called()
                ws.send_json({"type": "user.text", "text": "Explain this concept"})
                while ws.receive_json()["type"] != "map.add":
                    pass
                self.assertEqual(agent.call_args.args[0]["selectedNodeId"], "root")
                old_speech.assert_not_called()
        self.assertEqual(len(store.get(sid)["nodes"]), 2)

    def test_text_response_is_saved_if_voice_cannot_connect(self):
        sid = self.create()
        self.connector.stop()
        with patch.object(live_voice, "connect", new=AsyncMock(side_effect=OSError("offline"))), patch.object(app, "plan", return_value=NEXT):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                events = self.ready(ws)
                self.assertTrue(any(e["type"] == "error" for e in events))
                ws.send_json({"type": "user.text", "text": "Explain light"})
                while True:
                    event = ws.receive_json()
                    if event["type"] == "caption" and event["caption"]["role"] == "assistant":
                        self.assertEqual(event["caption"]["text"], NEXT["answer"])
                        break
        self.assertEqual(store.get(sid)["messages"][-1]["text"], NEXT["answer"])

    def test_review_completes_as_text_when_voice_is_paused(self):
        sid = self.create()
        reviewed = dict(NEXT["nodes"][1], id="own", summary="Light energy", review="agree", reviewReason="Supported by the material.")
        with patch.object(app, "plan", return_value=dict(NEXT, nodes=[ROOT, reviewed])):
            with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                self.ready(ws)
                ws.send_json({"type": "session.end"})
                while ws.receive_json().get("status") != "ended":
                    pass
                ws.send_json({"type": "user.map_edit", "op": "add", "nodeId": "own", "parentId": "root", "label": "Light energy"})
                while True:
                    event = ws.receive_json()
                    if event["type"] == "caption" and event["caption"]["role"] == "assistant":
                        self.assertTrue(event["caption"]["text"].startswith("Agreed:"))
                        break
        self.assertFalse(store.get(sid)["nodes"][-1]["userEdited"])

    def test_new_request_discards_late_map_result_from_previous_request(self):
        sid = self.create()
        started, release = threading.Event(), threading.Event()
        calls = []
        replacement = dict(NEXT, nodes=[ROOT, dict(NEXT["nodes"][1], id="water", label="Water")])
        def plan(snapshot, text, mode, feedback):
            calls.append(text)
            if len(calls) == 1:
                started.set()
                release.wait(3)
                return NEXT
            return replacement
        try:
            with patch.object(app, "plan", side_effect=plan):
                with self.client.websocket_connect(f"/api/sessions/{sid}/live") as ws:
                    self.ready(ws)
                    ws.send_json({"type": "user.text", "text": "Explain light"})
                    self.assertTrue(started.wait(3))
                    ws.send_json({"type": "user.text", "text": "Actually explain water"})
                    while True:
                        event = ws.receive_json()
                        if event["type"] == "caption" and event["caption"]["text"] == "Actually explain water":
                            break
                    release.set()
                    while True:
                        event = ws.receive_json()
                        if event["type"] == "map.add":
                            self.assertEqual(event["node"]["id"], "water")
                            break
        finally:
            release.set()
        self.assertEqual([n["id"] for n in store.get(sid)["nodes"]], ["root", "water"])
