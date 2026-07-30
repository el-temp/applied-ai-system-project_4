"""
Verifies the reliability of discover_songs_with_rag() (src/recommender.py).

For each user profile, this script calls discover_songs_with_rag() multiple
times and checks two things:

1. Size compliance — every run must return 0, 1, or 2 songs (never more).
2. Consistency — repeated runs against the same profile should tend to
   surface the same song(s), not a different pair every time. This is
   measured as the average pairwise Jaccard similarity (on normalized
   "title|artist" pairs) across all runs for a profile.

Requires ANTHROPIC_API_KEY to be set in the environment, since it makes
real calls to discover_songs_with_rag().

Usage:
    python scripts/verify_rag_reliability.py [--runs N] [--profile NAME]

    --runs N        Number of times to call discover_songs_with_rag() per
                     profile (default: 3).
    --profile NAME  Only test the profile with this exact name (default:
                     test every profile in main.PROFILES).
"""

import argparse
import sys
from itertools import combinations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from main import PROFILES  # noqa: E402
from recommender import (  # noqa: E402
    MAX_DISCOVERED_SONGS,
    discover_songs_with_rag,
    load_songs,
)


def _song_key(item: dict) -> str:
    """Normalizes a discovered song to a case-insensitive "title|artist" key."""
    title = str(item.get("title", "")).strip().lower()
    artist = str(item.get("artist", "")).strip().lower()
    return f"{title}|{artist}"


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets; 1.0 if both are empty."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def verify_profile(name: str, user_prefs: dict, songs: list, runs: int) -> dict:
    print("=" * 60)
    print(f"PROFILE: {name}")
    print(f"Preferences: {user_prefs}")
    print("=" * 60)

    run_results = []
    size_violations = []

    for i in range(1, runs + 1):
        discovered = discover_songs_with_rag(user_prefs, songs)
        keys = {_song_key(item) for item in discovered}
        run_results.append(keys)

        print(f"\nRun {i}/{runs}: {len(discovered)} song(s) returned")
        for item in discovered:
            print(f"  - {item.get('title')} by {item.get('artist')}")

        if len(discovered) > MAX_DISCOVERED_SONGS:
            size_violations.append(i)
            print(f"  !! VIOLATION: returned more than {MAX_DISCOVERED_SONGS} songs")

    # Pairwise consistency across all runs for this profile.
    pair_scores = [
        _jaccard(run_results[i], run_results[j])
        for i, j in combinations(range(len(run_results)), 2)
    ]
    avg_consistency = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0

    print(f"\nSize compliance: {'PASS' if not size_violations else 'FAIL'}"
          f" ({len(size_violations)} violation(s) out of {runs} run(s))")
    print(f"Average pairwise consistency (Jaccard): {avg_consistency:.2f}")
    print()

    return {
        "name": name,
        "runs": run_results,
        "size_violations": size_violations,
        "avg_consistency": avg_consistency,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Runs per profile (default: 3)")
    parser.add_argument("--profile", type=str, default=None, help="Only test this profile name")
    args = parser.parse_args()

    songs = load_songs(str(PROJECT_ROOT / "data" / "songs.csv"))

    profiles_to_test = PROFILES
    if args.profile:
        if args.profile not in PROFILES:
            print(f"Unknown profile: {args.profile!r}. Available: {list(PROFILES)}")
            sys.exit(1)
        profiles_to_test = {args.profile: PROFILES[args.profile]}

    results = [
        verify_profile(name, prefs, songs, args.runs)
        for name, prefs in profiles_to_test.items()
    ]

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_violations = sum(len(r["size_violations"]) for r in results)
    low_consistency = [r for r in results if r["avg_consistency"] < 0.5]

    for r in results:
        flag = "OK" if r["avg_consistency"] >= 0.5 and not r["size_violations"] else "REVIEW"
        print(f"[{flag}] {r['name']}: consistency={r['avg_consistency']:.2f}, "
              f"size_violations={len(r['size_violations'])}")

    print()
    print(f"Total size violations across all profiles: {total_violations}")
    print(f"Profiles with low consistency (<0.5): {len(low_consistency)} / {len(results)}")

    if total_violations == 0 and not low_consistency:
        print("\nAll checks passed.")
    else:
        print("\nSome checks need review — see details above.")


if __name__ == "__main__":
    main()
