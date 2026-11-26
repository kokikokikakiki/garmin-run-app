import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

st.set_page_config(
    page_title="Garmin Run Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
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

      /* エキスパンダー（ログイン枠・詳細データ枠）の視認性向上 */
      [data-testid="stExpander"] {
        background-color: #111827 !important;
        border: 1px solid #334155 !important;
        border-radius: 14px !important;
      }
      [data-testid="stExpander"] summary {
        color: #f8fafc !important;
        font-weight: 700 !important;
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
            distance_km = (act.get("distance") or 0) / 1000.0
            avg_speed = act.get("averageSpeed")
            pace_sec_per_km = calc_sec_per_km(avg_speed)
            cadence = act.get("averageRunningCadenceInStepsPerMinute")

            raw_ascent = act.get("elevationGain")
            if raw_ascent is None:
                raw_ascent = act.get("totalAscent")
            elevation_gain = f"{int(round(raw_ascent))} m" if raw_ascent is not None else "-"

            run_items.append(
                {
                    "id": activity_id,
                    "name": act.get("activityName") or "ランニング",
                    "date": act.get("startTimeLocal") or "-",
                    "distance_km": distance_km,
                    "distance_bucket": get_distance_bucket(distance_km),
                    "pace": format_pace_from_sec(pace_sec_per_km),
                    "pace_sec_per_km": pace_sec_per_km,
                    "duration": format_duration(act.get("duration")),
                    "avg_hr": act.get("averageHR") or "-",
                    "max_hr": act.get("maxHR") or "-",
                    "cadence": f"{int(round(cadence))} spm" if cadence is not None else "-",
                    "calories": f"{int(act.get('calories'))} kcal" if act.get("calories") is not None else "-",
                    "elevation_gain": elevation_gain,
                }
            )

        if len(activities) < batch_size:
            break
        start += batch_size

    return run_items


def extract_gear_name_from_list(gear_list):
    if not gear_list:
        return "未登録"
    names = [
        g.get("displayName") or g.get("customMakeModel") or g.get("gearModelName")
        for g in gear_list
        if g.get("displayName") or g.get("customMakeModel") or g.get("gearModelName")
    ]
    return " / ".join(names) if names else "未登録"


def populate_gears_for_runs(email_val, password_val, target_runs, gear_cache):
    missing_ids = [
        r.get("id") for r in target_runs if r.get("id") and r.get("id") not in gear_cache
    ]
    if not missing_ids:
        return

    client = create_client(email_val, password_val)
    for act_id in missing_ids:
        try:
            gear_list = client.get_activity_gear(act_id)
            gear_cache[act_id] = extract_gear_name_from_list(gear_list)
        except Exception:
            gear_cache[act_id] = "未登録"


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


st.title("🏃 Garmin Run Dashboard")

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
    if not email or not password:
        st.warning("メールアドレスとパスワードの両方を入力してください。")
    else:
        status_box = st.empty()
        with st.spinner("Garmin Connect から全ランニング履歴を取得中..."):
            try:
                clean_email = email.strip()
                runs = fetch_all_running_activities(clean_email, password, status_box)
                st.session_state["runs_data"] = runs
                st.session_state["auth_creds"] = {"email": clean_email, "password": password}
                st.session_state["splits_cache"] = {}
                st.session_state["gear_cache"] = {}
                st.session_state["login_expanded"] = False
                status_box.empty()
                st.rerun()
            except Exception as e:
                status_box.empty()
                st.error(f"データ取得に失敗しました: {e}")

runs_data = st.session_state.get("runs_data", [])

if runs_data:
    st.markdown("### 🔎 距離帯フィルター & 平均ペース順ソート")
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
        r for r in runs_data if selected_bucket == "すべて" or r.get("distance_bucket") == selected_bucket
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
        st.info("選択した走行距離帯に該当するランニングがありません。")
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
        gear_name = st.session_state["gear_cache"].get(act_id, "未登録")
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
else:
    st.info("上の「🔐 Garminログイン・全アクティビティ取得」からログインして、データを取得してください。")