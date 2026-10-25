import asyncio
import copy
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

import ai
import app
from agent import edit_scope, expansion_requested, expansion_target
from tutor import apply_plan, manual_edit


def response(answer):
    return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"answer": answer})}]}]}


def call(name, **arguments):
    return {"status": "completed", "output": [{"type": "function_call", "name": name,
            "call_id": "call_" + name, "arguments": json.dumps(arguments)}]}


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
        self.session = {"session": {"id": "test", "title": "Project", "topic": "Lifecycle"},
                        "chunks": [{"id": "c1", "materialId": "m1", "fileName": "lesson.txt", "page": 1,
                                    "text": "A phase is a stage of a project. Design comes before implementation."}],
                        "nodes": [], "details": {}, "messages": [], "turns": 0}
        self.root = dict(id="root", parentId=None, label="Project", subtitle="", status="normal", said="", actually="",
                         sourceId="c1", summary="A project has stages.", review="none", reviewReason="")
        self.phase = dict(self.root, id="phase", parentId="root", label="Phase", summary="A phase is a stage of a project.")
        apply_plan(self.session, dict(title="Project", topic="Lifecycle", answer="Ready.", nodes=[self.root, self.phase]))

    def run_agent(self, responses, text="Explain phases", mode="turn"):
        with patch.object(ai, "request", side_effect=responses) as send:
            result = ai.plan(self.session, text, mode)
        return result, send

    def test_deletion_is_not_rename_permission(self):
        result, send = self.run_agent([
            call("rename_node", nodeId="phase", label="Face"),
            call("propose_removal", nodeId="phase", reason="You requested removal."),
            response("Phase is marked for removal. Confirm deletion or keep it."),
        ], "Please delete the Phase node", "remove")
        self.assertEqual({t["name"] for t in send.call_args_list[0].args[1]["tools"]}, {"search_materials", "propose_removal"})
        self.assertIn("error", json.loads(send.call_args_list[1].args[1]["input"][-1]["output"]))
        self.assertFalse(self.session["nodes"][1].get("pendingRemoval"))
        apply_plan(self.session, result)
        self.assertEqual(self.session["nodes"][1]["label"], "Phase")
        self.assertTrue(self.session["nodes"][1]["pendingRemoval"])
        self.assertEqual(len(self.session["nodes"]), 2)

    def test_misheard_name_cannot_mutate_nearest_node(self):
        result, send = self.run_agent([
            call("propose_removal", nodeId="phase", reason="Delete face."),
            response("Did you mean the Phase node?"),
        ], "Delete the face node", "remove")
        self.assertEqual([t["name"] for t in send.call_args_list[0].args[1]["tools"]], ["search_materials"])
        self.assertTrue(all(n["review"] == "none" for n in result["nodes"]))

    def test_exact_duplicate_labels_require_clarification(self):
        self.session["nodes"].append(dict(self.session["nodes"][1], id="other"))
        self.assertEqual(edit_scope(self.session, "Delete Phase"), ("remove", set()))

    def test_selected_node_is_used_only_for_explicit_reference(self):
        self.session["selectedNodeId"] = "phase"
        self.assertEqual(edit_scope(self.session, "Delete this node"), ("remove", {"phase"}))
        self.assertEqual(edit_scope(self.session, "Delete face"), ("remove", set()))
        self.assertEqual(edit_scope(self.session, "How do I rename a node?"), (None, set()))
        self.assertEqual(edit_scope(self.session, "Reorganise my concept map"), ("move", {"phase"}))

    def test_source_search_then_individual_addition(self):
        node = dict(self.phase, id="design", label="Design", summary="Design comes before implementation.", status="new")
        result, send = self.run_agent([call("search_materials", query="design"), call("add_node", **node), response("Yes, design comes first.")],
                                      "Design comes before implementation")
        self.assertEqual(len(self.session["nodes"]), 2)
        apply_plan(self.session, result)
        self.assertEqual(self.session["nodes"][-1]["id"], "design")
        self.assertEqual(self.session["nodes"][-1]["status"], "new")
        supplied = json.loads(send.call_args_list[0].args[1]["input"][0]["content"])
        self.assertNotIn("text", supplied["source_passages"][0])
        self.assertFalse(send.call_args.args[1]["store"])
        if ai.TUTOR_MODEL.startswith("gpt-6"):
            self.assertEqual(send.call_args.args[1]["reasoning"], {"effort": "low"})

    def test_explicit_expansion_is_distinct_from_ordinary_explanation(self):
        for text in ("Expand the map structure", "Please extend the map", "Can you expand it?", "expand further", "Expand Phase",
                     "expand on anything we haven't covered yet"):
            with self.subTest(text=text):
                self.assertTrue(expansion_requested(text, self.session["nodes"]))
        for text in ("Explain a phase", "I don't know", "How do I expand the map?", "Don't expand the map"):
            with self.subTest(text=text):
                self.assertFalse(expansion_requested(text, self.session["nodes"]))

    def test_expansion_adds_source_outlines_without_moving_or_editing_existing_nodes(self):
        manual_edit(self.session, dict(op="move", nodeId="phase", x=700, y=150))
        before = copy.deepcopy(self.session["nodes"])
        node = dict(self.phase, id="design", parentId="phase", label="Design", summary="Design comes before implementation.", status="new")
        result, send = self.run_agent([call("search_materials", query="design"), call("expand_branch", nodes=[node]), response("Added Design beneath Phase.")],
                                      "Please expand node phase")
        first = send.call_args_list[0].args[1]
        context = json.loads(first["input"][0]["content"])
        self.assertTrue(context["map_expansion_requested"])
        self.assertIn("EXPLICIT MAP EXPANSION", first["instructions"])
        self.assertEqual({t["name"] for t in first["tools"]}, {"search_materials", "expand_branch"})
        apply_plan(self.session, result)
        self.assertEqual(self.session["nodes"][:2], before)
        self.assertEqual(self.session["nodes"][-1]["status"], "new")
        self.assertEqual(self.session["nodes"][-1]["parentId"], "phase")

    def test_expansion_reads_all_sources_not_only_the_first_six(self):
        self.session["chunks"].extend(dict(self.session["chunks"][0], id=f"c{i}", text=f"Uncovered project topic {i}.") for i in range(2, 8))
        _, send = self.run_agent([call("search_materials", query="project phase"), call("expand_branch", nodes=[]), response("Here are additional topics.")], "Expand further")
        passages = json.loads(send.call_args_list[1].args[1]["input"][-1]["output"])
        self.assertEqual({p["id"] for p in passages}, {f"c{i}" for i in range(1, 8)})
        _, send = self.run_agent([call("search_materials", query="phase"), response("A phase is a project stage.")], "Explain a phase")
        passages = json.loads(send.call_args.args[1]["input"][-1]["output"])
        self.assertEqual(passages[0]["id"], "c1")

    def test_expansion_must_attempt_the_batch_instead_of_only_promising_it(self):
        before = copy.deepcopy(self.session)
        with self.assertRaises(ai.AIError):
            self.run_agent([call("search_materials", query="project"), response("I will expand the map.")], "Expand the map")
        self.assertEqual(self.session, before)

    def test_complete_level_is_added_in_one_batch_beyond_old_limits(self):
        additions = [dict(self.phase, id=f"topic{i}", label=f"Topic {i}", status="new") for i in range(25)]
        before = copy.deepcopy(self.session["nodes"])
        result, send = self.run_agent([call("search_materials", query="project"), call("expand_branch", nodes=additions),
                                      response("Choose any topic to expand further or learn it.")], "Expand the map structure")
        self.assertEqual(send.call_count, 3)
        self.assertEqual(send.call_args.args[1]["tool_choice"], "none")
        _, events = apply_plan(self.session, result)
        self.assertEqual(len(self.session["nodes"]), 27)
        self.assertEqual(self.session["nodes"][:2], before)
        self.assertEqual(sum(event["type"] == "map.add" for event in events), 25)
        self.assertEqual(events[-1], {"type": "map.expanded", "nodeId": "root"})
        update = manual_edit(self.session, dict(op="move", nodeId="topic24", x=500, y=18000))
        self.assertEqual(update["patch"]["position"]["y"], 18000)

    def test_expansion_cannot_sneak_in_grandchildren_or_existing_node_edits(self):
        invalid = [dict(self.phase, id="design", parentId="root", label="Design", status="new"),
                   dict(self.phase, id="grandchild", parentId="design", label="Subtopic", status="new")]
        before = copy.deepcopy(self.session)
        result, send = self.run_agent([call("search_materials", query="design"), call("expand_branch", nodes=invalid), call("expand_branch", nodes=[]),
                                      response("That batch was rejected; no changes were made.")], "Expand the map")
        self.assertIn("immediate children", json.loads(send.call_args_list[2].args[1]["input"][-1]["output"])["error"])
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(self.session, before)

    def test_branch_selection_and_global_expansion_have_distinct_targets(self):
        self.session["selectedNodeId"] = "phase"
        self.assertEqual(expansion_target(self.session, "Expand the map structure"), "root")
        self.assertEqual(expansion_target(self.session, "Expand node phase"), "phase")
        self.assertEqual(expansion_target(self.session, "Expand Phase"), "phase")
        self.assertEqual(expansion_target(self.session, "Expand further"), "phase")
        self.assertIsNone(expansion_target(self.session, "Expand node missing"))
        self.session["nodes"].append(dict(self.phase, id="structure", label="Structure"))
        self.assertEqual(expansion_target(self.session, "Expand the map structure"), "root")
        self.assertEqual(expansion_target(self.session, "Expand node structure"), "structure")

    def test_complete_batch_does_not_overwrite_an_existing_node(self):
        before = copy.deepcopy(self.session)
        replacement = dict(self.phase, label="Renamed", status="new")
        result, send = self.run_agent([call("search_materials", query="phase"), call("expand_branch", nodes=[replacement]), call("expand_branch", nodes=[]),
                                      response("No changes were made.")], "Expand the map")
        self.assertIn("error", json.loads(send.call_args_list[2].args[1]["input"][-1]["output"]))
        self.assertEqual(result["nodes"][1]["label"], "Phase")
        self.assertEqual(self.session, before)

    def test_capacity_error_rejects_whole_batch_without_silent_truncation(self):
        additions = [dict(self.phase, id=f"topic{i}", label=f"Topic {i}", status="new") for i in range(200)]
        result, send = self.run_agent([call("search_materials", query="phase"), call("expand_branch", nodes=additions), call("expand_branch", nodes=[]),
                                      response("This level exceeds the prototype capacity; no partial branch was added.")], "Expand the map")
        self.assertIn("do not silently truncate", json.loads(send.call_args_list[2].args[1]["input"][-1]["output"])["error"])
        self.assertEqual(len(result["nodes"]), 2)

    def test_explained_idea_is_mapped_without_learner_repetition(self):
        node = dict(self.phase, id="design", label="Design", status="new")
        result, send = self.run_agent([call("search_materials", query="design"), call("add_node", **node), response("Design comes first.")],
                                      "Explain design for me")
        first = send.call_args_list[0].args[1]
        self.assertIn("even when the learner has not explained it back", first["instructions"])
        self.assertNotIn("Add only after the learner correctly explains", str(first["tools"]))
        apply_plan(self.session, result)
        self.assertEqual(self.session["nodes"][-1]["id"], "design")

    def test_content_change_without_search_is_rejected(self):
        node = dict(self.phase, id="design", label="Design", status="new")
        result, send = self.run_agent([call("add_node", **node), call("search_materials", query="design"), response("Let's check the material.")])
        error = json.loads(send.call_args_list[1].args[1]["input"][-1]["output"])["error"]
        self.assertIn("Search", error)
        self.assertEqual(len(result["nodes"]), 2)

    def test_unsourced_user_node_can_be_reviewed_and_agreed(self):
        manual_edit(self.session, dict(op="add", nodeId="own", parentId="root", label="Design"))
        result, send = self.run_agent([
            call("search_materials", query="design"),
            call("review_node", nodeId="own", decision="agree", reason="The source describes design.",
                 sourceId="c1", summary="Design", said="", actually=""),
            response("Agreed: Design is a project stage."),
        ], "Review only node own. Check its saved content.", "review")
        apply_plan(self.session, result)
        self.assertFalse(self.session["nodes"][-1]["userEdited"])
        self.assertEqual(self.session["details"]["own"]["sourceId"], "c1")
        self.assertEqual(send.call_args_list[0].args[1]["tool_choice"]["name"], "search_materials")
        self.assertEqual(send.call_args_list[1].args[1]["tool_choice"]["name"], "review_node")
        self.assertEqual(send.call_args_list[2].args[1]["tool_choice"], "none")

    def test_review_cannot_touch_other_nodes(self):
        manual_edit(self.session, dict(op="add", nodeId="own", parentId="root", label="Unknown"))
        result, send = self.run_agent([
            call("search_materials", query="stage"),
            call("review_node", nodeId="phase", decision="remove", reason="Not supported.", sourceId="c1", summary="", said="", actually=""),
            call("review_node", nodeId="own", decision="remove", reason="Not in this lesson.", sourceId="c1", summary="", said="", actually=""),
            response("Proposed deletion: Unknown is not in the lesson."),
        ], "Review only node own. Check its saved content.", "review")
        self.assertIn("Review only", json.loads(send.call_args_list[2].args[1]["input"][-1]["output"])["error"])
        apply_plan(self.session, result)
        self.assertTrue(self.session["nodes"][-1]["pendingRemoval"])
        self.assertFalse(self.session["nodes"][1].get("pendingRemoval"))

    def test_rename_cannot_move_or_target_another_node(self):
        result, send = self.run_agent([
            call("move_node", nodeId="phase", parentId="phase"),
            call("rename_node", nodeId="root", label="Face"),
            call("rename_node", nodeId="phase", label="Stage"), response("Renamed Phase to Stage."),
        ], "Rename Phase to Stage", "rename")
        apply_plan(self.session, result, allow_restructure=True)
        self.assertEqual(self.session["nodes"][1]["label"], "Stage")
        self.assertEqual(self.session["nodes"][1]["parentId"], "root")
        self.assertEqual(self.session["nodes"][0]["label"], "Project")

    def test_tool_loop_is_bounded_and_never_commits_on_failure(self):
        before = copy.deepcopy(self.session)
        with self.assertRaises(ai.AIError):
            self.run_agent([call("search_materials", query="stage")] * 6)
        self.assertEqual(self.session, before)

    def test_tool_budget_reserves_a_final_answer_instead_of_blame_on_request_length(self):
        result, send = self.run_agent([call("search_materials", query="stage")] * 5 + [response("A phase is a project stage.")])
        self.assertEqual(send.call_count, 6)
        self.assertEqual(send.call_args.args[1]["tool_choice"], "none")
        self.assertEqual(result["answer"], "A phase is a project stage.")
        self.assertEqual(len(result["nodes"]), 2)

    def test_reserved_answer_retains_only_successful_staged_changes(self):
        node = dict(self.phase, id="design", label="Design", summary="Design comes before implementation.", status="new")
        result, send = self.run_agent([call("search_materials", query="design"), call("add_node", **node)] +
                                      [call("search_materials", query="stage")] * 3 + [response("Added Design based on your explanation.")],
                                      "Design comes before implementation")
        self.assertEqual(send.call_args.args[1]["tool_choice"], "none")
        self.assertEqual(len(self.session["nodes"]), 2)
        apply_plan(self.session, result)
        self.assertEqual(self.session["nodes"][-1]["id"], "design")

    def test_completed_requested_edit_stops_tool_work(self):
        result, send = self.run_agent([call("propose_removal", nodeId="phase", reason="Requested removal."),
                                      response("Phase is marked for your confirmation.")], "Delete Phase", "remove")
        self.assertEqual(send.call_args.args[1]["tool_choice"], "none")
        self.assertEqual(result["nodes"][1]["review"], "remove")

    def test_explanation_cannot_skip_source_lookup(self):
        before = copy.deepcopy(self.session)
        with self.assertRaises(ai.AIError):
            self.run_agent([response("An unsupported answer.")])
        self.assertEqual(self.session, before)

    def test_failure_after_staged_change_does_not_commit(self):
        before = copy.deepcopy(self.session)
        with self.assertRaises(ai.AIError):
            self.run_agent([call("propose_removal", nodeId="phase", reason="Requested.")] +
                           [call("search_materials", query="phase")] * 5, "Delete Phase", "remove")
        self.assertEqual(self.session, before)

    def test_move_cycle_is_rejected(self):
        result, send = self.run_agent([call("move_node", nodeId="phase", parentId="phase"), response("The node cannot be its own parent.")],
                                      "Move Phase under Phase", "move")
        self.assertIn("error", json.loads(send.call_args.args[1]["input"][-1]["output"]))
        self.assertEqual(result["nodes"][1]["parentId"], "root")

    def test_invalid_source_cannot_be_used_for_new_content(self):
        node = dict(self.phase, id="design", label="Design", status="new", sourceId="invented")
        result, _ = self.run_agent([call("search_materials", query="design"), call("add_node", **node), response("I cannot support that addition.")])
        self.assertEqual(len(result["nodes"]), 2)

    def test_transcription_supplies_vocabulary(self):
        with patch.object(ai, "request", return_value={"text": "Delete Phase"}) as send:
            self.assertEqual(ai.transcribe(b"wav", "Phase, Design"), "Delete Phase")
        body = send.call_args.args[1]
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b"Phase, Design", body)

    def test_late_plan_retries_against_current_map(self):
        seen = []
        def generate(snapshot, text, mode, feedback):
            seen.append(snapshot)
            if len(seen) == 1:
                manual_edit(self.session, dict(op="move", nodeId="phase", x=700, y=200))
            return dict(title="Project", topic="Lifecycle", answer="A phase is a stage.", nodes=[self.root, self.phase])
        with patch.object(app, "plan", side_effect=generate):
            asyncio.run(app.checked_plan(self.session, "Explain phase", "turn"))
        self.assertEqual(len(seen), 2)
        self.assertEqual(self.session["nodes"][1]["position"], {"x": 700, "y": 200})


if __name__ == "__main__":
    unittest.main()
