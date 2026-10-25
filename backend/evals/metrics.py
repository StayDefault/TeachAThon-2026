"""Score simulated study sessions. Pure functions over recorded turns, so they can be tested offline."""

import difflib
import re
import statistics

PERSONAS = {
    "steady": "You mostly follow. After an explanation you explain the idea back in your own casual words, roughly right. Sometimes you ask a short question.",
    "confused": "You hold one or two plausible misconceptions about the topic and state them confidently at first. When corrected clearly, you update your view.",
    "stuck": "You find this hard and are tired. You often say you don't know, ask to skip, or say 'next'. You rarely explain anything at length.",
    "speech": "Your words reach the tutor through speech-to-text: short, with fillers like 'um', restarts, and sound-alike errors for technical terms (for example 'face' for 'phase'). Otherwise you are a typical learner.",
    "editor": "You like organising the map. Besides learning, you ask the tutor to rename, move, link or remove nodes by name.",
}


def sound_alike(label):
    """A plausible speech-recognition mistake for a node label."""
    swaps = (("ph", "f"), ("ce", "se"), ("c", "k"), ("y", "i"), ("ight", "ite"), ("tion", "shun"), ("s", "z"))
    lowered = label.casefold()
    for old, new in swaps:
        if old in lowered:
            return lowered.replace(old, new, 1)
    return lowered + "s"


def ends_with_question(text):
    return text.rstrip().endswith("?")


def questions_in_a_row(turns):
    longest = streak = 0
    for turn in turns:
        streak = streak + 1 if ends_with_question(turn.get("assistant", "")) else 0
        longest = max(longest, streak)
    return longest


def repeated_questions(turns, threshold=0.85):
    asked, repeats = [], 0
    for turn in turns:
        for question in re.findall(r"[^.!?]*\?", turn.get("assistant", "")):
            question = question.strip().casefold()
            if len(question) < 12:
                continue
            if any(difflib.SequenceMatcher(None, question, earlier).ratio() >= threshold for earlier in asked):
                repeats += 1
            asked.append(question)
    return repeats


def stuck_streak(turns):
    """Longest run of turns in which neither the lesson progress nor the map changed."""
    longest = streak = 0
    previous = None
    for turn in turns:
        snapshot = (tuple(sorted(turn.get("lesson", {}).items())), turn.get("map_changes", 0) > 0)
        changed = snapshot[1] or snapshot[0] != previous
        streak = 0 if changed else streak + 1
        longest = max(longest, streak)
        previous = snapshot[0]
    return longest


def percentile(values, share):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(share * (len(ordered) - 1)))]


def score(run):
    turns = run["turns"]
    final = turns[-1]["lesson"] if turns else {}
    understood = sum(state == "understood" for state in final.values())
    latencies = [t["latency_ms"] for t in turns if t.get("latency_ms") is not None]
    probes = [t["probe"] for t in turns if t.get("probe")]
    judged = [t["judgement"] for t in turns if t.get("judgement")]
    return {
        "scenario": run["scenario"], "persona": run["persona"], "turns": len(turns),
        "errors": sum(bool(t.get("error")) for t in turns),
        "lesson_size": len(final), "understood": understood,
        "turns_per_understood": round(len(turns) / understood, 1) if understood else None,
        "max_questions_in_a_row": questions_in_a_row(turns),
        "repeated_questions": repeated_questions(turns),
        "longest_stuck": stuck_streak(turns),
        "edit_accuracy": round(sum(p["passed"] for p in probes) / len(probes), 2) if probes else None,
        "grounded": round(sum(j == "supported" for j in judged) / len(judged), 2) if judged else None,
        "latency_p50_ms": percentile(latencies, 0.5), "latency_p95_ms": percentile(latencies, 0.95),
        "ai_calls_per_turn": round(statistics.mean(t.get("ai_calls", 0) for t in turns), 1) if turns else None,
    }


COLUMNS = ("scenario", "persona", "turns", "errors", "understood", "lesson_size", "turns_per_understood", "max_questions_in_a_row",
           "repeated_questions", "longest_stuck", "edit_accuracy", "grounded", "latency_p50_ms", "latency_p95_ms", "ai_calls_per_turn")


def report(scores):
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for row in scores:
        lines.append("| " + " | ".join("" if row[c] is None else str(row[c]) for c in COLUMNS) + " |")
    return "\n".join(lines)
