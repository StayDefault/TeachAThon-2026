"""Tutor agent. The model decides what to do; tools stage changes; the server validates and commits."""

import copy
import difflib
import json
import logging
import re
import time

from context import build, prompt, sources_fit, sources_message
from state import LEVELS, learner_said, mastery, normalize, validate_lesson
from tutor import MAX_NODES, PlanError, apply_plan

log = logging.getLogger("uvicorn.error.dyscover.agent")

TOOL_ROUNDS = 8
MAX_EDGES = 40
EXTRAS = ("planId", "mastery", "learnerWords")
STRING = {"type": "string"}


def function(name, description, properties):
    return {"type": "function", "name": name, "description": description, "strict": True,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": properties, "required": list(properties)}}


CHILD = {"type": "object", "additionalProperties": False, "required": ["id", "label", "summary", "sourceId"],
         "properties": {"id": STRING, "label": STRING, "summary": STRING, "sourceId": STRING}}
TOOLS = {
    "resolve_node": function("resolve_node", "Find map nodes matching a name the learner said or typed. Returns ranked candidates, including sound-alike matches from speech errors.", {"phrase": STRING}),
    "search_sources": function("search_sources", "Search the learner's material and return the most relevant passages with their text.", {"query": STRING}),
    "add_concept": function("add_concept", "Add one concept to the map with mastery introduced. For a lesson concept pass its planId; the node ID then equals the planId. Use an empty planId for other ideas, with a new short ID.", {
        "id": STRING, "planId": STRING, "parentId": STRING, "label": STRING, "summary": STRING, "sourceId": STRING}),
    "expand_branch": function("expand_branch", "Add all relevant immediate subtopics of one node in a single batch. Use at most once per turn.", {
        "parentId": STRING, "nodes": {"type": "array", "items": CHILD}}),
    "update_understanding": function("update_understanding", "Record the learner's understanding of a concept. conceptId is a node ID or a lesson concept ID; a lesson concept not yet on the map is added automatically. Level understood needs evidence quoting the learner's own words.", {
        "conceptId": STRING, "level": {"type": "string", "enum": list(LEVELS)}, "evidence": STRING}),
    "record_misconception": function("record_misconception", "Mark a misconception on a map node. said must quote the learner's words; actually is one short correction supported by sourceId.", {
        "nodeId": STRING, "said": STRING, "actually": STRING, "sourceId": STRING}),
    "edit_node": function("edit_node", "Rename and/or move a node when the learner asks. Use an empty string for a part that stays the same.", {
        "nodeId": STRING, "label": STRING, "parentId": STRING}),
    "link_nodes": function("link_nodes", "Draw a labelled cross-link between two nodes, for example 'causes' or 'is part of'.", {
        "fromId": STRING, "toId": STRING, "relation": STRING}),
    "unlink_nodes": function("unlink_nodes", "Remove a cross-link by its edge ID.", {"edgeId": STRING}),
    "propose_removal": function("propose_removal", "Propose removing a node. It stays on the map until the learner confirms on screen.", {
        "nodeId": STRING, "reason": STRING}),
    "set_focus": function("set_focus", "Make a lesson concept the current focus.", {"planId": STRING}),
    "add_plan_item": function("add_plan_item", "Add a concept from the material to the lesson. parentId is another lesson concept ID or an empty string.", {
        "title": STRING, "summary": STRING, "sourceId": STRING, "parentId": STRING}),
    "review_edit": function("review_edit", "Decide on a learner-edited node: agree, corrected or remove. For corrected, said quotes their saved wording, actually and summary give the supported correction.", {
        "nodeId": STRING, "decision": {"type": "string", "enum": ["agree", "corrected", "remove"]},
        "reason": STRING, "sourceId": STRING, "said": STRING, "actually": STRING, "summary": STRING}),
}
FINAL = {"type": "json_schema", "name": "tutor_answer", "strict": True,
         "schema": {"type": "object", "additionalProperties": False, "properties": {"answer": STRING}, "required": ["answer"]}}


def raw_nodes(session):
    result = []
    for node in session["nodes"]:
        detail = session["details"][node["id"]]
        correction = node.get("correction") or {}
        item = {"id": node["id"], "parentId": node["parentId"], "label": node["label"],
                "subtitle": node.get("subtitle", ""), "status": node["status"],
                "said": correction.get("said", ""), "actually": correction.get("actually", ""),
                "summary": detail["summary"], "sourceId": detail["sourceId"], "review": "none", "reviewReason": ""}
        item.update({key: node[key] for key in EXTRAS if node.get(key)})
        result.append(item)
    return result


def phonetic(word):
    word = re.sub(r"[^a-z]", "", word.casefold())
    for pattern, replacement in (("ph", "f"), ("ck", "k"), ("c(?=[eiy])", "s"), ("c", "k"), ("q", "k"), ("x", "ks"), ("z", "s"), ("wh", "w")):
        word = re.sub(pattern, replacement, word)
    return word[:1] + re.sub(r"[aeiouyhw]", "", word[1:]) if word else ""


def resolve(nodes, phrase):
    words = normalize(phrase).split()
    candidates = []
    for node in nodes:
        label = normalize(node["label"])
        size = max(1, len(label.split()))
        windows = [" ".join(words[i:i + size]) for i in range(max(1, len(words) - size + 1))] or [""]
        spelled = max(difflib.SequenceMatcher(None, label, window).ratio() for window in windows)
        sound = max((1.0 if [phonetic(w) for w in label.split()] == [phonetic(w) for w in window.split()] else 0.0) for window in windows)
        score = 1.0 if label in " ".join(words) and label else max(spelled, 0.85 * sound)
        if score >= 0.5:
            candidates.append({"nodeId": node["id"], "label": node["label"], "score": round(score, 2),
                               "match": "exact" if score == 1.0 else "sound-alike" if sound and score == 0.85 * sound else "similar spelling"})
    return sorted(candidates, key=lambda c: -c["score"])[:5]


def search(chunks, query):
    terms = set(re.findall(r"\w+", query.casefold()))
    ranked = sorted(chunks, key=lambda c: len(terms & set(re.findall(r"\w+", c["text"].casefold()))), reverse=True)[:6]
    return [{"id": c["id"], "text": c["text"], "file": c["fileName"], "page": c["page"]} for c in ranked]


class Stage:
    """Changes staged during one turn, validated against a copy of the session after every tool call."""

    def __init__(self, session):
        self.session = session
        self.proposal = {"title": session["session"]["title"], "topic": session["session"]["topic"],
                         "answer": "Working.", "nodes": raw_nodes(session)}
        self.extra = {"lesson": copy.deepcopy(session["lesson"]), "learner": copy.deepcopy(session["learner"]),
                      "focus": session["focus"], "edges": copy.deepcopy(session["edges"]),
                      "focusSince": session.get("focusSince", 0)}
        self.expanded = False
        self.reviewed = set()

    def node(self, nodes, node_id):
        found = next((n for n in nodes if n["id"] == node_id), None)
        if not found:
            raise ValueError(f"No map node has ID {node_id!r}; use resolve_node or the map context")
        return found

    def lesson_item(self, plan_id):
        found = next((i for i in self.extra["lesson"] if i["id"] == plan_id), None)
        if not found:
            raise ValueError(f"No lesson concept has ID {plan_id!r}")
        return found

    def commit_nodes(self, nodes):
        candidate = dict(self.proposal, nodes=nodes)
        apply_plan(copy.deepcopy(self.session), candidate, allow_restructure=True)
        self.proposal = candidate

    def reveal(self, nodes, plan_id):
        item = self.lesson_item(plan_id)
        parent = next((n["id"] for n in nodes if item["parentId"] and n.get("planId") == item["parentId"]), "root")
        node = {"id": plan_id, "parentId": parent, "label": item["title"], "subtitle": "", "status": "new",
                "said": "", "actually": "", "summary": item["summary"], "sourceId": item["sourceId"],
                "review": "none", "reviewReason": "", "planId": plan_id, "mastery": "introduced"}
        nodes.append(node)
        return node

    def learn(self, key, state, evidence=""):
        record = self.extra["learner"].setdefault(key, {"state": "introduced", "attempts": 0, "evidence": ""})
        if state == "attempted":
            record["attempts"] += 1
        record["state"] = state
        if evidence:
            record["evidence"] = evidence[:300]

    def call(self, name, args, mode, review_id):
        nodes = copy.deepcopy(self.proposal["nodes"])
        if mode == "review" and name != "search_sources" and (name != "review_edit" or args["nodeId"] != review_id):
            raise ValueError("This is an automatic review: call review_edit for the requested node only")
        if name == "resolve_node":
            return {"candidates": resolve(nodes, args["phrase"])}
        if name == "search_sources":
            return {"passages": search(self.session["chunks"], args["query"])}
        if name == "add_concept":
            plan_id = args["planId"].strip()
            if plan_id:
                self.lesson_item(plan_id)
                if any(n.get("planId") == plan_id for n in nodes):
                    raise ValueError("That lesson concept is already on the map; reuse its node")
                args = dict(args, id=plan_id)
            self.node(nodes, args["parentId"])
            if any(n["id"] == args["id"] for n in nodes):
                raise ValueError("That node ID already exists; choose a new ID")
            nodes.append({"id": args["id"], "parentId": args["parentId"], "label": args["label"], "subtitle": "",
                          "status": "new", "said": "", "actually": "", "summary": args["summary"], "sourceId": args["sourceId"],
                          "review": "none", "reviewReason": "", "mastery": "introduced", **({"planId": plan_id} if plan_id else {})})
            self.commit_nodes(nodes)
            if plan_id and self.extra["learner"].get(plan_id, {}).get("state") in (None, "unseen"):
                self.learn(plan_id, "introduced")
            return {"staged": True, "nodeId": args["id"]}
        if name == "expand_branch":
            if self.expanded:
                raise ValueError("This turn already expanded a branch")
            self.node(nodes, args["parentId"])
            siblings = {normalize(n["label"]) for n in nodes if n["parentId"] == args["parentId"]}
            if not args["nodes"] or len(nodes) + len(args["nodes"]) > MAX_NODES:
                raise ValueError(f"Add between one child and the {MAX_NODES}-node map capacity")
            for child in args["nodes"]:
                if any(n["id"] == child["id"] for n in nodes) or normalize(child["label"]) in siblings:
                    raise ValueError(f"{child['label']!r} duplicates an existing node or sibling")
                siblings.add(normalize(child["label"]))
                nodes.append({"id": child["id"], "parentId": args["parentId"], "label": child["label"], "subtitle": "",
                              "status": "new", "said": "", "actually": "", "summary": child["summary"],
                              "sourceId": child["sourceId"], "review": "none", "reviewReason": "", "mastery": "introduced"})
            self.commit_nodes(nodes)
            self.proposal["expandedNodeId"] = args["parentId"]
            self.expanded = True
            return {"staged": True, "childrenAdded": len(args["nodes"])}
        if name == "update_understanding":
            concept, level, evidence = args["conceptId"], args["level"], args["evidence"].strip()
            node = next((n for n in nodes if n["id"] == concept or n.get("planId") == concept), None)
            plan_id = node.get("planId") if node else concept
            if node is None and level != "skipped":
                node = self.reveal(nodes, concept)
            elif node is None:
                self.lesson_item(concept)
            if level == "understood" and not learner_said(self.session, evidence):
                raise ValueError("Evidence for understood must quote the learner's own recent words exactly")
            if node:
                node["mastery"] = mastery(level)
                if level == "understood":
                    node["learnerWords"] = evidence[:160]
                self.commit_nodes(nodes)
            self.learn(plan_id or node["id"], level, evidence if level == "understood" else "")
            return {"staged": True, "conceptId": plan_id or node["id"], "level": level}
        if name == "record_misconception":
            node = self.node(nodes, args["nodeId"])
            node.update(status="corrected", said=args["said"], actually=args["actually"], sourceId=args["sourceId"])
            self.commit_nodes(nodes)
            self.learn(node.get("planId") or node["id"], "attempted")
            return {"staged": True, "nodeId": node["id"]}
        if name == "edit_node":
            node = self.node(nodes, args["nodeId"])
            if args["parentId"].strip():
                if node["id"] == "root":
                    raise ValueError("The root cannot move")
                self.node(nodes, args["parentId"])
                node["parentId"] = args["parentId"]
            if args["label"].strip():
                node["label"] = args["label"].strip()
            self.commit_nodes(nodes)
            return {"staged": True, "nodeId": node["id"], "label": node["label"], "parentId": node["parentId"]}
        if name == "link_nodes":
            ends = (self.node(nodes, args["fromId"])["id"], self.node(nodes, args["toId"])["id"])
            relation = args["relation"].strip()
            if ends[0] == ends[1] or not 1 <= len(relation.split()) <= 4 or len(relation) > 40:
                raise ValueError("Link two different nodes with a relation of one to four words")
            edges = self.extra["edges"]
            if any({e["from"], e["to"]} == set(ends) for e in edges) or len(edges) >= MAX_EDGES:
                raise ValueError("These nodes are already linked, or the map has too many links")
            edge_id = f"e{max([int(e['id'][1:]) for e in edges if e['id'][1:].isdigit()] + [0]) + 1}"
            edges.append({"id": edge_id, "from": ends[0], "to": ends[1], "label": relation})
            return {"staged": True, "edgeId": edge_id}
        if name == "unlink_nodes":
            before = len(self.extra["edges"])
            self.extra["edges"] = [e for e in self.extra["edges"] if e["id"] != args["edgeId"]]
            if len(self.extra["edges"]) == before:
                raise ValueError("No cross-link has that ID")
            return {"staged": True}
        if name == "propose_removal":
            node = self.node(nodes, args["nodeId"])
            if node["id"] == "root" or not args["reason"].strip():
                raise ValueError("The root cannot be removed, and a removal needs a reason")
            node.update(review="remove", reviewReason=args["reason"])
            self.commit_nodes(nodes)
            return {"staged": True, "nodeId": node["id"], "note": "Shown as a proposal until the learner confirms"}
        if name == "set_focus":
            self.lesson_item(args["planId"])
            if self.extra["focus"] != args["planId"]:
                self.extra["focus"] = args["planId"]
                self.extra["focusSince"] = len(self.session["messages"])
            return {"staged": True, "focus": args["planId"]}
        if name == "add_plan_item":
            lesson = self.extra["lesson"]
            plan_id = f"p{max([int(i['id'][1:]) for i in lesson if i['id'][1:].isdigit()] + [0]) + 1}"
            item = {"id": plan_id, "title": args["title"], "summary": args["summary"], "sourceId": args["sourceId"], "parentId": args["parentId"]}
            self.extra["lesson"] = validate_lesson(self.session, lesson + [item])
            return {"staged": True, "planId": plan_id}
        if name == "review_edit":
            node = self.node(nodes, args["nodeId"])
            if not next((n for n in self.session["nodes"] if n["id"] == node["id"]), {}).get("userEdited"):
                raise ValueError("review_edit is only for nodes the learner edited")
            if args["decision"] == "corrected":
                node.update(status="corrected", said=args["said"], actually=args["actually"], summary=args["summary"], sourceId=args["sourceId"])
            else:
                node.update(review=args["decision"], reviewReason=args["reason"], sourceId=args["sourceId"])
            self.commit_nodes(nodes)
            self.reviewed.add(node["id"])
            return {"staged": True, "nodeId": node["id"], "decision": args["decision"]}
        raise ValueError(f"Unknown tool {name}")


def run(session, text, mode, payload, request, error_type, review_id=None, feedback=None):
    started = time.monotonic()
    stage = Stage(session)
    names = ["review_edit", "search_sources"] if mode == "review" else list(TOOLS)
    if sources_fit(session):
        names.remove("search_sources")
    tools = [TOOLS[n] for n in names]
    instructions = prompt("tutor") + ("\n\n" + prompt("review") if mode == "review" else "")
    if feedback:
        instructions += f"\n\nYour previous attempt was rejected by the server: {feedback}. Fix that in this attempt."
    inputs = [{"role": "user", "content": sources_message(session)},
              {"role": "user", "content": json.dumps(build(session, text, mode, review_id), ensure_ascii=False)}]
    for step in range(TOOL_ROUNDS):
        body = dict(payload, instructions=instructions, input=copy.deepcopy(inputs), tools=tools,
                    parallel_tool_calls=False, include=["reasoning.encrypted_content"], text={"format": FINAL})
        if mode == "review" and review_id not in stage.reviewed:
            body["tool_choice"] = "required"
        if step == TOOL_ROUNDS - 1 or (mode == "review" and review_id in stage.reviewed):
            body["tool_choice"] = "none"
        response = request("responses", body)
        outputs = response.get("output") if response.get("status") == "completed" else None
        if not isinstance(outputs, list) or not all(isinstance(item, dict) for item in outputs):
            raise error_type("The tutor could not finish this turn. Please try again.")
        calls = [item for item in outputs if item.get("type") == "function_call"]
        if any(not isinstance(call.get("call_id"), str) for call in calls):
            raise error_type("The tutor returned an invalid tool request. Please try again.")
        if not calls:
            try:
                answer = next(p["text"] for item in outputs if item.get("type") == "message"
                              for p in item.get("content", []) if p.get("type") == "output_text")
                final = json.loads(answer)
                if set(final) != {"answer"} or not isinstance(final["answer"], str) or not final["answer"].strip():
                    raise ValueError
                if mode == "review" and review_id not in stage.reviewed:
                    raise ValueError
                stage.proposal["answer"] = final["answer"].strip()
                apply_plan(copy.deepcopy(session), stage.proposal, allow_restructure=True)
            except (ValueError, TypeError, KeyError, StopIteration, PlanError):
                raise error_type("The tutor returned an incomplete answer. Please try again.") from None
            log.info("Tutor agent finished steps=%s elapsed_ms=%s", step + 1, round((time.monotonic() - started) * 1000))
            return dict(stage.proposal, staged=stage.extra)
        if step == TOOL_ROUNDS - 1:
            raise error_type("The tutor could not finish its reply. Please try again. No map changes were saved.")
        inputs.extend(outputs)
        for call in calls:
            name = call.get("name")
            try:
                if name not in {t["name"] for t in tools}:
                    raise ValueError(f"Tool {name} is not available in this turn")
                args = json.loads(call["arguments"])
                if not isinstance(args, dict) or set(args) != set(TOOLS[name]["parameters"]["properties"]):
                    raise ValueError("Invalid tool arguments")
                result = stage.call(name, args, mode, review_id)
                log.info("Tutor tool=%s outcome=ok", name)
            except (ValueError, TypeError, KeyError, PlanError) as exc:
                result = {"error": getattr(exc, "reason", None) or str(exc)}
                log.warning("Tutor tool=%s outcome=rejected reason=%s", name, result["error"])
            inputs.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(result, ensure_ascii=False)})
    raise error_type("The tutor could not finish its reply. Please try again. No map changes were saved.")
