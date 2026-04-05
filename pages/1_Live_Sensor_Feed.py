# live sensor page
import streamlit as st
import pandas as pd
from pathlib import Path
import time

st.set_page_config(page_title="Live Sensor Feed", layout="wide", initial_sidebar_state="collapsed")

# background design

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(1100px 520px at 15% 10%, rgba(47,111,237,0.22), transparent 60%),
          radial-gradient(950px 520px at 85% 15%, rgba(0,124,65,0.18), transparent 55%),
          radial-gradient(900px 520px at 50% 85%, rgba(255,255,255,0.06), transparent 60%),
          linear-gradient(180deg, rgba(9,10,12,1) 0%, rgba(7,8,10,1) 100%);
      }
      .block-container { padding-top: 2.8rem; }

      .card {
        border-radius: 16px;
        padding: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }
      .kpi-title { font-size: 12px; opacity: 0.7; }
      .kpi-value { font-size: 24px; font-weight: 800; }
      .meta { opacity: 0.80; font-size: 13px; }
      .meta b { color: #2DBE7F; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_FILE = Path("data/live/live.csv")  # receiver writes here

st.title("Live Sensor Feed")

col1, col2 = st.columns([3, 1])
with col1:
    refresh_seconds = st.slider("Auto refresh (seconds)", 0, 10, 2, 1)
with col2:
    if st.button("Refresh now"):
        st.rerun()

# -------------------------
# Load CSV (take first 6 columns only)
# -------------------------
if not DATA_FILE.exists():
    st.warning("Page has been locked. It was being used for testing purposes. Page can be unlocked and viewed as per user's request...")
    st.stop()

raw = pd.read_csv(DATA_FILE, header=None, on_bad_lines="skip")

if raw.shape[1] < 6:
    st.error("live.csv does not have enough  yet (need at least 6).")
    st.stop()

df = raw.iloc[:, :6].copy()
df.columns = ["timestamp", "motion", "temp_c", "humidity_pct", "light_lux", "noise_dbfs"]

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

latest = df.iloc[-1]

# -------------------------
# Live numbers
# -------------------------
m0, m1, m2, m3, m4, m5 = st.columns([1.6, 1, 1, 1, 1, 1])

def kpi(col, title, value):
    col.markdown(
        f"""
        <div class="card">
          <div class="kpi-title">{title}</div>
          <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

kpi(m0, "Timestamp", latest["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
kpi(m1, "Temperature", f"{latest['temp_c']:.1f} °C")
kpi(m2, "Humidity", f"{latest['humidity_pct']:.1f} %")
kpi(m3, "Noise", f"{latest['noise_dbfs']:.1f} dBFS")
kpi(m4, "Light", f"{latest['light_lux']:.0f} lux")
motion = int(latest["motion"])
kpi(m5, "Motion", ("🟩" if motion == 1 else "🛑"))
st.write("")


with st.expander("Show last 10 readings"): # to debug later on 
    view = df.tail(10).copy()
    view["timestamp"] = view["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(view, use_container_width=True)

if refresh_seconds > 0:  # Simple auto refresh

    time.sleep(refresh_seconds)
    st.rerun()
