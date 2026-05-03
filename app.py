import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google import genai
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🔥 AI Playlist Roaster",
    page_icon="🔥",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Space Mono', monospace; }
  h1 { font-family: 'Syne', sans-serif; font-weight: 800; }

  .roast-box {
    background: linear-gradient(135deg, #1a0a00 0%, #2d1200 100%);
    border: 2px solid #ff4500;
    border-radius: 12px;
    padding: 24px 28px;
    margin-top: 16px;
    color: #ff9966;
    font-size: 1.05rem;
    line-height: 1.7;
    box-shadow: 0 0 30px rgba(255,69,0,0.3);
  }
  .track-item {
    background: #111;
    border-left: 3px solid #1DB954;
    padding: 8px 14px;
    border-radius: 4px;
    margin: 6px 0;
    font-size: 0.88rem;
    color: #ccc;
  }
  .badge {
    display: inline-block;
    background: #1DB954;
    color: #000;
    font-weight: 700;
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 20px;
    margin-right: 8px;
  }
</style>
""", unsafe_allow_html=True)

# ── Credentials from st.secrets ───────────────────────────────────────────────
CLIENT_ID     = st.secrets["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]
REDIRECT_URI  = st.secrets["SPOTIPY_REDIRECT_URI"]
GEMINI_KEY    = st.secrets["GEMINI_API_KEY"]

SCOPE = "user-top-read"

# ── Spotify OAuth helper ──────────────────────────────────────────────────────
def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=None,
        show_dialog=True,
    )

# ── Handle the OAuth callback code in the URL ─────────────────────────────────
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

# ── Token refresh helper ──────────────────────────────────────────────────────
def get_valid_token():
    sp_oauth = get_spotify_oauth()
    token_info = st.session_state.get("token_info")
    if not token_info:
        return None
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        st.session_state["token_info"] = token_info
    return token_info["access_token"]

# ── Gemini roast generator ────────────────────────────────────────────────────
def generate_roast(track_names: list[str]) -> str:
    client = genai.Client(api_key=GEMINI_KEY)
    track_list = "\n".join(f"- {t}" for t in track_names)
    prompt = (
        "You are a savage but hilarious music critic who only speaks in Gen-Z slang. "
        "Roast the following person's top 10 most-played Spotify tracks in exactly 3-4 sentences. "
        "Be brutally funny, use words like 'no cap', 'slay', 'mid', 'it's giving', 'based', 'rent free', 'understood the assignment' etc. "
        "Do NOT be mean about the artists themselves, only about what listening to them says about the person's personality and life choices.\n\n"
        f"Their top tracks:\n{track_list}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
handle_callback()

st.title("🔥 AI Playlist Roaster")
st.markdown("*Let Gemini AI drag your music taste — no cap.*")
st.divider()

# ── Not logged in ─────────────────────────────────────────────────────────────
if "token_info" not in st.session_state:
    st.markdown("### Step 1 — Connect Spotify")
    st.markdown(
        "We'll look at your **top 10 most-played tracks** (last 4 weeks) "
        "and write you a personalised roast. We don't store anything. 🤝"
    )

    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()

    st.link_button("🎵  Login with Spotify", auth_url, type="primary")
    st.caption("You'll be redirected back here automatically after authorising.")

# ── Logged in ─────────────────────────────────────────────────────────────────
else:
    access_token = get_valid_token()
    if not access_token:
        st.error("Session expired. Please log in again.")
        del st.session_state["token_info"]
        st.rerun()

    sp = spotipy.Spotify(auth=access_token)

    # Fetch top tracks once per session
    if "top_tracks" not in st.session_state:
        with st.spinner("Fetching your listening history…"):
            results = sp.current_user_top_tracks(limit=10, time_range="short_term")
            st.session_state["top_tracks"] = [
                f"{item['name']} — {item['artists'][0]['name']}"
                for item in results["items"]
            ]
        st.session_state.pop("roast", None)

    top_tracks = st.session_state["top_tracks"]

    # Display tracks
    st.markdown("### 🎧 Your Top 10 Tracks (last 4 weeks)")
    if top_tracks:
        for i, track in enumerate(top_tracks, 1):
            st.markdown(
                f'<div class="track-item"><span class="badge">{i}</span>{track}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "Hmm, Spotify says you haven't listened to much recently. "
            "Try changing the time range or listen to more music! 🎶"
        )

    st.divider()

    # Roast button
    col1, col2 = st.columns([2, 1])
    with col1:
        roast_btn = st.button("🔥 Roast My Taste!", type="primary", disabled=not top_tracks)
    with col2:
        if st.button("🚪 Log out"):
            st.session_state.clear()
            st.rerun()

    if roast_btn:
        with st.spinner("Judging your questionable life choices… 👀"):
            time.sleep(0.5)
            roast = generate_roast(top_tracks)
            st.session_state["roast"] = roast

    if "roast" in st.session_state:
        st.markdown("### 💀 The Verdict")
        st.markdown(
            f'<div class="roast-box">{st.session_state["roast"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Disclaimer: this roast was AI-generated and meant purely for laughs. No cap. 🙏")