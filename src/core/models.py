from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Song:
    id: str
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    acousticness: float
    valence: float
    danceability: float
    tempo_bpm: float


@dataclass
class UserProfile:
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    target_acousticness: float
    target_valence: float
    target_danceability: float
    target_tempo_bpm: float


@dataclass
class ScoredSong:
    song: Song
    total_score: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)
