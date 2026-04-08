import streamlit as st
import altair as alt
import pandas as pd
from pathlib import Path

from utils.sleep_metrics import (
    compute_night_metrics_cached,
    get_recent_nights_cached,
    list_csv_files,
    minutes_to_hours,
)
st.set_page_config(page_title="My Sleep Trends", layout="wide", initial_sidebar_state="collapsed")

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

      .block-container {
        padding-top: 2.8rem;
      }

      .card {
        border-radius: 16px;
        padding: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }

      .kpi-title {
        font-size: 12px;
        opacity: 0.7;
      }

      .kpi-value {
        font-size: 22px;
        font-weight: 800;
      }

      .insight-card {
        border-radius: 16px;
        padding: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        min-height: 108px;
      }

      .insight-title {
        font-size: 12px;
        opacity: 0.7;
        margin-bottom: 8px;
      }

      .insight-main {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 6px;
      }

      .insight-sub {
        font-size: 13px;
        opacity: 0.82;
        line-height: 1.45;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

HISTORY_DIR = Path("data/history")


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


def insight_box(col, title, main, sub):
    col.markdown(
        f"""
        <div class="insight-card">
          <div class="insight-title">{title}</div>
          <div class="insight-main">{main}</div>
          <div class="insight-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def nice_num(x):
    x = float(x)
    if x.is_integer():
        return str(int(x))
    return f"{x:.1f}"


def pretty_date(x):
    return pd.to_datetime(x).strftime("%b %d, %Y")


def total_sleep_label_from_hours(hours_val):
    mins = int(round(float(hours_val) * 60))
    return minutes_to_hours(mins)


def get_metric_delta_text(latest_val, avg_val, higher_is_better=True, is_percent=False, is_hours=False):
    diff = float(latest_val) - float(avg_val)

    if is_hours:
        diff_text = total_sleep_label_from_hours(abs(diff))
    elif is_percent:
        diff_text = f"{nice_num(abs(diff))}%"
    else:
        diff_text = nice_num(abs(diff))

    if abs(diff) < 0.01:
        return "Latest night is right on the weekly average."

    if higher_is_better:
        if diff > 0:
            return f"Latest night is above the weekly average by {diff_text}."
        return f"Latest night is below the weekly average by {diff_text}."
    else:
        if diff > 0:
            return f"Latest night is above the weekly average by {diff_text}."
        return f"Latest night is below the weekly average by {diff_text}."


def get_trend_text(df, col, label, higher_is_better=True, is_percent=False, is_hours=False):
    if len(df) < 2:
        return f"Not enough nights yet to judge the {label.lower()} trend."

    first_val = float(df.iloc[0][col])
    last_val = float(df.iloc[-1][col])
    diff = last_val - first_val

    if abs(diff) < 0.01:
        return f"{label} stayed about the same over the week."

    if is_hours:
        diff_text = total_sleep_label_from_hours(abs(diff))
    elif is_percent:
        diff_text = f"{nice_num(abs(diff))}%"
    else:
        diff_text = nice_num(abs(diff))

    if higher_is_better:
        if diff > 0:
            return f"{label} improved over the week (+{diff_text})."
        return f"{label} trended down over the week (-{diff_text})."
    else:
        if diff > 0:
            return f"{label} increased over the week (+{diff_text})."
        return f"{label} improved over the week (-{diff_text})."


def make_line_chart(data, y_col, title, color, y_title=""):
    line = (
        alt.Chart(data)
        .mark_line(
            color=color,
            strokeWidth=3,
            point=alt.OverlayMarkDef(size=80, filled=True)
        )
        .encode(
            x=alt.X(
                "date:T",
                title="",
                axis=alt.Axis(
                    labelAngle=0,
                    format="%b %d",
                    tickCount=min(7, len(data)),
                    domain=False,
                    grid=False,
                    labelColor="rgba(255,255,255,0.85)",
                    tickColor="rgba(255,255,255,0.15)",
                ),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=y_title,
                axis=alt.Axis(
                    domain=False,
                    grid=True,
                    gridColor="rgba(255,255,255,0.10)",
                    labelColor="rgba(255,255,255,0.75)",
                ),
            ),
            tooltip=[
                alt.Tooltip("night:N", title="Night"),
                alt.Tooltip(f"{y_col}:Q", title=title, format=".1f"),
            ],
        )
        .properties(height=260, title=title)
        .configure_view(strokeOpacity=0)
        .configure_title(
            anchor="start",
            color="rgba(255,255,255,0.90)",
            fontSize=16
        )
    )

    return line


def make_bar_chart(data, y_col, title, color, y_title=""):
    chart = (
        alt.Chart(data)
        .mark_bar(color=color, cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X(
                "date:T",
                title="",
                axis=alt.Axis(
                    labelAngle=0,
                    format="%b %d",
                    tickCount=min(7, len(data)),
                    domain=False,
                    grid=False,
                    labelColor="rgba(255,255,255,0.85)",
                    tickColor="rgba(255,255,255,0.15)",
                ),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=y_title,
                axis=alt.Axis(
                    domain=False,
                    grid=True,
                    gridColor="rgba(255,255,255,0.10)",
                    labelColor="rgba(255,255,255,0.75)",
                ),
            ),
            tooltip=[
                alt.Tooltip("night:N", title="Night"),
                alt.Tooltip(f"{y_col}:Q", title=title, format=".1f"),
            ],
        )
        .properties(height=260, title=title)
        .configure_view(strokeOpacity=0)
        .configure_title(
            anchor="start",
            color="rgba(255,255,255,0.90)",
            fontSize=16
        )
    )

    return chart


def make_stage_mix_chart(data):
    long_df = data.melt(
        id_vars=["night", "date"],
        value_vars=["deep_pct", "rem_pct", "light_pct", "awake_pct"],
        var_name="stage",
        value_name="pct"
    )

    stage_map = {
        "deep_pct": "Deep",
        "rem_pct": "REM",
        "light_pct": "Light",
        "awake_pct": "Awake",
    }
    long_df["stage"] = long_df["stage"].map(stage_map)

    color_scale = alt.Scale(
        domain=["Deep", "REM", "Light", "Awake"],
        range=["#1F6BFF", "#E24DFF", "#8BE9FD", "#F5F1EB"]
    )

    chart = (
        alt.Chart(long_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "date:T",
                title="",
                axis=alt.Axis(
                    labelAngle=0,
                    format="%b %d",
                    tickCount=min(7, len(data)),
                    domain=False,
                    grid=False,
                    labelColor="rgba(255,255,255,0.85)",
                    tickColor="rgba(255,255,255,0.15)",
                ),
            ),
            y=alt.Y(
                "pct:Q",
                title="Percent",
                stack="zero",
                axis=alt.Axis(
                    domain=False,
                    grid=True,
                    gridColor="rgba(255,255,255,0.10)",
                    labelColor="rgba(255,255,255,0.75)",
                ),
            ),
            color=alt.Color(
                "stage:N",
                scale=color_scale,
                legend=alt.Legend(
                    title="",
                    orient="top",
                    labelColor="rgba(255,255,255,0.85)"
                )
            ),
            tooltip=[
                alt.Tooltip("night:N", title="Night"),
                alt.Tooltip("stage:N", title="Stage"),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
            ],
        )
        .properties(height=300, title="Sleep Stage Mix")
        .configure_view(strokeOpacity=0)
        .configure_title(
            anchor="start",
            color="rgba(255,255,255,0.90)",
            fontSize=16
        )
    )

    return chart


files = list_csv_files(str(HISTORY_DIR))

if not files:
    st.warning("No session data found in data/history/.")
    st.stop()

last_files = files[-7:]
file_keys = tuple((str(path), path.stat().st_mtime) for path in last_files)
rows = get_recent_nights_cached(str(HISTORY_DIR), file_keys)

if not rows:
    st.error("Could not build trends from the available files.")
    st.stop()

trend_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

best_row = trend_df.loc[trend_df["sleep_score"].idxmax()]
worst_row = trend_df.loc[trend_df["sleep_score"].idxmin()]
latest_row = trend_df.iloc[-1]

avg_sleep_score = trend_df["sleep_score"].mean()
avg_total_sleep_min = trend_df["total_sleep_min"].mean()
avg_disturbances = trend_df["disturbances"].mean()
avg_deep_pct = trend_df["deep_pct"].mean()
avg_rem_pct = trend_df["rem_pct"].mean()

best_label = pretty_date(best_row["date"])
worst_label = pretty_date(worst_row["date"])

st.markdown(
    f"""
    <div class="card">
      <div style="opacity:.7;font-size:13px">AtmoSleep · My Sleep Trends</div>

      <div style="font-size:28px;font-weight:800">
        My Sleep Trends
      </div>

      <div style="opacity:.8; font-size:14px; margin-top:6px;">
        Showing the last {len(trend_df)} available night file(s)
      </div>

      <div style="margin-top:10px; font-size:14px; opacity:0.85;">
        🏆 Best: <b>{best_label}</b> ({int(best_row['sleep_score'])}) &nbsp;&nbsp;•&nbsp;&nbsp;
        📉 Worst: <b>{worst_label}</b> ({int(worst_row['sleep_score'])})
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

k1, k2, k3, k4, k5 = st.columns(5)
kpi(k1, "Average Sleep Score", nice_num(avg_sleep_score))
kpi(k2, "Average Total Sleep", minutes_to_hours(avg_total_sleep_min))
kpi(k3, "Average Disturbances", nice_num(avg_disturbances))
kpi(k4, "Average Deep", f"{nice_num(avg_deep_pct)}%")
kpi(k5, "Average REM", f"{nice_num(avg_rem_pct)}%")

st.write("")

i1, i2 = st.columns(2)

insight_box(
    i1,
    "Sleep Score Trend",
    get_trend_text(trend_df, "sleep_score", "Sleep score", higher_is_better=True),
    get_metric_delta_text(
        latest_row["sleep_score"],
        trend_df["sleep_score"].mean(),
        higher_is_better=True
    )
)

insight_box(
    i2,
    "Disturbance Trend",
    get_trend_text(trend_df, "disturbances", "Disturbances", higher_is_better=False),
    get_metric_delta_text(
        latest_row["disturbances"],
        trend_df["disturbances"].mean(),
        higher_is_better=False
    )
)

st.write("")

st.altair_chart(make_stage_mix_chart(trend_df), use_container_width=True)

c1, c2 = st.columns(2)

with c1:
    st.altair_chart(
        make_bar_chart(
            trend_df,
            "disturbances",
            "Disturbances by Night",
            "#FF5A5F",
            y_title="Count"
        ),
        use_container_width=True
    )

with c2:
    st.altair_chart(
        make_line_chart(
            trend_df,
            "total_sleep_hr",
            "Total Sleep by Night",
            "#8BE9FD",
            y_title="Hours"
        ),
        use_container_width=True
    )

st.altair_chart(
    make_line_chart(
        trend_df,
        "sleep_score",
        "Sleep Score by Night",
        "#2F6FED",
        y_title="Score"
    ),
    use_container_width=True
)

st.subheader("Latest Night vs Average")

compare_df = pd.DataFrame([
    {
        "Metric": "Sleep Score",
        "Latest Night": nice_num(latest_row["sleep_score"]),
        "Average": nice_num(trend_df["sleep_score"].mean()),
        "Difference": nice_num(latest_row["sleep_score"] - trend_df["sleep_score"].mean()),
    },
    {
        "Metric": "Total Sleep",
        "Latest Night": minutes_to_hours(latest_row["total_sleep_min"]),
        "Average": minutes_to_hours(trend_df["total_sleep_min"].mean()),
        "Difference": minutes_to_hours(abs(latest_row["total_sleep_min"] - trend_df["total_sleep_min"].mean())),
    },
    {
        "Metric": "Disturbances",
        "Latest Night": nice_num(latest_row["disturbances"]),
        "Average": nice_num(trend_df["disturbances"].mean()),
        "Difference": nice_num(latest_row["disturbances"] - trend_df["disturbances"].mean()),
    },
    {
        "Metric": "Deep %",
        "Latest Night": f"{nice_num(latest_row['deep_pct'])}%",
        "Average": f"{nice_num(trend_df['deep_pct'].mean())}%",
        "Difference": f"{nice_num(latest_row['deep_pct'] - trend_df['deep_pct'].mean())}%",
    },
    {
        "Metric": "REM %",
        "Latest Night": f"{nice_num(latest_row['rem_pct'])}%",
        "Average": f"{nice_num(trend_df['rem_pct'].mean())}%",
        "Difference": f"{nice_num(latest_row['rem_pct'] - trend_df['rem_pct'].mean())}%",
    },
])

st.dataframe(compare_df, use_container_width=True, hide_index=True)

st.subheader("Nightly Summary")

show_df = trend_df.copy()
show_df["Night"] = show_df["night"]
show_df["Sleep Score"] = show_df["sleep_score"].apply(nice_num)
show_df["Total Sleep"] = show_df["total_sleep_min"].apply(minutes_to_hours)
show_df["Disturbances"] = show_df["disturbances"].apply(nice_num)
show_df["Deep %"] = show_df["deep_pct"].apply(lambda x: f"{nice_num(x)}%")
show_df["REM %"] = show_df["rem_pct"].apply(lambda x: f"{nice_num(x)}%")
show_df["Light %"] = show_df["light_pct"].apply(lambda x: f"{nice_num(x)}%")
show_df["Awake %"] = show_df["awake_pct"].apply(lambda x: f"{nice_num(x)}%")

st.dataframe(
    show_df[
        [
            "Night",
            "Sleep Score",
            "Total Sleep",
            "Disturbances",
            "Deep %",
            "REM %",
            "Light %",
            "Awake %",
        ]
    ],
    use_container_width=True,
    hide_index=True
)
