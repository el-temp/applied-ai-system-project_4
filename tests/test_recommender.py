import json
import logging

import pytest

from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    load_songs,
    score_song,
    recommend_songs,
    discover_songs_with_rag,
    MAX_DISCOVERED_SONGS,
)


def make_songs():
    return [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]


def make_small_recommender() -> Recommender:
    return Recommender(make_songs())


def make_song_dicts():
    return [
        {
            "id": 1, "title": "Test Pop Track", "artist": "Test Artist",
            "genre": "pop", "mood": "happy", "energy": 0.8, "tempo_bpm": 120,
            "valence": 0.9, "danceability": 0.8, "acousticness": 0.2,
        },
        {
            "id": 2, "title": "Chill Lofi Loop", "artist": "Test Artist",
            "genre": "lofi", "mood": "chill", "energy": 0.4, "tempo_bpm": 80,
            "valence": 0.6, "danceability": 0.5, "acousticness": 0.9,
        },
    ]


def make_user_prefs(**overrides):
    prefs = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    }
    prefs.update(overrides)
    return prefs


# --- Recommender (OOP) ---------------------------------------------------


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_recommend_respects_k():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = make_small_recommender()
    assert len(rec.recommend(user, k=1)) == 1


def test_recommend_k_zero_returns_empty():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = make_small_recommender()
    assert rec.recommend(user, k=0) == []


def test_recommend_k_negative_returns_empty():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = make_small_recommender()
    assert rec.recommend(user, k=-3) == []


def test_recommend_empty_catalog_returns_empty():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = Recommender([])
    assert rec.recommend(user, k=5) == []


def test_recommend_k_larger_than_catalog_returns_all():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = make_small_recommender()
    assert len(rec.recommend(user, k=100)) == 2


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_explain_recommendation_includes_confidence():
    user = UserProfile("pop", "happy", 0.8, False)
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(user, rec.songs[0])
    assert "confidence" in explanation.lower()


# --- load_songs ------------------------------------------------------------


def test_load_songs_reads_valid_csv(tmp_path):
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
        "1,Song A,Artist A,pop,happy,0.8,120,0.9,0.8,0.2\n",
        encoding="utf-8",
    )
    songs = load_songs(str(csv_path))
    assert len(songs) == 1
    assert songs[0]["title"] == "Song A"
    assert songs[0]["energy"] == 0.8


def test_load_songs_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_songs("this/path/does/not/exist.csv")


def test_load_songs_skips_malformed_rows(tmp_path, caplog):
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
        "1,Good Song,Artist A,pop,happy,0.8,120,0.9,0.8,0.2\n"
        "2,Bad Song,Artist B,pop,happy,not-a-number,120,0.9,0.8,0.2\n",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        songs = load_songs(str(csv_path))

    assert len(songs) == 1
    assert songs[0]["title"] == "Good Song"
    assert any("malformed row" in record.message for record in caplog.records)


def test_load_songs_empty_file_returns_empty_list(tmp_path):
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n",
        encoding="utf-8",
    )
    assert load_songs(str(csv_path)) == []


# --- score_song --------------------------------------------------------


def test_score_song_perfect_match_scores_high_with_high_confidence():
    user = make_user_prefs(target_energy=0.8, likes_acoustic=False)
    song = make_song_dicts()[0]  # pop, happy, energy 0.8, acousticness 0.2
    score, reasons, confidence = score_song(user, song)

    assert score == pytest.approx(2 + 2 + 1 + 0.8)
    assert "genre match (+2.0)" in reasons
    assert "mood match (+2.0)" in reasons
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.8


def test_score_song_no_match_scores_low_with_low_confidence():
    user = make_user_prefs(favorite_genre="rock", favorite_mood="sad", target_energy=0.1, likes_acoustic=True)
    song = make_song_dicts()[0]  # pop, happy, energy 0.8, acousticness 0.2
    score, reasons, confidence = score_song(user, song)

    assert not any("genre match" in r for r in reasons)
    assert not any("mood match" in r for r in reasons)
    assert confidence < 0.5


def test_score_song_confidence_always_in_unit_range():
    user = make_user_prefs()
    song = make_song_dicts()[0]
    _, _, confidence = score_song(user, song)
    assert 0.0 <= confidence <= 1.0


def test_score_song_missing_user_pref_key_raises_value_error():
    song = make_song_dicts()[0]
    with pytest.raises(ValueError):
        score_song({"favorite_genre": "pop"}, song)


def test_score_song_missing_song_key_raises_value_error():
    user = make_user_prefs()
    with pytest.raises(ValueError):
        score_song(user, {"genre": "pop"})


def test_score_song_energy_extremes_do_not_crash():
    user = make_user_prefs(target_energy=0.0)
    song = dict(make_song_dicts()[0])
    song["energy"] = 1.0
    score, reasons, confidence = score_song(user, song)
    assert score >= 0
    assert 0.0 <= confidence <= 1.0


def test_score_song_likes_acoustic_true_uses_acousticness_directly():
    user = make_user_prefs(likes_acoustic=True)
    song = dict(make_song_dicts()[1])  # acousticness 0.9
    score, reasons, _ = score_song(user, song)
    assert any("acoustic match" in r and "non-acoustic" not in r for r in reasons)


# --- recommend_songs -----------------------------------------------------


def test_recommend_songs_sorted_highest_first():
    user = make_user_prefs()
    songs = make_song_dicts()
    results = recommend_songs(user, songs, k=5)

    assert len(results) == 2
    assert results[0][1] >= results[1][1]
    for song, score, reasons, confidence in results:
        assert isinstance(reasons, list)
        assert 0.0 <= confidence <= 1.0


def test_recommend_songs_respects_k():
    user = make_user_prefs()
    songs = make_song_dicts()
    assert len(recommend_songs(user, songs, k=1)) == 1


def test_recommend_songs_empty_catalog_returns_empty():
    assert recommend_songs(make_user_prefs(), [], k=5) == []


def test_recommend_songs_k_zero_returns_empty():
    assert recommend_songs(make_user_prefs(), make_song_dicts(), k=0) == []


def test_recommend_songs_skips_malformed_song(caplog):
    user = make_user_prefs()
    songs = make_song_dicts() + [{"title": "Broken Song"}]
    with caplog.at_level(logging.WARNING):
        results = recommend_songs(user, songs, k=5)

    assert len(results) == 2
    assert any("Skipping song" in record.message for record in caplog.records)


# --- discover_songs_with_rag ------------------------------------------------


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, response_text):
        self._response_text = response_text

    def generate_content(self, **kwargs):
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text):
        self.models = _FakeModels(response_text)


def _patch_client(monkeypatch, response_text=None, raise_on_init=None):
    import src.recommender as recommender_module

    def fake_client_factory(*args, **kwargs):
        if raise_on_init is not None:
            raise raise_on_init
        return _FakeClient(response_text)

    monkeypatch.setattr(recommender_module.genai, "Client", fake_client_factory)


def test_discover_songs_parses_valid_response(monkeypatch):
    payload = json.dumps([{"title": "New Song", "artist": "New Artist", "reason": "matches vibe"}])
    _patch_client(monkeypatch, response_text=f"Here you go: {payload}")

    result = discover_songs_with_rag(make_user_prefs(), make_song_dicts())

    assert len(result) == 1
    assert result[0]["title"] == "New Song"
    assert 0.0 < result[0]["confidence"] <= 1.0


def test_discover_songs_empty_array_returns_empty(monkeypatch):
    _patch_client(monkeypatch, response_text="[]")
    assert discover_songs_with_rag(make_user_prefs(), make_song_dicts()) == []


def test_discover_songs_no_json_array_returns_empty(monkeypatch, caplog):
    _patch_client(monkeypatch, response_text="I don't have a good match for you.")
    with caplog.at_level(logging.WARNING):
        result = discover_songs_with_rag(make_user_prefs(), make_song_dicts())
    assert result == []


def test_discover_songs_invalid_json_returns_empty(monkeypatch):
    _patch_client(monkeypatch, response_text="[{not valid json}]")
    assert discover_songs_with_rag(make_user_prefs(), make_song_dicts()) == []


def test_discover_songs_non_list_json_returns_empty(monkeypatch):
    _patch_client(monkeypatch, response_text='{"title": "oops"}')
    assert discover_songs_with_rag(make_user_prefs(), make_song_dicts()) == []


def test_discover_songs_drops_items_missing_title_or_artist(monkeypatch):
    payload = json.dumps([
        {"title": "Has Both", "artist": "Someone", "reason": "why not"},
        {"title": "Missing Artist"},
    ])
    _patch_client(monkeypatch, response_text=payload)

    result = discover_songs_with_rag(make_user_prefs(), make_song_dicts())
    assert len(result) == 1
    assert result[0]["title"] == "Has Both"


def test_discover_songs_caps_at_max_discovered_songs(monkeypatch):
    payload = json.dumps([
        {"title": f"Song {i}", "artist": f"Artist {i}", "reason": "reason"}
        for i in range(5)
    ])
    _patch_client(monkeypatch, response_text=payload)

    result = discover_songs_with_rag(make_user_prefs(), make_song_dicts(), k=10)
    assert len(result) <= MAX_DISCOVERED_SONGS


def test_discover_songs_client_init_failure_returns_empty(monkeypatch):
    _patch_client(monkeypatch, raise_on_init=RuntimeError("no API key"))
    assert discover_songs_with_rag(make_user_prefs(), make_song_dicts()) == []


def test_discover_songs_lower_confidence_when_reason_missing(monkeypatch):
    payload = json.dumps([{"title": "No Reason Song", "artist": "Someone"}])
    _patch_client(monkeypatch, response_text=payload)

    result = discover_songs_with_rag(make_user_prefs(), make_song_dicts())
    assert len(result) == 1
    assert result[0]["confidence"] < 0.8
