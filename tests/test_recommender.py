import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src.core.models import Song, UserProfile, ScoredSong
from src.core.recommender import score_catalog


def _song(id="s1", title="Test Song", artist="Artist", genre="pop", mood="chill",
          energy=0.5, acousticness=0.5, valence=0.5, danceability=0.5, tempo_bpm=100.0):
    return Song(id=id, title=title, artist=artist, genre=genre, mood=mood,
                energy=energy, acousticness=acousticness, valence=valence,
                danceability=danceability, tempo_bpm=tempo_bpm)


def _profile(genre="pop", mood="chill", energy=0.5, acousticness=0.5,
             valence=0.5, danceability=0.5, tempo_bpm=100.0):
    return UserProfile(favorite_genre=genre, favorite_mood=mood,
                       target_energy=energy, target_acousticness=acousticness,
                       target_valence=valence, target_danceability=danceability,
                       target_tempo_bpm=tempo_bpm)


def test_score_exact_match():
    """Perfect genre + mood + numeric alignment should hit near-maximum score."""
    profile = _profile(genre="pop", mood="chill", energy=0.5, acousticness=0.5,
                       valence=0.5, danceability=0.5, tempo_bpm=100.0)
    song = _song(genre="pop", mood="chill", energy=0.5, acousticness=0.5,
                 valence=0.5, danceability=0.5, tempo_bpm=100.0)
    results = score_catalog(profile, [song], top_k=1)
    assert len(results) == 1
    assert results[0].total_score >= 8.0


def test_genre_bonus():
    """Genre match is worth exactly 2.0 points over an otherwise identical song."""
    profile = _profile(genre="pop", mood="chill")
    song_match    = _song(id="a", genre="pop",  mood="chill", artist="Artist A")
    song_no_match = _song(id="b", genre="jazz", mood="chill", artist="Artist B")

    results = score_catalog(profile, [song_match, song_no_match], top_k=2)
    by_id = {r.song.id: r.total_score for r in results}
    assert by_id["a"] - by_id["b"] == 2.0


def test_mood_soft_match():
    """A related-mood song (relaxed under chill) scores 0.75, not the 1.5 exact bonus."""
    profile = _profile(mood="chill")
    song = _song(mood="relaxed")
    results = score_catalog(profile, [song], top_k=1)
    breakdown = results[0].score_breakdown
    assert "mood_related" in breakdown
    assert breakdown["mood_related"] == 0.75
    assert "mood_exact" not in breakdown


def test_no_match_no_crash():
    """An unknown genre like 'reggae' should produce results without raising."""
    profile = _profile(genre="reggae")
    songs = [
        _song(id=str(i), genre=g, artist=f"Artist {i}")
        for i, g in enumerate(
            ["pop", "rock", "jazz", "lofi", "edm",
             "classical", "hip-hop", "folk", "blues", "ambient"]
        )
    ]
    results = score_catalog(profile, songs)
    assert len(results) > 0


def test_top_k():
    """score_catalog respects top_k and returns exactly that many results."""
    profile = _profile()
    songs = [_song(id=str(i), artist=f"Artist {i}") for i in range(12)]
    results = score_catalog(profile, songs, top_k=3)
    assert len(results) == 3
