import streamlit as st
import altair as alt
import pandas as pd
from pathlib import Path

from utils.sleep_metrics import (
    compute_night_detail_cached,
    list_csv_files,
    minutes_to_hours,
)

st.set_page_config(page_title="Last Night", layout="wide", initial_sidebar_state="collapsed")

# background
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
      .kpi-value { font-size: 22px; font-weight: 800; }
    </style>
    """,
    unsafe_allow_html=True,
)

HISTORY_DIR = Path("data/history")


def format_file_stem_for_display(path_obj):
    raw = path_obj.stem
    dt = pd.to_datetime(raw, format="%Y%m%d", errors="coerce")
    if pd.isna(dt):
        return raw
    return dt.strftime("%Y-%m-%d")


# ----------------------------
#  for visuals and design
# ----------------------------
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


def mini_stage(col, title, value, text):
    col.markdown(
        f"""
        <div class="card">
          <div style="font-size:12px; opacity:0.85; margin-bottom:4px; font-weight:700; color:{text};">{title}</div>
          <div style="font-size:22px; font-weight:800; color:{text};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_legend(items):
    bits = []

    for kind, label, color in items:
        if kind == "dot":
            bits.append(
                f'<div style="display:flex; align-items:center; gap:6px;">'
                f'<div style="width:10px; height:10px; border-radius:50%; background:{color};"></div>'
                f'<span style="font-size:13px; opacity:0.8;">{label}</span>'
                f'</div>'
            )
        elif kind == "rule":
            bits.append(
                f'<div style="display:flex; align-items:center; gap:6px;">'
                f'<div style="width:2px; height:14px; background:{color};"></div>'
                f'<span style="font-size:13px; opacity:0.8;">{label}</span>'
                f'</div>'
            )

    html = (
        '<div style="display:flex; align-items:center; gap:20px; margin-bottom:10px; flex-wrap:wrap;">'
        + "".join(bits) +
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def build_event_text(row):
    items = []

    if row["temp_event"] == 1:
        items.append(f"Temperature {'Spike' if row['temp_diff'] > 0 else 'Drop'} ({row['temp_diff']:+.2f} °C)")

    if row["humidity_event"] == 1:
        items.append(f"Humidity {'Spike' if row['hum_diff'] > 0 else 'Drop'} ({row['hum_diff']:+.2f} %)")

    if row["light_event"] == 1:
        items.append(f"Light Spike ({row['lux_diff']:+.2f} lux)")

    if row["audio_event"] == 1:
        items.append(f"Noise Spike ({row['noise_diff']:+.2f} dBFS)")

    return " | ".join(items)


# ----------------------------
# pick file bar on the left
# ----------------------------
files = list_csv_files(str(HISTORY_DIR))
if not files:
    st.warning("No session data found in data/history/.")
    st.stop()

choice = st.sidebar.selectbox(
    "Session",
    files,
    index=len(files) - 1,
    format_func=format_file_stem_for_display,
)

# ----------------------------
# load all nightly metrics from helper
# ----------------------------
night = compute_night_detail_cached(str(choice), choice.stat().st_mtime)

raw_df = night["raw_df"].copy()
seg = night["seg"].copy()

night_label = night["night"]

sleep_score = night["sleep_score"]
total_sleep_min = night["total_sleep_min"]
disturbances = night["disturbances"]

deep_min = int(round(night["deep_min"]))
rem_min = int(round(night["rem_min"]))
light_min = int(round(night["light_min"]))
awake_min = int(round(night["awake_min"]))

deep_pct = int(round(night["deep_pct"]))
rem_pct = int(round(night["rem_pct"]))
light_pct = int(round(night["light_pct"]))
awake_pct = int(round(night["awake_pct"]))

domain_start = raw_df["timestamp"].min()
domain_end = raw_df["timestamp"].max()
total_minutes = (domain_end - domain_start).total_seconds() / 60.0

# ----------------------------
# graph data
# short recording -> raw rows
# long recording -> 10-second resolution
# disturbance logic still stays on raw_df
# ----------------------------
if total_minutes < 10:
    graph_df = raw_df.copy()
else:
    graph_df = (
        raw_df.set_index("timestamp")
        .resample("10s")
        .mean(numeric_only=True)
        .reset_index()
    )

graph_df = graph_df.sort_values("timestamp").reset_index(drop=True)

for c in ["temp_c", "humidity_pct", "lux", "noise_dbfs"]:
    if c in graph_df.columns:
        graph_df[c] = graph_df[c].ffill().bfill()

# ----------------------------
# disturbance rows only
# only build event text where there is actually an event
# detection still uses raw_df
# ----------------------------
disturbance_rows = raw_df[
    (raw_df["temp_event"] == 1) |
    (raw_df["humidity_event"] == 1) |
    (raw_df["light_event"] == 1) |
    (raw_df["audio_event"] == 1)
].copy()

if not disturbance_rows.empty:
    disturbance_rows["event"] = disturbance_rows.apply(build_event_text, axis=1)
else:
    disturbance_rows["event"] = pd.Series(dtype="object")

temp_rules = disturbance_rows[disturbance_rows["temp_event"] == 1][["timestamp", "event"]].copy()
hum_rules = disturbance_rows[disturbance_rows["humidity_event"] == 1][["timestamp", "event"]].copy()
light_rules = disturbance_rows[disturbance_rows["light_event"] == 1][["timestamp", "event"]].copy()
noise_rules = disturbance_rows[disturbance_rows["audio_event"] == 1][["timestamp", "event"]].copy()

temp_points = disturbance_rows[disturbance_rows["temp_event"] == 1][["timestamp", "temp_c", "event"]].copy()
hum_points = disturbance_rows[disturbance_rows["humidity_event"] == 1][["timestamp", "humidity_pct", "event"]].copy()
light_points = disturbance_rows[disturbance_rows["light_event"] == 1][["timestamp", "lux", "event"]].copy()
noise_points = disturbance_rows[disturbance_rows["audio_event"] == 1][["timestamp", "noise_dbfs", "event"]].copy()

# ----------------------------
# sleep stage fields for chart hover
# ----------------------------
seg["Stage"] = seg["stage"].replace({
    "awake": "Awake",
    "light": "Light",
    "deep": "Deep",
    "rem": "REM"
})
seg["start_label"] = seg["start"].dt.strftime("%I:%M:%S %p")
seg["end_label"] = seg["end"].dt.strftime("%I:%M:%S %p")
seg["y"] = seg["stage"].map({
    "deep": 0,
    "light": 1,
    "rem": 2,
    "awake": 3
})

# ----------------------------
# header
# ----------------------------
st.markdown(
    f"""
    <div class="card">
      <div style="opacity:.7;font-size:13px">AtmoSleep · Last Night</div>
      <div style="font-size:26px;font-weight:800">{night_label}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpi(k1, "Sleep Score", f"{sleep_score}")
kpi(k2, "Total Sleep", minutes_to_hours(total_sleep_min))
kpi(k3, "Disturbances", f"{disturbances}")
kpi(k4, "Deep", f"{deep_pct}%")
kpi(k5, "REM", f"{rem_pct}%")
kpi(k6, "Light / Awake", f"{light_pct}% / {awake_pct}%")

# ----------------------------
# sleep stages
# short recording -> raw rows
# long recording -> 10-second increments
# ----------------------------
st.subheader("Sleep Stages")

sleep_df = raw_df[["timestamp", "stage"]].copy()
sleep_df = sleep_df.dropna(subset=["timestamp", "stage"]).sort_values("timestamp").reset_index(drop=True)

if total_minutes < 10:
    sleep_plot = sleep_df.copy()
else:
    sleep_plot = (
        sleep_df.set_index("timestamp")
        .resample("10s")
        .agg({
            "stage": lambda s: s.dropna().iloc[-1] if not s.dropna().empty else None
        })
        .dropna(subset=["stage"])
        .reset_index()
    )

stage_y = {"deep": 0, "light": 1, "rem": 2, "awake": 3}
sleep_plot["y"] = sleep_plot["stage"].map(stage_y)
sleep_plot["x2"] = sleep_plot["timestamp"].shift(-1)
sleep_plot["y2"] = sleep_plot["y"].shift(-1)

seg_df = sleep_plot.dropna(subset=["x2", "y2"]).copy()

colors = {
    "deep": "#1F6BFF",
    "light": "#8BE9FD",
    "rem": "#E24DFF",
    "awake": "#F5F1EB"
}

x_enc = alt.X(
    "timestamp:T",
    title="",
    scale=alt.Scale(domain=[domain_start, domain_end]),
    axis=alt.Axis(
        labelAngle=0,
        tickCount=12,
        format="%I:%M %p",
        domain=False,
        grid=False,
        tickColor="rgba(255,255,255,0.15)",
        labelColor="rgba(255,255,255,0.85)",
    ),
)

y_enc = alt.Y(
    "y:Q",
    title="",
    scale=alt.Scale(domain=[-0.2, 3.2]),
    axis=alt.Axis(
        values=[3, 2, 1, 0],
        labelExpr="datum.value == 3 ? 'Awake' : datum.value == 2 ? 'REM' : datum.value == 1 ? 'Light' : 'Deep'",
        domain=False,
        grid=False,
        ticks=False,
        labelColor="rgba(255,255,255,0.85)",
        labelFontSize=13,
        labelFontWeight="bold"
    ),
)

layers = []

for stage in ["deep", "light", "rem", "awake"]:
    data = seg_df[seg_df["stage"] == stage]

    layers.append(
        alt.Chart(data).mark_line(
            interpolate="step-after",
            strokeWidth=4,
            color=colors[stage],
            strokeCap="round",
            strokeJoin="round",
        ).encode(
            x=x_enc,
            y=y_enc,
            x2="x2:T",
            y2="y2:Q",
            tooltip=[]
        )
    )

hover_layer = (
    alt.Chart(seg)
    .mark_bar(opacity=0)
    .encode(
        x=alt.X("start:T", scale=alt.Scale(domain=[domain_start, domain_end])),
        x2="end:T",
        y=alt.Y("y:Q", scale=alt.Scale(domain=[-0.2, 3.2])),
        tooltip=[
            alt.Tooltip("Stage:N", title="Stage"),
            alt.Tooltip("start_label:N", title="From"),
            alt.Tooltip("end_label:N", title="To"),
        ],
    )
    .properties(height=320)
)

chart = (
    alt.layer(*layers, hover_layer)
    .properties(height=320)
    .configure_view(strokeOpacity=0)
)

st.altair_chart(chart, use_container_width=True)

s1, s2, s3, s4 = st.columns(4)
mini_stage(s1, "Awake", minutes_to_hours(awake_min), "#F5F1EB")
mini_stage(s2, "Light", minutes_to_hours(light_min), "#8BE9FD")
mini_stage(s3, "REM", minutes_to_hours(rem_min), "#E24DFF")
mini_stage(s4, "Deep", minutes_to_hours(deep_min), "#1F6BFF")

tab1, tab2 = st.tabs(["Environment", "Disturbances"])

with tab1:
    st.markdown("#### Overnight Environment")
    show_legend([
        ("dot", "Temperature (°C)", "#2F6FED"),
        ("dot", "Humidity (%)", "#8BE9FD"),
        ("rule", "Disturbance", "#FF5A5F"),
    ])

    temp_df = graph_df[["timestamp", "temp_c"]].copy()
    hum_df = graph_df[["timestamp", "humidity_pct"]].copy()
    lux_df = graph_df[["timestamp", "lux"]].copy()
    noise_df = graph_df[["timestamp", "noise_dbfs"]].copy()

    temp_line = (
        alt.Chart(temp_df)
        .mark_line(color="#2F6FED")
        .encode(
            x=alt.X("timestamp:T", title="", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("temp_c:Q", title=""),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("temp_c:Q", title="Temperature (°C)", format=".2f"),
            ],
        )
    )

    hum_line = (
        alt.Chart(hum_df)
        .mark_line(color="#8BE9FD")
        .encode(
            x=alt.X("timestamp:T", title="", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("humidity_pct:Q", title=""),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("humidity_pct:Q", title="Humidity (%)", format=".2f"),
            ],
        )
    )

    temp_rule = (
        alt.Chart(temp_rules)
        .mark_rule(color="#FF5A5F", strokeWidth=1.5, opacity=0.85)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    hum_rule = (
        alt.Chart(hum_rules)
        .mark_rule(color="#FF5A5F", strokeWidth=1.5, opacity=0.85)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    temp_mark = (
        alt.Chart(temp_points)
        .mark_circle(size=90, color="#2F6FED", stroke="white", strokeWidth=1.2)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("temp_c:Q"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("temp_c:Q", title="Temperature (°C)", format=".2f"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    hum_mark = (
        alt.Chart(hum_points)
        .mark_circle(size=90, color="#8BE9FD", stroke="white", strokeWidth=1.2)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("humidity_pct:Q"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("humidity_pct:Q", title="Humidity (%)", format=".2f"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    env_chart = (
        alt.layer(temp_line, hum_line, temp_rule, hum_rule, temp_mark, hum_mark)
        .properties(height=270, padding={"left": 10, "right": 10, "top": 10, "bottom": 70})
        .configure_axis(
            labelColor="rgba(255,255,255,0.75)",
            gridColor="rgba(255,255,255,0.10)"
        )
        .configure_view(strokeOpacity=0)
    )

    st.altair_chart(env_chart, use_container_width=True)

    st.markdown("#### Light Intensity (Lux)")
    show_legend([
        ("dot", "Light (Lux)", "#8BE9FD"),
        ("rule", "Disturbance", "#FF5A5F"),
    ])

    light_line = (
        alt.Chart(lux_df)
        .mark_line(color="#8BE9FD")
        .encode(
            x=alt.X("timestamp:T", title="", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("lux:Q", title=""),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("lux:Q", title="Lux", format=".2f"),
            ],
        )
    )

    light_rule = (
        alt.Chart(light_rules)
        .mark_rule(color="#FF5A5F", strokeWidth=1.5, opacity=0.85)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    light_mark = (
        alt.Chart(light_points)
        .mark_circle(size=90, color="#8BE9FD", stroke="white", strokeWidth=1.2)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("lux:Q"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("lux:Q", title="Lux", format=".2f"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    light_chart = (
        alt.layer(light_line, light_rule, light_mark)
        .properties(height=260, padding={"left": 10, "right": 10, "top": 10, "bottom": 70})
        .configure_axis(
            labelColor="rgba(255,255,255,0.75)",
            gridColor="rgba(255,255,255,0.10)"
        )
        .configure_view(strokeOpacity=0)
    )

    st.altair_chart(light_chart, use_container_width=True)

    st.markdown("#### Noise (dBFS)")
    show_legend([
        ("dot", "Noise (dBFS)", "#E24DFF"),
        ("rule", "Disturbance", "#FF5A5F"),
    ])

    noise_line = (
        alt.Chart(noise_df)
        .mark_line(color="#E24DFF")
        .encode(
            x=alt.X("timestamp:T", title="", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("noise_dbfs:Q", title=""),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("noise_dbfs:Q", title="Noise (dBFS)", format=".3f"),
            ],
        )
    )

    noise_rule = (
        alt.Chart(noise_rules)
        .mark_rule(color="#FF5A5F", strokeWidth=1.5, opacity=0.85)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    noise_mark = (
        alt.Chart(noise_points)
        .mark_circle(size=90, color="#E24DFF", stroke="white", strokeWidth=1.2)
        .encode(
            x=alt.X("timestamp:T", scale=alt.Scale(domain=[domain_start, domain_end])),
            y=alt.Y("noise_dbfs:Q"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M:%S %p"),
                alt.Tooltip("noise_dbfs:Q", title="Noise (dBFS)", format=".3f"),
                alt.Tooltip("event:N", title="Disturbance"),
            ],
        )
    )

    noise_chart = (
        alt.layer(noise_line, noise_rule, noise_mark)
        .properties(height=260, padding={"left": 10, "right": 10, "top": 10, "bottom": 70})
        .configure_axis(
            labelColor="rgba(255,255,255,0.75)",
            gridColor="rgba(255,255,255,0.10)"
        )
        .configure_view(strokeOpacity=0)
    )

    st.altair_chart(noise_chart, use_container_width=True)

with tab2:
    st.markdown("#### Disturbances")

    disturbance_table = disturbance_rows[["timestamp", "event"]].copy()
    disturbance_table = disturbance_table.drop_duplicates(subset=["timestamp"])
    disturbance_table = disturbance_table.sort_values("timestamp").reset_index(drop=True)

    if disturbance_table.empty:
        st.info("No disturbances recorded.")
    else:
        disturbance_table["Time"] = disturbance_table["timestamp"].dt.strftime("%H:%M:%S")
        disturbance_table = disturbance_table.rename(columns={"event": "Event"})

        st.dataframe(
            disturbance_table[["Time", "Event"]],
            use_container_width=True,
            hide_index=True
        )
