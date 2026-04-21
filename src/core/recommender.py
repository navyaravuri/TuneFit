from typing import Dict, List, Set, Tuple

from .models import Song, ScoredSong, UserProfile

# Each mood key maps to the full related-mood set (including itself).
MOOD_GROUPS: Dict[str, Set[str]] = {
    "chill":      {"chill", "relaxed", "focused"},
    "relaxed":    {"chill", "relaxed", "focused"},
    "focused":    {"chill", "relaxed", "focused"},
    "happy":      {"happy", "euphoric", "energetic"},
    "euphoric":   {"happy", "euphoric", "energetic"},
    "energetic":  {"happy", "euphoric", "energetic"},
    "sad":        {"sad", "melancholic", "moody"},
    "melancholic":{"sad", "melancholic", "moody"},
    "moody":      {"sad", "melancholic", "moody"},
    "intense":    {"intense", "angry"},
    "angry":      {"intense", "angry"},
}

GENRE_GROUPS: Dict[str, Set[str]] = {
    "rock":      {"rock", "metal"},
    "metal":     {"metal", "rock"},
    "pop":       {"pop", "indie pop"},
    "indie pop": {"indie pop", "pop"},
    "lofi":      {"lofi", "ambient"},
    "ambient":   {"ambient", "lofi"},
    "jazz":      {"jazz", "blues"},
    "blues":     {"blues", "jazz"},
    "folk":      {"folk", "country"},
    "country":   {"country", "folk"},
    "hip-hop":   {"hip-hop", "r&b"},
    "r&b":       {"r&b", "hip-hop"},
    "classical": {"classical"},
    "synthwave": {"synthwave"},
    "edm":       {"edm"},
}


def _score_song(profile: UserProfile, song: Song) -> Tuple[float, Dict[str, float]]:
    breakdown: Dict[str, float] = {}

    if song.genre == profile.favorite_genre:
        breakdown["genre_match"] = 2.0

    related = MOOD_GROUPS.get(profile.favorite_mood, {profile.favorite_mood})
    if song.mood == profile.favorite_mood:
        breakdown["mood_exact"] = 1.5
    elif song.mood in related:
        breakdown["mood_related"] = 0.75

    breakdown["energy"] = (1.0 - abs(profile.target_energy - song.energy)) * 1.5
    breakdown["acousticness"] = (1.0 - abs(profile.target_acousticness - song.acousticness)) * 1.5
    breakdown["valence"] = (1.0 - abs(profile.target_valence - song.valence)) * 1.0
    breakdown["tempo"] = max(0.0, 1.0 - abs(profile.target_tempo_bpm - song.tempo_bpm) / 100) * 1.0
    breakdown["danceability"] = (1.0 - abs(profile.target_danceability - song.danceability)) * 0.5

    return sum(breakdown.values()), breakdown


def score_catalog(
    profile: UserProfile,
    songs: List[Song],
    top_k: int = 5,
) -> List[ScoredSong]:
    """Score all songs and return the top_k with diversity penalties applied."""
    prescored: List[Tuple[float, Dict[str, float], Song]] = sorted(
        [(*_score_song(profile, s), s) for s in songs],
        key=lambda x: x[0],
        reverse=True,
    )

    results: List[ScoredSong] = []
    remaining = list(prescored)

    while len(results) < top_k and remaining:
        selected_artists: Set[str] = {r.song.artist for r in results}
        blocked_genres: Set[str] = set()
        for g in {r.song.genre for r in results}:
            blocked_genres.update(GENRE_GROUPS.get(g, {g}))

        best_adj = float("-inf")
        best_idx = 0
        for i, (score, _, song) in enumerate(remaining):
            adj = score
            if song.artist in selected_artists:
                adj -= 1.50
            if song.genre in blocked_genres:
                adj -= 0.75
            if adj > best_adj:
                best_adj = adj
                best_idx = i

        raw_score, breakdown, song = remaining.pop(best_idx)

        penalties: Dict[str, float] = {}
        if song.artist in selected_artists:
            penalties["artist_repeat"] = -1.50
        if song.genre in blocked_genres:
            penalties["genre_group_repeat"] = -0.75

        results.append(ScoredSong(
            song=song,
            total_score=raw_score + sum(penalties.values()),
            score_breakdown={**breakdown, **penalties},
        ))

    return results
