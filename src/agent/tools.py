import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.catalog import load_catalog
from ..core.models import ScoredSong, UserProfile
from ..core.recommender import score_catalog
from .llm_client import LLMClient

logger = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "favorite_genre": "pop",
    "favorite_mood": "chill",
    "target_energy": 0.5,
    "target_acousticness": 0.5,
    "target_valence": 0.5,
    "target_danceability": 0.5,
    "target_tempo_bpm": 100,
}

_EXTRACTION_PROMPT = """\
Extract music preferences from the user message and return ONLY a JSON object.

User message: {message}

Return a JSON object with exactly these keys (use the defaults for any not mentioned):
{{
  "favorite_genre":     string  (e.g. "pop", "rock", "lofi", "jazz", "classical") [default: "pop"],
  "favorite_mood":      string  (e.g. "chill", "happy", "sad", "intense", "energetic") [default: "chill"],
  "target_energy":      float 0-1  (0=very calm, 1=very energetic) [default: 0.5],
  "target_acousticness": float 0-1  (0=electronic, 1=fully acoustic) [default: 0.5],
  "target_valence":     float 0-1  (0=negative/sad, 1=positive/happy) [default: 0.5],
  "target_danceability": float 0-1  (0=not danceable, 1=very danceable) [default: 0.5],
  "target_tempo_bpm":   float  (beats per minute, typically 60-180) [default: 100]
}}

Return ONLY the JSON object, no explanation.\
"""

_FORMAT_PROMPT = """\
You are a music recommendation assistant. Write a friendly 3-4 sentence response about these song recommendations.

Top recommendations:
{song_list}

Match confidence: {quality}
{warning_line}

Name the top songs, explain briefly why they matched, and if confidence is low note why the matches \
may not be perfect. Be warm and concise.\
"""


@dataclass
class ReasoningStep:
    tool_name: str
    input_summary: str
    output_summary: str
    timestamp: str  # datetime.now().strftime("%H:%M:%S")


def extract_preferences(user_message: str, llm_client: LLMClient, steps: list) -> Dict[str, Any]:
    """Call the LLM to parse user intent into a structured preferences dict."""
    prompt = _EXTRACTION_PROMPT.format(message=user_message)
    logger.debug("extract_preferences LLM call | prompt_len=%d", len(prompt))

    prefs: Dict[str, Any] = dict(DEFAULTS)
    try:
        raw = llm_client.complete(prompt)
        logger.debug("extract_preferences LLM response: %s", raw)

        parsed: Optional[Dict] = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*?\}", raw, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        if parsed and isinstance(parsed, dict):
            for key, default in DEFAULTS.items():
                prefs[key] = parsed.get(key, default)

    except Exception as exc:
        logger.warning("extract_preferences failed, using defaults: %s", exc)

    steps.append(ReasoningStep(
        tool_name="extract_preferences",
        input_summary=user_message[:80],
        output_summary=(
            f"genre={prefs['favorite_genre']}, mood={prefs['favorite_mood']}, "
            f"energy={prefs['target_energy']:.1f}"
        ),
        timestamp=datetime.now().strftime("%H:%M:%S"),
    ))
    return prefs


def score_and_retrieve(preferences: Dict[str, Any], steps: list) -> List[ScoredSong]:
    """Build a UserProfile, load the catalog, and return the top-5 scored songs."""
    profile = UserProfile(
        favorite_genre=str(preferences["favorite_genre"]),
        favorite_mood=str(preferences["favorite_mood"]),
        target_energy=float(preferences["target_energy"]),
        target_acousticness=float(preferences["target_acousticness"]),
        target_valence=float(preferences["target_valence"]),
        target_danceability=float(preferences["target_danceability"]),
        target_tempo_bpm=float(preferences["target_tempo_bpm"]),
    )

    songs = load_catalog()
    results = score_catalog(profile, songs, top_k=5)

    top = results[0] if results else None
    steps.append(ReasoningStep(
        tool_name="score_and_retrieve",
        input_summary="UserProfile constructed from preferences",
        output_summary=(
            f"Scored {len(songs)} songs. Top: {top.song.title} ({top.total_score:.2f}/9.0)"
            if top else "No results returned."
        ),
        timestamp=datetime.now().strftime("%H:%M:%S"),
    ))
    return results


def evaluate_confidence(results: List[ScoredSong], preferences: Dict[str, Any], steps: list) -> dict:
    """Assess how well the top results matched the user's preferences."""
    top_score = results[0].total_score if results else 0.0
    confidence = top_score / 9.0

    warning: Optional[str] = None

    # Detect contradictory numeric preferences before inspecting results.
    # High energy + high acousticness never co-occur in the catalog, so any
    # request asking for both cannot be satisfied regardless of score.
    energy = float(preferences.get("target_energy", 0.5))
    acousticness = float(preferences.get("target_acousticness", 0.5))
    if energy > 0.65 and acousticness > 0.65:
        warning = "Conflicting preferences detected: high energy and high acousticness rarely appear together. Results may not fully match your request."
        quality = "medium" if confidence > 0.4 else "low"
    else:
        quality = "high" if confidence > 0.7 else ("medium" if confidence > 0.4 else "low")
        if not any("genre_match" in r.score_breakdown for r in results):
            warning = "No songs matched your preferred genre."
        elif not any(
            "mood_exact" in r.score_breakdown or "mood_related" in r.score_breakdown
            for r in results
        ):
            warning = "Weak mood match — your mood preference was not found."
        elif confidence < 0.35:
            warning = "Conflicting preferences may have reduced match quality."

    steps.append(ReasoningStep(
        tool_name="evaluate_confidence",
        input_summary="Top 5 results with scores",
        output_summary=f"Confidence: {quality} ({confidence:.2f}). {warning or 'No warnings.'}",
        timestamp=datetime.now().strftime("%H:%M:%S"),
    ))
    return {
        "confidence": confidence,
        "quality": quality,
        "warning": warning,
        "top_score": top_score,
    }


def format_response(
    results: List[ScoredSong],
    confidence: dict,
    preferences: dict,
    llm_client: LLMClient,
    steps: list,
) -> str:
    """Ask the LLM to write a friendly recommendation summary."""
    song_list = "\n".join(
        f"- {r.song.title} by {r.song.artist} (score: {r.total_score:.2f}/9.0)"
        for r in results
    )
    warning_line = f"Warning: {confidence['warning']}" if confidence.get("warning") else ""
    prompt = _FORMAT_PROMPT.format(
        song_list=song_list,
        quality=confidence["quality"],
        warning_line=warning_line,
    )

    logger.debug("format_response LLM call | prompt_len=%d", len(prompt))
    try:
        response = llm_client.complete(prompt)
        logger.debug("format_response LLM response: %s", response)
    except Exception as exc:
        logger.warning("format_response LLM call failed: %s", exc)
        titles = ", ".join(r.song.title for r in results[:3])
        response = f"Here are your top matches: {titles}. Enjoy your music!"

    steps.append(ReasoningStep(
        tool_name="format_response",
        input_summary=f"{len(results)} results, confidence={confidence['quality']}",
        output_summary=response[:80] + "...",
        timestamp=datetime.now().strftime("%H:%M:%S"),
    ))
    return response
