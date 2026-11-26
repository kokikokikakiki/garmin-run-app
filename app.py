import os
import html
import streamlit as st
from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

st.set_page_config(page_title="Garmin Run Log", page_icon="🏃‍♂️", layout="wide")

# ダークネイビー＆カードUI用のカスタムCSS
st.markdown(
    """
    <style>
    /* 全体の背景を深い紺〜ブラック基調に */
    .stApp {
        background: linear-gradient(160deg, #070b14 0%, #0d1629 50%, #080d1a 100%);
        color: #f1f5f9;
    }
    /* サイドバーの背景 */
    [data-testid="stSidebar"] {
        background-color: #090e1a;
        border-right: 1px solid #1e293b;
    }
    /* ヘッダーの余白や背景をなじませる */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    /* ランカードのスタイル */
    .run-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .run-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    .run-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15);
    }
    .run-date {
        font-size: 0.92rem;
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .run-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
    }
    @media (max-width: 768px) {
        .metrics-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    .metric-box {
        background: rgba(30, 41, 59, 0.55);
        border-radius: 12px;
        padding: 10px 12px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .metric-icon {
        font-size: 1.45rem;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.72rem;
        color: #94a3b8;
        margin-bottom: 2px;
    }
    .metric-value {
        font-size: 1.02rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .accent-pace { color: #38bdf8; }
    .accent-hr { color: #fb7185; }
    .accent-shoe { color: #a78bfa; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("## 🏃‍♂️ Garmin Run Dashboard")
st.caption("直近のランニング記録をカードビューで表示します")

with st.sidebar:
    st.header("⚙️ 設定")
    email = st.text_input("Garmin メールアドレス", value=os.getenv("GARMIN_EMAIL", ""))
    password = st.text_input("Garmin パスワード", type="password", value=os.getenv("GARMIN_PASSWORD", ""))
    limit = st.slider("取得件数", min_value=5, max_value=50, value=15, step=5)


def format_pace(speed_mps):
    if not speed_mps or speed_mps <= 0:
        return "-"
    sec_per_km = 1000.0 / speed_mps
    mins = int(sec_per_km // 60)
    secs = int(round(sec_per_km % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}'{secs:02d}\"/km"


def get_shoes(client, activity_id):
    try:
        gear_list = client.get_activity_gear(activity_id)
        if not gear_list:
            return "未設定"
        names = []
        for g in gear_list:
            nickname = (
                g.get("displayName")
                or g.get("customMakeModel")
                or g.get("gearNickname")
                or g.get("gearModelName")
                or g.get("modelName")
            )
            if nickname:
                names.append(str(nickname).strip())
        return ", ".join(names) if names else "未設定"
    except Exception:
        return "未設定"


def get_garmin_client(user_email, user_password):
    client = Garmin(user_email, user_password)
    client.login()
    return client


if st.button("🔄 データを取得", type="primary"):
    if not email or not password:
        st.warning("サイドバーでメールアドレスとパスワードを設定してください。")
        st.stop()

    with st.spinner("Garmin Connect からデータを取得中..."):
        try:
            client = get_garmin_client(email, password)
            activities = client.get_activities(0, limit)

            runs = []
            for act in activities:
                act_type = (act.get("activityType") or {}).get("typeKey", "")
                if "running" not in act_type:
                    continue

                dist_km = (act.get("distance") or 0) / 1000.0
                avg_speed = act.get("averageSpeed")
                avg_hr = act.get("averageHR")
                act_id = act.get("activityId")
                act_name = act.get("activityName") or "ランニング"
                start_local = (act.get("startTimeLocal") or "")[:16]

                shoes = get_shoes(client, act_id) if act_id else "未設定"

                runs.append({
                    "date": start_local,
                    "title": act_name,
                    "distance": f"{dist_km:.2f} km",
                    "pace": format_pace(avg_speed),
                    "hr": f"{int(avg_hr)} bpm" if avg_hr else "-",
                    "shoes": shoes,
                })

            if not runs:
                st.info("指定件数の中にランアクティビティが見つかりませんでした。")
            else:
                for r in runs:
                    card_html = f"""
                    <div class="run-card">
                        <div class="run-card-header">
                            <span class="run-title">🏃 {html.escape(r['title'])}</span>
                            <span class="run-date">📅 {html.escape(r['date'])}</span>
                        </div>
                        <div class="metrics-grid">
                            <div class="metric-box">
                                <div class="metric-icon">📏</div>
                                <div>
                                    <div class="metric-label">距離</div>
                                    <div class="metric-value">{html.escape(r['distance'])}</div>
                                </div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-icon">⚡</div>
                                <div>
                                    <div class="metric-label">平均ペース</div>
                                    <div class="metric-value accent-pace">{html.escape(r['pace'])}</div>
                                </div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-icon">❤️</div>
                                <div>
                                    <div class="metric-label">平均心拍</div>
                                    <div class="metric-value accent-hr">{html.escape(r['hr'])}</div>
                                </div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-icon">👟</div>
                                <div>
                                    <div class="metric-label">使用シューズ</div>
                                    <div class="metric-value accent-shoe">{html.escape(r['shoes'])}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"取得エラー: {e}")