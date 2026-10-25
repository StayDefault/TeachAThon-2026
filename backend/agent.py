"""Bounded tutor tool loop. Tools stage changes; the caller commits a validated plan."""

import copy
import json
import logging
import re
import time

from tutor import MAX_NODES, PlanError, apply_plan

log = logging.getLogger("uvicorn.error.dyscover.agent")


def edit_scope(session, text):
    """Resolve explicit editing verbs and exact targets; never fuzzy-match a mutation."""
    command = re.match(r"\s*(?:(?:please|can you|could you|would you|I want to|I'd like to|I would like to|let's)\s+)*(delete|remove|rename|move|reorganize|reorganise|rearrange|restructure|change)\b(.*)", text, re.I)
    if not command:
        return None, set()
    verb, rest = command.group(1).lower(), command.group(2)
    action = {"delete": "remove", "remove": "remove", "rename": "rename", "change": "rename"}.get(verb, "move")
    if verb == "change" and not re.search(r"\b(label|name)\b", rest, re.I):
        return None, set()
    if verb in ("reorganize", "reorganise", "rearrange", "restructure"):
        return ("move", {n["id"] for n in session["nodes"] if n["id"] != "root"}) if re.search(r"\bmap\b", rest, re.I) else (None, set())
    target_text = re.split(r"\b(?:under|beneath|to|as)\b", rest, maxsplit=1, flags=re.I)[0]
    matches = {n["id"] for n in session["nodes"] if re.search(r"(?<!\w)" + re.escape(n["label"]) + r"(?!\w)", target_text, re.I)}
    if not matches and re.search(r"\b(this|that|selected)\b", target_text, re.I):
        selected = session.get("selectedNodeId")
        matches = {selected} if any(n["id"] == selected for n in session["nodes"]) else set()
    return action, matches if len(matches) == 1 else set()


def raw_nodes(session):
    result = []
    for node in session["nodes"]:
        detail = session["details"][node["id"]]
        correction = node.get("correction", {})
        result.append({"id": node["id"], "parentId": node["parentId"], "label": node["label"],
                       "subtitle": node.get("subtitle", ""), "status": node["status"],
                       "said": correction.get("said", ""), "actually": correction.get("actually", ""),
                       "summary": detail["summary"], "sourceId": detail["sourceId"],
                       "review": "none", "reviewReason": ""})
    return result


def function(name, description, properties):
    return {"type": "function", "name": name, "description": description, "strict": True,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": properties, "required": list(properties)}}


STRING = {"type": "string"}


def expansion_requested(text, nodes=()):
    command = re.match(r"\s*(?:(?:please|can you|could you|would you|I want to|I want you to|I'd like to)\s+)*(?:expand|extend|grow)\b(.*)", text, re.I)
    if not command:
        return False
    rest = command.group(1).strip(" .!?")
    return (not rest or rest.casefold() in ("it", "this", "that", "further", "more", "on that", "on this", "on it", "it further")
            or bool(re.search(r"\b(map|graph|structure|tree|branch|nodes?|concepts?|content|topics?|material|missing|uncovered|covered)\b", rest, re.I))
            or any(re.search(r"(?<!\w)" + re.escape(node["label"]) + r"(?!\w)", rest, re.I) for node in nodes))


def expansion_target(session, text):
    named = re.search(r"\b(?:node|branch|topic|concept)\s+([A-Za-z0-9_-]+)", text, re.I)
    ids = {node["id"] for node in session["nodes"]}
    if named and named[1] in ids:
        return named[1]
    if re.search(r"\b(map|graph|tree)\b", text, re.I) and not re.search(r"\b(node|branch|topic|concept|under|beneath)\b", text, re.I):
        return "root"
    matches = [node for node in session["nodes"] if re.search(r"(?<!\w)" + re.escape(node["label"]) + r"(?!\w)", text, re.I)]
    if matches:
        longest = max(len(node["label"]) for node in matches)
        winners = [node for node in matches if len(node["label"]) == longest]
        if len(winners) != 1 or any(node["label"].casefold() not in winners[0]["label"].casefold() for node in matches):
            return None
        return winners[0]["id"]
    if re.search(r"\b(map|graph|structure|tree)\b", text, re.I):
        return "root"
    if named and named[1].casefold() not in ("further", "more", "this", "that", "selected"):
        return None
    selected = session.get("selectedNodeId")
    return selected if selected in ids else "root"


def run(session, text, mode, payload, request, node_schema, error_type):
    started = time.monotonic()
    action, targets = edit_scope(session, text)
    expanding = mode != "review" and expansion_requested(text, session["nodes"])
    target = expansion_target(session, text) if expanding else None
    expanded = False
    proposal = {"title": session["session"]["title"], "topic": session["session"]["topic"],
                "answer": "Checking the material.", "nodes": raw_nodes(session)}
    tools = [function("search_materials", "Find source passages before explaining or changing content. An empty query lists passages for missing-topic exploration.", {"query": STRING})]
    if mode != "review" and not action and not expanding and len(session["nodes"]) < MAX_NODES:
        tools.append(function("add_node", "Map each new source-supported idea you explain, without requiring learner repetition. Reuse existing concepts instead of duplicates.", node_schema["properties"]))
    if expanding and target and len(session["nodes"]) < MAX_NODES:
        tools.append(function("expand_branch", "Add ALL missing relevant immediate subtopics of expansion_target_id in ONE batch. Each node must be a cited New child of that target. Do not recursively expand grandchildren or alter existing nodes. Return an empty list if already complete.",
                              {"nodes": {"type": "array", "items": node_schema}}))
    tools.append(function("review_node", "Review an existing learner edit or misconception. Removal preserves the node until confirmation.", {
        "nodeId": STRING, "decision": {"type": "string", "enum": ["agree", "corrected", "remove"]},
        "reason": STRING, "sourceId": STRING, "summary": STRING, "said": STRING, "actually": STRING}))
    if mode == "review":
        tools = [t for t in tools if t["name"] in ("search_materials", "review_node")]
    elif expanding:
        tools = [t for t in tools if t["name"] in ("search_materials", "expand_branch")]
    elif targets:
        if action == "remove":
            tools = [tools[0], function("propose_removal", "Propose removal of the explicitly requested node, without renaming or correcting it.", {"nodeId": STRING, "reason": STRING})]
        elif action == "rename":
            tools = [tools[0], function("rename_node", "Rename only the explicitly requested node.", {"nodeId": STRING, "label": STRING})]
        elif action == "move":
            tools = [tools[0], function("move_node", "Change the parent of an explicitly requested node.", {"nodeId": STRING, "parentId": STRING})]
    if action and not targets:
        tools = [tools[0]]
    context = json.loads(payload["input"])
    context["source_passages"] = [{"id": c["id"], "file": c["fileName"], "page": c["page"]} for c in session["chunks"]]
    context.update(selected_node_id=session.get("selectedNodeId"), permitted_action=action,
                   permitted_targets=sorted(targets), expansion_target_id=target, remaining_node_slots=max(0, MAX_NODES - len(session["nodes"])))
    instructions = payload["instructions"]
    for obsolete in (
        "Return the COMPLETE map on every turn; keep existing IDs and parents unless the learner requests an edit. ",
        "If a node should be removed, keep it in the COMPLETE map and set review remove with a short reviewReason. ",
        "Return title and topic unchanged after init. ",
    ):
        instructions = instructions.replace(obsolete, "")
    instructions += (
        " You are a backend tutor agent. The final JSON contains only answer. Use search_materials for evidence before factual explanations or content changes. "
        "Tool results describe staged changes, not committed changes. If a tool fails, do not claim success; fix it or explain the problem. "
        "Tool permissions are enforced by the server. Never substitute rename, move or correction for a requested deletion. "
        "If permitted_action is non-null but permitted_targets is empty, ask which existing node they mean and change nothing; speech may misrecognize names. "
        "Do not infer a rename from a similar-sounding word. Use exact existing node IDs. "
        "For automatic review, review only the node identified in learner_message. Otherwise review only learner-edited nodes or actual learner misconceptions. "
        "Agree with accurate brief notes; brevity or omitted optional detail alone is not a misconception. "
        "Do not ask a question the learner has already said they cannot answer: explain differently first. "
        "You have at most five tool rounds before the final answer. Search again only when you need different source passages. "
        "Once you have enough evidence and have staged the requested changes, stop calling tools and answer."
    )
    if expanding:
        instructions += (
            " For explicit expansion, read all supplied source passages and add the complete relevant next level in one expand_branch call. "
            "Do not stop at three topics or select only a few examples. Existing children are retained; add all missing siblings. "
            "Stop after this one level so the learner controls deeper expansion. If expansion_target_id is null, ask which branch and change nothing. "
            "After expansion, briefly invite choosing a subtopic to expand further or using Learn this topic to return to the learner conversation. "
            "Keep the answer under 1500 characters; the panel lists the children, so do not read out a long complete list."
        )
    final_schema = {"type": "object", "additionalProperties": False, "properties": {"answer": STRING}, "required": ["answer"]}
    inputs = [{"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
    seen_sources, touched = set(), set()
    allowed = {tool["name"]: tool for tool in tools}
    review_match = re.search(r"Review only node ([A-Za-z0-9_-]+)", text)
    review_id = review_match.group(1) if review_match else None
    for step in range(6):
        body = dict(payload, instructions=instructions, input=copy.deepcopy(inputs), tools=tools,
                    parallel_tool_calls=False, include=["reasoning.encrypted_content"],
                    text={"format": {"type": "json_schema", "name": "tutor_answer", "strict": True, "schema": final_schema}})
        if mode == "review":
            body["tool_choice"] = "none" if review_id in touched else {
                "type": "function", "name": "review_node" if seen_sources else "search_materials"}
        elif not action and not seen_sources:
            body["tool_choice"] = {"type": "function", "name": "search_materials"}
        elif expanding and target and "expand_branch" in allowed and not expanded:
            body["tool_choice"] = {"type": "function", "name": "expand_branch"}
        if step == 5 or expanded or (not expanding and len(touched) >= 3) or (action and targets and targets <= touched):
            body["tool_choice"] = "none"
            body["instructions"] += (
                " Tool work is finished for this turn. Return the final answer now using the evidence already retrieved. "
                "Describe only successfully staged changes; state any part you could not complete. "
                "Do not claim rejected operations succeeded or ask the learner to shorten an ordinary request."
            )
        response = request("responses", body)
        if response.get("status") != "completed" or not isinstance(response.get("output"), list):
            raise error_type("The tutor could not finish this turn. Please try again.")
        outputs = response["output"]
        if not all(isinstance(item, dict) for item in outputs):
            raise error_type("The tutor returned an invalid response. Please try again.")
        calls = [item for item in outputs if item.get("type") == "function_call"]
        if any(not isinstance(call.get("call_id"), str) for call in calls):
            raise error_type("The tutor returned an invalid tool request. Please try again.")
        if step == 5 and calls:
            raise error_type("The tutor could not finish its reply. Please try again. No map changes were saved.")
        if not calls:
            if mode == "review" and review_id not in touched:
                raise error_type("The tutor could not finish reviewing this edit. Your edit is saved; save it again to retry the review.")
            if expanding and target and "expand_branch" in allowed and not expanded:
                raise error_type("The tutor could not complete this branch expansion. Please try again. No map changes were saved.")
            try:
                answer = next(p["text"] for item in outputs if item.get("type") == "message" for p in item.get("content", []) if p.get("type") == "output_text")
                final = json.loads(answer)
                if set(final) != {"answer"} or not isinstance(final["answer"], str):
                    raise ValueError
                if mode == "review" and review_id not in touched:
                    raise ValueError
                if not action and not seen_sources:
                    raise ValueError
                proposal["answer"] = final["answer"]
                apply_plan(copy.deepcopy(session), proposal, allow_restructure=True)
            except (ValueError, TypeError, KeyError, StopIteration):
                raise error_type("The tutor returned an incomplete answer. Please try again.") from None
            log.info("Tutor agent completed steps=%s changes=%s elapsed_ms=%s", step + 1, len(touched), round((time.monotonic() - started) * 1000))
            return proposal
        inputs.extend(outputs)
        for call in calls:
            name = call.get("name")
            try:
                args = json.loads(call["arguments"])
                schema = allowed[name]["parameters"]["properties"]
                if not isinstance(args, dict) or set(args) != set(schema):
                    raise ValueError("Invalid tool arguments")
                for key, field in schema.items():
                    if field["type"] == "array":
                        if not isinstance(args[key], list) or not all(isinstance(item, dict) and set(item) == set(node_schema["properties"]) for item in args[key]):
                            raise ValueError("Invalid branch node list")
                        continue
                    if not isinstance(args[key], str) and not (args[key] is None and isinstance(field["type"], list) and "null" in field["type"]):
                        raise ValueError("Invalid tool argument type")
                    if "enum" in field and args[key] not in field["enum"]:
                        raise ValueError("Invalid tool decision")
                if name == "search_materials":
                    terms = set(re.findall(r"\w+", args["query"].casefold()))
                    def rank(chunk):
                        matches = len(terms & set(re.findall(r"\w+", chunk["text"].casefold())))
                        return matches
                    ranked = session["chunks"] if expanding else sorted(session["chunks"], key=rank, reverse=True)[:6]
                    seen_sources.update(c["id"] for c in ranked)
                    result = [{"id": c["id"], "text": c["text"], "file": c["fileName"], "page": c["page"]} for c in ranked]
                elif name == "expand_branch":
                    if expanded:
                        raise ValueError("This level is already expanded; return the final answer")
                    candidate = copy.deepcopy(proposal)
                    additions = args["nodes"]
                    labels = {node["label"].strip().casefold() for node in candidate["nodes"] if node["parentId"] == target}
                    existing_ids = {node["id"] for node in candidate["nodes"]}
                    if len(candidate["nodes"]) + len(additions) > MAX_NODES:
                        raise ValueError(f"This complete branch exceeds the {MAX_NODES}-node prototype capacity; do not silently truncate it")
                    for node in additions:
                        if (node["id"] in existing_ids or node["parentId"] != target or node["status"] != "new"
                                or node["review"] != "none" or node["sourceId"] not in seen_sources):
                            raise ValueError("Add only new, source-backed immediate children of the expansion target")
                        if not isinstance(node["label"], str) or node["label"].strip().casefold() in labels:
                            raise ValueError("Do not duplicate an existing sibling topic")
                        labels.add(node["label"].strip().casefold())
                        existing_ids.add(node["id"])
                    candidate["nodes"].extend(copy.deepcopy(additions))
                    candidate["expandedNodeId"] = target
                    apply_plan(copy.deepcopy(session), candidate, allow_restructure=True)
                    proposal = candidate
                    touched.update(node["id"] for node in additions)
                    expanded = True
                    result = {"staged": True, "expandedNodeId": target, "childrenAdded": len(additions),
                              "next": "Choose a child to expand further or Learn this topic."}
                else:
                    candidate = copy.deepcopy(proposal)
                    node_id = args.get("nodeId", args.get("id"))
                    node = next((n for n in candidate["nodes"] if n["id"] == node_id), None)
                    if mode == "review" and node_id != review_id:
                        raise ValueError("Review only the requested node")
                    if name == "add_node":
                        if node or args["status"] != "new" or args["review"] != "none":
                            raise ValueError("Add a new node with status new and review none")
                        candidate["nodes"].append(args.copy())
                    elif name == "review_node":
                        if not node or (action == "remove"):
                            raise ValueError("Use the requested operation on an existing node")
                        if args["decision"] == "agree" and not next(n for n in session["nodes"] if n["id"] == node_id).get("userEdited"):
                            raise ValueError("Agreement is only for learner content edits")
                        if args["decision"] == "corrected":
                            node.update(status="corrected", said=args["said"], actually=args["actually"], summary=args["summary"], sourceId=args["sourceId"], review="none", reviewReason="")
                        else:
                            node.update(review=args["decision"], reviewReason=args["reason"], sourceId=args["sourceId"])
                    else:
                        if not node or node_id not in targets:
                            raise ValueError("The learner did not authorize this target")
                        if name == "propose_removal":
                            node.update(review="remove", reviewReason=args["reason"])
                        elif name == "rename_node":
                            node["label"] = args["label"]
                        elif name == "move_node":
                            node["parentId"] = args["parentId"]
                    if name in ("add_node", "review_node") and args["sourceId"] not in seen_sources:
                        raise ValueError("Search for the supporting source before changing content")
                    if len(touched | {node_id}) > 3:
                        raise ValueError("Change at most three nodes per turn")
                    apply_plan(copy.deepcopy(session), candidate, allow_restructure=True)
                    proposal = candidate
                    touched.add(node_id)
                    result = {"staged": True, "nodeId": node_id}
                log.info("Tutor tool=%s node=%s outcome=ok", name, args.get("nodeId", args.get("id", "-")))
            except (ValueError, TypeError, KeyError, PlanError) as exc:
                result = {"error": str(exc)}
                log.warning("Tutor tool=%s outcome=rejected reason=%s", name, getattr(exc, "reason", str(exc)))
            inputs.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(result, ensure_ascii=False)})
    raise error_type("The tutor could not finish its reply. Please try again. No map changes were saved.")
