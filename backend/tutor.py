"""Validate grounded AI plans and turn them into frontend map events."""

import re
import uuid
from datetime import datetime, timezone

MAX_NODES = 200

class PlanError(ValueError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason or "The map format was invalid"


def apply_plan(session, proposal, initial=False, allow_restructure=False):
    try:
        title, topic, answer, raw_nodes = (proposal[k] for k in ("title", "topic", "answer", "nodes"))
        if not all(isinstance(x, str) for x in (title, topic, answer)) or not isinstance(raw_nodes, list):
            raise ValueError("title, topic, answer and nodes have invalid types")
        if not 1 <= len(title.strip()) <= 80 or not 1 <= len(topic.strip()) <= 80:
            raise ValueError("title or topic is empty or too long")
        if initial and not answer.strip():
            answer = f"I've read your files. How much do you already know about {topic.strip()}?"
        if not 1 <= len(answer.strip()) <= 1500:
            raise ValueError("answer is empty or too long")
        if not 1 <= len(raw_nodes) <= MAX_NODES or (initial and len(raw_nodes) != 1):
            raise ValueError("the map has an invalid number of nodes; init requires exactly one root")
        if not initial and (title != session["session"]["title"] or topic != session["session"]["topic"]):
            raise ValueError("title and topic changed during an existing session")
        sources = {c["id"]: c for c in session["chunks"]}
        existing = {node["id"]: node for node in session["nodes"]}
        existing_ids = set(existing)
        ids = set()
        nodes, details = [], {}
        for item in raw_nodes:
            node_id, parent, label = item["id"], item["parentId"], item["label"]
            status, source_id, summary = item["status"], item["sourceId"], item["summary"]
            if node_id not in existing and item.get("review", "none") != "none":
                raise ValueError("only existing nodes can be reviewed")
            if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", node_id) or node_id in ids:
                raise ValueError("a node ID is invalid or duplicated")
            if parent is not None and (not isinstance(parent, str) or parent == node_id):
                raise ValueError("a parent ID is invalid")
            if not isinstance(label, str) or not 1 <= len(label.split()) <= 5 or len(label) > 60:
                raise ValueError("a node label must contain one to five words and at most 60 characters")
            before = existing.get(node_id)
            unverified = (source_id is None and before and session["details"][node_id].get("sourceId") is None
                          and label == before["label"] and summary == session["details"][node_id]["summary"]
                          and status == before["status"] and item.get("review", "none") in ("none", "remove"))
            if status not in ("normal", "new", "corrected") or (source_id not in sources and not unverified):
                raise ValueError("a node status or sourceId is invalid; cite an exact supplied passage ID")
            if not initial and node_id not in existing_ids and node_id != "root" and status != "corrected":
                status = "new"
            if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 600:
                raise ValueError("a node summary must contain one to 600 characters")
            node = {"id": node_id, "parentId": parent, "label": label.strip(), "status": status}
            if node_id == "root":
                if parent is not None:
                    raise ValueError("the root node must have a null parentId")
                node["status"] = "new" if initial else status
                if item["subtitle"].strip():
                    node["subtitle"] = item["subtitle"].strip()[:100]
            elif parent is None:
                raise ValueError("a non-root node needs a parentId")
            if status == "corrected" and item.get("review") != "remove" and not existing.get(node_id, {}).get("pendingRemoval"):
                said, actually = item["said"], item["actually"]
                if not isinstance(said, str) or not isinstance(actually, str) or not said.strip() or not actually.strip():
                    raise ValueError("a corrected node needs nonempty said and actually fields")
                node["correction"] = {"said": said[:200], "actually": actually[:300]}
                before = existing.get(node_id, {})
                if node["correction"] != before.get("correction"):
                    claims = [item["text"] for item in session.get("messages", []) if item.get("role") == "user"]
                    if session.get("details", {}).get(node_id, {}).get("userEdited"):
                        claims.append(session["details"][node_id]["summary"])
                        claims.append(existing.get(node_id, {}).get("label", ""))
                    quote = re.sub(r"\s+", " ", said).strip(" .!?").casefold()
                    if not any(quote in re.sub(r"\s+", " ", claim).casefold() for claim in claims):
                        raise ValueError("a correction must quote an actual learner statement or edited note; use review remove for an unsupported system-created node")
            source = sources.get(source_id)
            details[node_id] = session["details"][node_id].copy() if unverified else {"summary": summary.strip(), "sourceId": source_id,
                                "source": {"materialId": source["materialId"], "fileName": source["fileName"],
                                           "page": source["page"], "quote": source["text"]}}
            nodes.append(node)
            ids.add(node_id)
        if not initial:
            for node in nodes:
                before = existing.get(node["id"])
                if before:
                    item = next(item for item in raw_nodes if item["id"] == node["id"])
                    review = item.get("review", "none")
                    reason = item.get("reviewReason", "")
                    if review not in ("none", "agree", "remove") or not isinstance(reason, str) or len(reason) > 600:
                        raise ValueError("invalid node review")
                    if review != "none" and not reason.strip():
                        raise ValueError("a node review needs an explanation")
                    keys = ("position", "userEdited", "pendingRemoval") if allow_restructure else ("parentId", "label", "subtitle", "position", "userEdited", "pendingRemoval")
                    for key in keys:
                        if key in before:
                            node[key] = before[key]
                        else:
                            node.pop(key, None)
                    if review == "remove" or before.get("pendingRemoval"):
                        if node["id"] == "root":
                            raise ValueError("the root cannot be proposed for deletion")
                        node.clear()
                        node.update(before, pendingRemoval=reason.strip() if review == "remove" else before["pendingRemoval"])
                        details[node["id"]] = session["details"][node["id"]]
                        continue
                    proposed_correction = node["status"] == "corrected"
                    corrected = proposed_correction and (before["status"] != "corrected" or node.get("correction") != before.get("correction"))
                    if not corrected:
                        node["status"] = before["status"]
                        if before.get("correction"):
                            node["correction"] = before["correction"]
                    if review == "agree" and before.get("userEdited"):
                        if item["label"].strip() != before["label"] or item["summary"].strip() != session["details"][node["id"]]["summary"] or proposed_correction:
                            raise ValueError("agree must preserve the learner's label and description and must not correct it")
                        details[node["id"]]["summary"] = session["details"][node["id"]]["summary"]
                        details[node["id"]]["userEdited"] = False
                        node.update(userEdited=False, status="normal", pendingRemoval=None)
                        node.pop("correction", None)
                    elif corrected:
                        node.update(userEdited=False, pendingRemoval=None)
                        details[node["id"]]["userEdited"] = False
                    else:
                        details[node["id"]] = session["details"].get(node["id"], details[node["id"]])
            for before in session["nodes"]:
                if before["id"] not in ids:
                    retained = before.copy()
                    if allow_restructure and before["id"] != "root":
                        retained["pendingRemoval"] = "The tutor suggests removing this node. Confirm deletion or keep it."
                    nodes.append(retained)
                    details[before["id"]] = session["details"][before["id"]]
                    ids.add(before["id"])
        if len(nodes) > MAX_NODES:
            raise ValueError("the map has too many nodes")
        for before in session["nodes"]:
            removal_claim = rf"\b(?:I suggest|I recommend|I propose|we should|you should|let['’]s)\s+(?:remove|removing|delete|deleting|drop|dropping)\s+(?:the\s+)?[\"'`*]*{re.escape(before['label'])}\b"
            target = next((node for node in nodes if node["id"] == before["id"]), None)
            if re.search(removal_claim, answer, re.I) and target and not target.get("pendingRemoval"):
                raise ValueError("the answer proposes deleting a node but its review is not remove; mark that node review remove instead of corrected")
        if "root" not in ids or (initial and nodes[0]["id"] != "root"):
            raise ValueError("the map needs a root node with ID root, first during init")
        if "expandedNodeId" in proposal and (not isinstance(proposal["expandedNodeId"], str) or proposal["expandedNodeId"] not in ids):
            raise ValueError("the expanded branch does not exist")
        parents = {node["id"]: node["parentId"] for node in nodes}
        for node_id in ids:
            seen = set()
            cursor = node_id
            while cursor is not None:
                if cursor not in parents or cursor in seen:
                    raise ValueError("a node has a missing parent or a parent cycle")
                seen.add(cursor)
                cursor = parents[cursor]
        orders = {}
        if not initial:
            for node in nodes:
                before = existing.get(node["id"])
                if before and before["parentId"] == node["parentId"]:
                    node["order"] = before.get("order", 0)
                    parent = node["parentId"]
                    orders[parent] = max(orders.get(parent, 0), node["order"] + 1)
        for node in nodes:
            if "order" in node:
                continue
            parent = node["parentId"]
            node["order"] = orders.get(parent, 0)
            orders[parent] = node["order"] + 1
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise PlanError("AI returned a map that could not be checked against the uploaded material", str(exc)) from None

    old = {node["id"]: node for node in session["nodes"]}
    new = {node["id"]: node for node in nodes}
    events = []
    if initial:
        events.append({"type": "map.reset", "nodes": nodes})
    else:
        removed = [node_id for node_id in old if node_id not in new]
        if any(old[n]["status"] == "corrected" and new[n]["status"] != "corrected" for n in old.keys() & new.keys()):
            events.append({"type": "map.reset", "nodes": nodes})
        else:
            events.extend({"type": "map.remove", "nodeId": node_id} for node_id in removed)
            # Parents must arrive before children so the layout can place them.
            additions = [node for node in nodes if node["id"] not in old]
            additions.sort(key=lambda node: len(ancestors(node["id"], {n["id"]: n["parentId"] for n in nodes})))
            events.extend({"type": "map.add", "node": node} for node in additions)
            for node in nodes:
                before = old.get(node["id"])
                if before and before != node:
                    patch = {key: value for key, value in node.items() if before.get(key) != value}
                    events.append({"type": "map.update", "nodeId": node["id"], "patch": patch})
    changed = next((node["id"] for node in nodes if node["status"] == "corrected" and old.get(node["id"]) != node), None)
    if not changed:
        changed = next((node["id"] for node in reversed(nodes) if node["id"] not in old), None)
    if changed and not initial:
        events.append({"type": "map.focus", "nodeId": changed})
    if not initial and proposal.get("expandedNodeId") in new:
        events.append({"type": "map.expanded", "nodeId": proposal["expandedNodeId"]})
    session["nodes"] = nodes
    session["details"] = details
    if initial:
        session["session"]["title"] = title.strip()
        session["session"]["topic"] = topic.strip()
    return answer.strip(), events


def ancestors(node_id, parents):
    result = []
    while parents[node_id] is not None:
        node_id = parents[node_id]
        result.append(node_id)
    return result


def manual_edit(session, event):
    nodes = session["nodes"]
    by_id = {node["id"]: node for node in nodes}
    op = event.get("op")
    node_id = event.get("nodeId")
    if op not in ("rename", "remove", "add", "move", "update", "acknowledge", "keep"):
        raise PlanError("Unknown map edit")
    if op == "add":
        parent = event.get("parentId")
        label = event.get("label")
        if parent not in by_id or not isinstance(label, str) or not 1 <= len(label.split()) <= 5 or len(label) > 60:
            raise PlanError("Choose a parent and a short label")
        node_id = node_id if isinstance(node_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", node_id) else uuid.uuid4().hex[:12]
        if node_id in by_id or len(nodes) >= MAX_NODES:
            raise PlanError("Cannot add this node")
        node = {"id": node_id, "parentId": parent, "label": label.strip(), "status": "normal", "userEdited": True,
                "order": sum(n["parentId"] == parent for n in nodes)}
        nodes.append(node)
        session["details"][node_id] = {"summary": label.strip(), "sourceId": None,
                                        "source": None, "userEdited": True}
        return {"type": "map.add", "node": node}
    if node_id not in by_id or (node_id == "root" and op in ("remove", "move")):
        raise PlanError("This node cannot be edited")
    if op == "acknowledge":
        if by_id[node_id]["status"] == "new":
            by_id[node_id]["status"] = "normal"
        return {"type": "map.update", "nodeId": node_id, "patch": {"status": by_id[node_id]["status"]}}
    if op == "keep":
        by_id[node_id]["pendingRemoval"] = None
        session["messages"].append(message("user", f"Keep {by_id[node_id]['label']} on my map."))
        return {"type": "map.update", "nodeId": node_id, "patch": {"pendingRemoval": None}}
    if op == "move":
        x, y = event.get("x"), event.get("y")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100_000 for value in (x, y)):
            raise PlanError("Choose a valid map position")
        by_id[node_id]["position"] = {"x": round(x), "y": round(y)}
        return {"type": "map.update", "nodeId": node_id, "patch": {"position": by_id[node_id]["position"]}}
    if op in ("rename", "update"):
        label, summary = event.get("label"), event.get("summary")
        if not isinstance(label, str) or not 1 <= len(label.split()) <= 5 or len(label) > 60:
            raise PlanError("Use a label of one to five words")
        if op == "update" and (not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 600):
            raise PlanError("Use a short description of up to 600 characters")
        by_id[node_id]["label"] = label.strip()
        if op == "update":
            session["details"][node_id]["summary"] = summary.strip()
        session["details"][node_id]["userEdited"] = True
        by_id[node_id]["userEdited"] = True
        by_id[node_id].update(status="normal", pendingRemoval=None)
        by_id[node_id].pop("correction", None)
        return {"type": "map.update", "nodeId": node_id, "patch": {"label": label.strip(), "userEdited": True, "status": "normal", "correction": None, "pendingRemoval": None}}
    doomed = {node_id}
    while True:
        children = {node["id"] for node in nodes if node["parentId"] in doomed}
        if children <= doomed:
            break
        doomed |= children
    session["nodes"] = [node for node in nodes if node["id"] not in doomed]
    for dead in doomed:
        session["details"].pop(dead, None)
    return {"type": "map.remove", "nodeId": node_id}


def message(role, text):
    return {"id": uuid.uuid4().hex, "role": role, "text": text,
            "at": datetime.now(timezone.utc).isoformat()}
