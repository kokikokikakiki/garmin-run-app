import os
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
      .run-card {
        background: linear-gradient(145deg, #111827, #0f172a);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
      }
      .run-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 4px;
      }
      .run-date {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 12px;
      }
      .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }
      .metric-box {
        background-color: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 12px;
        padding: 10px 12px;
      }
      .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 2px;
      }
      .metric-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #38bdf8;
      }
      .gear-badge {
        display: inline-block;
        margin-top: 12px;
        padding: 4px 10px;
        border-radius: 999px;
        background-color: rgba(56, 189, 248, 0.14);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #7dd3fc;
        font-size: 0.8rem;
        font-weight: 600;
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
        run_items.append(
            {
                "name": act.get("activityName") or "ランニング",
                "date": act.get("startTimeLocal") or "-",
                "distance_km": distance_km,
                "pace": format_pace(act.get("averageSpeed")),
                "duration": format_duration(act.get("duration")),
                "avg_hr": act.get("averageHR") or "-",
                "gear": gear_name,
            }
        )
        if len(run_items) >= limit_val:
            break

    return run_items


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
                runs = fetch_running_activities(email.strip(), password, int(limit))
                st.session_state["runs_data"] = runs
                st.session_state["login_expanded"] = False
                st.rerun()
            except Exception as e:
                st.error(f"データ取得に失敗しました: {e}")

runs_data = st.session_state.get("runs_data", [])

if runs_data:
    for run in runs_data:
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
          <div class="gear-badge">👟 {run["gear"]}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
else:
    st.info("上の「🔐 Garminログイン・データ取得」からログインして、データを取得してください。")