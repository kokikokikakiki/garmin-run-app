import os
from collections import defaultdict
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

st.set_page_config(
    page_title="Garmin Run",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      /* 上部のGitHubアイコン・ツールバー・右下のManage app/Streamlitバッジをすべて非表示 */
      [data-testid="stToolbar"],
      [data-testid="stHeaderActionElements"],
      [data-testid="stDecoration"],
      [data-testid="stStatusWidget"],
      [data-testid="manage-app-button"],
      button[kind="manageApp"],
      #MainMenu,
      footer,
      .stAppDeployButton,
      div[class*="viewerBadge"],
      div[class*="StatusWidget"],
      a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
      }

      header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 0px !important;
      }

      .stApp {
        background-color: #0b1120;
        color: #f8fafc;
      }
      .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 960px;
      }
      h1, h2, h3, p, label, .stMarkdown {
        color: #f8fafc !important;
      }

      /* トップタイトル（ピクトグラム風SVGアイコン + Garmin Run） */
      .app-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1.1rem;
      }
      .run-pictogram {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 9px;
        background-color: #38bdf8;
        color: #0b1120;
        flex-shrink: 0;
      }
      .app-title-text {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        line-height: 1.1;
      }

      /* 今月の走行距離サマリーバナー */
      .monthly-summary-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #38bdf8;
        border-radius: 16px;
        padding: 16px 18px;
        margin-top: 10px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(2, 132, 199, 0.18);
      }
      .monthly-summary-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 10px;
      }
      .monthly-summary-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #7dd3fc;
      }
      .monthly-summary-sub {
        font-size: 0.8rem;
        color: #94a3b8;
      }
      .monthly-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
      }
      .monthly-stat-box {
        background-color: rgba(11, 17, 32, 0.65);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 10px 12px;
      }
      .monthly-stat-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 2px;
      }
      .monthly-stat-value {
        font-size: 1.15rem;
        font-weight: 800;
        color: #38bdf8;
      }

      /* 比較カード */
      .compare-header-card {
        background: linear-gradient(145deg, #111827, #0f172a);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
        height: 100%;
      }
      .compare-tag {
        display: inline-block;
        padding: 2px 9px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 6px;
      }
      .compare-tag-a {
        background-color: #0c4a6e;
        border: 1px solid #38bdf8;
        color: #e0f2fe;
      }
      .compare-tag-b {
        background-color: #064e3b;
        border: 1px solid #34d399;
        color: #ecfdf5;
      }
      .compare-row {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 8px;
      }
      .compare-row-label {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-bottom: 4px;
        text-align: center;
      }
      .compare-row-values {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: 8px;
      }
      .compare-val-a {
        font-size: 1rem;
        font-weight: 700;
        color: #7dd3fc;
        text-align: left;
      }
      .compare-val-b {
        font-size: 1rem;
        font-weight: 700;
        color: #6ee7b7;
        text-align: right;
      }
      .compare-diff-badge {
        font-size: 0.76rem;
        font-weight: 600;
        color: #cbd5e1;
        background-color: #1e293b;
        border: 1px solid #475569;
        border-radius: 999px;
        padding: 2px 9px;
        white-space: nowrap;
      }

      /* 自前ダーク案内ボックス */
      .guide-box {
        background-color: #111827;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 14px 16px;
        color: #f8fafc;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-top: 8px;
      }

      /* アラート（st.error / st.warning / st.info）の視認性向上 */
      [data-testid="stAlert"],
      [data-testid="stAlert"] > div,
      [data-testid="stNotification"] {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 12px !important;
      }
      [data-testid="stAlert"] p,
      [data-testid="stAlert"] div,
      [data-testid="stAlert"] span,
      [data-testid="stNotification"] p,
      [data-testid="stNotification"] div,
      [data-testid="stNotification"] span {
        color: #f8fafc !important;
        background-color: transparent !important;
      }

      /* 入力欄・セレクト・ボタンの視認性向上 */
      .stTextInput input {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
      }
      .stTextInput input::placeholder {
        color: #94a3b8 !important;
      }
      [data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border-color: #475569 !important;
      }
      [data-baseweb="select"] span {
        color: #f8fafc !important;
      }
      .stButton button {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #38bdf8 !important;
        font-weight: 600 !important;
      }
      .stButton button:hover {
        background-color: #0284c7 !important;
        color: #ffffff !important;
      }

      /* エキスパンダー（ログイン枠・詳細データ枠・シューズ別アクティビティ枠）の視認性向上 */
      [data-testid="stExpander"] {
        background-color: #111827 !important;
        border: 1px solid #334155 !important;
        border-radius: 14px !important;
      }
      [data-testid="stExpander"] details,
      [data-testid="stExpander"] details > div,
      [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #111827 !important;
        color: #f8fafc !important;
      }
      [data-testid="stExpander"] summary {
        background-color: #111827 !important;
        color: #f8fafc !important;
        font-weight: 700 !important;
        border-radius: 14px !important;
      }
      [data-testid="stExpander"] summary span,
      [data-testid="stExpander"] summary p {
        color: #f8fafc !important;
      }

      /* メトリクス表示の文字色 */
      [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
      }
      [data-testid="stMetricValue"] {
        color: #7dd3fc !important;
        font-weight: 700 !important;
      }

      /* ラップテーブルの文字色 */
      [data-testid="stDataFrame"] {
        background-color: #0f172a !important;
        border-radius: 10px !important;
      }

      /* シューズランキングカード */
      .shoe-rank-card {
        background: linear-gradient(145deg, #111827, #0f172a);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      }
      .shoe-rank-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
      }
      .rank-badge {
        font-size: 1.15rem;
        font-weight: 800;
        color: #38bdf8;
        min-width: 44px;
        text-align: center;
      }
      .shoe-rank-name {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        word-break: break-word;
      }
      .shoe-rank-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 2px;
      }
      .shoe-rank-pace {
        font-size: 0.84rem;
        color: #7dd3fc;
        font-weight: 600;
        margin-top: 3px;
      }
      .shoe-rank-right {
        text-align: right;
        flex-shrink: 0;
      }
      .shoe-rank-dist {
        font-size: 1.05rem;
        font-weight: 800;
        color: #38bdf8;
      }
      .shoe-rank-count {
        font-size: 0.82rem;
        color: #cbd5e1;
        margin-top: 2px;
      }

      /* シューズ別アクティビティ行 */
      .shoe-act-row {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
      }
      .shoe-act-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #ffffff;
      }
      .shoe-act-meta {
        font-size: 0.8rem;
        color: #cbd5e1;
        margin-top: 2px;
      }

      /* ランカード */
      .run-card {
        background: linear-gradient(145deg, #111827, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 8px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
      }
      .run-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
      }
      .run-date {
        font-size: 0.88rem;
        color: #cbd5e1;
        margin-bottom: 12px;
      }
      .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }
      .metric-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 10px 12px;
      }
      .metric-label {
        font-size: 0.78rem;
        color: #cbd5e1;
        margin-bottom: 2px;
      }
      .metric-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #38bdf8;
      }
      .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
      }
      .gear-badge {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background-color: #0c4a6e;
        border: 1px solid #38bdf8;
        color: #e0f2fe;
        font-size: 0.82rem;
        font-weight: 600;
      }
      .garmin-link {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background-color: #064e3b;
        border: 1px solid #34d399;
        color: #ecfdf5 !important;
        font-size: 0.82rem;
        font-weight: 600;
        text-decoration: none;
      }
      @media (max-width: 640px) {
        .block-container {
          padding-top: 1rem !important;
          padding-left: 0.75rem !important;
          padding-right: 0.75rem !important;
        }
        .app-title-text {
          font-size: 1.5rem;
        }
        .monthly-summary-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .monthly-stat-value {
          font-size: 1.05rem;
        }
        .run-card {
          padding: 14px !important;
          border-radius: 14px !important;
        }
        .run-title {
          font-size: 1rem !important;
        }
        .metric-value {
          font-size: 0.98rem !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if "runs_data" not in st.session_state:
    st.session_state["runs_data"] = []
if "login_expanded" not in st.session_state:
    st.session_state["login_expanded"] = True
if "splits_cache" not in st.session_state:
    st.session_state["splits_cache"] = {}
if "gear_cache" not in st.session_state:
    st.session_state["gear_cache"] = {}
if "auth_creds" not in st.session_state:
    st.session_state["auth_creds"] = {"email": "", "password": ""}
if "active_view" not in st.session_state:
    st.session_state["active_view"] = None
if "last_fetch_message" not in st.session_state:
    st.session_state["last_fetch_message"] = ""


def calc_sec_per_km(avg_speed_mps):
    if not avg_speed_mps or avg_speed_mps <= 0:
        return None
    return 1000.0 / float(avg_speed_mps)


def format_pace_from_sec(sec_per_km):
    if sec_per_km is None or sec_per_km <= 0:
        return "-"
    mins = int(sec_per_km // 60)
    secs = int(round(sec_per_km % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}'{secs:02d}\"/km"


def format_pace(avg_speed_mps):
    return format_pace_from_sec(calc_sec_per_km(avg_speed_mps))


def format_duration(seconds):
    if not seconds:
        return "-"
    total_sec = int(seconds)
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def get_distance_bucket(distance_km):
    if distance_km < 3.0:
        return "3km未満"
    if distance_km < 5.0:
        return "3〜5km未満"
    if distance_km < 10.0:
        return "5〜10km未満"
    if distance_km < 15.0:
        return "10〜15km未満"
    if distance_km < 20.0:
        return "15〜20km未満"
    if distance_km < 25.0:
        return "ハーフ前後（20〜25km未満）"
    if distance_km < 40.0:
        return "25〜40km未満"
    return "フル以上（40km〜）"


DISTANCE_BUCKETS = [
    "すべて",
    "3km未満",
    "3〜5km未満",
    "5〜10km未満",
    "10〜15km未満",
    "15〜20km未満",
    "ハーフ前後（20〜25km未満）",
    "25〜40km未満",
    "フル以上（40km〜）",
]


def matches_keyword(run_item, keyword_query):
    query = (keyword_query or "").strip().lower()
    if not query:
        return True
    tokens = query.split()
    searchable = f"{run_item.get('name', '')} {run_item.get('date', '')}".lower()
    return all(tok in searchable for tok in tokens)


def create_client(email_val, password_val):
    client = Garmin(email_val, password_val)
    client.login()
    return client


def fetch_all_running_activities(email_val, password_val, status_placeholder=None):
    client = create_client(email_val, password_val)
    run_items = []
    start = 0
    batch_size = 100
    max_total_fetch = 2000

    while start < max_total_fetch:
        if status_placeholder:
            status_placeholder.caption(f"全アクティビティを取得中...（{start}件目〜 / 抽出済み {len(run_items)}件）")

        activities = client.get_activities(start, batch_size)
        if not activities:
            break

        for act in activities:
            act_type = (act.get("activityType") or {}).get("typeKey", "")
            if "running" not in act_type and "run" not in act_type:
                continue

            activity_id = act.get("activityId")
            date_str = act.get("startTimeLocal") or "-"
            year_str = date_str[:4] if len(date_str) >= 4 and date_str[:4].isdigit() else "不明"
            ym_str = date_str[:7] if len(date_str) >= 7 and date_str[:4].isdigit() else "不明"

            distance_km = (act.get("distance") or 0) / 1000.0
            duration_sec = float(act.get("duration") or 0.0)
            avg_speed = act.get("averageSpeed")
            pace_sec_per_km = calc_sec_per_km(avg_speed)
            cadence = act.get("averageRunningCadenceInStepsPerMinute")

            raw_ascent = act.get("elevationGain")
            if raw_ascent is None:
                raw_ascent = act.get("totalAscent")
            elevation_gain = f"{int(round(raw_ascent))} m" if raw_ascent is not None else "-"
            elevation_num = float(raw_ascent) if raw_ascent is not None else None

            avg_hr_val = act.get("averageHR")
            max_hr_val = act.get("maxHR")

            run_items.append(
                {
                    "id": activity_id,
                    "name": act.get("activityName") or "ランニング",
                    "date": date_str,
                    "year": year_str,
                    "year_month": ym_str,
                    "distance_km": distance_km,
                    "duration_sec": duration_sec,
                    "distance_bucket": get_distance_bucket(distance_km),
                    "pace": format_pace_from_sec(pace_sec_per_km),
                    "pace_sec_per_km": pace_sec_per_km,
                    "duration": format_duration(duration_sec),
                    "avg_hr": avg_hr_val if avg_hr_val is not None else "-",
                    "avg_hr_num": float(avg_hr_val) if avg_hr_val is not None else None,
                    "max_hr": max_hr_val if max_hr_val is not None else "-",
                    "max_hr_num": float(max_hr_val) if max_hr_val is not None else None,
                    "cadence": f"{int(round(cadence))} spm" if cadence is not None else "-",
                    "cadence_num": float(cadence) if cadence is not None else None,
                    "calories": f"{int(act.get('calories'))} kcal" if act.get("calories") is not None else "-",
                    "elevation_gain": elevation_gain,
                    "elevation_num": elevation_num,
                }
            )

        if len(activities) < batch_size:
            break
        start += batch_size

    return run_items


def _is_shoe_gear(gear_item):
    if not isinstance(gear_item, dict):
        return False
    g_type_obj = gear_item.get("gearType")
    type_key = ""
    if isinstance(g_type_obj, dict):
        type_key = str(g_type_obj.get("gearTypeKey") or g_type_obj.get("typeKey") or "").lower()
    elif g_type_obj is not None:
        type_key = str(g_type_obj).lower()

    type_name = str(gear_item.get("gearTypeName") or gear_item.get("typeName") or "").lower()
    combined = f"{type_key} {type_name}"
    return "shoe" in combined or "シューズ" in combined


def parse_gear_info(gear_list):
    if not gear_list:
        return {"display_gear": "未登録", "shoes_only": []}

    all_names = []
    shoes_only = []

    for g in gear_list:
        name = g.get("displayName") or g.get("customMakeModel") or g.get("gearModelName")
        if not name:
            continue
        all_names.append(name)
        if _is_shoe_gear(g):
            shoes_only.append(name)

    display_gear = " / ".join(all_names) if all_names else "未登録"
    return {"display_gear": display_gear, "shoes_only": shoes_only}


def populate_gears_for_runs(email_val, password_val, target_runs, gear_cache, progress_placeholder=None):
    missing_ids = [
        r.get("id") for r in target_runs if r.get("id") and r.get("id") not in gear_cache
    ]
    if not missing_ids:
        return

    client = create_client(email_val, password_val)
    total = len(missing_ids)
    for idx, act_id in enumerate(missing_ids, start=1):
        if progress_placeholder:
            progress_placeholder.caption(f"シューズ情報を取得中...（{idx} / {total}件）")
        try:
            gear_list = client.get_activity_gear(act_id)
            gear_cache[act_id] = parse_gear_info(gear_list)
        except Exception:
            gear_cache[act_id] = {"display_gear": "未登録", "shoes_only": []}


def get_cached_display_gear(gear_cache, act_id):
    entry = gear_cache.get(act_id)
    if isinstance(entry, dict):
        return entry.get("display_gear", "未登録")
    if isinstance(entry, str):
        return entry
    return "未登録"


def get_cached_shoes_only(gear_cache, act_id):
    entry = gear_cache.get(act_id)
    if isinstance(entry, dict):
        return entry.get("shoes_only", [])
    return []


def fetch_activity_splits(email_val, password_val, activity_id):
    client = create_client(email_val, password_val)
    splits_data = client.get_activity_splits(activity_id)
    laps = splits_data.get("lapDTOs", []) if isinstance(splits_data, dict) else []
    rows = []
    for idx, lap in enumerate(laps, start=1):
        dist_km = (lap.get("distance") or 0) / 1000.0
        rows.append(
            {
                "ラップ": idx,
                "距離 (km)": round(dist_km, 2),
                "タイム": format_duration(lap.get("duration")),
                "ペース": format_pace(lap.get("averageSpeed")),
                "平均心拍": int(lap.get("averageHR")) if lap.get("averageHR") is not None else "-",
            }
        )
    return rows


def build_side_by_side_laps_df(rows_a, rows_b):
    max_laps = max(len(rows_a or []), len(rows_b or []))
    combined = []
    for i in range(max_laps):
        a = rows_a[i] if rows_a and i < len(rows_a) else None
        b = rows_b[i] if rows_b and i < len(rows_b) else None
        combined.append(
            {
                "ラップ": i + 1,
                "A 距離": f"{a['距離 (km)']:.2f}" if a else "-",
                "A タイム": a["タイム"] if a else "-",
                "A ペース": a["ペース"] if a else "-",
                "A 心拍": a["平均心拍"] if a else "-",
                "B 距離": f"{b['距離 (km)']:.2f}" if b else "-",
                "B タイム": b["タイム"] if b else "-",
                "B ペース": b["ペース"] if b else "-",
                "B 心拍": b["平均心拍"] if b else "-",
            }
        )
    return pd.DataFrame(combined)


def format_rank_label(rank_idx):
    if rank_idx == 1:
        return "🥇 1位"
    if rank_idx == 2:
        return "🥈 2位"
    if rank_idx == 3:
        return "🥉 3位"
    return f"{rank_idx}位"


def render_monthly_summary(runs_list):
    current_ym = datetime.now().strftime("%Y-%m")
    this_month_runs = [r for r in runs_list if r.get("year_month") == current_ym]
    total_km = sum(r.get("distance_km") or 0.0 for r in this_month_runs)
    total_sec = sum(r.get("duration_sec") or 0.0 for r in this_month_runs)
    run_count = len(this_month_runs)

    if total_km > 0 and total_sec > 0:
        avg_pace_str = format_pace_from_sec(total_sec / total_km)
    else:
        avg_pace_str = "-"

    total_time_str = format_duration(total_sec) if total_sec > 0 else "0:00"

    summary_html = f"""
    <div class="monthly-summary-card">
      <div class="monthly-summary-header">
        <span class="monthly-summary-title">📅 今月の走行サマリー（{current_ym}）</span>
        <span class="monthly-summary-sub">全履歴 {len(runs_list)}件 取得済み</span>
      </div>
      <div class="monthly-summary-grid">
        <div class="monthly-stat-box">
          <div class="monthly-stat-label">今月の走行距離</div>
          <div class="monthly-stat-value">{total_km:.1f} km</div>
        </div>
        <div class="monthly-stat-box">
          <div class="monthly-stat-label">ラン回数</div>
          <div class="monthly-stat-value">{run_count} 回</div>
        </div>
        <div class="monthly-stat-box">
          <div class="monthly-stat-label">平均ペース</div>
          <div class="monthly-stat-value">{avg_pace_str}</div>
        </div>
        <div class="monthly-stat-box">
          <div class="monthly-stat-label">累計タイム</div>
          <div class="monthly-stat-value">{total_time_str}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(summary_html, unsafe_allow_html=True)


def render_compare_row(label, val_a, val_b, diff_text="—"):
    st.markdown(
        f"""
        <div class="compare-row">
          <div class="compare-row-label">{label}</div>
          <div class="compare-row-values">
            <div class="compare-val-a">{val_a}</div>
            <div class="compare-diff-badge">{diff_text}</div>
            <div class="compare-val-b">{val_b}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="app-header">
      <span class="run-pictogram" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="15.5" cy="4.5" r="2.2" />
          <path d="M13.5 7.5l-3.2 1.6-2.3 3.4 1.7 1.1 1.9-2.8 1.5-.7-1.7 5.5-4.3 2.4.9 1.8 4.8-2.7 1.3-4.1 2.9 2.4-.5 5.4h2l.6-6.3-2.9-2.5 1.2-3.8 2.4 1.2 1.8-1.5-1.1-1.3-1.4 1.2z" />
        </svg>
      </span>
      <span class="app-title-text">Garmin Run</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("🔐 Garminログイン・全アクティビティ取得", expanded=st.session_state["login_expanded"]):
    email = st.text_input(
        "Garmin メールアドレス",
        value=os.getenv("GARMIN_EMAIL", ""),
        placeholder="example@email.com",
    )
    password = st.text_input(
        "Garmin パスワード",
        value=os.getenv("GARMIN_PASSWORD", ""),
        type="password",
        placeholder="パスワードを入力",
    )
    fetch_clicked = st.button("🔄 全ランデータを取得", use_container_width=True)

if fetch_clicked:
    clean_email = email.strip()
    if not clean_email or not password:
        st.warning("メールアドレスとパスワードの両方を入力してください。")
    else:
        status_box = st.empty()
        with st.spinner("Garmin Connect から全ランニング履歴を取得中..."):
            try:
                runs = fetch_all_running_activities(clean_email, password, status_box)
                st.session_state["runs_data"] = runs
                st.session_state["auth_creds"] = {"email": clean_email, "password": password}
                st.session_state["splits_cache"] = {}
                st.session_state["gear_cache"] = {}
                st.session_state["active_view"] = None
                if runs:
                    st.session_state["login_expanded"] = False
                    st.session_state["last_fetch_message"] = ""
                else:
                    st.session_state["login_expanded"] = True
                    st.session_state["last_fetch_message"] = "ログインはできましたが、ランニング種別のアクティビティが0件でした。"
                status_box.empty()
                st.rerun()
            except Exception as e:
                status_box.empty()
                st.error(f"データ取得に失敗しました: {e}")

if st.session_state.get("last_fetch_message"):
    st.info(st.session_state["last_fetch_message"])

runs_data = st.session_state.get("runs_data", [])

if runs_data:
    # ログイン後、上部に今月の走行距離サマリーを表示
    render_monthly_summary(runs_data)

    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        if st.button("📏 距離別ラン", use_container_width=True):
            st.session_state["active_view"] = "distance"
            st.rerun()
    with nav_col2:
        if st.button("👟 シューズ順位", use_container_width=True):
            st.session_state["active_view"] = "shoes"
            st.rerun()
    with nav_col3:
        if st.button("⚖️ ラン比較", use_container_width=True):
            st.session_state["active_view"] = "compare"
            st.rerun()

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # --- 未選択時：ボタンを押すまで表示しない ---
    if st.session_state["active_view"] is None:
        st.markdown(
            '<div class="guide-box">上の「📏 距離別ラン」「👟 シューズ順位」「⚖️ ラン比較」ボタンから見たいメニューを選んでください。</div>',
            unsafe_allow_html=True,
        )

    # --- 1) 距離別ランデータ（フリーワード検索対応） ---
    elif st.session_state["active_view"] == "distance":
        st.markdown("### 📏 距離別ランデータ")

        keyword_filter = st.text_input(
            "🔍 アクティビティ名・日付で検索（フリーワード）",
            value="",
            placeholder="例：マラソン / 30km / インターバル / 2026-02",
        )

        col_filter, col_sort, col_limit = st.columns([2, 2, 1])

        with col_filter:
            selected_bucket = st.selectbox("走行距離帯（全履歴から選択）", DISTANCE_BUCKETS, index=0)

        with col_sort:
            sort_order = st.selectbox(
                "並び順",
                [
                    "平均ペースが速い順",
                    "平均ペースが遅い順",
                    "日付が新しい順",
                    "距離が長い順",
                ],
                index=0,
            )

        with col_limit:
            max_display = st.selectbox("表示件数", [10, 20, 50, 100], index=0)

        filtered_runs = [
            r
            for r in runs_data
            if (selected_bucket == "すべて" or r.get("distance_bucket") == selected_bucket)
            and matches_keyword(r, keyword_filter)
        ]

        if sort_order == "平均ペースが速い順":
            filtered_runs = sorted(
                filtered_runs,
                key=lambda x: (x["pace_sec_per_km"] is None, x["pace_sec_per_km"] or 999999),
            )
        elif sort_order == "平均ペースが遅い順":
            filtered_runs = sorted(
                filtered_runs,
                key=lambda x: (x["pace_sec_per_km"] is None, -(x["pace_sec_per_km"] or 0)),
            )
        elif sort_order == "日付が新しい順":
            filtered_runs = sorted(filtered_runs, key=lambda x: x.get("date") or "", reverse=True)
        elif sort_order == "距離が長い順":
            filtered_runs = sorted(filtered_runs, key=lambda x: x.get("distance_km") or 0.0, reverse=True)

        st.caption(f"全ラン {len(runs_data)}件 中 / 該当 {len(filtered_runs)}件（上位 {min(len(filtered_runs), max_display)}件を表示）")

        display_runs = filtered_runs[:max_display]

        if not display_runs:
            st.markdown(
                '<div class="guide-box">条件に一致するランニングが見つかりませんでした。検索ワードや距離帯を変えてみてください。</div>',
                unsafe_allow_html=True,
            )
        else:
            creds = st.session_state.get("auth_creds", {})
            if creds.get("email") and creds.get("password"):
                missing_count = sum(
                    1 for r in display_runs if r.get("id") and r.get("id") not in st.session_state["gear_cache"]
                )
                if missing_count > 0:
                    with st.spinner(f"表示中 {len(display_runs)}件のシューズ情報を読み込み中..."):
                        populate_gears_for_runs(
                            creds["email"],
                            creds["password"],
                            display_runs,
                            st.session_state["gear_cache"],
                        )

        for run in display_runs:
            act_id = run.get("id")
            gear_name = get_cached_display_gear(st.session_state["gear_cache"], act_id)
            garmin_url = f"https://connect.garmin.com/modern/activity/{act_id}" if act_id else ""
            link_html = (
                f'<a class="garmin-link" href="{garmin_url}" target="_blank">🔗 Garmin Connectで開く</a>'
                if garmin_url
                else ""
            )

            card_html = f"""
            <div class="run-card">
              <div class="run-title">{run["name"]}</div>
              <div class="run-date">📅 {run["date"]} ・ {run["distance_bucket"]}</div>
              <div class="metric-grid">
                <div class="metric-box">
                  <div class="metric-label">距離</div>
                  <div class="metric-value">{run["distance_km"]:.2f} km</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">平均ペース</div>
                  <div class="metric-value">{run["pace"]}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">タイム</div>
                  <div class="metric-value">{run["duration"]}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">平均心拍</div>
                  <div class="metric-value">{run["avg_hr"]} bpm</div>
                </div>
              </div>
              <div class="card-footer">
                <span class="gear-badge">👟 {gear_name}</span>
                {link_html}
              </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            with st.expander(f"📊 詳細データ・ラップ ({run['name']})"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("最大心拍", f"{run['max_hr']} bpm")
                c2.metric("平均ピッチ", run["cadence"])
                c3.metric("獲得標高", run["elevation_gain"])
                c4.metric("消費カロリー", run["calories"])

                if act_id:
                    if act_id in st.session_state["splits_cache"]:
                        laps_rows = st.session_state["splits_cache"][act_id]
                        if laps_rows:
                            st.dataframe(pd.DataFrame(laps_rows), use_container_width=True, hide_index=True)
                        else:
                            st.caption("ラップデータがありません。")
                    else:
                        if st.button("⏱ ラップタイムを読み込む", key=f"lap_btn_{act_id}", use_container_width=True):
                            creds = st.session_state.get("auth_creds", {})
                            with st.spinner("ラップを取得中..."):
                                try:
                                    rows = fetch_activity_splits(creds["email"], creds["password"], act_id)
                                    st.session_state["splits_cache"][act_id] = rows
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"ラップ取得エラー: {e}")

            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    # --- 2) シューズランキング ---
    elif st.session_state["active_view"] == "shoes":
        st.markdown("### 👟 シューズ使用ランキング（年別・月別）")
        years = sorted({r["year"] for r in runs_data if r.get("year") and r["year"] != "不明"}, reverse=True)
        year_months = sorted(
            {r["year_month"] for r in runs_data if r.get("year_month") and r["year_month"] != "不明"},
            reverse=True,
        )

        r_col1, r_col2, r_col3 = st.columns([1.2, 1.5, 1.5])
        with r_col1:
            period_mode = st.selectbox("集計単位", ["月別", "年別", "全期間"], index=0)
        with r_col2:
            if period_mode == "月別":
                selected_period = st.selectbox("対象月", year_months if year_months else ["不明"], index=0)
                period_runs = [r for r in runs_data if r.get("year_month") == selected_period]
                period_label = f"{selected_period}"
            elif period_mode == "年別":
                selected_period = st.selectbox("対象年", years if years else ["不明"], index=0)
                period_runs = [r for r in runs_data if r.get("year") == selected_period]
                period_label = f"{selected_period}年"
            else:
                period_runs = runs_data
                period_label = "全期間"
        with r_col3:
            shoe_sort_by = st.selectbox(
                "ランキング基準",
                ["総走行距離順", "使用回数順", "平均ペースが速い順"],
                index=0,
            )

        creds = st.session_state.get("auth_creds", {})
        missing_in_period = [
            r for r in period_runs if r.get("id") and r.get("id") not in st.session_state["gear_cache"]
        ]

        if missing_in_period and creds.get("email") and creds.get("password"):
            if period_mode == "月別" or len(missing_in_period) <= 40:
                prog_box = st.empty()
                with st.spinner(f"{period_label} のシューズ使用状況を集計中..."):
                    populate_gears_for_runs(
                        creds["email"],
                        creds["password"],
                        period_runs,
                        st.session_state["gear_cache"],
                        prog_box,
                    )
                prog_box.empty()
            else:
                if st.button(
                    f"👟 {period_label} のシューズデータをすべて読み込んで集計する（未取得 {len(missing_in_period)}件）",
                    use_container_width=True,
                ):
                    prog_box = st.empty()
                    with st.spinner(f"{period_label} のシューズ情報を読み込み中..."):
                        populate_gears_for_runs(
                            creds["email"],
                            creds["password"],
                            period_runs,
                            st.session_state["gear_cache"],
                            prog_box,
                        )
                    prog_box.empty()
                    st.rerun()

        shoe_stats = defaultdict(
            lambda: {"count": 0, "distance_km": 0.0, "duration_sec": 0.0, "activities": []}
        )
        for r in period_runs:
            act_id = r.get("id")
            dist_km = r.get("distance_km") or 0.0
            dur_sec = r.get("duration_sec") or 0.0
            shoes_for_run = get_cached_shoes_only(st.session_state["gear_cache"], act_id)
            for shoe_name in shoes_for_run:
                shoe_stats[shoe_name]["count"] += 1
                shoe_stats[shoe_name]["distance_km"] += dist_km
                shoe_stats[shoe_name]["duration_sec"] += dur_sec
                shoe_stats[shoe_name]["activities"].append(r)

        ranking_list = []
        for shoe_name, info in shoe_stats.items():
            total_km = info["distance_km"]
            total_sec = info["duration_sec"]
            if total_km > 0 and total_sec > 0:
                avg_sec_per_km = total_sec / total_km
                avg_pace_str = format_pace_from_sec(avg_sec_per_km)
            else:
                avg_sec_per_km = None
                avg_pace_str = "-"
            ranking_list.append(
                {
                    "shoe": shoe_name,
                    "count": info["count"],
                    "distance_km": total_km,
                    "avg_sec_per_km": avg_sec_per_km,
                    "avg_pace": avg_pace_str,
                    "activities": info["activities"],
                }
            )

        if shoe_sort_by == "総走行距離順":
            ranking_list.sort(key=lambda x: (-x["distance_km"], -x["count"]))
        elif shoe_sort_by == "使用回数順":
            ranking_list.sort(key=lambda x: (-x["count"], -x["distance_km"]))
        else:
            ranking_list.sort(
                key=lambda x: (x["avg_sec_per_km"] is None, x["avg_sec_per_km"] or 999999, -x["distance_km"])
            )

        total_period_km = sum(r.get("distance_km") or 0.0 for r in period_runs)
        st.caption(f"{period_label} のラン合計：{len(period_runs)}回 / {total_period_km:.2f} km（シューズ種別のみ集計）")

        if ranking_list:
            for idx, item in enumerate(ranking_list, start=1):
                avg_dist = item["distance_km"] / item["count"] if item["count"] > 0 else 0.0
                rank_html = f"""
                <div class="shoe-rank-card">
                  <div class="shoe-rank-left">
                    <div class="rank-badge">{format_rank_label(idx)}</div>
                    <div>
                      <div class="shoe-rank-name">👟 {item["shoe"]}</div>
                      <div class="shoe-rank-sub">1回あたり平均 {avg_dist:.1f} km</div>
                      <div class="shoe-rank-pace">平均ペース：{item["avg_pace"]}</div>
                    </div>
                  </div>
                  <div class="shoe-rank-right">
                    <div class="shoe-rank-dist">{item["distance_km"]:.1f} km</div>
                    <div class="shoe-rank-count">{item["count"]} 回使用</div>
                  </div>
                </div>
                """
                st.markdown(rank_html, unsafe_allow_html=True)

                with st.expander(f"👟 {item['shoe']} のアクティビティを見る（{item['count']}件）"):
                    for act in item["activities"]:
                        a_id = act.get("id")
                        g_url = f"https://connect.garmin.com/modern/activity/{a_id}" if a_id else ""
                        g_btn = (
                            f'<a class="garmin-link" href="{g_url}" target="_blank">🔗 Garmin Connectで開く</a>'
                            if g_url
                            else ""
                        )
                        row_html = f"""
                        <div class="shoe-act-row">
                          <div>
                            <div class="shoe-act-title">{act["name"]}</div>
                            <div class="shoe-act-meta">📅 {act["date"]} ・ {act["distance_km"]:.2f} km ・ {act["pace"]} ・ {act["duration"]}</div>
                          </div>
                          <div>{g_btn}</div>
                        </div>
                        """
                        st.markdown(row_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="guide-box">対象期間にシューズ種別として登録されたギアのデータがありません。</div>',
                unsafe_allow_html=True,
            )

    # --- 3) ランアクティビティ比較 ---
    else:
        st.markdown("### ⚖️ ランアクティビティ比較")

        f_col1, f_col2 = st.columns([1.4, 1.6])
        with f_col1:
            cmp_bucket = st.selectbox(
                "📏 走行距離帯で絞り込み",
                DISTANCE_BUCKETS,
                index=0,
                key="compare_bucket_select",
            )
        with f_col2:
            cmp_search = st.text_input(
                "🔍 アクティビティ名・日付で検索",
                value="",
                placeholder="例：マラソン / 30km / 2026",
                key="compare_keyword_input",
            )

        sorted_for_cmp = sorted(
            [
                r
                for r in runs_data
                if (cmp_bucket == "すべて" or r.get("distance_bucket") == cmp_bucket)
                and matches_keyword(r, cmp_search)
            ],
            key=lambda x: x.get("date") or "",
            reverse=True,
        )

        st.caption(f"絞り込み結果：{len(sorted_for_cmp)}件（全 {len(runs_data)}件中）")

        if len(sorted_for_cmp) < 2:
            st.markdown(
                '<div class="guide-box">比較できるアクティビティが2件以上ありません。走行距離帯や検索条件を広げてみてください。</div>',
                unsafe_allow_html=True,
            )
        else:
            option_indices = list(range(len(sorted_for_cmp)))

            def format_cmp_option(i):
                item = sorted_for_cmp[i]
                date_short = (item.get("date") or "-")[:10]
                return f"{date_short} | {item['name']}（{item['distance_km']:.2f}km / {item['pace']}）"

            sel_col1, sel_col2 = st.columns(2)
            with sel_col1:
                idx_a = st.selectbox(
                    "🟦 ラン A（基準）",
                    option_indices,
                    index=0,
                    format_func=format_cmp_option,
                    key="cmp_select_a",
                )
            with sel_col2:
                default_b = 1 if len(option_indices) > 1 else 0
                idx_b = st.selectbox(
                    "🟩 ラン B（比較対象）",
                    option_indices,
                    index=default_b,
                    format_func=format_cmp_option,
                    key="cmp_select_b",
                )

            run_a = sorted_for_cmp[idx_a]
            run_b = sorted_for_cmp[idx_b]

            creds = st.session_state.get("auth_creds", {})
            pair_runs = [run_a, run_b]
            missing_pair = [
                r for r in pair_runs if r.get("id") and r.get("id") not in st.session_state["gear_cache"]
            ]
            if missing_pair and creds.get("email") and creds.get("password"):
                with st.spinner("選択した2件のシューズ情報を読み込み中..."):
                    populate_gears_for_runs(
                        creds["email"],
                        creds["password"],
                        pair_runs,
                        st.session_state["gear_cache"],
                    )

            gear_a = get_cached_display_gear(st.session_state["gear_cache"], run_a.get("id"))
            gear_b = get_cached_display_gear(st.session_state["gear_cache"], run_b.get("id"))

            url_a = f"https://connect.garmin.com/modern/activity/{run_a.get('id')}" if run_a.get("id") else ""
            url_b = f"https://connect.garmin.com/modern/activity/{run_b.get('id')}" if run_b.get("id") else ""
            link_a = f'<a class="garmin-link" href="{url_a}" target="_blank">🔗 Garmin Connectで開く</a>' if url_a else ""
            link_b = f'<a class="garmin-link" href="{url_b}" target="_blank">🔗 Garmin Connectで開く</a>' if url_b else ""

            h_col1, h_col2 = st.columns(2)
            with h_col1:
                st.markdown(
                    f"""
                    <div class="compare-header-card">
                      <span class="compare-tag compare-tag-a">ラン A</span>
                      <div class="run-title">{run_a["name"]}</div>
                      <div class="run-date">📅 {run_a["date"]} ・ {run_a["distance_bucket"]}</div>
                      <div style="margin-top:8px;">{link_a}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with h_col2:
                st.markdown(
                    f"""
                    <div class="compare-header-card">
                      <span class="compare-tag compare-tag-b">ラン B</span>
                      <div class="run-title">{run_b["name"]}</div>
                      <div class="run-date">📅 {run_b["date"]} ・ {run_b["distance_bucket"]}</div>
                      <div style="margin-top:8px;">{link_b}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 差分計算（A - B）
            dist_diff = (run_a.get("distance_km") or 0.0) - (run_b.get("distance_km") or 0.0)
            dist_diff_str = f"A基準 {dist_diff:+.2f} km"

            pace_a_sec = run_a.get("pace_sec_per_km")
            pace_b_sec = run_b.get("pace_sec_per_km")
            if pace_a_sec is not None and pace_b_sec is not None:
                p_diff = int(round(pace_a_sec - pace_b_sec))
                if p_diff == 0:
                    pace_diff_str = "同ペース"
                elif p_diff < 0:
                    pace_diff_str = f"Aが {abs(p_diff)}秒/km 速い"
                else:
                    pace_diff_str = f"Aが {p_diff}秒/km 遅い"
            else:
                pace_diff_str = "—"

            dur_a = run_a.get("duration_sec") or 0.0
            dur_b = run_b.get("duration_sec") or 0.0
            dur_diff = int(round(dur_a - dur_b))
            if dur_diff == 0:
                dur_diff_str = "同タイム"
            else:
                sign = "+" if dur_diff > 0 else "-"
                dur_diff_str = f"A基準 {sign}{format_duration(abs(dur_diff))}"

            hr_a = run_a.get("avg_hr_num")
            hr_b = run_b.get("avg_hr_num")
            if hr_a is not None and hr_b is not None:
                hr_diff_str = f"A基準 {int(round(hr_a - hr_b)):+d} bpm"
            else:
                hr_diff_str = "—"

            max_hr_a = run_a.get("max_hr_num")
            max_hr_b = run_b.get("max_hr_num")
            if max_hr_a is not None and max_hr_b is not None:
                max_hr_diff_str = f"A基準 {int(round(max_hr_a - max_hr_b)):+d} bpm"
            else:
                max_hr_diff_str = "—"

            cad_a = run_a.get("cadence_num")
            cad_b = run_b.get("cadence_num")
            if cad_a is not None and cad_b is not None:
                cad_diff_str = f"A基準 {int(round(cad_a - cad_b)):+d} spm"
            else:
                cad_diff_str = "—"

            ele_a = run_a.get("elevation_num")
            ele_b = run_b.get("elevation_num")
            if ele_a is not None and ele_b is not None:
                ele_diff_str = f"A基準 {int(round(ele_a - ele_b)):+d} m"
            else:
                ele_diff_str = "—"

            render_compare_row("走行距離", f"{run_a['distance_km']:.2f} km", f"{run_b['distance_km']:.2f} km", dist_diff_str)
            render_compare_row("平均ペース", run_a["pace"], run_b["pace"], pace_diff_str)
            render_compare_row("タイム", run_a["duration"], run_b["duration"], dur_diff_str)
            render_compare_row("平均心拍", f"{run_a['avg_hr']} bpm", f"{run_b['avg_hr']} bpm", hr_diff_str)
            render_compare_row("最大心拍", f"{run_a['max_hr']} bpm", f"{run_b['max_hr']} bpm", max_hr_diff_str)
            render_compare_row("平均ピッチ", run_a["cadence"], run_b["cadence"], cad_diff_str)
            render_compare_row("獲得標高", run_a["elevation_gain"], run_b["elevation_gain"], ele_diff_str)
            render_compare_row("使用シューズ", gear_a, gear_b, "ギア比較")

            # ラップタイム横並び比較
            with st.expander("⏱ ラン A と ラン B のラップタイムを横並び比較する"):
                id_a = run_a.get("id")
                id_b = run_b.get("id")
                need_fetch_a = id_a and id_a not in st.session_state["splits_cache"]
                need_fetch_b = id_b and id_b not in st.session_state["splits_cache"]

                if (need_fetch_a or need_fetch_b) and creds.get("email") and creds.get("password"):
                    if st.button("⏱ 両方のラップタイムを読み込む", key="cmp_load_laps_btn", use_container_width=True):
                        with st.spinner("2件分のラップデータを取得中..."):
                            try:
                                if need_fetch_a:
                                    st.session_state["splits_cache"][id_a] = fetch_activity_splits(
                                        creds["email"], creds["password"], id_a
                                    )
                                if need_fetch_b:
                                    st.session_state["splits_cache"][id_b] = fetch_activity_splits(
                                        creds["email"], creds["password"], id_b
                                    )
                                st.rerun()
                            except Exception as e:
                                st.error(f"ラップ取得エラー: {e}")

                rows_a = st.session_state["splits_cache"].get(id_a)
                rows_b = st.session_state["splits_cache"].get(id_b)

                if rows_a is not None or rows_b is not None:
                    st.caption(f"🟦 A：{run_a['name']}（{(run_a.get('date') or '-')[:10]}） ／ 🟩 B：{run_b['name']}（{(run_b.get('date') or '-')[:10]}）")
                    side_df = build_side_by_side_laps_df(rows_a, rows_b)
                    if not side_df.empty:
                        st.dataframe(side_df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("ラップデータがありません。")
                else:
                    st.caption("上のボタンを押すと、AとBのラップを1つの表に横並びで表示します。")
else:
    st.markdown(
        '<div class="guide-box">上の「🔐 Garminログイン・全アクティビティ取得」からログインして、データを取得してください。</div>',
        unsafe_allow_html=True,
    )