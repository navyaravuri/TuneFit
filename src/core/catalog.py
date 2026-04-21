from pathlib import Path
from typing import List

import pandas as pd

from .models import Song


def load_catalog(csv_path: str = "data/songs.csv") -> List[Song]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Song catalog not found: {csv_path}")

    df = pd.read_csv(path)
    return [
        Song(
            id=str(row["id"]),
            title=str(row["title"]),
            artist=str(row["artist"]),
            genre=str(row["genre"]),
            mood=str(row["mood"]),
            energy=float(row["energy"]),
            acousticness=float(row["acousticness"]),
            valence=float(row["valence"]),
            danceability=float(row["danceability"]),
            tempo_bpm=float(row["tempo_bpm"]),
        )
        for _, row in df.iterrows()
    ]
