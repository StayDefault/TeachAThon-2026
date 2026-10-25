"""Run simulated study sessions against the real tutor and score them.

From the repository root, with OPENAI_API_KEY set:
    backend/.venv/bin/python backend/evals/run.py --scenario S1 S3 --persona steady stuck --turns 12 --judge

Each run uploads a test-pack PDF, lets an LLM play a learner persona for N turns, and records the tutor's
answers, map changes, lesson progress, latency and API calls. Results go to backend/evals/results/<time>/.
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DYSCOVER_DB", str(Path(tempfile.mkdtemp()) / "eval.sqlite3"))
os.environ.setdefault("DYSCOVER_MAX_AI_CALLS", "100000")

# The modules below read the environment set above when they are imported.
import ai
import app
import store
from context import RECENT, summary_due
from evals.metrics import PERSONAS, report, score, sound_alike
from ingest import chunks_for, extract
from state import ensure, progress
from tutor import PlanError, message

FIXTURES = BACKEND.parent / "testing" / "Dyscover_Testing_Pack" / "fixtures"
SCENARIOS = {"S1": FIXTURES / "S1" / "assessment-1_0.pdf", "S2": FIXTURES / "S2" / "week-05-lecture.pdf",
             "S3": FIXTURES / "S3" / "week-04-lab-student.pdf"}
LEARNER_MODEL = os.environ.get("EVAL_LEARNER_MODEL", ai.TUTOR_MODEL)
PROBE_TURNS = (3, 7)


def schema(name, properties):
    return {"type": "json_schema", "name": name, "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}}


REPLY = schema("learner_reply", {"message": {"type": "string"}})
VERDICT = schema("grounding_verdict", {"verdict": {"type": "string", "enum": ["supported", "partly", "unsupported"]},
                                       "reason": {"type": "string"}})


def ask(instructions, data, text_format):
    payload = {"model": LEARNER_MODEL, "store": False, "instructions": instructions,
               "input": json.dumps(data, ensure_ascii=False), "text": {"format": text_format}}
    return json.loads(ai.response_text(ai.request("responses", payload)))


def ai_calls():
    with store.database() as db:
        row = db.execute("SELECT count FROM usage WHERE kind = 'ai_calls'").fetchone()
    return row[0] if row else 0


def new_session(path):
    result = extract(path.name, path.read_bytes())
    materials = [{"id": "m1", "name": path.name, "kind": result["kind"], "label": result["label"]}]
    session = ensure({"owner": "eval", "session": {"id": "eval", "title": "", "topic": "", "updatedAt": ""},
                      "materials": materials, "chunks": chunks_for(materials, [result]),
                      "nodes": [], "details": {}, "messages": [], "turns": 0})
    answer, _ = asyncio.run(app.checked_plan(session, "", "init", initial=True))
    session["messages"].append(message("assistant", answer))
    return session


def learner_says(persona, session):
    instructions = Path(__file__).with_name("learner.md").read_text(encoding="utf-8").replace("{persona}", PERSONAS[persona])
    conversation = [{"speaker": "student" if m["role"] == "user" else "tutor", "text": m["text"]} for m in session["messages"][-12:]]
    return ask(instructions, {"conversation": conversation, "map_labels": [n["label"] for n in session["nodes"]]}, REPLY)["message"].strip()


def judge(session, answer):
    instructions = Path(__file__).with_name("judge.md").read_text(encoding="utf-8")
    return ask(instructions, {"material": "\n".join(c["text"] for c in session["chunks"]), "reply": answer}, VERDICT)["verdict"]


def deletion_probe(session):
    """Ask to delete a node by a misheard name; passing means the right node is proposed for removal and nothing is renamed."""
    target = next((n for n in reversed(session["nodes"]) if n["id"] != "root" and not n.get("pendingRemoval")), None)
    if not target:
        return None
    return {"text": f"Can you delete the {sound_alike(target['label'])} node?", "target": target["id"],
            "labels": {n["id"]: n["label"] for n in session["nodes"]},
            "pending": {n["id"] for n in session["nodes"] if n.get("pendingRemoval")}}


def check_probe(session, probe):
    nodes = {n["id"]: n for n in session["nodes"]}
    renamed = any(nodes[i]["label"] != label for i, label in probe["labels"].items() if i in nodes)
    stray = {i for i, n in nodes.items() if n.get("pendingRemoval")} - probe["pending"] - {probe["target"]}
    passed = bool(nodes.get(probe["target"], {}).get("pendingRemoval")) and not renamed and not stray
    return {"text": probe["text"], "target": probe["target"], "passed": passed}


def run_dialogue(session, scenario, persona, turns, use_judge=False, say=learner_says, grade=judge):
    records = []
    for index in range(turns):
        probe = deletion_probe(session) if persona == "editor" and index in PROBE_TURNS else None
        record = {"turn": index + 1}
        try:
            text = probe["text"] if probe else say(persona, session)
            record["user"] = text
            session["messages"].append(message("user", text))
            calls, started = ai_calls(), time.monotonic()
            answer, events = asyncio.run(app.checked_plan(session, text, "turn"))
            record.update(latency_ms=round((time.monotonic() - started) * 1000), ai_calls=ai_calls() - calls, assistant=answer,
                          map_changes=sum(e["type"] not in ("map.focus", "lesson.update") for e in events))
            session["messages"].append(message("assistant", answer))
            session["turns"] += 1
            if probe:
                record["probe"] = check_probe(session, probe)
            if use_judge:
                record["judgement"] = grade(session, answer)
            if summary_due(session):
                end = len(session["messages"]) - RECENT
                session.update(summary=ai.summarize(session, session["messages"][session["summaryUpTo"]:end]), summaryUpTo=end)
        except (ai.AIError, PlanError) as exc:
            record["error"] = getattr(exc, "message", str(exc))
        record["lesson"] = {item["id"]: item["state"] for item in progress(session)["items"]}
        records.append(record)
    return {"scenario": scenario, "persona": persona, "lesson": session["lesson"], "summary": session["summary"],
            "turns": records, "map": session["nodes"], "edges": session["edges"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", nargs="+", choices=sorted(SCENARIOS), default=["S1"])
    parser.add_argument("--persona", nargs="+", choices=sorted(PERSONAS), default=sorted(PERSONAS))
    parser.add_argument("--turns", type=int, default=12)
    parser.add_argument("--judge", action="store_true", help="rate each tutor reply for grounding (extra API calls)")
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY to run evaluations.")
    out = Path(__file__).with_name("results") / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    scores = []
    for scenario in args.scenario:
        for persona in args.persona:
            print(f"Running {scenario} / {persona} …", flush=True)
            try:
                run = run_dialogue(new_session(SCENARIOS[scenario]), scenario, persona, args.turns, args.judge)
            except (ai.AIError, PlanError) as exc:
                print(f"  setup failed: {getattr(exc, 'message', exc)}")
                continue
            (out / f"{scenario}-{persona}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
            scores.append(score(run))
    header = f"# Dyscover evaluation {out.name}\n\nTutor model: `{ai.TUTOR_MODEL}`. Learner/judge model: `{LEARNER_MODEL}`. Turns per run: {args.turns}.\n\n"
    (out / "report.md").write_text(header + report(scores) + "\n", encoding="utf-8")
    print(report(scores))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
