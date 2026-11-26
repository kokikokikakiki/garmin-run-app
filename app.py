import os
import streamlit as st
import pandas as pd
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

      /* 入力欄・スライダー・ボタンの視認性向上 */
      .stTextInput input {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
      }
      .stTextInput input::placeholder {
        color: #94a3b8 !important;
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
if "auth_creds" not in st.session_state:
    st.session_state["auth_creds"] = {"email": "", "password": ""}


def format_pace(avg_speed_mps):
    if not avg_speed_mps or avg_speed_mps <= 0:
        return "-"
    sec_per_km = 1000.0 / avg_speed_mps
    mins = int(sec_per_km // 60)
    secs = int(round(sec_per_km % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}'{secs:02d}\"/km"


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


def fetch_running_activities(email_val, password_val, limit_val):
    client = Garmin(email_val, password_val)
    client.login()

    activities = client.get_activities(0, limit_val * 2)
    run_items = []

    for act in activities:
        act_type = (act.get("activityType") or {}).get("typeKey", "")
        if "running" not in act_type and "run" not in act_type:
            continue

        activity_id = act.get("activityId")
        gear_name = "未登録"
        if activity_id:
            try:
                gear_list = client.get_activity_gear(activity_id)
                if gear_list:
                    names = [
                        g.get("displayName") or g.get("customMakeModel") or g.get("gearModelName")
                        for g in gear_list
                        if g.get("displayName") or g.get("customMakeModel") or g.get("gearModelName")
                    ]
                    if names:
                        gear_name = " / ".join(names)
            except Exception:
                pass

        distance_km = (act.get("distance") or 0) / 1000.0
        cadence = act.get("averageRunningCadenceInStepsPerMinute")
        run_items.append(
            {
                "id": activity_id,
                "name": act.get("activityName") or "ランニング",
                "date": act.get("startTimeLocal") or "-",
                "distance_km": distance_km,
                "pace": format_pace(act.get("averageSpeed")),
                "duration": format_duration(act.get("duration")),
                "avg_hr": act.get("averageHR") or "-",
                "max_hr": act.get("maxHR") or "-",
                "cadence": f"{int(round(cadence))} spm" if cadence else "-",
                "calories": f"{int(act.get('calories'))} kcal" if act.get("calories") else "-",
                "elevation_gain": f"{int(round(act.get('elevationGain')))} m" if act.get("elevationGain") else "-",
                "gear": gear_name,
            }
        )
        if len(run_items) >= limit_val:
            break

    return run_items


def fetch_activity_splits(email_val, password_val, activity_id):
    client = Garmin(email_val, password_val)
    client.login()
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
                "平均心拍": int(lap.get("averageHR")) if lap.get("averageHR") else "-",
            }
        )
    return rows


st.title("🏃 Garmin Run Dashboard")

with st.expander("🔐 Garminログイン・データ取得", expanded=st.session_state["login_expanded"]):
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
    limit = st.slider("取得するラン件数", min_value=3, max_value=30, value=10, step=1)
    fetch_clicked = st.button("🔄 データを取得", use_container_width=True)

if fetch_clicked:
    if not email or not password:
        st.warning("メールアドレスとパスワードの両方を入力してください。")
    else:
        with st.spinner("Garmin Connect からランデータを取得中..."):
            try:
                clean_email = email.strip()
                runs = fetch_running_activities(clean_email, password, int(limit))
                st.session_state["runs_data"] = runs
                st.session_state["auth_creds"] = {"email": clean_email, "password": password}
                st.session_state["splits_cache"] = {}
                st.session_state["login_expanded"] = False
                st.rerun()
            except Exception as e:
                st.error(f"データ取得に失敗しました: {e}")

runs_data = st.session_state.get("runs_data", [])

if runs_data:
    for run in runs_data:
        act_id = run.get("id")
        garmin_url = f"https://connect.garmin.com/modern/activity/{act_id}" if act_id else ""
        link_html = (
            f'<a class="garmin-link" href="{garmin_url}" target="_blank">🔗 Garmin Connectで開く</a>'
            if garmin_url
            else ""
        )

        card_html = f"""
        <div class="run-card">
          <div class="run-title">{run["name"]}</div>
          <div class="run-date">📅 {run["date"]}</div>
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
            <span class="gear-badge">👟 {run["gear"]}</span>
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
    st.info("上の「🔐 Garminログイン・データ取得」からログインして、データを取得してください。")