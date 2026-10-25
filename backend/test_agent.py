import asyncio
import copy
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

import agent
import ai
import app
import context
import state
from tutor import apply_plan, manual_edit


def response(answer):
    return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"answer": answer})}]}]}


def call(name, **arguments):
    return {"status": "completed", "output": [{"type": "function_call", "name": name,
            "call_id": "call_" + name, "arguments": json.dumps(arguments)}]}


def tool_output(send, index):
    return json.loads(send.call_args_list[index].args[1]["input"][-1]["output"])


class AgentTest(unittest.TestCase):
    def test_upgraded_model_defaults_and_existing_overrides(self):
        cases = [({}, "gpt-6-astra", "gpt-6.1-sol"),
                 ({"OPENAI_MODEL": "legacy-image"}, "legacy-image", "legacy-image"),
                 ({"OPENAI_MODEL": "custom-image", "OPENAI_TUTOR_MODEL": "custom-tutor"}, "custom-tutor", "custom-image")]
        for values, tutor, image in cases:
            with self.subTest(values=values), patch.dict(os.environ):
                os.environ.pop("OPENAI_MODEL", None)
                os.environ.pop("OPENAI_TUTOR_MODEL", None)
                os.environ.update(values)
                spec = importlib.util.spec_from_file_location("model_configuration_test", ai.__file__)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertEqual(module.TUTOR_MODEL, tutor)
                self.assertEqual(module.TEXT_MODEL, image)

    def test_image_model_upgrade_preserves_verbatim_vision_request_and_rollback(self):
        for model in ("gpt-6.1-sol", "gpt-4o-mini"):
            result = response("ignored")
            result["output"][0]["content"][0]["text"] = "Design comes first."
            with self.subTest(model=model), patch.object(ai, "TEXT_MODEL", model), patch.object(ai, "request", return_value=result) as send:
                self.assertEqual(ai.ocr_image(b"image", "image/png"), "Design comes first.")
                payload = send.call_args.args[1]
                self.assertEqual(payload["model"], model)
                self.assertEqual(payload["input"][0]["content"][1]["image_url"], "data:image/png;base64,aW1hZ2U=")
                self.assertIn("faithfully", payload["instructions"])
                self.assertEqual(payload.get("reasoning"), {"effort": "low"} if model.startswith("gpt-6") else None)

    def setUp(self):
        self.session = state.ensure({
            "session": {"id": "test", "title": "Project", "topic": "Lifecycle"},
            "chunks": [{"id": "c1", "materialId": "m1", "fileName": "lesson.txt", "page": 1,
                        "text": "A phase is a stage of a project. Design comes before implementation."},
                       {"id": "c2", "materialId": "m1", "fileName": "lesson.txt", "page": 1,
                        "text": "Testing checks that the product works."}],
            "nodes": [], "details": {}, "messages": [], "turns": 0})
        self.root = dict(id="root", parentId=None, label="Project", subtitle="", status="normal", said="", actually="",
                         sourceId="c1", summary="A project has stages.", review="none", reviewReason="")
        self.phase = dict(self.root, id="phase", parentId="root", label="Phase", summary="A phase is a stage of a project.", planId="p1")
        apply_plan(self.session, dict(title="Project", topic="Lifecycle", answer="Ready.", nodes=[self.root, self.phase]))
        self.session["lesson"] = state.validate_lesson(self.session, [
            {"id": "p1", "title": "Phase", "summary": "A phase is a project stage.", "sourceId": "c1", "parentId": ""},
            {"id": "p2", "title": "Design", "summary": "Design comes before implementation.", "sourceId": "c1", "parentId": ""},
            {"id": "p3", "title": "Testing", "summary": "Testing checks the product works.", "sourceId": "c2", "parentId": "p2"}])
        self.session["focus"] = "p1"

    def say(self, text):
        self.session["messages"].append({"id": str(len(self.session["messages"])), "role": "user", "text": text, "at": ""})

    def run_agent(self, responses, text="Explain phases", mode="turn", review_id=None):
        with patch.object(ai, "request", side_effect=responses) as send:
            result = ai.plan(self.session, text, mode, None, review_id)
        return result, send

    def commit(self, result):
        answer, events = apply_plan(self.session, result, allow_restructure=True)
        return answer, events + state.commit(self.session, result["staged"])

    def test_every_tool_is_open_and_the_model_gets_structured_context(self):
        _, send = self.run_agent([response("A phase is a stage of a project.")])
        body = send.call_args.args[1]
        names = {tool["name"] for tool in body["tools"]}
        self.assertEqual(names, set(agent.TOOLS) - {"search_sources"})
        self.assertNotIn("tool_choice", body)
        self.assertIn("Teaching loop", body["instructions"])
        self.assertIn("Design comes before implementation.", body["input"][0]["content"])
        supplied = json.loads(body["input"][1]["content"])
        self.assertEqual(supplied["focus"]["id"], "p1")
        self.assertEqual(supplied["focus"]["source"], self.session["chunks"][0]["text"])
        self.assertEqual([item["state"] for item in supplied["lesson"]], ["introduced", "unseen", "unseen"])
        self.assertIn("questions_in_a_row", supplied["signals"])
        self.assertFalse(body["store"])

    def test_long_material_switches_to_search(self):
        self.session["chunks"] += [dict(self.session["chunks"][1], id=f"x{i}", text="filler " * 60) for i in range(80)]
        _, send = self.run_agent([call("search_sources", query="testing product"), response("Testing checks the product.")])
        first = send.call_args_list[0].args[1]
        self.assertIn("search_sources", {tool["name"] for tool in first["tools"]})
        self.assertNotIn("Design comes before", first["input"][0]["content"])
        self.assertEqual(tool_output(send, 1)["passages"][0]["id"], "c2")

    def test_sound_alike_name_resolves_to_the_intended_node(self):
        candidates = agent.resolve(self.session["nodes"], "delete the face node")
        self.assertEqual(candidates[0]["nodeId"], "phase")
        self.assertEqual(candidates[0]["match"], "sound-alike")
        self.assertEqual(agent.resolve(self.session["nodes"], "Phase")[0]["match"], "exact")
        self.assertEqual(agent.resolve(self.session["nodes"], "photosynthesis"), [])

    def test_misheard_removal_is_proposed_on_the_resolved_node_without_renaming(self):
        result, send = self.run_agent([call("resolve_node", phrase="face"), call("propose_removal", nodeId="phase", reason="You asked to delete it."),
                                       response("I've marked Phase for removal. Confirm it on screen.")], "delete the face node")
        self.assertEqual(tool_output(send, 1)["candidates"][0]["nodeId"], "phase")
        self.commit(result)
        self.assertEqual(self.session["nodes"][1]["label"], "Phase")
        self.assertTrue(self.session["nodes"][1]["pendingRemoval"])

    def test_edit_node_renames_and_moves_but_rejects_cycles_and_root_moves(self):
        result, send = self.run_agent([
            call("add_concept", id="design", planId="", parentId="root", label="Design", summary="Design comes first.", sourceId="c1"),
            call("edit_node", nodeId="phase", label="", parentId="phase"),
            call("edit_node", nodeId="root", label="", parentId="design"),
            call("edit_node", nodeId="phase", label="Stage", parentId="design"),
            response("Renamed Phase to Stage under Design.")], "Rename phase to stage and put it under design")
        self.assertIn("error", tool_output(send, 2))
        self.assertIn("root cannot move", tool_output(send, 3)["error"])
        self.commit(result)
        phase = next(n for n in self.session["nodes"] if n["id"] == "phase")
        self.assertEqual((phase["label"], phase["parentId"]), ("Stage", "design"))

    def test_lesson_concept_node_takes_its_plan_id(self):
        result, send = self.run_agent([
            call("add_concept", id="anything", planId="p2", parentId="root", label="Design", summary="Design comes before implementation.", sourceId="c1"),
            call("add_concept", id="again", planId="p2", parentId="root", label="Design", summary="Again.", sourceId="c1"),
            response("Design comes before implementation.")])
        self.assertIn("already on the map", tool_output(send, 2)["error"])
        _, events = self.commit(result)
        design = self.session["nodes"][-1]
        self.assertEqual((design["id"], design["planId"], design["mastery"], design["status"]), ("p2", "p2", "introduced", "new"))
        self.assertEqual(self.session["learner"]["p2"]["state"], "introduced")
        self.assertIn("lesson.update", [event["type"] for event in events])

    def test_understanding_needs_the_learners_own_words(self):
        self.say("I think a phase is like one stage in the project")
        result, send = self.run_agent([
            call("update_understanding", conceptId="p1", level="understood", evidence="a phase is a part of the timeline"),
            call("update_understanding", conceptId="p1", level="understood", evidence="a phase is like one stage in the project"),
            call("set_focus", planId="p2"),
            response("Exactly. Next, design comes before implementation.")], "I think a phase is like one stage in the project")
        self.assertIn("learner's own", tool_output(send, 1)["error"])
        _, events = self.commit(result)
        phase = self.session["nodes"][1]
        self.assertEqual((phase["mastery"], phase["learnerWords"]), ("understood", "a phase is like one stage in the project"))
        self.assertEqual(self.session["learner"]["p1"]["state"], "understood")
        self.assertEqual(self.session["focus"], "p2")
        self.assertEqual(self.session["focusSince"], 1)
        update = next(event for event in events if event["type"] == "lesson.update")
        self.assertEqual(update["focusId"], "p2")
        self.assertEqual(update["items"][0]["state"], "understood")
        self.assertTrue(any(event["type"] == "map.update" and event["patch"].get("mastery") == "understood" for event in events))

    def test_progress_on_an_unrevealed_concept_reveals_it_and_skip_needs_no_node(self):
        result, _ = self.run_agent([
            call("update_understanding", conceptId="p3", level="review", evidence=""),
            call("update_understanding", conceptId="p2", level="skipped", evidence=""),
            call("update_understanding", conceptId="p3", level="attempted", evidence=""),
            response("Let's review testing later.")], "skip that")
        self.commit(result)
        testing = next(n for n in self.session["nodes"] if n.get("planId") == "p3")
        self.assertEqual((testing["id"], testing["parentId"], testing["mastery"]), ("p3", "root", "introduced"))
        self.assertEqual(self.session["learner"]["p3"], {"state": "attempted", "attempts": 1, "evidence": ""})
        self.assertEqual(self.session["learner"]["p2"]["state"], "skipped")
        self.assertFalse(any(n.get("planId") == "p2" for n in self.session["nodes"]))

    def test_misconception_must_quote_the_learner(self):
        self.say("phases happen all at once")
        result, send = self.run_agent([
            call("record_misconception", nodeId="phase", said="phases are random", actually="Phases are ordered stages.", sourceId="c1"),
            call("record_misconception", nodeId="phase", said="phases happen all at once", actually="Phases are ordered stages.", sourceId="c1"),
            response("Not quite. Phases come one after another.")], "phases happen all at once")
        self.assertIn("error", tool_output(send, 1))
        self.commit(result)
        self.assertEqual(self.session["nodes"][1]["correction"]["said"], "phases happen all at once")
        self.assertEqual(self.session["learner"]["p1"]["attempts"], 1)

    def test_expansion_adds_a_whole_level_once(self):
        manual_edit(self.session, dict(op="move", nodeId="phase", x=700, y=150))
        before = copy.deepcopy(self.session["nodes"])
        children = [dict(id=f"t{i}", label=f"Topic {i}", summary="A project stage.", sourceId="c1") for i in range(25)]
        result, send = self.run_agent([
            call("expand_branch", parentId="phase", nodes=[children[0], dict(children[1], label="Topic 0")]),
            call("expand_branch", parentId="phase", nodes=children),
            call("expand_branch", parentId="phase", nodes=children[:1]),
            response("Here are the stages inside a phase.")], "Expand Phase into its subtopics.")
        self.assertIn("duplicates", tool_output(send, 1)["error"])
        self.assertIn("already expanded", tool_output(send, 3)["error"])
        _, events = self.commit(result)
        self.assertEqual(self.session["nodes"][:2], before)
        self.assertEqual(sum(event["type"] == "map.add" for event in events), 25)
        self.assertIn({"type": "map.expanded", "nodeId": "phase"}, events)

    def test_expansion_rejects_duplicates_and_capacity_overflow_whole(self):
        too_many = [dict(id=f"t{i}", label=f"Topic {i}", summary="A stage.", sourceId="c1") for i in range(200)]
        result, send = self.run_agent([
            call("expand_branch", parentId="root", nodes=[dict(id="x", label="Phase", summary="Dup.", sourceId="c1")]),
            call("expand_branch", parentId="root", nodes=too_many),
            response("That was too large, so nothing was added.")], "Expand everything")
        self.assertIn("duplicates", tool_output(send, 1)["error"])
        self.assertIn("capacity", tool_output(send, 2)["error"])
        self.assertEqual(len(result["nodes"]), 2)

    def test_cross_links_are_staged_committed_and_pruned(self):
        result, send = self.run_agent([
            call("add_concept", id="design", planId="p2", parentId="root", label="Design", summary="Design comes first.", sourceId="c1"),
            call("link_nodes", fromId="phase", toId="p2", relation="includes"),
            call("link_nodes", fromId="p2", toId="phase", relation="belongs to"),
            call("link_nodes", fromId="phase", toId="phase", relation="is"),
            response("A phase can include design.")])
        self.assertIn("already linked", tool_output(send, 3)["error"])
        self.assertIn("error", tool_output(send, 4))
        _, events = self.commit(result)
        self.assertEqual(self.session["edges"], [{"id": "e1", "from": "phase", "to": "p2", "label": "includes"}])
        self.assertIn({"type": "map.edges", "edges": self.session["edges"]}, events)
        manual_edit(self.session, dict(op="remove", nodeId="p2"))
        self.assertEqual(self.session["edges"], [])

    def test_learner_can_add_a_concept_to_the_lesson_and_study_it(self):
        result, send = self.run_agent([
            call("add_plan_item", title="Implementation", summary="Building the product.", sourceId="c1", parentId="p2"),
            call("add_plan_item", title="Invented", summary="Not cited.", sourceId="nope", parentId=""),
            call("set_focus", planId="p4"),
            response("Let's look at implementation.")], "Can we do implementation?")
        self.assertEqual(tool_output(send, 1), {"staged": True, "planId": "p4"})
        self.assertIn("error", tool_output(send, 2))
        self.commit(result)
        self.assertEqual([item["id"] for item in self.session["lesson"]], ["p1", "p2", "p3", "p4"])
        self.assertEqual(self.session["focus"], "p4")

    def test_invalid_source_and_unknown_nodes_are_reported_to_the_model(self):
        result, send = self.run_agent([
            call("add_concept", id="design", planId="", parentId="root", label="Design", summary="Made up.", sourceId="invented"),
            call("propose_removal", nodeId="ghost", reason="Gone."),
            response("I couldn't support that from your material.")])
        self.assertIn("sourceId", tool_output(send, 1)["error"])
        self.assertIn("resolve_node", tool_output(send, 2)["error"])
        self.assertEqual(len(result["nodes"]), 2)

    def test_review_mode_reviews_only_the_requested_node(self):
        manual_edit(self.session, dict(op="add", nodeId="own", parentId="root", label="Design"))
        result, send = self.run_agent([
            call("review_edit", nodeId="phase", decision="remove", reason="No.", sourceId="c1", said="", actually="", summary=""),
            call("review_edit", nodeId="own", decision="agree", reason="The source describes design.", sourceId="c1", said="", actually="", summary=""),
            response("Agreed: design is a stage.")], "Review node own", "review", "own")
        self.assertEqual({tool["name"] for tool in send.call_args_list[0].args[1]["tools"]}, {"review_edit"})
        self.assertEqual(send.call_args_list[0].args[1]["tool_choice"], "required")
        self.assertEqual(send.call_args_list[2].args[1]["tool_choice"], "none")
        self.assertIn("requested node only", tool_output(send, 1)["error"])
        self.assertIn("Automatic review", send.call_args_list[0].args[1]["instructions"])
        self.commit(result)
        self.assertFalse(self.session["nodes"][-1]["userEdited"])
        self.assertEqual(self.session["details"]["own"]["sourceId"], "c1")

    def test_review_must_happen_before_the_answer(self):
        manual_edit(self.session, dict(op="add", nodeId="own", parentId="root", label="Design"))
        with self.assertRaises(ai.AIError):
            self.run_agent([response("Agreed.")], "Review node own", "review", "own")

    def test_tool_loop_is_bounded_and_never_commits_on_failure(self):
        before = copy.deepcopy(self.session)
        with self.assertRaises(ai.AIError):
            self.run_agent([call("resolve_node", phrase="phase")] * agent.TOOL_ROUNDS)
        self.assertEqual(self.session, before)

    def test_last_round_reserves_a_final_answer_and_keeps_staged_changes(self):
        node = dict(id="design", planId="", parentId="root", label="Design", summary="Design comes first.", sourceId="c1")
        result, send = self.run_agent([call("add_concept", **node)] + [call("resolve_node", phrase="x")] * (agent.TOOL_ROUNDS - 2) +
                                      [response("Design comes first.")])
        self.assertEqual(send.call_args.args[1]["tool_choice"], "none")
        self.assertEqual(result["nodes"][-1]["id"], "design")
        self.assertEqual(len(self.session["nodes"]), 2)

    def test_empty_answer_is_rejected(self):
        with self.assertRaises(ai.AIError):
            self.run_agent([response("  ")])

    def test_signals_count_questions_in_a_row(self):
        self.session["messages"] = [{"role": "assistant", "text": "Ready."}, {"role": "user", "text": "ok"},
                                    {"role": "assistant", "text": "What is a phase?"}, {"role": "user", "text": "no idea"},
                                    {"role": "assistant", "text": "Can you guess? "}]
        self.assertEqual(context.signals(self.session)["questions_in_a_row"], 2)

    def test_init_installs_the_lesson_and_retries_an_invalid_one(self):
        session = state.ensure({"session": {"id": "s", "title": "", "topic": ""}, "chunks": self.session["chunks"],
                                "nodes": [], "details": {}, "messages": [], "turns": 0})
        bad = dict(title="Project", topic="Lifecycle", answer="Let's start with phases.", nodes=[self.root],
                   lesson=[{"id": "p1", "title": "Phase", "summary": "Stage.", "sourceId": "made-up", "parentId": ""}])
        good = dict(bad, lesson=[dict(bad["lesson"][0], sourceId="c1"),
                                 {"id": "p2", "title": "Design", "summary": "Comes first.", "sourceId": "c1", "parentId": "p1"}])
        with patch.object(app, "plan", side_effect=[bad, good]) as generate:
            answer, events = asyncio.run(app.checked_plan(session, "", "init", initial=True))
        self.assertIn("unknown sourceId", generate.call_args.args[3])
        self.assertEqual([item["id"] for item in session["lesson"]], ["p1", "p2"])
        self.assertEqual(session["lesson"][1]["parentId"], "p1")
        self.assertEqual((session["focus"], session["opening"]), ("p1", answer))

    def test_init_request_uses_the_planner_prompt_and_schema(self):
        good = dict(title="Project", topic="Lifecycle", answer="Hi.", nodes=[self.root], lesson=[])
        result = response("x")
        result["output"][0]["content"][0]["text"] = json.dumps(good)
        with patch.object(ai, "request", return_value=result) as send:
            self.assertEqual(ai.plan(self.session, "", "init"), good)
        body = send.call_args.args[1]
        self.assertIn("lesson planner", body["instructions"])
        self.assertEqual(body["text"]["format"]["schema"], ai.INIT_SCHEMA)

    def test_button_presses_become_plain_requests(self):
        self.assertEqual(state.action_text(self.session, {"action": "expand", "nodeId": "phase"}), "Expand Phase into its subtopics.")
        self.assertEqual(state.action_text(self.session, {"action": "learn", "planId": "p3"}), "Teach me about Testing.")
        self.assertIsNone(state.action_text(self.session, {"action": "learn", "nodeId": "ghost"}))
        self.assertIsNone(state.action_text(self.session, {"action": "delete", "nodeId": "phase"}))

    def test_summary_is_due_after_messages_leave_the_window(self):
        self.session["messages"] = [{"role": "user", "text": str(i)} for i in range(context.RECENT + context.SUMMARY_AFTER - 1)]
        self.assertFalse(context.summary_due(self.session))
        self.session["messages"].append({"role": "assistant", "text": "more"})
        self.assertTrue(context.summary_due(self.session))
        with patch.object(ai, "request", return_value=response("x")) as send:
            ai.summarize(self.session, self.session["messages"][:3])
        body = send.call_args.args[1]
        self.assertIn("running summary", body["instructions"])
        self.assertEqual(len(json.loads(body["input"])["messages"]), 3)

    def test_study_context_gives_the_voice_layer_the_current_concept(self):
        text = context.study_context(self.session)
        self.assertIn("Current concept: Phase", text)
        self.assertIn("A phase is a stage of a project.", text)
        self.assertIn("Design (unseen)", text)

    def test_transcription_supplies_vocabulary(self):
        with patch.object(ai, "request", return_value={"text": "Delete Phase"}) as send:
            self.assertEqual(ai.transcribe(b"wav", "Phase, Design"), "Delete Phase")
        body = send.call_args.args[1]
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b"Phase, Design", body)

    def test_late_plan_retries_against_current_map(self):
        seen = []
        def generate(snapshot, text, mode, feedback, review_id):
            seen.append(snapshot)
            if len(seen) == 1:
                manual_edit(self.session, dict(op="move", nodeId="phase", x=700, y=200))
            return dict(title="Project", topic="Lifecycle", answer="A phase is a stage.", nodes=agent.raw_nodes(snapshot), staged={
                "lesson": snapshot["lesson"], "learner": snapshot["learner"], "focus": "p2", "edges": [], "focusSince": 0})
        with patch.object(app, "plan", side_effect=generate):
            asyncio.run(app.checked_plan(self.session, "Explain phase", "turn"))
        self.assertEqual(len(seen), 2)
        self.assertEqual(self.session["nodes"][1]["position"], {"x": 700, "y": 200})
        self.assertEqual(self.session["focus"], "p2")


if __name__ == "__main__":
    unittest.main()
