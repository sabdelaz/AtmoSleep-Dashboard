import pandas as pd
from pathlib import Path


# keep score between 0 and 100
def clamp01_100(x):
    try:
        x = float(x)
    except Exception:
        return 0
    return int(max(0, min(100, round(x))))


# convert minutes → "xh ym"
def minutes_to_hours(m):
    m = int(round(m))
    h = m // 60
    mm = m % 60
    return f"{h}h {mm}m" if h > 0 else f"{mm}m"


# convert filename like 20260403 → 2026-04-03 (for display)
def extract_night_label(path: Path) -> str:
    raw = path.stem
    dt = pd.to_datetime(raw, format="%Y%m%d", errors="coerce")

    if pd.isna(dt):
        return raw

    return dt.strftime("%Y-%m-%d")


# actual date object (used for sorting)
def parse_night_date_from_path(path: Path):
    return pd.to_datetime(path.stem, format="%Y%m%d", errors="coerce")


# read csv + clean column names
def load_csv(path_str):
    raw = pd.read_csv(path_str)
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw


# this makes sure we don’t count multiple disturbances in a short time
# basically → max 1 disturbance every ~10 seconds (100 rows)
def pick_events(df_in, active_col, row_gap=100):
    event = pd.Series(0, index=df_in.index, dtype=int)

    hit_idx = df_in.index[df_in[active_col] == 1].tolist()
    last_idx = None

    for idx in hit_idx:
        if last_idx is None or (idx - last_idx) > row_gap:
            event.loc[idx] = 1
            last_idx = idx

    return event


# clean + standardize dataframe
def clean_night_df(raw):

    # rename columns from ESP32 → nicer names
    col_map = {
        "timestamp": "timestamp",
        "sleep_stage": "stage",
        "tempC": "temp_c",
        "humPct": "humidity_pct",
        "lux": "lux",
        "dbfs": "noise_dbfs",
        "pir": "motion",
        "centroidHz": "centroid_hz",
        "B1_50_200": "b1",
        "B2_200_1200": "b2",
        "B3_1200_4000": "b3",
        "B4_4000_8000": "b4",
    }

    missing = [c for c in col_map if c not in raw.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = raw.rename(columns=col_map).copy()

    # keep only needed columns
    keep_cols = [
        "timestamp", "stage", "temp_c", "humidity_pct", "lux", "noise_dbfs",
        "motion", "centroid_hz", "b1", "b2", "b3", "b4"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    # convert timestamp to actual datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # convert all numeric columns safely
    num_cols = [
        "temp_c", "humidity_pct", "lux", "noise_dbfs",
        "motion", "centroid_hz", "b1", "b2", "b3", "b4"
    ]

    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").ffill().fillna(0)

    # normalize stage values
    df["stage"] = df["stage"].astype(str).str.strip().str.lower()
    df = df[df["stage"].isin(["awake", "light", "deep", "rem"])]

    # sort by time
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid data in this file.")

    return df


# THIS IS THE MAIN DISTURBANCE LOGIC
def add_disturbance_columns(raw_df):

    df = raw_df.copy()

    df["temp_diff_200"] = df["temp_c"] - df["temp_c"].shift(200)
    df["hum_diff_200"] = df["humidity_pct"] - df["humidity_pct"].shift(200)
    df["lux_diff_100"] = df["lux"] - df["lux"].shift(100)
    df["noise_diff_100"] = df["noise_dbfs"] - df["noise_dbfs"].shift(100)

    # just saving the actual diff that triggered
    df["temp_diff"] = 0.0
    df["hum_diff"] = 0.0
    df["lux_diff"] = 0.0
    df["noise_diff"] = 0.0

    # ===== TEMP =====
    # only compare to 200 rows ago
    df["temp_hit"] = 0
    df.loc[df["temp_diff_200"].abs() >= 1, "temp_hit"] = 1
    df.loc[df["temp_diff_200"].abs() >= 1, "temp_diff"] = df["temp_diff_200"]

    # ===== HUMIDITY =====
    # only compare to 200 rows ago
    df["humidity_hit"] = 0
    df.loc[df["hum_diff_200"].abs() >= 15, "humidity_hit"] = 1
    df.loc[df["hum_diff_200"].abs() >= 15, "hum_diff"] = df["hum_diff_200"]

    # ===== LIGHT =====
    # only compare to 100 rows ago
    df["light_hit"] = 0
    df.loc[df["lux_diff_100"] >= 100, "light_hit"] = 1
    df.loc[df["lux_diff_100"] >= 100, "lux_diff"] = df["lux_diff_100"]

    # ===== AUDIO =====
    # only compare to 100 rows ago
    df["audio_hit"] = 0
    df.loc[df["noise_diff_100"] >= 0.7, "audio_hit"] = 1
    df.loc[df["noise_diff_100"] >= 0.7, "noise_diff"] = df["noise_diff_100"]

    # ===== FINAL STEP: stop duplicates from counting too close together =====
    df["temp_event"] = pick_events(df, "temp_hit", row_gap=100)
    df["humidity_event"] = pick_events(df, "humidity_hit", row_gap=300)
    df["light_event"] = pick_events(df, "light_hit", row_gap=100)
    df["audio_event"] = pick_events(df, "audio_hit", row_gap=100)

    return df


def get_stage_segments(raw_df):

    tmp = raw_df[["timestamp", "stage"]].copy()
    tmp = tmp.sort_values("timestamp").reset_index(drop=True)

    tmp["chg"] = tmp["stage"].ne(tmp["stage"].shift()).cumsum()

    seg = (
        tmp.groupby("chg")
        .agg(
            start=("timestamp", "first"),
            end=("timestamp", "last"),
            stage=("stage", "first"),
        )
        .reset_index(drop=True)
    )

    seg["duration_min"] = (seg["end"] - seg["start"]).dt.total_seconds() / 60.0
    seg.loc[seg["duration_min"] <= 0, "duration_min"] = 0.5

    return seg


def compute_sleep_score(total_sleep_min, awake_pct, deep_pct, rem_pct, disturbances):

    total_sleep_hours = total_sleep_min / 60.0

    if total_sleep_hours >= 7:
        duration_score = 100
    elif total_sleep_hours >= 6:
        duration_score = 85
    elif total_sleep_hours >= 5:
        duration_score = 65
    elif total_sleep_hours >= 4:
        duration_score = 40
    else:
        duration_score = 20

    continuity_score = clamp01_100(100 - (4 * awake_pct))
    stage_score = clamp01_100((deep_pct / 25) * 60 + (rem_pct / 25) * 40)
    disturbance_score = clamp01_100(100 - (5 * disturbances))

    if total_sleep_min < 5:
        return 0

    return clamp01_100(
        (0.35 * duration_score) +
        (0.25 * continuity_score) +
        (0.25 * stage_score) +
        (0.15 * disturbance_score)
    )


def compute_night_metrics(path):

    path = Path(path)

    raw = load_csv(str(path))
    raw_df = clean_night_df(raw)

    # 🔥 disturbances computed HERE
    raw_df = add_disturbance_columns(raw_df)

    seg = get_stage_segments(raw_df)

    deep_min = float(seg.loc[seg["stage"] == "deep", "duration_min"].sum())
    rem_min = float(seg.loc[seg["stage"] == "rem", "duration_min"].sum())
    light_min = float(seg.loc[seg["stage"] == "light", "duration_min"].sum())
    awake_min = float(seg.loc[seg["stage"] == "awake", "duration_min"].sum())

    total_sleep_min = deep_min + rem_min + light_min
    total_min = max(1.0, deep_min + rem_min + light_min + awake_min)

    deep_pct = round(100 * deep_min / total_min, 1)
    rem_pct = round(100 * rem_min / total_min, 1)
    light_pct = round(100 * light_min / total_min, 1)
    awake_pct = round(max(0, 100 - deep_pct - rem_pct - light_pct), 1)

    disturbances = int(
        raw_df["temp_event"].sum()
        + raw_df["humidity_event"].sum()
        + raw_df["light_event"].sum()
        + raw_df["audio_event"].sum()
    )

    sleep_score = compute_sleep_score(
        total_sleep_min,
        awake_pct,
        deep_pct,
        rem_pct,
        disturbances
    )

    return {
        "night": extract_night_label(path),
        "date": parse_night_date_from_path(path),
        "sleep_score": sleep_score,
        "total_sleep_min": round(total_sleep_min, 1),
        "total_sleep_hr": round(total_sleep_min / 60.0, 2),
        "disturbances": disturbances,
        "deep_min": round(deep_min, 1),
        "rem_min": round(rem_min, 1),
        "light_min": round(light_min, 1),
        "awake_min": round(awake_min, 1),
        "deep_pct": round(deep_pct, 1),
        "rem_pct": round(rem_pct, 1),
        "light_pct": round(light_pct, 1),
        "awake_pct": round(awake_pct, 1),
        "raw_df": raw_df,
        "seg": seg,
    }
