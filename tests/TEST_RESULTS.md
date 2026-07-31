# Test Results

Summary of the automated test suite in [`tests/test_recommender.py`](test_recommender.py), covering `src/recommender.py`'s major functions: `load_songs`, `score_song`, `recommend_songs`, `discover_songs_with_rag`, and the `Recommender` OOP wrapper (`recommend`, `explain_recommendation`).

**Last run:** 33 passed, 0 failed (1 unrelated third-party deprecation warning from `google-genai`).

```
python -m pytest tests/ -v
```

## What's covered

### `Recommender` (OOP wrapper)
- Returns songs sorted by score, respects `k`.
- Edge cases: `k=0`, negative `k`, empty catalog, `k` larger than the catalog.
- `explain_recommendation` returns a non-empty string that includes a confidence value.

### `load_songs`
- Reads a valid CSV correctly.
- Missing file raises `FileNotFoundError` instead of crashing with an unhandled exception.
- Malformed rows (e.g. a non-numeric field) are skipped and logged as a warning rather than aborting the whole load.
- An empty (header-only) CSV returns an empty list.

### `score_song`
- Perfect-match and no-match scoring produce the expected reasons and score.
- Confidence is always within `[0, 1]` and tracks how good the match is (high for a strong match, low for a poor one).
- Missing required keys in either `user_prefs` or `song` raise a `ValueError` instead of a raw `KeyError`.
- Energy extremes (0.0 vs 1.0) don't crash.
- `likes_acoustic=True` correctly switches the scoring path to reward acousticness directly.

### `recommend_songs`
- Sorted output, `k` is respected.
- Edge cases: empty catalog, `k=0`.
- A malformed song dict (missing required fields) is skipped and logged rather than raising and stopping the whole batch.

### `discover_songs_with_rag` (Gemini RAG discovery)
The Gemini client is mocked (no real API calls in tests) to exercise:
- A valid JSON response is parsed into song dicts with a `confidence` field.
- An empty `[]` response, a response with no JSON array at all, invalid JSON, and a non-list JSON payload all safely return `[]` instead of raising.
- Items missing `title`/`artist` are dropped.
- Results are always capped at `MAX_DISCOVERED_SONGS` (2), even if the model returns more.
- Client construction failure (e.g. missing API key) returns `[]` instead of raising.
- Confidence is lower for discovered items missing a `reason` field, since the RAG layer is not web-grounded and its output isn't independently verified — see [Limitations and Risks](../README.md#limitations-and-risks).

## Notes

- Tests use `pytest`'s `tmp_path` and `caplog` fixtures to test file I/O and logging behavior without touching real project data.
- No real network/API calls are made — `discover_songs_with_rag` tests monkeypatch `genai.Client`.
