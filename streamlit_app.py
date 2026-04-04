import streamlit as st
from pathlib import Path

# Basic Streamlit page setup (title & wide layout for a dashboard feel)
st.set_page_config(page_title="AtmoSleep", layout="wide", initial_sidebar_state="collapsed")

# this is for styling of the page

# streamlit allows injecting CSS using st.markdown + unsafe HTML

st.markdown(
    """
    <style>
      /* App background */
      .stApp {
        background:
          radial-gradient(1100px 520px at 15% 10%, rgba(47,111,237,0.22), transparent 60%),
          radial-gradient(950px 520px at 85% 15%, rgba(0,124,65,0.18), transparent 55%),
          radial-gradient(900px 520px at 50% 85%, rgba(255,255,255,0.06), transparent 60%),
          linear-gradient(180deg, rgba(9,10,12,1) 0%, rgba(7,8,10,1) 100%);
      }

      /* Small top padding so content doesn't look glued to the edge */
      .block-container { padding-top: 2.8rem; }

      /* Top header bar */
      .topbar {
        position: sticky;
        top: 0;
        z-index: 999;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.03);
        border-radius: 18px;
        padding: 12px 14px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        backdrop-filter: blur(10px);
      }

      /* Left-side branding text in the header */
      .brandTitle { font-size: 20px; font-weight: 900; letter-spacing: -0.3px; margin: 0; }
      .brandSub { opacity: 0.78; font-size: 13px; margin-top: 2px; }

      /* Right-side university label */
      .uaText { font-weight: 850; font-size: 13px; letter-spacing: -0.2px; color: #007C41; text-align: right; }
      .uaSub { opacity: 0.72; font-size: 11px; text-align: right; margin-top: 1px; }

      /* Simple animated dots in the middle of the header */
      .pulseWrap { display:flex; justify-content:center; align-items:center; gap:6px; }
      .dot {
        width: 8px; height: 8px; border-radius: 999px;
        background: rgba(47,111,237,0.80);
        animation: blink 1.6s ease-in-out infinite;
      }
      .dot:nth-child(2){ animation-delay: .2s; }
      .dot:nth-child(3){ animation-delay: .4s; }
      @keyframes blink {
        0% { transform: scale(0.85); opacity: 0.35; }
        50% { transform: scale(1.25); opacity: 1.0; }
        100% { transform: scale(0.85); opacity: 0.35; }
      }

      /*
        Spacer used to place the “homepage pill” around mid-screen on load.
        Adjust height if you want the pill higher/lower.
      */
      .midSpacer {
        height: 32vh;
      }

      /*
        Wrapper for the pill. The bottom margin is intentionally large here
        to create space before the main hero title/buttons.
      */
      .titlePillWrap {
        width: min(1040px, 94vw);
        margin: 0 auto 360px auto;
        display: flex;
        justify-content: center;
      }

      /* The pill itself (glassmorphism style card) */
      .titlePill {
        width: min(980px, 92vw);
        border-radius: 26px;
        padding: 18px 22px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.03);
        box-shadow: 0 14px 40px rgba(0,0,0,0.25);
        backdrop-filter: blur(10px);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
      }

      /* Pill text styles */
      .pillTitle { font-size: 18px; font-weight: 950; letter-spacing: -0.3px; margin: 0; opacity: 0.95; }
      .pillSub { margin-top: 6px; font-size: 12px; opacity: 0.70; }

      /* “Scroll ↓” area on the right side of the pill */
      .pillRight { display: flex; align-items: center; gap: 10px; opacity: 0.75; font-size: 12px; white-space: nowrap; }

      /* Small scroll arrow animation */
      .scrollHint {
        font-weight: 900;
        opacity: 0.7;
        font-size: 18px;
        animation: bob 1.4s ease-in-out infinite;
      }
      @keyframes bob {
        0%   { transform: translateY(0px); opacity: 0.60; }
        50%  { transform: translateY(3px); opacity: 1.0; }
        100% { transform: translateY(0px); opacity: 0.60; }
      }

      /* Main content width control (keeps everything centered and readable) */
      .heroInner { width: min(1040px, 94vw); margin: 0 auto; }

      /* Hero title/subtitle */
      .heroTitle { font-size: 44px; font-weight: 950; letter-spacing: -0.7px; margin: 0; }
      .heroSub { opacity: 0.78; margin-top: 8px; font-size: 14px; line-height: 1.35; }

      /* Button styling (Streamlit renders buttons with its own structure) */
      div.stButton > button {
        width: 100%;
        border-radius: 16px !important;
        padding: 16px 14px !important;
        font-weight: 800 !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        background: rgba(255,255,255,0.05) !important;
        transition: transform .08s ease, border-color .08s ease;
      }
      div.stButton > button:hover { transform: translateY(-1px); border-color: rgba(255,255,255,0.26) !important; }
      .btnHint { opacity: 0.70; font-size: 12px; margin-top: 6px; }

      /* Highlight section (cards) */
      .gridTitle { font-size: 18px; font-weight: 900; letter-spacing: -0.2px; margin-top: 6px; margin-bottom: 10px; }
      .tile {
        border-radius: 20px;
        padding: 18px 16px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.03);
        box-shadow: 0 10px 30px rgba(0,0,0,0.20);
        backdrop-filter: blur(10px);
      }
      .tileKicker { font-size: 12px; opacity: 0.70; margin-bottom: 6px; }
      .tileHead { font-size: 16px; font-weight: 900; margin: 0; }
      .tileBody { font-size: 13px; opacity: 0.78; margin-top: 6px; line-height: 1.35; }
      .tileMeta { font-size: 12px; opacity: 0.65; margin-top: 10px; }

      /* Footer label */
      .footer { opacity: 0.55; text-align: center; font-size: 12px; margin-top: 18px; margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# top bar
# -------------------------
st.markdown('<div class="topbar">', unsafe_allow_html=True)

left, mid, right = st.columns([2, 1, 2], vertical_alignment="center")

with left:
    st.markdown('<div class="brandTitle">AtmoSleep</div>', unsafe_allow_html=True)
    st.markdown('<div class="brandSub">Home</div>', unsafe_allow_html=True)

with mid:
    st.markdown(
        '<div class="pulseWrap"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown('<div class="uaText">University of Alberta</div>', unsafe_allow_html=True)
    st.markdown('<div class="uaSub">Faculty of Engineering</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Spacing
# -------------------------

# Push content down so the pill lands around mid-screen at page load
st.markdown('<div class="midSpacer"></div>', unsafe_allow_html=True)

# Landing pill: quick message + visual “scroll down” hint
st.markdown(
    """
    <div class="titlePillWrap">
      <div class="titlePill">
        <div>
          <div class="pillTitle">My AtmoSleep Homepage</div>
          <div class="pillSub">Scroll down for highlights and quick shortcuts.</div>
        </div>
        <div class="pillRight">
          <span>Scroll</span>
          <span class="scrollHint">↓</span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Main content
# -------------------------
st.markdown('<div class="heroInner">', unsafe_allow_html=True)

# Main title 
st.markdown(
    """
    <div class="heroTitle">Sleep + Environment: All in one view!</div>
    """,
    unsafe_allow_html=True,
)

# navigation buttons (these jump to the other pages)
c1, c2, c3 = st.columns(3, gap="large")

with c1:
    if st.button("🔴 Live Sensor Feed", use_container_width=True):
        st.switch_page("pages/1_Live_Sensor_Feed.py")
    st.markdown('<div class="btnHint">Live environment readings in real time.</div>', unsafe_allow_html=True)

with c2:
    if st.button("🌙 Last Night", use_container_width=True):
        st.switch_page("pages/2_Last_Night.py")
    st.markdown('<div class="btnHint">Stages, disturbances, and key takeaways.</div>', unsafe_allow_html=True)

with c3:
    # Only show the Trends button if that page exists
    if Path("pages/3_Trends.py").exists():
        if st.button("📈 Trends", use_container_width=True):
            st.switch_page("pages/3_Trends.py")
        st.markdown('<div class="btnHint">Patterns across the week.</div>', unsafe_allow_html=True)
    else:
        st.button("📈 Trends", use_container_width=True, disabled=True)
        st.markdown('<div class="btnHint">Coming soon.</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Highlights
# -------------------------
st.write("")
st.write("")

st.markdown(
    """
    <div class="heroTitle">
      <div class="gridTitle" style="font-size:15px; margin-bottom:10px;">Highlights</div>
    </div>
    """,
    unsafe_allow_html=True,
)
a, b, c, d = st.columns(4, gap="large")

with a:
    st.markdown(
        """
        <div class="tile">
          <div class="tileKicker">Last Night</div>
          <div class="tileHead">Sleep stages</div>
          <div class="tileBody">Deep / Rem / Light / Awake timeline with graphs & disturbances.</div>
          <div class="tileMeta">Open “Last Night” for details</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with b:
    st.markdown(
        """
        <div class="tile">
          <div class="tileKicker">Environment</div>
          <div class="tileHead">Comfort trends</div>
          <div class="tileBody">Temperature, humidity, light, and noise patterns that shape sleep quality.</div>
          <div class="tileMeta">Seen across “Last Night” and “Trends”</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c:
    st.markdown(
        """
        <div class="tile"> 
          <div class="tileKicker">Insights</div>
          <div class="tileHead">Sleep notes</div>
          <div class="tileBody">Clear summaries and key moments that explain your night at a glance.</div>
          <div class="tileMeta">Future Work</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d:
    st.markdown(
        """
        <div class="tile">
          <div class="tileKicker">Trends</div>
          <div class="tileHead">Weekly patterns</div>
          <div class="tileBody">A view of progress over time, with what’s improving and what’s not.</div>
          <div class="tileMeta">Open “Trends”</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Footer 
st.markdown('<div class="footer">University of Alberta</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">Department of Electrical & Computer Engineering</div>', unsafe_allow_html=True)

