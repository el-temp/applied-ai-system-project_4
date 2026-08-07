import streamlit as st
from typing import List, Dict

from recommender import load_songs, recommend_songs, discover_songs_with_rag


st.set_page_config(page_title="Custom Profile Recommender", layout="centered")

# Neon/Neo CSS for a youthful, energetic aesthetic
st.markdown(
    """
    <style>
    :root{
      --bg-1: #0b0f1a; /* deep space */
      --neon-pink: #ff2d95;
      --neon-cyan: #00f0ff;
      --neon-purple: #8a2be2;
      --card-bg: rgba(10,12,20,0.55);
      --muted: #9fb3c8;
      --bright-blue: #00aaff; /* bright blue for important text/buttons */
    }

    /* animated gradient background */
    html, body, .stApp {
      height: 100%;
      background: radial-gradient(1200px 600px at 10% 10%, rgba(0,240,255,0.06), transparent),
                  radial-gradient(1000px 500px at 90% 90%, rgba(255,45,149,0.06), transparent),
                  linear-gradient(180deg, var(--bg-1) 0%, #04040a 100%);
      color: #eaf6ff;
      font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    .block-container {
      padding-top: 2.5rem;
      padding-left: 2rem;
      padding-right: 2rem;
    }

    /* Neon header */
    .neo-header{
      text-align: center;
      padding: 22px 12px;
      border-radius: 14px;
      margin-bottom: 16px;
      background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      box-shadow: 0 8px 40px rgba(10,12,20,0.6), 0 0 18px rgba(0,240,255,0.035) inset;
      border: 1px solid rgba(255,255,255,0.04);
    }

    .neo-header h1{
      margin: 0;
      font-size: 32px;
      letter-spacing: 0.6px;
      background: linear-gradient(90deg, var(--neon-cyan), var(--neon-pink));
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-shadow: 0 0 18px rgba(138,43,226,0.08);
    }

    .tagline{
      color: var(--muted);
      margin-top: 6px;
      font-weight: 500;
    }

    /* Cards with neon outlines */
    .card {
      background: var(--card-bg);
      border-radius: 14px;
      padding: 18px;
      border: 1px solid rgba(255,255,255,0.03);
      box-shadow: 0 10px 30px rgba(2,6,23,0.7), 0 0 18px rgba(0,240,255,0.02);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .card:hover{ transform: translateY(-4px); box-shadow: 0 22px 40px rgba(2,6,23,0.75), 0 0 30px rgba(255,45,149,0.06);
    }

    /* Muted text */
    .muted { color: var(--muted); }

    /* Streamlit button glow */
    .stButton>button {
      background: linear-gradient(90deg, rgba(0,240,255,0.12), rgba(255,45,149,0.12));
      color: #fff;
      border-radius: 10px;
      padding: 8px 14px;
      border: 1px solid rgba(255,255,255,0.06);
      box-shadow: 0 6px 20px rgba(138,43,226,0.06);
    }
    .stButton>button:hover{ box-shadow: 0 10px 30px rgba(138,43,226,0.12), 0 0 30px rgba(0,240,255,0.06); transform: translateY(-2px); }

    /* Make the form submit button text bright blue for visibility */
    /* Make the form submit button text black (user request) */
    .stForm .stButton>button { color: #000000 !important; font-weight:700 }
    .stForm .stButton>button:hover { text-shadow: none }

    /* Expander styling */
    .stExpander {
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.03);
      background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.005));
    }

    /* Small responsive tweaks */
    @media (max-width: 640px){
      .neo-header h1{ font-size: 24px }
      .block-container { padding-left: 12px; padding-right: 12px }
    }
    </style>

    <div class="neo-header">
      <h1>⚡ Create your vibe</h1>
      <div class="tagline">Quickly build a profile and get neon-ready song recs</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Small spacer to visually separate header from form
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# Load catalog
try:
    songs = load_songs("data/songs.csv")
except FileNotFoundError:
    st.error("Could not find data/songs.csv. Run this from the project root or place a CSV at data/songs.csv.")
    st.stop()

if not songs:
    st.warning("Song catalog is empty — add rows to data/songs.csv to get recommendations.")

# Derive options for dropdowns
genres = sorted({s.get("genre", "unknown") for s in songs if s.get("genre")})
moods = sorted({s.get("mood", "neutral") for s in songs if s.get("mood")})

if not genres:
    genres = ["pop", "rock", "lofi", "electronic"]
if not moods:
    moods = ["happy", "sad", "chill", "intense"]

# Profile form
with st.form(key="profile_form"):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        favorite_genre = st.selectbox("Favorite genre", options=genres)
        likes_acoustic_choice = st.selectbox("Likes acoustic?", options=["Yes", "No"], index=1)
        likes_acoustic = likes_acoustic_choice == "Yes"
    with col2:
        favorite_mood = st.selectbox("Favorite mood", options=moods)
        target_energy = st.slider("Target energy", min_value=0.0, max_value=1.0, value=0.5, step=0.01)
    st.markdown("</div>", unsafe_allow_html=True)

    submitted = st.form_submit_button("Create profile & get recommendations")

if submitted:
    user_profile: Dict = {
        "favorite_genre": favorite_genre,
        "favorite_mood": favorite_mood,
        "target_energy": float(target_energy),
        "likes_acoustic": bool(likes_acoustic),
    }

    st.markdown("""
    <div class='card'>
      <h3 style='margin:0'>Profile summary</h3>
      <div class='muted'>A quick glance at your preferences</div>
    </div>
    """, unsafe_allow_html=True)

    st.write(user_profile)

    # Get recommendations
    results = recommend_songs(user_profile, songs, k=5)

    st.markdown("<br/>", unsafe_allow_html=True)

    st.markdown("""
    <div class='card'>
      <h3 style='margin:0'>Top recommendations</h3>
      <div class='muted'>Click each item to see reasons and confidence</div>
    </div>
    """, unsafe_allow_html=True)

    if not results:
        st.info("No recommendations could be produced for this profile.")
    else:
        for rank, (song, score, reasons, confidence) in enumerate(results, start=1):
            with st.expander(f"{rank}. {song.get('title')} — {song.get('artist')} (score: {score:.2f})"):
                st.write({
                    "Title": song.get("title"),
                    "Artist": song.get("artist"),
                    "Genre": song.get("genre"),
                    "Mood": song.get("mood"),
                    "Energy": song.get("energy"),
                    "Acousticness": song.get("acousticness"),
                })
                st.write("Reasons:")
                for r in reasons:
                    st.markdown(f"- {r}")
                st.write(f"Confidence: {confidence:.0%}")
    # Offer to discover additional songs via RAG (Gemini)
    st.markdown("<hr/>", unsafe_allow_html=True)
    if st.button("Discover additional songs (RAG)"):
        with st.spinner("Discovering songs outside the catalog..."):
            discovered = discover_songs_with_rag(user_profile, songs)
        if discovered:
            st.success(f"Found {len(discovered)} item(s)")
            for item in discovered:
                st.write(item)
        else:
            st.info("No additional songs discovered or the discovery step failed.")

# Small footer
st.markdown("""
<div style='text-align:center; margin-top:18px; color:#9fb3c8'>
  Built with Streamlit — a minimal demo UI for generating taste profiles and recommendations
</div>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    # Streamlit runs the script top-to-bottom; nothing to start explicitly here.
    pass
