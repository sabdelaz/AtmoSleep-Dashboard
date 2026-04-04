import streamlit as st
import pandas as pd
from pathlib import Path
import altair as alt

from utils.sleep_metrics import compute_night_metrics, minutes_to_hours

st.set_page_config(page_title="My Sleep Trends", layout="wide")

# ----------------------------
# background styling
# ----------------------------
st.markdown("""
<style>
.stApp {
    background:
    radial-gradient(1100px 520px at 15% 10%, rgba(47,111,237,0.22), transparent 60%),
    radial-gradient(950px 520px at 85% 15%, rgba(0,124,65,0.18), transparent 55%),
    linear-gradient(180deg, rgba(9,10,12,1) 0%, rgba(7,8,10,1) 100%);
}
.block-container { padding-top: 2.8rem; }

.card {
    border-radius: 18px;
    padding: 16px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# load data
# ----------------------------
HISTORY_DIR = Path("data/history")
files = sorted(HISTORY_DIR.glob("night_*.csv"))

rows = []

for f in files:
    try:
        night = compute_night_metrics(f)
        rows.append(night)
    except:
        continue

if len(rows) == 0:
    st.error("No valid data found")
    st.stop()

trend_df = pd.DataFrame(rows)
trend_df = trend_df.sort_values("night")

# ----------------------------
# helpers
# ----------------------------
def pretty_date(d):
    return pd.to_datetime(d).strftime("%b %d, %Y")

# ----------------------------
# best / worst
# ----------------------------
best_row = trend_df.loc[trend_df["sleep_score"].idxmax()]
worst_row = trend_df.loc[trend_df["sleep_score"].idxmin()]

best_label = pretty_date(best_row["night"])
worst_label = pretty_date(worst_row["night"])

# ----------------------------
# TITLE + BANNER (FIXED)
# ----------------------------
st.markdown(
    f"""
    <div class="card">
      <div style="opacity:.7;font-size:13px">AtmoSleep · My Sleep Trends</div>
      <div style="font-size:28px;font-weight:800">My Sleep Trends</div>
      <div style="opacity:.78;font-size:14px; margin-top:6px;">
        Showing the last {len(trend_df)} available night file(s)
      </div>

      <div style="display:flex; gap:14px; flex-wrap:wrap; margin-top:16px;">
        <div style="
            flex:1;
            min-width:220px;
            border-radius:14px;
            padding:12px 14px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.07);
        ">
          <div style="font-size:12px; opacity:0.7;">🏆 1st Place</div>
          <div style="font-size:18px; font-weight:800; margin-top:4px;">{best_label}</div>
          <div style="font-size:13px; opacity:0.82; margin-top:2px;">Sleep Score: {int(best_row['sleep_score'])}</div>
        </div>

        <div style="
            flex:1;
            min-width:220px;
            border-radius:14px;
            padding:12px 14px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.07);
        ">
          <div style="font-size:12px; opacity:0.7;">📉 Lowest Night</div>
          <div style="font-size:18px; font-weight:800; margin-top:4px;">{worst_label}</div>
          <div style="font-size:13px; opacity:0.82; margin-top:2px;">Sleep Score: {int(worst_row['sleep_score'])}</div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# KPIs
# ----------------------------
avg_score = trend_df["sleep_score"].mean()
avg_sleep = trend_df["total_sleep_min"].mean()
avg_dist = trend_df["disturbances"].mean()
avg_deep = trend_df["deep_pct"].mean()
avg_rem = trend_df["rem_pct"].mean()

c1, c2, c3, c4, c5 = st.columns(5)

c1.markdown(f"<div class='card'><div>Average Sleep Score</div><h2>{int(avg_score)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card'><div>Average Total Sleep</div><h2>{minutes_to_hours(avg_sleep)}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card'><div>Average Disturbances</div><h2>{round(avg_dist,1)}</h2></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='card'><div>Average Deep</div><h2>{round(avg_deep,1)}%</h2></div>", unsafe_allow_html=True)
c5.markdown(f"<div class='card'><div>Average REM</div><h2>{round(avg_rem,1)}%</h2></div>", unsafe_allow_html=True)

# ----------------------------
# SLEEP STAGES (FIRST)
# ----------------------------
stage_df = trend_df.melt(
    id_vars="night",
    value_vars=["deep_pct", "rem_pct", "light_pct", "awake_pct"],
    var_name="stage",
    value_name="percent"
)

stage_chart = alt.Chart(stage_df).mark_line(point=True).encode(
    x=alt.X("night:T", axis=alt.Axis(format="%b %d")),
    y="percent:Q",
    color="stage:N"
)

st.markdown("### Sleep Stages")
st.altair_chart(stage_chart, use_container_width=True)

# ----------------------------
# DISTURBANCES
# ----------------------------
dist_chart = alt.Chart(trend_df).mark_bar().encode(
    x=alt.X("night:T", axis=alt.Axis(format="%b %d")),
    y="disturbances:Q"
)

st.markdown("### Disturbances")
st.altair_chart(dist_chart, use_container_width=True)

# ----------------------------
# TOTAL SLEEP
# ----------------------------
sleep_chart = alt.Chart(trend_df).mark_line(point=True).encode(
    x=alt.X("night:T", axis=alt.Axis(format="%b %d")),
    y="total_sleep_min:Q"
)

st.markdown("### Total Sleep")
st.altair_chart(sleep_chart, use_container_width=True)

# ----------------------------
# SLEEP SCORE
# ----------------------------
score_chart = alt.Chart(trend_df).mark_line(point=True).encode(
    x=alt.X("night:T", axis=alt.Axis(format="%b %d")),
    y="sleep_score:Q"
)

st.markdown("### Sleep Score")
st.altair_chart(score_chart, use_container_width=True)

# ----------------------------
# TABLE (fixed wording)
# ----------------------------
table = trend_df.copy()
table["total_sleep"] = table["total_sleep_min"].apply(minutes_to_hours)

table = table.rename(columns={
    "sleep_score": "Sleep Score",
    "total_sleep": "Total Sleep",
    "disturbances": "Disturbances",
    "deep_pct": "Deep %",
    "rem_pct": "REM %",
    "light_pct": "Light %",
    "awake_pct": "Awake %"
})

st.markdown("### Summary Table")
st.dataframe(table[[
    "night",
    "Sleep Score",
    "Total Sleep",
    "Disturbances",
    "Deep %",
    "REM %",
    "Light %",
    "Awake %"
]])
