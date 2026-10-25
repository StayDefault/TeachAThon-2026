"""Lesson plan, learner progress, focus and cross-links stored alongside the map."""

import re

LEVELS = ("introduced", "attempted", "understood", "review", "skipped")
MAX_LESSON = 12
ID = re.compile(r"[A-Za-z0-9_-]{1,32}")


def ensure(session):
    """Fill defaults for sessions saved before lessons existed."""
    session.setdefault("lesson", [])
    session.setdefault("learner", {})
    session.setdefault("focus", None)
    session.setdefault("focusSince", 0)
    session.setdefault("edges", [])
    session.setdefault("summary", "")
    session.setdefault("summaryUpTo", 0)
    return session


def normalize(text):
    return re.sub(r"[^\w\s]", "", re.sub(r"\s+", " ", text)).strip().casefold()


def learner_said(session, quote, recent=8):
    quote = normalize(quote)
    claims = [m["text"] for m in session.get("messages", []) if m.get("role") == "user"][-recent:]
    return bool(quote) and any(quote in normalize(claim) for claim in claims)


def validate_lesson(session, items):
    sources = {c["id"] for c in session["chunks"]}
    if not isinstance(items, list) or len(items) > MAX_LESSON:
        raise ValueError(f"the lesson needs at most {MAX_LESSON} concepts")
    ids, lesson = set(), []
    for order, item in enumerate(items):
        concept_id, title, summary = item["id"], item["title"], item["summary"]
        parent, source_id = item["parentId"] or None, item["sourceId"]
        if not isinstance(concept_id, str) or not ID.fullmatch(concept_id) or concept_id in ids or concept_id == "root":
            raise ValueError("a lesson concept ID is invalid or duplicated")
        if not isinstance(title, str) or not 1 <= len(title.split()) <= 5 or len(title) > 60:
            raise ValueError("a lesson title must contain one to five words")
        if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 400:
            raise ValueError("a lesson summary must contain one to 400 characters")
        if source_id not in sources:
            raise ValueError("a lesson concept cites an unknown sourceId")
        if parent is not None and parent not in ids:
            raise ValueError("a lesson parent must be an earlier concept")
        ids.add(concept_id)
        lesson.append({"id": concept_id, "title": title.strip(), "summary": summary.strip(),
                       "sourceId": source_id, "parentId": parent, "order": order})
    return lesson


def progress(session):
    learner = session["learner"]
    on_map = {n.get("planId") for n in session["nodes"]}
    items = []
    for item in session["lesson"]:
        state = learner.get(item["id"], {}).get("state") or ("introduced" if item["id"] in on_map else "unseen")
        items.append({"id": item["id"], "title": item["title"], "state": state})
    return {"type": "lesson.update", "items": items, "focusId": session["focus"]}


def mastery(state):
    return {"understood": "understood", "review": "review", "skipped": "review"}.get(state, "introduced")


def commit(session, staged):
    """Apply staged lesson/learner/focus/edge changes after the map itself has been validated."""
    before = (session["lesson"], session["learner"], session["focus"], session["edges"])
    session["lesson"], session["learner"] = staged["lesson"], staged["learner"]
    session["focus"] = staged["focus"]
    session["focusSince"] = staged["focusSince"]
    ids = {n["id"] for n in session["nodes"]}
    session["edges"] = [e for e in staged["edges"] if e["from"] in ids and e["to"] in ids]
    events = []
    if (session["lesson"], session["learner"], session["focus"]) != before[:3]:
        events.append(progress(session))
    if session["edges"] != before[3]:
        events.append({"type": "map.edges", "edges": session["edges"]})
    return events


def prune_edges(session):
    ids = {n["id"] for n in session["nodes"]}
    session["edges"] = [e for e in session["edges"] if e["from"] in ids and e["to"] in ids]


def action_text(session, event):
    """Phrase a button press as the learner's request; the tutor decides what to do with it."""
    target = event.get("nodeId") or event.get("planId")
    label = next((n["label"] for n in session["nodes"] if n["id"] == target), None) or \
        next((i["title"] for i in session["lesson"] if i["id"] == target), None)
    if not label or event.get("action") not in ("learn", "expand"):
        return None
    return f"Teach me about {label}." if event["action"] == "learn" else f"Expand {label} into its subtopics."
