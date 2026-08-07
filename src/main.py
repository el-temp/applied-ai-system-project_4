"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import logging
import sys

from recommender import load_songs, recommend_songs, discover_songs_with_rag

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Three distinct user preference profiles, plus adversarial / edge case
# profiles designed to see if the scoring logic can be "tricked" or
# produces unexpected results.
PROFILES = {
    "High-Energy Pop": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.9,
        "likes_acoustic": False,
    },
    # Remaining profiles commented out to limit Gemini API usage.
    # Uncomment as needed.
    # "Chill Lofi": {
    #     "favorite_genre": "lofi",
    #    "favorite_mood": "chill",
    #     "target_energy": 0.3,
    #     "likes_acoustic": True,
    # },
    # "Deep Intense Rock": {
    #     "favorite_genre": "rock",
    #     "favorite_mood": "intense",
    #     "target_energy": 0.85,
    #     "likes_acoustic": False,
    # },
    # # Adversarial / edge case profiles
    # "Adversarial: High Energy + Sad Mood": {
    #     "favorite_genre": "pop",
    #     "favorite_mood": "sad",
    #     "target_energy": 0.9,
    #     "likes_acoustic": False,
    # },
    # "Adversarial: Nonexistent Genre": {
    #     "favorite_genre": "polka",
    #     "favorite_mood": "happy",
    #     "target_energy": 0.5,
    #     "likes_acoustic": False,
    # },
    # "Adversarial: Extreme Energy + Acoustic Conflict": {
    #     "favorite_genre": "metal",
    #     "favorite_mood": "angry",
    #     "target_energy": 1.0,
    #     "likes_acoustic": True,
    # },
}


def main() -> None:
    try:
        songs = load_songs("data/songs.csv")
    except FileNotFoundError:
        logger.error("Could not find data/songs.csv — run this script from the project root.")
        sys.exit(1)

    if not songs:
        logger.warning("No songs were loaded from data/songs.csv; nothing to recommend.")
        return

    for name, user_prefs in PROFILES.items():
        print("=" * 60)
        print(f"PROFILE: {name}")
        print(f"Preferences: {user_prefs}")
        print("=" * 60)

        recommendations = recommend_songs(user_prefs, songs, k=5)

        print("\nTop recommendations:\n")
        for rank, (song, score, reasons, confidence) in enumerate(recommendations, start=1):
            print(f"{rank}. {song['title']} by {song['artist']} — Score: {score:.2f} (confidence: {confidence:.0%})")
            for reason in reasons:
                print(f"   - {reason}")
            print()

        print("Discovering additional songs outside the catalog (RAG + web search)...")
        discovered = discover_songs_with_rag(user_prefs, songs)
        if discovered:
            print("\nYou might also like (not in our catalog):\n")
            for item in discovered:
                print(f"- {item.get('title')} by {item.get('artist')} (confidence: {item.get('confidence', 0):.0%})")
                print(f"   - {item.get('reason')}")
            print()
        else:
            print("(No additional songs discovered.)\n")


if __name__ == "__main__":
    main()
