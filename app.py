import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google import genai
import time

st.set_page_config(
    page_title="AI Playlist Roaster",
    page_icon="🔥",
    layout="centered",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Anton&family=Space+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] { font-family: 'Space Mono', monospace; background: #000; color: #fff; }
  h1, h2, h3 { font-family: 'Anton', sans-serif; }

  .top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 48px;
    padding-bottom: 16px;
    border-bottom: 1px solid #111;
  }
  .brand { font-size: 0.7rem; letter-spacing: 3px; text-transform: uppercase; color: #1DB954; }
  .year { font-size: 0.65rem; color: #333; letter-spacing: 2px; text-transform: uppercase; }

  .page-title {
    font-family: 'Anton', sans-serif;
    font-size: 4rem;
    text-transform: uppercase;
    letter-spacing: -2px;
    border-bottom: 4px solid #1DB954;
    padding-bottom: 16px;
    margin-bottom: 8px;
    line-height: 1;
    color: #fff;
  }
  .page-sub {
    font-size: 0.7rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #1DB954;
    margin-bottom: 48px;
  }

  .track-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid #111;
    transition: all 0.15s;
  }
  .track-item:hover { padding-left: 8px; }
  .track-num { font-size: 0.7rem; color: #333; min-width: 28px; }
  .track-dot { width: 6px; height: 6px; border-radius: 50%; background: #1DB954; opacity: 0; transition: opacity 0.15s; }
  .track-item:hover .track-dot { opacity: 1; }
  .track-name { font-size: 0.9rem; font-weight: 700; color: #fff; }
  .track-artist { font-size: 0.75rem; color: #555; margin-top: 2px; }

  .roast-box {
    border: 3px solid #1DB954;
    padding: 28px;
    margin-top: 24px;
    font-size: 0.9rem;
    line-height: 1.8;
    color: #ccc;
    box-shadow: 0 0 30px rgba(29,185,84,0.1);
  }
  .roast-label {
    font-family: 'Anton', sans-serif;
    font-size: 1.5rem;
    letter-spacing: 2px;
    color: #1DB954;
    margin-bottom: 16px;
  }

  .playlist-box {
    border: 3px solid #fff;
    padding: 28px;
    margin-top: 24px;
  }
  .playlist-label {
    font-family: 'Anton', sans-serif;
    font-size: 1.5rem;
    letter-spacing: 2px;
    color: #fff;
    margin-bottom: 20px;
  }
  .playlist-track {
    display: flex;
    gap: 16px;
    padding: 10px 0;
    border-bottom: 1px solid #111;
    font-size: 0.82rem;
  }
  .playlist-track:last-child { border-bottom: none; }
  .playlist-num { color: #333; min-width: 28px; }
  .playlist-name { color: #fff; font-weight: 700; flex: 1; }
  .playlist-artist { color: #555; }

  .footer {
    margin-top: 80px;
    padding-top: 24px;
    border-top: 1px solid #111;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.65rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #333;
  }
  .footer span { color: #1DB954; }

  div[data-testid="stButton"] button {
    background: #1DB954 !important;
    color: #000 !important;
    font-family: 'Anton', sans-serif !important;
    font-size: 1.1rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border: none !important;
    padding: 12px 32px !important;
    border-radius: 0 !important;
    transition: all 0.15s !important;
  }
  div[data-testid="stButton"] button:hover {
    background: #fff !important;
    color: #000 !important;
  }
  div[data-testid="stButton"] button[kind="secondary"] {
    background: #000 !important;
    color: #fff !important;
    border: 1px solid #333 !important;
  }
  div[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #fff !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Credentials ───────────────────────────────────────────────────────────────
CLIENT_ID     = st.secrets["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]
REDIRECT_URI  = st.secrets["SPOTIPY_REDIRECT_URI"]
GEMINI_KEY    = st.secrets["GEMINI_API_KEY"]

SCOPE = "user-top-read"

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=None,
        show_dialog=True,
    )

def handle_callback():
    params = st.query_params
    if "code" in params and "token_info" not in st.session_state:
        code = params["code"]
        sp_oauth = get_spotify_oauth()
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)
            st.session_state["token_info"] = token_info
        except Exception as e:
            st.error(f"Spotify auth failed: {e}")
        st.query_params.clear()
        st.rerun()

def get_valid_token():
    sp_oauth = get_spotify_oauth()
    token_info = st.session_state.get("token_info")
    if not token_info:
        return None
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        st.session_state["token_info"] = token_info
    return token_info["access_token"]

def generate_roast(track_names: list[str]) -> str:
    client = genai.Client(api_key=GEMINI_KEY)
    track_list = "\n".join(f"- {t}" for t in track_names)
    prompt = (
        "You are a savage but hilarious music critic who only speaks in Gen-Z slang. "
        "Roast the following person's top 10 most-played Spotify tracks in exactly 3-4 sentences. "
        "Be brutally funny, use words like 'no cap', 'slay', 'mid', 'it's giving', 'based', 'rent free', 'understood the assignment' etc. "
        "Do NOT be mean about the artists themselves, only about what listening to them says about the person's personality.\n\n"
        f"Their top tracks:\n{track_list}"
    )
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip()

def generate_playlist(track_names: list[str]) -> str:
    client = genai.Client(api_key=GEMINI_KEY)
    track_list = "\n".join(f"- {t}" for t in track_names)
    prompt = (
        "Based on these top tracks, suggest exactly 15 songs with the same vibe. "
        "Format your response EXACTLY like this, one per line, nothing else:\n"
        "Song Name|Artist Name\n\n"
        "Do not include numbering, bullet points, headers, or any extra text. Just 15 lines in that format.\n\n"
        f"Top tracks:\n{track_list}"
    )
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip()

# ═══════════════════════════════════════════════════════════════════════════════
handle_callback()

# Top bar
st.markdown("""
<div class="top-bar">
  <div class="brand">Spotify x Han Han</div>
  <div class="year">2026</div>
</div>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="page-title">AI Playlist Roaster</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Your taste, destroyed by AI</div>', unsafe_allow_html=True)

# ── Not logged in ─────────────────────────────────────────────────────────────
if "token_info" not in st.session_state:
    st.markdown("#### Connect your Spotify to get started")
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    st.link_button("Login with Spotify", auth_url, type="primary")
    st.caption("We only read your top tracks. Nothing is stored.")

# ── Logged in ─────────────────────────────────────────────────────────────────
else:
    access_token = get_valid_token()
    if not access_token:
        st.error("Session expired. Please log in again.")
        del st.session_state["token_info"]
        st.rerun()

    sp = spotipy.Spotify(auth=access_token)

    if "top_tracks" not in st.session_state:
        with st.spinner("Fetching your listening history..."):
            results = sp.current_user_top_tracks(limit=10, time_range="short_term")
            st.session_state["top_tracks"] = [
                f"{item['name']} — {item['artists'][0]['name']}"
                for item in results["items"]
            ]
        st.session_state.pop("roast", None)
        st.session_state.pop("playlist", None)

    top_tracks = st.session_state["top_tracks"]

    # Display tracks
    st.markdown("#### Your Top 10 Tracks")
    track_html = '<div style="border-top: 2px solid #1a1a1a;">'
    for i, track in enumerate(top_tracks, 1):
        parts = track.split(" — ")
        name = parts[0] if len(parts) > 0 else track
        artist = parts[1] if len(parts) > 1 else ""
        track_html += f'''
        <div class="track-item">
          <span class="track-num">{str(i).zfill(2)}</span>
          <div class="track-dot"></div>
          <div>
            <div class="track-name">{name}</div>
            <div class="track-artist">{artist}</div>
          </div>
        </div>'''
    track_html += '</div>'
    st.markdown(track_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        roast_btn = st.button("Roast My Taste", type="primary", disabled=not top_tracks)
    with col2:
        playlist_btn = st.button("Build My Playlist", type="primary", disabled=not top_tracks)
    with col3:
        if st.button("Log out", type="secondary"):
            st.session_state.clear()
            st.rerun()

    # Generate roast
    if roast_btn:
        with st.spinner("Judging your questionable life choices..."):
            time.sleep(0.5)
            roast = generate_roast(top_tracks)
            st.session_state["roast"] = roast

    # Generate playlist
    if playlist_btn:
        with st.spinner("Building your playlist..."):
            playlist_raw = generate_playlist(top_tracks)
            st.session_state["playlist"] = playlist_raw

    # Show roast
    if "roast" in st.session_state:
        roast_html = f'''
        <div class="roast-box">
          <div class="roast-label">The Verdict</div>
          {st.session_state["roast"]}
        </div>'''
        st.markdown(roast_html, unsafe_allow_html=True)

    # Show playlist
    if "playlist" in st.session_state:
        lines = [l for l in st.session_state["playlist"].split("\n") if "|" in l]
        playlist_html = '<div class="playlist-box"><div class="playlist-label">Your Vibe Playlist</div>'
        for i, line in enumerate(lines[:15], 1):
            parts = line.split("|")
            song = parts[0].strip() if len(parts) > 0 else line
            artist = parts[1].strip() if len(parts) > 1 else ""
            playlist_html += f'''
            <div class="playlist-track">
              <span class="playlist-num">{str(i).zfill(2)}</span>
              <span class="playlist-name">{song}</span>
              <span class="playlist-artist">{artist}</span>
            </div>'''
        playlist_html += '</div>'
        st.markdown(playlist_html, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
  <div>made by <span>hhan</span></div>
  <div>AI Playlist Roaster</div>
</div>
""", unsafe_allow_html=True)
