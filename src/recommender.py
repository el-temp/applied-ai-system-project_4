import csv
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

import anthropic

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    print(f"Loaded songs: {len(songs)}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Scores a song against user preferences, returning (score, reasons)."""
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs["favorite_genre"]:
        score += 2
        reasons.append("genre match (+2.0)")

    if song["mood"] == user_prefs["favorite_mood"]:
        score += 2
        reasons.append("mood match (+2.0)")

    energy_score = 1 - abs(song["energy"] - user_prefs["target_energy"])
    score += energy_score
    reasons.append(f"energy closeness ({energy_score:+.1f})")

    if user_prefs["likes_acoustic"]:
        acoustic_score = song["acousticness"]
        reasons.append(f"acoustic match ({acoustic_score:+.1f})")
    else:
        acoustic_score = 1 - song["acousticness"]
        reasons.append(f"non-acoustic match ({acoustic_score:+.1f})")
    score += acoustic_score

    return (score, reasons)

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Scores all songs and returns the top k, sorted highest score first."""
    scored = [(song, *score_song(user_prefs, song)) for song in songs]
    scored.sort(key=lambda entry: entry[1], reverse=True)
    return scored[:k]


def _energy_descriptor(target_energy: float) -> str:
    """Converts a 0-1 energy value into a search-friendly phrase."""
    if target_energy >= 0.7:
        return "high-energy, upbeat"
    if target_energy >= 0.4:
        return "moderate-energy"
    return "low-energy, mellow"


def _build_search_query(user_prefs: Dict) -> str:
    """
    Turns the raw user profile fields (numeric energy, boolean acoustic flag)
    into a natural-language phrase that reads like something a person would
    type into a search engine, so web search actually returns song results.
    """
    energy_phrase = _energy_descriptor(user_prefs["target_energy"])
    acoustic_phrase = "acoustic" if user_prefs["likes_acoustic"] else "non-acoustic/produced"
    return (
        f"{energy_phrase} {user_prefs['favorite_genre']} songs with a "
        f"{user_prefs['favorite_mood']} mood, {acoustic_phrase} sound"
    )


MAX_DISCOVERED_SONGS = 2


def discover_songs_with_rag(user_prefs: Dict, catalog_songs: List[Dict], k: int = MAX_DISCOVERED_SONGS) -> List[Dict]:
    """
    Uses Claude with web search to look up real songs matching the user's
    preferences that are not present in the local catalog. Returns a list of
    dicts with "title", "artist", and "reason", or an empty list on failure
    (e.g. missing API credentials or an unparsable response).

    Always returns at most MAX_DISCOVERED_SONGS (2) songs, regardless of `k`.
    """
    k = max(1, min(k, MAX_DISCOVERED_SONGS))
    client = anthropic.Anthropic()

    known_tracks = "\n".join(f"- {s['title']} by {s['artist']}" for s in catalog_songs)
    search_query = _build_search_query(user_prefs)

    prompt = (
        "You are helping a music recommendation system find fresh suggestions.\n"
        f"Search the web using a query like: \"{search_query}\" (adjust wording as "
        "needed to get good results — for example try genre + mood + \"songs\" or "
        "\"playlist\", rather than the raw phrase verbatim).\n\n"
        f"Find ONLY {k} real, currently existing song(s) that fit this description "
        f"— no more than {k}, even if you find more good candidates. "
        f"Do NOT suggest any song already in this catalog:\n"
        f"{known_tracks}\n\n"
        "Respond with ONLY a JSON array and no other text, containing at most "
        f"{k} item(s). Each item must have the keys \"title\", \"artist\", and "
        '"reason" (a short one-sentence reason it fits the user\'s preferences). '
        "If you cannot find any good matches, return an empty array rather than "
        "inventing songs that don't exist."
    )

    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=2048,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
    except (anthropic.APIError, TypeError) as e:
        print(f"[discover_songs_with_rag] API call failed: {e}")
        return []

    text = "".join(block.text for block in response.content if block.type == "text")
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        print(f"[discover_songs_with_rag] No JSON array found in response: {text!r}")
        return []

    try:
        discovered = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        print(f"[discover_songs_with_rag] Failed to parse JSON: {e}\nRaw text: {text!r}")
        return []

    if not isinstance(discovered, list):
        return []
    return discovered[:MAX_DISCOVERED_SONGS]
