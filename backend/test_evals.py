import unittest
from unittest.mock import patch

import test_agent
from evals import metrics, run


class MetricsTest(unittest.TestCase):
    def test_sound_alike_makes_a_speech_style_mistake(self):
        self.assertEqual(metrics.sound_alike("Phase"), "fase")
        self.assertEqual(metrics.sound_alike("Loss"), "lozs")

    def test_question_loops_and_repeats_are_counted(self):
        turns = [{"assistant": "A phase is a stage. What is a phase?"}, {"assistant": "Can you tell me what a phase is?"},
                 {"assistant": "So, what is a phase?"}, {"assistant": "Right. Next is design."}]
        self.assertEqual(metrics.questions_in_a_row(turns), 3)
        self.assertEqual(metrics.repeated_questions(turns), 1)

    def test_stuck_streak_counts_turns_without_progress_or_map_changes(self):
        same = {"p1": "introduced"}
        turns = [{"lesson": same, "map_changes": 1}, {"lesson": same, "map_changes": 0}, {"lesson": same, "map_changes": 0},
                 {"lesson": {"p1": "understood"}, "map_changes": 0}, {"lesson": {"p1": "understood"}, "map_changes": 0}]
        self.assertEqual(metrics.stuck_streak(turns), 2)

    def test_score_and_report(self):
        run_record = {"scenario": "S1", "persona": "steady", "turns": [
            {"assistant": "Hi?", "latency_ms": 100, "ai_calls": 2, "lesson": {"p1": "introduced", "p2": "unseen"}, "judgement": "supported"},
            {"assistant": "Good.", "latency_ms": 300, "ai_calls": 4, "lesson": {"p1": "understood", "p2": "unseen"},
             "probe": {"passed": True}, "judgement": "partly"},
            {"error": "boom", "lesson": {"p1": "understood", "p2": "unseen"}}]}
        result = metrics.score(run_record)
        self.assertEqual((result["understood"], result["lesson_size"], result["errors"]), (1, 2, 1))
        self.assertEqual((result["edit_accuracy"], result["grounded"], result["turns_per_understood"]), (1.0, 0.5, 3.0))
        self.assertEqual(result["latency_p50_ms"], 100)
        self.assertEqual(result["ai_calls_per_turn"], 2.0)
        table = metrics.report([result])
        self.assertIn("| S1 | steady | 3 | 1 | 1 | 2 |", table)


class DialogueTest(unittest.TestCase):
    def setUp(self):
        fixture = test_agent.AgentTest()
        fixture.setUp()
        self.session = fixture.session

    def test_dialogue_records_turns_progress_and_probes(self):
        async def tutor(session, text, mode):
            if text.startswith("Can you delete"):
                next(n for n in session["nodes"] if n["id"] == "phase")["pendingRemoval"] = "Requested."
                return "Marked Phase for removal.", [{"type": "map.update"}]
            session["learner"]["p1"] = {"state": "understood", "attempts": 0, "evidence": ""}
            return "Good. Next is design?", [{"type": "lesson.update"}]
        with patch.object(run.app, "checked_plan", side_effect=tutor), patch.object(run, "ai_calls", side_effect=range(100)):
            result = run.run_dialogue(self.session, "S1", "editor", 4, use_judge=True,
                                      say=lambda persona, session: "a phase is a stage", grade=lambda session, answer: "supported")
        turns = result["turns"]
        self.assertEqual([t["user"] for t in turns][:3], ["a phase is a stage"] * 3)
        self.assertEqual(turns[3]["user"], "Can you delete the fase node?")
        self.assertTrue(turns[3]["probe"]["passed"])
        self.assertEqual(turns[0]["lesson"]["p1"], "understood")
        self.assertEqual(turns[0]["ai_calls"], 1)
        self.assertEqual(turns[0]["judgement"], "supported")
        self.assertEqual(len(self.session["messages"]), 8)

    def test_errors_are_recorded_and_the_run_continues(self):
        async def failing(session, text, mode):
            raise run.ai.AIError("The tutor could not finish this turn.")
        with patch.object(run.app, "checked_plan", side_effect=failing), patch.object(run, "ai_calls", return_value=0):
            result = run.run_dialogue(self.session, "S1", "stuck", 2, say=lambda persona, session: "I don't know")
        self.assertEqual([t["error"] for t in result["turns"]], ["The tutor could not finish this turn."] * 2)


if __name__ == "__main__":
    unittest.main()
