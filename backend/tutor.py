"""Validate grounded AI plans and turn them into frontend map events."""

import re
import uuid
from datetime import datetime, timezone


class PlanError(ValueError):
    pass


def apply_plan(session, proposal, initial=False):
    try:
        title, topic, answer, raw_nodes = (proposal[k] for k in ("title", "topic", "answer", "nodes"))
        if not all(isinstance(x, str) for x in (title, topic, answer)) or not isinstance(raw_nodes, list):
            raise ValueError
        if not 1 <= len(title.strip()) <= 80 or not 1 <= len(topic.strip()) <= 80 or not 1 <= len(answer.strip()) <= 1500:
            raise ValueError
        if not 1 <= len(raw_nodes) <= 20 or (initial and len(raw_nodes) != 1):
            raise ValueError
        if not initial and (title != session["session"]["title"] or topic != session["session"]["topic"]):
            raise ValueError
        sources = {c["id"]: c for c in session["chunks"]}
        ids = set()
        nodes, details = [], {}
        for item in raw_nodes:
            node_id, parent, label = item["id"], item["parentId"], item["label"]
            status, source_id, summary = item["status"], item["sourceId"], item["summary"]
            if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", node_id) or node_id in ids:
                raise ValueError
            if parent is not None and (not isinstance(parent, str) or parent == node_id):
                raise ValueError
            if not isinstance(label, str) or not 1 <= len(label.split()) <= 5 or len(label) > 60:
                raise ValueError
            if status not in ("normal", "new", "corrected") or source_id not in sources:
                raise ValueError
            if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 600:
                raise ValueError
            node = {"id": node_id, "parentId": parent, "label": label.strip(), "status": status}
            if node_id == "root":
                if parent is not None:
                    raise ValueError
                node["status"] = "normal"
                if item["subtitle"].strip():
                    node["subtitle"] = item["subtitle"].strip()[:100]
            elif parent is None:
                raise ValueError
            if status == "corrected":
                said, actually = item["said"], item["actually"]
                if not isinstance(said, str) or not isinstance(actually, str) or not said.strip() or not actually.strip():
                    raise ValueError
                node["correction"] = {"said": said[:200], "actually": actually[:300]}
            source = sources[source_id]
            details[node_id] = {"summary": summary.strip(), "sourceId": source_id,
                                "source": {"materialId": source["materialId"], "fileName": source["fileName"],
                                           "page": source["page"], "quote": source["text"]}}
            nodes.append(node)
            ids.add(node_id)
        if "root" not in ids or (initial and nodes[0]["id"] != "root"):
            raise ValueError
        parents = {node["id"]: node["parentId"] for node in nodes}
        for node_id in ids:
            seen = set()
            cursor = node_id
            while cursor is not None:
                if cursor not in parents or cursor in seen:
                    raise ValueError
                seen.add(cursor)
                cursor = parents[cursor]
        orders = {}
        for node in nodes:
            parent = node["parentId"]
            node["order"] = orders.get(parent, 0)
            orders[parent] = node["order"] + 1
    except (KeyError, TypeError, ValueError, AttributeError):
        raise PlanError("AI returned a map that could not be checked against the uploaded material") from None

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
    if op not in ("rename", "remove", "add"):
        raise PlanError("Unknown map edit")
    if op == "add":
        parent = event.get("parentId")
        label = event.get("label")
        if parent not in by_id or not isinstance(label, str) or not 1 <= len(label.split()) <= 5:
            raise PlanError("Choose a parent and a short label")
        source = next((c for c in session["chunks"] if all(word.lower().strip(".,!?;:") in c["text"].lower()
                      for word in label.split())), None)
        if source is None:
            raise PlanError("This label could not be found in the uploaded material")
        node_id = node_id if isinstance(node_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", node_id) else uuid.uuid4().hex[:12]
        if node_id in by_id or len(nodes) >= 20:
            raise PlanError("Cannot add this node")
        node = {"id": node_id, "parentId": parent, "label": label.strip(), "status": "new",
                "order": sum(n["parentId"] == parent for n in nodes)}
        nodes.append(node)
        session["details"][node_id] = {"summary": label.strip(), "sourceId": source["id"],
                                        "source": {"materialId": source["materialId"], "fileName": source["fileName"],
                                                   "page": source["page"], "quote": source["text"]}}
        return {"type": "map.add", "node": node}
    if node_id not in by_id or node_id == "root":
        raise PlanError("This node cannot be edited")
    if op == "rename":
        label = event.get("label")
        if not isinstance(label, str) or not 1 <= len(label.split()) <= 5:
            raise PlanError("Use a label of one to five words")
        by_id[node_id]["label"] = label.strip()
        return {"type": "map.update", "nodeId": node_id, "patch": {"label": label.strip()}}
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


def message(role, text, node_id=None):
    return {"id": uuid.uuid4().hex, "role": role, "text": text,
            "at": datetime.now(timezone.utc).isoformat(), "nodeId": node_id}
