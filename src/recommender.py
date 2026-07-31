import csv
import json
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

REQUIRED_USER_PREF_KEYS = ("favorite_genre", "favorite_mood", "target_energy", "likes_acoustic")
REQUIRED_SONG_KEYS = ("genre", "mood", "energy", "acousticness")


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
        """Returns the top-k songs for `user`, highest score first."""
        if k <= 0 or not self.songs:
            return []

        user_prefs = asdict(user)
        scored = []
        for song in self.songs:
            try:
                score, _reasons, _confidence = score_song(user_prefs, asdict(song))
            except (KeyError, ValueError) as e:
                logger.warning("Skipping song id=%s during recommend: %s", getattr(song, "id", "?"), e)
                continue
            scored.append((song, score))

        scored.sort(key=lambda entry: entry[1], reverse=True)
        return [song for song, _score in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a human-readable explanation of why `song` matches `user`, with a confidence score."""
        try:
            score, reasons, confidence = score_song(asdict(user), asdict(song))
        except (KeyError, ValueError) as e:
            logger.error("Failed to explain recommendation for song id=%s: %s", getattr(song, "id", "?"), e)
            return f"Unable to generate explanation: {e}"

        reason_text = "; ".join(reasons)
        return (
            f"'{song.title}' by {song.artist} scored {score:.2f} "
            f"(confidence: {confidence:.0%}) — {reason_text}"
        )

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py

    Raises FileNotFoundError if csv_path does not exist. Rows that are
    missing required fields or contain non-numeric values are skipped
    (and logged) rather than aborting the whole load.
    """
    songs = []
    try:
        f = open(csv_path, newline="", encoding="utf-8")
    except FileNotFoundError:
        logger.error("Songs CSV not found at %r", csv_path)
        raise

    with f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):  # header is line 1
            try:
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
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed row %d in %s: %s", line_num, csv_path, e)
                continue

    logger.info("Loaded songs: %d", len(songs))
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str], float]:
    """
    Scores a song against user preferences, returning (score, reasons, confidence).

    `confidence` is a 0-1 estimate of how strong the match is, derived from
    the score relative to the maximum possible score (6.0).

    Raises ValueError if `user_prefs` or `song` is missing required keys.
    """
    missing_user_keys = [k for k in REQUIRED_USER_PREF_KEYS if k not in user_prefs]
    missing_song_keys = [k for k in REQUIRED_SONG_KEYS if k not in song]
    if missing_user_keys or missing_song_keys:
        msg = (
            f"score_song missing required keys — user_prefs: {missing_user_keys}, "
            f"song: {missing_song_keys}"
        )
        logger.error(msg)
        raise ValueError(msg)

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

    max_possible_score = 6.0
    confidence = max(0.0, min(1.0, score / max_possible_score))

    return (score, reasons, confidence)

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, List[str], float]]:
    """
    Scores all songs and returns the top k, sorted highest score first, as
    (song, score, reasons, confidence) tuples.

    Returns an empty list if `songs` is empty or `k` <= 0. Songs missing
    required fields are skipped and logged rather than raising.
    """
    if k <= 0 or not songs:
        return []

    scored = []
    for song in songs:
        try:
            score, reasons, confidence = score_song(user_prefs, song)
        except ValueError as e:
            logger.warning("Skipping song %r during recommend_songs: %s", song.get("title", "?"), e)
            continue
        scored.append((song, score, reasons, confidence))

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


def _discovered_item_confidence(item: Dict) -> float:
    """
    Heuristic confidence for a single RAG-discovered item, based on how
    complete its fields are. These come from ungrounded LLM knowledge (no
    web search verification), so confidence is capped below 1.0.
    """
    has_title = bool(str(item.get("title") or "").strip())
    has_artist = bool(str(item.get("artist") or "").strip())
    has_reason = bool(str(item.get("reason") or "").strip())

    if not (has_title and has_artist):
        return 0.0
    return 0.8 if has_reason else 0.5


def discover_songs_with_rag(user_prefs: Dict, catalog_songs: List[Dict], k: int = MAX_DISCOVERED_SONGS) -> List[Dict]:
    """
    Uses the free-tier Gemini API (from its own trained knowledge, no web
    search grounding) to look up real songs matching the user's preferences
    that are not present in the local catalog. Returns a list of dicts with
    "title", "artist", "reason", and "confidence" (0-1, heuristic — see
    `_discovered_item_confidence`), or an empty list on failure (e.g.
    missing API credentials or an unparsable response).

    Always returns at most MAX_DISCOVERED_SONGS (2) songs, regardless of `k`.
    Items missing a title or artist are dropped.

    Requires a GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable.
    """
    k = max(1, min(k, MAX_DISCOVERED_SONGS))

    try:
        client = genai.Client()
    except Exception as e:
        logger.error("[discover_songs_with_rag] Failed to create Gemini client: %s", e)
        return []

    known_tracks = ", ".join(f"{s['title']}/{s['artist']}" for s in catalog_songs)
    search_query = _build_search_query(user_prefs)

    prompt = (
        f'Search: "{search_query}". Find {k} real song(s) matching this, not in: '
        f"{known_tracks}. "
        f'Reply with ONLY a JSON array of up to {k} items, each {{"title","artist",'
        '"reason"}} (reason: <10 words). No real match -> [].'
    )

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=512),
        )
    except (genai_errors.APIError, TypeError) as e:
        logger.error("[discover_songs_with_rag] API call failed: %s", e)
        return []

    text = response.text or ""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        logger.warning("[discover_songs_with_rag] No JSON array found in response: %r", text)
        return []

    try:
        discovered = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        logger.warning("[discover_songs_with_rag] Failed to parse JSON: %s\nRaw text: %r", e, text)
        return []

    if not isinstance(discovered, list):
        logger.warning("[discover_songs_with_rag] Expected a JSON list, got %s", type(discovered).__name__)
        return []

    results = []
    for item in discovered[:MAX_DISCOVERED_SONGS]:
        if not isinstance(item, dict):
            logger.warning("[discover_songs_with_rag] Skipping non-dict item: %r", item)
            continue
        confidence = _discovered_item_confidence(item)
        if confidence <= 0.0:
            logger.warning("[discover_songs_with_rag] Skipping item missing title/artist: %r", item)
            continue
        results.append({**item, "confidence": confidence})

    return results
