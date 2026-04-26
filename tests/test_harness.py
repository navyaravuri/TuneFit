import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time

print("NOTE: This harness makes real LLM API calls. Requires .env with GROQ_API_KEY or Ollama running.")

from src.agent.orchestrator import AgentOrchestrator, AgentResult

# ── Test cases ────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "description":    "Chill Study Music",
        "input_message":  "play me something chill and relaxing for studying",
        "expected_genres": ["lofi", "ambient"],
        "expected_moods":  ["chill", "relaxed"],
        "min_confidence": 0.5,
        "adversarial":    False,
        "adversarial_check": None,
    },
    {
        "description":    "High Energy Workout",
        "input_message":  "I want high energy music to work out to, something intense",
        "expected_genres": ["rock", "edm", "metal"],
        "expected_moods":  ["intense", "energetic"],
        "min_confidence": 0.5,
        "adversarial":    False,
        "adversarial_check": None,
    },
    {
        "description":    "Happy Pop Vibes",
        "input_message":  "something happy and upbeat, pop vibes",
        "expected_genres": ["pop", "indie pop"],
        "expected_moods":  ["happy", "euphoric"],
        "min_confidence": 0.5,
        "adversarial":    False,
        "adversarial_check": None,
    },
    {
        "description":    "Late Night Jazz",
        "input_message":  "moody jazz, late night kind of feel",
        "expected_genres": ["jazz"],
        "expected_moods":  ["moody"],
        "min_confidence": 0.4,
        "adversarial":    False,
        "adversarial_check": None,
    },
    {
        "description":    "ADVERSARIAL — Unknown Genre",
        "input_message":  "I want reggae music",
        "expected_genres": [],
        "expected_moods":  [],
        "min_confidence": 0.0,
        "adversarial":    True,
        "adversarial_check": "warning",
    },
    {
        "description":    "ADVERSARIAL — Conflicting Preferences",
        "input_message":  "give me something super high energy but also very acoustic and peaceful",
        "expected_genres": [],
        "expected_moods":  [],
        "min_confidence": 0.0,
        "adversarial":    True,
        "adversarial_check": "low_confidence",
    },
]

# ── Evaluation logic ──────────────────────────────────────────────────────────

def evaluate(tc: dict, result: AgentResult) -> tuple[bool, str]:
    if result.error:
        return False, f"error: {result.error}"

    if tc["adversarial"]:
        if tc["adversarial_check"] == "warning":
            passed = result.confidence.get("warning") is not None
            return passed, "warning returned ✓" if passed else "no warning returned ✗"
        if tc["adversarial_check"] == "low_confidence":
            passed = result.confidence.get("quality") == "low"
            label = "low confidence returned ✓" if passed else f"quality={result.confidence.get('quality')} ✗"
            return passed, label

    top3_genres = {r.song.genre for r in result.recommendations[:3]}
    top3_moods  = {r.song.mood  for r in result.recommendations[:3]}
    genre_hit   = bool(top3_genres & set(tc["expected_genres"]))
    mood_hit    = bool(top3_moods  & set(tc["expected_moods"]))
    conf        = result.confidence.get("confidence", 0.0)
    top_title   = result.recommendations[0].song.title if result.recommendations else "—"

    passed = (genre_hit or mood_hit) and conf >= tc["min_confidence"]
    return passed, f"confidence: {conf:.2f}, top: {top_title}"

# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> None:
    agent = AgentOrchestrator()
    log: list[tuple] = []

    for i, tc in enumerate(TEST_CASES, start=1):
        result = agent.run(tc["input_message"])
        passed, detail = evaluate(tc, result)
        conf = result.confidence.get("confidence", 0.0)
        log.append((i, tc["description"], passed, detail, conf, tc["adversarial"]))
        if i < len(TEST_CASES):
            time.sleep(2)

    # ── Report ────────────────────────────────────────────────────────────────
    SEP = "=" * 48
    print()
    print(SEP)
    print("TUNEFIT 2.0 — EVALUATION REPORT")
    print(SEP)

    passed_count = 0
    conf_sum = 0.0
    conf_n = 0

    for i, desc, passed, detail, conf, adversarial in log:
        label = f"Test {i}: {desc} "
        dots  = "." * max(3, 41 - len(label))
        status = "PASS" if passed else "FAIL"
        print(f"  {label}{dots} {status}  ({detail})")
        if passed:
            passed_count += 1
        if not adversarial:
            conf_sum += conf
            conf_n += 1

    avg_conf = conf_sum / conf_n if conf_n else 0.0
    print("-" * 48)
    print(f"Results: {passed_count}/{len(TEST_CASES)} passed")
    print(f"Average confidence (non-adversarial tests): {avg_conf:.2f}")
    print(SEP)


if __name__ == "__main__":
    main()
