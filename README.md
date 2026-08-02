# 🎵 Music Recommender Simulation + RAG Discovery

## Original Project (Module 3): Music Recommender Simulation

This project builds on **Module 3: Music Recommender Simulation**, whose original goal was to represent songs and a user "taste profile" as data, then design a rule-based scoring function that turns those profiles into ranked recommendations from a small local catalog (`data/songs.csv`). The original capabilities were entirely deterministic: it scored every song in the catalog against a user's favorite genre, favorite mood, target energy, and acoustic preference, then returned the top-K matches with a plain-language breakdown of why each song scored the way it did.

This repo extends that Module 3 foundation with a **RAG-based discovery feature**: on top of the original rule-based scorer, the system now also queries a Google Gemini model with web-search grounding to suggest real songs that fit the user's taste profile but aren't already in the local catalog.

---

## Title and Summary

**Music Recommender Simulation + Gemini-Powered Discovery**

This project simulates how a real-world music recommender turns stated user preferences into ranked song suggestions, and then goes one step further by using a free-tier LLM (Gemini) with live web search to surface songs *outside* the local catalog that a purely rule-based system could never recommend, since it can only rank what it already has. This matters because it demonstrates both sides of modern recommenders in one small system: the transparent, auditable scoring logic real systems still rely on for their core catalog, and the generative/retrieval layer that lets platforms like Spotify or YouTube Music suggest things you haven't heard yet.

---

## Architecture Overview

See [`diagrams/system_architecture.mmd`](diagrams/system_architecture.mmd) for the full diagram. In short, the system has four stages:

1. **Input** — A `UserProfile`-shaped dict (`favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`) and the local `data/songs.csv` catalog.
2. **Process** — Two parallel paths consume the same input:
   - `load_songs()` → `score_song()` / `recommend_songs()`: the deterministic rule-based scoring engine (Module 3 logic, unchanged).
   - `_build_search_query()` → `discover_songs_with_rag()`: converts the numeric/boolean profile into a natural-language search phrase, then sends it to Gemini (with Google Search grounding) to find real songs outside the catalog.
3. **Output** — The scored top-K catalog recommendations and the (at most 2) discovered songs are both printed to the console by `src/main.py`.
4. **Checking** — `tests/test_recommender.py` unit-tests the scoring logic; `scripts/verify_rag_reliability.py` repeatedly calls the Gemini discovery path to check it never exceeds the 2-song cap and that repeated runs on the same profile tend to agree (Jaccard similarity), since LLM output isn't deterministic the way the scorer is.

The key design point the diagram makes visible: the rule-based path and the AI path are independent and additive. If the Gemini call fails or the quota is exhausted, `discover_songs_with_rag()` returns `[]` and the rest of the system (catalog scoring, CLI output) is unaffected.

---

## Relaibility evaulation for AI: How "Confidence" Works

The `confidence` shown next to a song means something different depending on which path produced it:

- **Catalog recommendations** (`score_song()` / `recommend_songs()`): confidence is the match score normalized against the maximum possible score of 6.0 — `confidence = score / 6.0`, clamped to `[0.0, 1.0]`. It's a direct measure of *how good the match is*: a song that hits genre, mood, energy, and acoustic preference perfectly scores near 1.0 (100%); a song that misses most of those scores low.
- **RAG-discovered songs** (`discover_songs_with_rag()` / `_discovered_item_confidence()`): confidence is **not** a match-quality score. It's a heuristic about how complete Gemini's response looked:
  - Missing `title` or `artist` → `0.0` (the item is dropped entirely, never shown)
  - `title` + `artist` present but no `reason` → `0.5`
  - `title` + `artist` + `reason` all present → `0.8`

  It's capped at `0.8` (never `1.0`) because these songs come from Gemini's own trained knowledge with no web-search verification of the claim, so the system never claims full certainty in a discovered pick the way it can for a fully-computed catalog score.

In short: catalog confidence measures fit-to-preferences; RAG confidence measures response completeness, not accuracy.

---

## Setup Instructions

1. **Clone the repo and create a virtual environment:**

   ```bash
   python -m venv .venv
   ```

   Activate it:

   ```powershell
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

   ```bash
   # Mac/Linux
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Get a free Gemini API key** from [aistudio.google.com/apikey](https://aistudio.google.com/apikey), then set it as an environment variable so `discover_songs_with_rag()` can authenticate:

   ```powershell
   $env:GEMINI_API_KEY = "your-key-here"
   ```

   (Or add that line to the bottom of `.venv\Scripts\Activate.ps1` so it's set automatically every time you activate this venv.)

4. **Run the app** (from the project root, with `src/` added to `PYTHONPATH` so `main.py`'s bare `from recommender import ...` resolves):

   ```bash
   # Mac/Linux
   PYTHONPATH=src python src/main.py
   ```

   ```powershell
   # Windows (PowerShell)
   $env:PYTHONPATH = "src"
   python src/main.py
   ```

   By default, only one profile ("High-Energy Pop") is active in `src/main.py` to keep free-tier API usage low; the rest are commented out and can be re-enabled as needed.

5. **Run the tests:**

   ```bash
   pytest
   ```

6. **(Optional) Check RAG reliability:**

   ```bash
   python scripts/verify_rag_reliability.py --runs 3
   ```

---

## Sample Interactions

### Example 1 — Catalog scoring: High-Energy Pop

Input: `{'favorite_genre': 'pop', 'favorite_mood': 'happy', 'target_energy': 0.9, 'likes_acoustic': False}`

```
1. Sunrise City by Neon Echo — Score: 5.74
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.8)

2. Gym Hero by Max Pulse — Score: 3.92
   - genre match (+2.0)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)
```

### Example 2 — Catalog scoring: Chill Lofi

Input: `{'favorite_genre': 'lofi', 'favorite_mood': 'chill', 'target_energy': 0.3, 'likes_acoustic': True}`

```
1. Library Rain by Paper Lanterns — Score: 5.81
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - acoustic match (+0.9)

2. Midnight Coding by LoRoom — Score: 5.59
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - acoustic match (+0.7)
```

### Example 3 — Gemini RAG discovery (live captured output)

Input: same "High-Energy Pop" profile above. `_build_search_query()` turns it into the phrase `"high-energy, upbeat pop songs with a happy mood, non-acoustic/produced sound"`, which is sent to Gemini with Google Search grounding.

```
Discovering additional songs outside the catalog (RAG + web search)...

You might also like (not in our catalog):

- Levitating by Dua Lipa (confidence: 80%)
   - Upbeat, heavily produced pop song with a joyful mood.
- Blinding Lights by The Weeknd (confidence: 80%)
   - High-energy synth-pop track with an infectious, upbeat feel.
```

> This is real captured output from a live run with `GEMINI_API_KEY` set. Both picks land at 80% confidence since Gemini returned a title, artist, and reason for each — see [How "Confidence" Works](#how-confidence-works) for why RAG confidence caps at 80% rather than 100%. Because this path calls a live LLM, re-running the same profile can surface different (but usually genre/mood-appropriate) songs — see [`scripts/verify_rag_reliability.py`](scripts/verify_rag_reliability.py) for how run-to-run consistency is measured.

---

## Execution Evidence

Every command and output below was run and captured directly from this repo (not hand-written) so the system can be graded without a video. Reproduce any of it yourself with the exact commands shown.

### 1. End-to-end system run (3 inputs)

Command (run from the project root, with `data/songs.csv` present and `src/` on `PYTHONPATH`):

```bash
PYTHONPATH=src python src/main.py
```

**Input 1 — High-Energy Pop** (`{'favorite_genre': 'pop', 'favorite_mood': 'happy', 'target_energy': 0.9, 'likes_acoustic': False}`, the default active profile in `src/main.py`):

```
INFO recommender: Loaded songs: 17
ERROR recommender: [discover_songs_with_rag] Failed to create Gemini client: No API key was provided. Please pass a valid API key. Learn how to create an API key at https://ai.google.dev/gemini-api/docs/api-key.
============================================================
PROFILE: High-Energy Pop
Preferences: {'favorite_genre': 'pop', 'favorite_mood': 'happy', 'target_energy': 0.9, 'likes_acoustic': False}
============================================================

Top recommendations:

1. Sunrise City by Neon Echo — Score: 5.74 (confidence: 96%)
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.8)

2. Gym Hero by Max Pulse — Score: 3.92 (confidence: 65%)
   - genre match (+2.0)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)

3. Rooftop Lights by Indigo Parade — Score: 3.51 (confidence: 58%)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.7)

4. Iron Fists by Grey Anvil — Score: 1.90 (confidence: 32%)
   - energy closeness (+0.9)
   - non-acoustic match (+1.0)

5. City Pulse by DJ Solstice — Score: 1.90 (confidence: 32%)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)

Discovering additional songs outside the catalog (RAG + web search)...
(No additional songs discovered.)
```

This is real captured output from a machine with **no `GEMINI_API_KEY` set** — note the `ERROR recommender: ... Failed to create Gemini client: No API key was provided` line. This is the RAG guardrail (see [§3](#3-reliabilityguardrail-evidence)) working as designed: `discover_songs_with_rag()` catches the client-construction failure, logs it, and returns `[]` instead of crashing, so the catalog recommendations above still print normally.

**Input 1, re-run with `GEMINI_API_KEY` set** — same profile, same catalog scores, but this time the RAG discovery call succeeds instead of falling back:

```
INFO recommender: Loaded songs: 17
============================================================
PROFILE: High-Energy Pop
Preferences: {'favorite_genre': 'pop', 'favorite_mood': 'happy', 'target_energy': 0.9, 'likes_acoustic': False}
============================================================

Top recommendations:

1. Sunrise City by Neon Echo — Score: 5.74 (confidence: 96%)
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.8)

2. Gym Hero by Max Pulse — Score: 3.92 (confidence: 65%)
   - genre match (+2.0)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)

3. Rooftop Lights by Indigo Parade — Score: 3.51 (confidence: 58%)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.7)

4. Iron Fists by Grey Anvil — Score: 1.90 (confidence: 32%)
   - energy closeness (+0.9)
   - non-acoustic match (+1.0)

5. City Pulse by DJ Solstice — Score: 1.90 (confidence: 32%)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)

Discovering additional songs outside the catalog (RAG + web search)...
INFO google_genai.models: AFC is enabled with max remote calls: 10.
INFO httpx: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent "HTTP/1.1 200 OK"

You might also like (not in our catalog):

- Levitating by Dua Lipa (confidence: 80%)
   - Upbeat, heavily produced pop song with a joyful mood.
- Blinding Lights by The Weeknd (confidence: 80%)
   - High-energy synth-pop track with an infectious, upbeat feel.
```

This demonstrates the two paths are genuinely independent, as the diagram claims: the catalog scores are byte-for-byte identical whether or not `GEMINI_API_KEY` is set, and only the RAG discovery section changes based on whether that call succeeds.

**Input 2 — Chill Lofi** and **Input 3 — Deep Intense Rock** (calling `recommend_songs()` directly with the same loaded catalog, since only one profile is left active in `src/main.py` by default to limit API usage — see [Design Decisions](#design-decisions)):

```
============================================================
PROFILE: Chill Lofi
Preferences: {'favorite_genre': 'lofi', 'favorite_mood': 'chill', 'target_energy': 0.3, 'likes_acoustic': True}
============================================================
1. Library Rain by Paper Lanterns -- Score: 5.81 (confidence: 97%)
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - acoustic match (+0.9)
2. Midnight Coding by LoRoom -- Score: 5.59 (confidence: 93%)
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - acoustic match (+0.7)
3. Spacewalk Thoughts by Orbit Bloom -- Score: 3.90 (confidence: 65%)
   - mood match (+2.0)
   - energy closeness (+1.0)
   - acoustic match (+0.9)

============================================================
PROFILE: Deep Intense Rock
Preferences: {'favorite_genre': 'rock', 'favorite_mood': 'intense', 'target_energy': 0.85, 'likes_acoustic': False}
============================================================
1. Storm Runner by Voltline -- Score: 5.84 (confidence: 97%)
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.9)
2. Gym Hero by Max Pulse -- Score: 3.87 (confidence: 64%)
   - mood match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.9)
3. City Pulse by DJ Solstice -- Score: 1.89 (confidence: 32%)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)
```

### 2. AI feature behavior (Gemini RAG discovery)

`discover_songs_with_rag()` is a thin wrapper around one Gemini call plus JSON parsing, so its "AI behavior" is exercised here with the real code path but a mocked `genai.Client` (no live network call, no API key needed to reproduce) — this isolates what the *code* guarantees about the model's output from what the *model* happens to say on a given day. Command:

```bash
PYTHONPATH=src python -c "
import json
import recommender as r

user_prefs = {'favorite_genre': 'pop', 'favorite_mood': 'happy', 'target_energy': 0.9, 'likes_acoustic': False}
songs = r.load_songs('data/songs.csv')

class FakeResp:
    def __init__(self, text): self.text = text
class FakeModels:
    def __init__(self, text): self._t = text
    def generate_content(self, **kw): return FakeResp(self._t)
class FakeClient:
    def __init__(self, text): self.models = FakeModels(text)

r.genai.Client = lambda *a, **k: FakeClient(json.dumps([
    {'title': 'Aftershock', 'artist': 'Nova Ray', 'reason': 'upbeat pop hook matches happy/high-energy'}
]))
print(r.discover_songs_with_rag(user_prefs, songs))
"
```

Output:

```
[{'title': 'Aftershock', 'artist': 'Nova Ray', 'reason': 'upbeat pop hook matches happy/high-energy', 'confidence': 0.8}]
```

This shows the full AI-feature pipeline: numeric/boolean profile → `_build_search_query()` natural-language phrase → Gemini prompt → JSON parse → attached `confidence` (0.8, since `reason` is present — see `_discovered_item_confidence`). A real run against the live API (with `GEMINI_API_KEY` set) produces the same shape with a model-chosen title/artist/reason instead of the mocked one.

### 3. Reliability/guardrail evidence

Each of these is a real failure mode the code is designed to survive, captured directly (not described):

**3a. Missing catalog file** — `load_songs()` raises a clear, catchable error instead of an unhandled traceback:

```bash
PYTHONPATH=src python -c "
from recommender import load_songs
try:
    load_songs('data/does_not_exist.csv')
except FileNotFoundError as e:
    print(f'Caught FileNotFoundError as expected: {e}')
"
```
```
ERROR recommender: Songs CSV not found at 'data/does_not_exist.csv'
Caught FileNotFoundError as expected: [Errno 2] No such file or directory: 'data/does_not_exist.csv'
```

**3b. Malformed CSV row** — one bad row is skipped and logged; good rows still load:

```bash
PYTHONPATH=src python -c "
from recommender import load_songs
import tempfile
path = tempfile.mktemp(suffix='.csv')
open(path, 'w', encoding='utf-8').write(
    'id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n'
    '1,Good Song,Artist A,pop,happy,0.8,120,0.9,0.8,0.2\n'
    '2,Bad Song,Artist B,pop,happy,not-a-number,120,0.9,0.8,0.2\n'
)
songs = load_songs(path)
print(f'Rows loaded: {len(songs)} -> {[s[\"title\"] for s in songs]}')
"
```
```
WARNING recommender: Skipping malformed row 3 in <tmpfile>.csv: could not convert string to float: 'not-a-number'
INFO recommender: Loaded songs: 1
Rows loaded: 1 -> ['Good Song']
```

**3c. Missing required fields passed to `score_song`** — raises a descriptive `ValueError` naming exactly which keys are missing, instead of an opaque `KeyError` deep in the scoring math:

```bash
PYTHONPATH=src python -c "
from recommender import score_song
try:
    score_song({'favorite_genre': 'pop'}, {'genre': 'pop', 'mood': 'happy', 'energy': 0.5, 'acousticness': 0.5})
except ValueError as e:
    print(f'Caught ValueError as expected: {e}')
"
```
```
ERROR recommender: score_song missing required keys — user_prefs: ['favorite_mood', 'target_energy', 'likes_acoustic'], song: []
Caught ValueError as expected: score_song missing required keys — user_prefs: ['favorite_mood', 'target_energy', 'likes_acoustic'], song: []
```

**3d. RAG output size cap** — even if the model returns more songs than allowed, the guardrail caps the result at `MAX_DISCOVERED_SONGS` (2):

```
=== model asked to return 10, mocked to return 5 ===
2 returned (cap is 2): [{'title': 'Song 0', 'artist': 'Artist 0', 'reason': 'r', 'confidence': 0.8}, {'title': 'Song 1', 'artist': 'Artist 1', 'reason': 'r', 'confidence': 0.8}]
```

**3e. Unparseable model output** — if Gemini's response has no JSON array in it at all, the guardrail logs a warning and returns `[]` instead of raising:

```
WARNING recommender: [discover_songs_with_rag] No JSON array found in response: 'sorry, no good matches for that!'
[]
```

**3f. Missing Gemini API key** — see Input 1's captured output in [§1](#1-end-to-end-system-run-3-inputs): `ERROR recommender: [discover_songs_with_rag] Failed to create Gemini client: No API key was provided ...`, followed by `(No additional songs discovered.)` — the rest of the CLI run is unaffected.

### 4. Automated test suite (evaluation behavior)

```bash
python -m pytest tests/ -v
```

```
collected 33 items

tests/test_recommender.py::test_recommend_returns_songs_sorted_by_score PASSED
tests/test_recommender.py::test_recommend_respects_k PASSED
tests/test_recommender.py::test_recommend_k_zero_returns_empty PASSED
tests/test_recommender.py::test_recommend_k_negative_returns_empty PASSED
tests/test_recommender.py::test_recommend_empty_catalog_returns_empty PASSED
tests/test_recommender.py::test_recommend_k_larger_than_catalog_returns_all PASSED
tests/test_recommender.py::test_explain_recommendation_returns_non_empty_string PASSED
tests/test_recommender.py::test_explain_recommendation_includes_confidence PASSED
tests/test_recommender.py::test_load_songs_reads_valid_csv PASSED
tests/test_recommender.py::test_load_songs_missing_file_raises PASSED
tests/test_recommender.py::test_load_songs_skips_malformed_rows PASSED
tests/test_recommender.py::test_load_songs_empty_file_returns_empty_list PASSED
tests/test_recommender.py::test_score_song_perfect_match_scores_high_with_high_confidence PASSED
tests/test_recommender.py::test_score_song_no_match_scores_low_with_low_confidence PASSED
tests/test_recommender.py::test_score_song_confidence_always_in_unit_range PASSED
tests/test_recommender.py::test_score_song_missing_user_pref_key_raises_value_error PASSED
tests/test_recommender.py::test_score_song_missing_song_key_raises_value_error PASSED
tests/test_recommender.py::test_score_song_energy_extremes_do_not_crash PASSED
tests/test_recommender.py::test_score_song_likes_acoustic_true_uses_acousticness_directly PASSED
tests/test_recommender.py::test_recommend_songs_sorted_highest_first PASSED
tests/test_recommender.py::test_recommend_songs_respects_k PASSED
tests/test_recommender.py::test_recommend_songs_empty_catalog_returns_empty PASSED
tests/test_recommender.py::test_recommend_songs_k_zero_returns_empty PASSED
tests/test_recommender.py::test_recommend_songs_skips_malformed_song PASSED
tests/test_recommender.py::test_discover_songs_parses_valid_response PASSED
tests/test_recommender.py::test_discover_songs_empty_array_returns_empty PASSED
tests/test_recommender.py::test_discover_songs_no_json_array_returns_empty PASSED
tests/test_recommender.py::test_discover_songs_invalid_json_returns_empty PASSED
tests/test_recommender.py::test_discover_songs_non_list_json_returns_empty PASSED
tests/test_recommender.py::test_discover_songs_drops_items_missing_title_or_artist PASSED
tests/test_recommender.py::test_discover_songs_caps_at_max_discovered_songs PASSED
tests/test_recommender.py::test_discover_songs_client_init_failure_returns_empty PASSED
tests/test_recommender.py::test_discover_songs_lower_confidence_when_reason_missing PASSED

======================== 33 passed, 1 warning in 2.03s ========================
```

Full breakdown of what each test covers: [**tests/TEST_RESULTS.md**](tests/TEST_RESULTS.md).

---

## Design Decisions

- **Rule-based scoring kept separate from the LLM layer.** The original Module 3 scorer (`score_song`, `recommend_songs`) is untouched by the Gemini addition. Trade-off: this means the two recommendation sources can disagree or even suggest genre-mismatched songs from the AI side, but it keeps the catalog ranking fully deterministic, auditable, and testable with plain unit tests — properties an LLM-based scorer would give up.
- **Gemini over a paid API.** The RAG discovery step needed a model with live web-search grounding, but this is a classroom project, so a free-tier model (Google Gemini, `gemini-flash-lite-latest`) was chosen over a paid option to keep the project runnable without a billing account. Trade-off: free-tier rate limits are low and grounding requests have their own tighter quota, so the discovery feature can and does occasionally fail with `429 RESOURCE_EXHAUSTED` — handled by catching the error and returning `[]` instead of crashing.
- **Flash-Lite over full Flash.** Within Gemini's free tier, `gemini-flash-lite-latest` was picked over `gemini-flash-latest` for lower latency/cost per call, since this task (find ≤2 songs, short reason) doesn't need the larger model's extra reasoning quality. Trade-off: Flash-Lite is more prone to inconsistent picks across repeated runs on the same profile, which is exactly what `scripts/verify_rag_reliability.py` was built to measure.
- **Hard cap of 2 discovered songs (`MAX_DISCOVERED_SONGS`).** Keeps prompts and outputs small (fewer tokens, less quota burned per run) and keeps the "you might also like" section a small supplement rather than a competing recommendation list.
- **Terse prompt strings.** The Gemini prompt was deliberately rewritten to be a single compact line (comma-separated catalog instead of a bulleted list, abbreviated JSON-shape instructions) purely to reduce input tokens per call, since free-tier quota is the binding constraint, not response quality.
- **Only one profile active by default in `src/main.py`.** With six total test profiles, running all of them each time would multiply API calls (and quota risk) by 6x for no benefit during normal development; the rest are commented out rather than deleted so they're easy to restore for a full test pass.
- **Fail-soft, not fail-loud.** `discover_songs_with_rag()` catches API errors and JSON-parsing failures and returns `[]` rather than raising, so a quota error or a malformed model response never takes down the whole CLI run — the catalog-based recommendations still print either way.

---

## Experiments You Tried

### Weight Experiment: Double Energy, Halve Genre

As a temporary experiment, `score_song` in `recommender.py` was changed so that:

- genre match: `+2.0` → `+1.0` (halved)
- energy closeness: `1 - abs(diff)` → `(1 - abs(diff)) * 2` (doubled, max `+2.0`)

`main.py` was re-run against all six profiles with these new weights. Selected before/after comparisons:

**High-Energy Pop** — rank order changed: "Gym Hero" (genre-only match) dropped from #2 to #3, displaced by "Rooftop Lights" (mood-only match), because losing a point of genre weight let a mood match edge it out. "Storm Runner" and "City Pulse" (energy-only matches) climbed into the top 5 (2.88 each) on the strength of near-perfect energy closeness alone.

**Deep Intense Rock** — "Iron Fists" fell out of the top 5 entirely, replaced by "Sunrise City," since Iron Fists had been relying on close energy + non-acoustic match without any genre/mood match, and doubling energy wasn't enough to keep it ahead once other pure-energy matches also got the same boost.

**Adversarial: Extreme Energy + Acoustic Conflict** — "Iron Fists" still wins by a wide margin (4.97 vs. 1.92 for #2), but the gap shrank from roughly 4x to roughly 2.6x. Doubling energy weight raised everyone's energy-closeness contribution roughly equally, so it didn't meaningfully rebalance the genre+mood-vs-acousticness conflict — Iron Fists's categorical bonuses (genre 1.0 + mood 2.0 = 3.0) still dwarf the acoustic penalty it incurs (0.0 instead of up to 1.0).

**Conclusion: different, not more accurate.** This reweighting didn't fix any of the underlying issues found in the adversarial testing — it just shifted which songs win in close calls. Pure energy-matches now rank higher relative to pure genre-matches (arguably reasonable, since energy is a continuous/precise signal and genre is a coarse binary one), but the core problem — that additive categorical bonuses can still swamp a fully-failed continuous preference — persists. Whether this reweighting counts as "more accurate" depends entirely on which axis a real user weights more heavily in their own head, which the system has no way to learn; it's a different tradeoff, not a strictly better one. The weight change was reverted back to the original values (genre `+2.0`, energy `1 - abs(diff)`) after this experiment.

### Adversarial / Edge Case Profiles

To stress-test the scoring logic, I ran profiles with internally conflicting preferences to see whether the system would produce misleading or nonsensical "confident" recommendations.

#### Adversarial Profile 1: High Energy + Sad Mood

`{'favorite_genre': 'pop', 'favorite_mood': 'sad', 'target_energy': 0.9, 'likes_acoustic': False}` — conflicting because high-energy songs in this catalog are almost never tagged "sad."

```
1. Gym Hero by Max Pulse — Score: 3.92
   - genre match (+2.0)
   - energy closeness (+1.0)
   - non-acoustic match (+0.9)

2. Sunrise City by Neon Echo — Score: 3.74
   - genre match (+2.0)
   - energy closeness (+0.9)
   - non-acoustic match (+0.8)
```

**Observation:** No song in the catalog has mood "sad," so the mood match bonus never fires for anyone. The system silently falls back to genre + energy + acousticness and never signals that "sad" was an impossible target — it just quietly ignores that preference. This isn't really "tricked," but it reveals that unmatched categorical preferences fail silently instead of surfacing a warning to the user.

#### Adversarial Profile 2: Nonexistent Genre

`{'favorite_genre': 'polka', 'favorite_mood': 'happy', 'target_energy': 0.5, 'likes_acoustic': False}` — genre doesn't exist in the catalog at all.

**Observation:** Same failure mode as above — an impossible genre just means the +2.0 genre bonus never applies to anyone, so the system quietly recommends based on mood/energy/acousticness alone. The recommender never detects or reports that "polka" isn't a real option; it degrades gracefully but silently, which could mislead a user into thinking the recommendations reflect their genre preference when they don't at all.

#### Adversarial Profile 3: Extreme Energy + Acoustic Conflict

`{'favorite_genre': 'metal', 'favorite_mood': 'angry', 'target_energy': 1.0, 'likes_acoustic': True}` — asks for maximum energy (metal/angry) *and* strong acoustic preference, which are contradictory in this catalog (the metal/angry song is the least acoustic track available).

```
1. Iron Fists by Grey Anvil — Score: 5.00
   - genre match (+2.0)
   - mood match (+2.0)
   - energy closeness (+1.0)
   - acoustic match (+0.0)

2. Coffee Shop Stories by Slow Stereo — Score: 1.26
   - energy closeness (+0.4)
   - acoustic match (+0.9)
```

**Observation:** This is the most interesting case. Even though the user asked for `likes_acoustic: True`, "Iron Fists" wins by a wide margin (5.00 vs 1.26) purely because it perfectly matches genre and mood while completely failing the acoustic preference (acoustic score of 0.0, the worst possible). This exposes a real weight-balance issue: the additive scoring lets two +2.0 categorical bonuses (genre + mood, worth 4.0 combined) completely dominate and mask a total failure on another axis (acousticness, worth at most 1.0). A user with truly conflicting preferences gets a recommendation that satisfies only part of what they asked for, with no indication that a tradeoff was made.

### Summary of what the adversarial testing revealed

- Unmatched categorical preferences (a mood or genre that doesn't exist in the catalog) fail silently — the corresponding bonus just never applies, with no feedback to the user.
- The additive scoring model lets high-weight categorical matches (genre +2.0, mood +2.0) drown out a complete failure on a lower-weight continuous preference (acousticness, max +1.0), so conflicting preferences resolve in favor of whichever axis has more available point-weight rather than a balanced compromise.
- The system never flags contradictions in the input itself (e.g., high energy + "sad" mood, or high energy + acoustic) — it just scores whatever combination it's given.

---

## Testing

Automated tests live in [`tests/test_recommender.py`](tests/test_recommender.py) and cover scoring, recommendation ranking, CSV loading, confidence scoring, error handling, and the Gemini RAG discovery layer (mocked, no live API calls), including edge cases like empty catalogs, malformed data, and API failures.

Run them with:

```bash
python -m pytest tests/ -v
```

See [**Test Results**](tests/TEST_RESULTS.md) for a summary of what's covered and the latest run's outcome.

---

## Limitations and Risks

- It only works on a tiny catalog (17 songs).
- It does not understand lyrics or language.
- **Energy "dead zones" underserve moderate-energy users.** The catalog's energy values cluster into a low band (0.28–0.45) and a high band (0.75–0.97), with gaps of 0.10–0.13 in the middle (only 2 songs sit between 0.45 and 0.75). A user targeting `energy=0.6` can never score as well on the energy axis as a user targeting `0.3` or `0.9`, purely because of catalog density — the system never flags this, so it presents a structurally worse recommendation with the same confidence as a well-matched one.
- **Genre/mood matching is exact-string and binary, which reinforces filter bubbles.** 12 of 14 genres and 9 of 13 moods appear only once in the catalog, and there's no notion of genre/mood *similarity* (`"pop"`, `"indie pop"`, and `"dream pop"` are totally unrelated to the scorer). A niche-taste user gets at most one song that can ever earn the genre/mood bonus, and the system never surfaces adjacent styles as a bridge — it only ever reinforces the exact label a user typed, never nudges them toward related music.
- **Categorical bonuses (genre +2, mood +2) outweigh continuous features (energy, acousticness, each capped at +1).** This means two label matches will beat a perfect audio-feature match almost every time. Users whose taste is really about *feel* rather than a genre/mood tag are structurally shortchanged.
- **Small-catalog artist concentration compounds the genre bias.** Two artists ("Neon Echo," "LoRoom") each have 2 of the catalog's 17 songs; for the 3-song "lofi" genre, that means one artist supplies two-thirds of the recommendations for anyone who likes lofi.
- **No diversity or exploration mechanism** in the catalog scorer — a given profile always returns the exact same top 5, with no randomness or cross-genre "you might also like" logic. The Gemini discovery layer partially addresses this, but is itself constrained to at most 2 songs and free-tier rate limits.
- **Unmatched/impossible preferences fail silently** (see Experiments section) — a genre or mood that doesn't exist in the catalog just contributes nothing to the score, with no warning to the user that part of their profile was ignored.
- **The RAG discovery layer is not fully deterministic or always available.** LLM output can vary run-to-run (measured via `scripts/verify_rag_reliability.py`), and free-tier quota exhaustion (`429 RESOURCE_EXHAUSTED`) can cause it to silently return no discovered songs at all.

---

## Reflection

Read the full model card: [**Model Card**](model_card.md)

Building the RAG discovery layer on top of the Module 3 scorer made the contrast between the two recommendation paradigms concrete: the rule-based scorer is fully explainable and reproducible but structurally capped by whatever's in the catalog, while the LLM-plus-search layer can genuinely discover things outside that catalog but trades away determinism, explainability by inspection, and free availability (rate limits, quota). It also made clear how much of an LLM-based feature's real-world reliability comes down to guardrails around the model call itself — capping output size, handling rate-limit errors gracefully, and verifying run-to-run consistency — rather than the prompt alone. That's a dimension of bias/unfairness this project didn't have to grapple with in Module 3, since a deterministic scorer's biases are static and auditable, whereas an LLM's search-grounded picks could favor certain genres/artists based on what's more visible on the web rather than what best fits the user.

Project 4 update: The project taught me that AI is generally good at executing plans a good plan is still neccesary for the AI to be at it's most useful and that plan is best come up with by an actual person. One flawed AI suggestion was explaining the error for why I kept getting token limit was being reached even though no token was used that day. It took delving into the the limitations of the models to realize how to remove the google search part of the ai so the token limit was not reached. One good suggestion was the implementation of many tests to verify the code worked. I was largely unfamilliar with logs and the many tests the ai came up with were more than I would know to think of. 

## Testing Summary:

Most of the project worked as intended. There was some issues getting things to run initially since there was issues with getting api keys and getting the project to run in vscode without the special command. Because of that I ended up learning more about diferent ai models and their advantages/disadvantages and token usage.