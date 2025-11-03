import os
import pandas as pd
import altair as alt
import streamlit as st

# Optional OpenAI import (app works without it)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="AI Wellness Coach Pro",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- CSS Helpers --------------------
def apply_css(css_style: str) -> None:
    st.markdown("<style>" + css_style + "</style>", unsafe_allow_html=True)

BACKGROUND_CSS = """
/***** Global tidy-up *****/
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}

/***** Keep sidebar visible; style it tastefully *****/
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(21,32,42,0.9) 0%, rgba(15,20,25,0.9) 100%);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(231, 76, 60, 0.25);
}

/***** Main area gradient background *****/
[data-testid="stAppViewContainer"] > .main{
  background: linear-gradient(-45deg, #0f1419, #1a252f, #15202a, #0d1117, #2c1810, #1a1a2e);
  background-size: 400% 400%;
  animation: gradientShift 25s ease infinite;
}

@keyframes gradientShift{
  0%{background-position:0% 50%;}
  50%{background-position:100% 50%;}
  100%{background-position:0% 50%;}
}

/***** Card styling *****/
.block-container{
  padding-top: 2rem;
}

.stMetric, .stAlert, .stButton > button{
  border-radius: 10px;
}
"""
apply_css(BACKGROUND_CSS)

# -------------------- State --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"

# -------------------- Sidebar --------------------
def build_sidebar():
    with st.sidebar:
        st.title("AI Wellness Coach")
        st.caption("Personal coaching, daily habits, and insights")

        nav = st.radio(
            "Navigation",
            options=["Dashboard", "Journal", "Coach", "Settings"],
            index=["Dashboard", "Journal", "Coach", "Settings"].index(
                st.session_state.nav
                if st.session_state.get("nav") in ["Dashboard", "Journal", "Coach", "Settings"]
                else "Dashboard"
            ),
        )
        st.session_state.nav = nav

        st.divider()
        st.subheader("Profile")
        st.text_input("Name", value="Alex Doe")
        st.selectbox("Focus Area", ["Stress", "Sleep", "Fitness", "Nutrition"], index=0)
        st.slider("Daily Goal (mins)", 5, 120, 30)

        st.divider()
        st.caption("Powered by OpenAI · Altair · Streamlit")
        if not st.session_state.logged_in:
            st.info("You are viewing the login screen. Sidebar stays visible.")

# -------------------- Data / Samples --------------------
@st.cache_data
def load_demo_metrics():
    df = pd.DataFrame({
        "day": pd.date_range(end=pd.Timestamp.today().normalize(), periods=14, freq="D"),
        "mood": [6,7,6,8,7,7,8,6,7,8,7,9,8,8],
        "sleep": [6.5,7.1,6.8,7.8,7.0,6.9,7.2,6.3,7.0,7.4,7.1,8.0,7.6,7.7],
        "steps": [5500,7200,6100,9000,8000,7600,8400,5000,7900,8600,8200,10000,9500,9800],
    })
    return df

# -------------------- Pages --------------------
def page_dashboard():
    st.header("Dashboard")
    df = load_demo_metrics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Mood (14d)", str(round(df.mood.mean(), 1)))
    col2.metric("Avg Sleep (hrs)", str(round(df.sleep.mean(), 1)))
    col3.metric("Avg Steps", str(int(df.steps.mean())))

    c1, c2 = st.columns([2, 1])
    with c1:
        mood_chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("day:T", title="Date"),
            y=alt.Y("mood:Q", title="Mood", scale=alt.Scale(domain=[0, 10])),
            tooltip=["day", "mood"]
        ).properties(height=280)
        st.altair_chart(mood_chart, use_container_width=True)

    with c2:
        st.write("Daily Notes")
        st.text_area("", value="Feeling more energetic. Practiced breathing exercises.", height=260)

    steps_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("day:T", title="Date"),
        y=alt.Y("steps:Q", title="Steps"),
        tooltip=["day", "steps"]
    ).properties(height=240)
    st.altair_chart(steps_chart, use_container_width=True)

def page_journal():
    st.header("Journal")
    st.write("Capture how you feel, what you did, and what you plan.")
    with st.form("journal_form"):
        mood = st.slider("Mood", 0, 10, 7)
        sleep = st.number_input("Sleep (hours)", 0.0, 12.0, 7.2, 0.1)
        entry = st.text_area("Notes", placeholder="Write about your day...")
        submitted = st.form_submit_button("Save Entry")
    if submitted:
        st.success("Entry saved locally (demo). Connect your DB to persist.")
        st.write("Mood:", mood)
        st.write("Sleep:", sleep)
        st.write("Notes:")
        st.write(entry)

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None
    if not api_key or not OPENAI_AVAILABLE:
        return None
    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception:
        return None

def local_coach(q: str) -> str:
    q_lower = q.lower()
    if "sleep" in q_lower:
        return "Aim for a consistent bedtime, dim lights 60 minutes before sleep, and avoid caffeine after 2 pm. Try a 10-minute wind-down routine."
    if "stress" in q_lower:
        return "Use 4-7-8 breathing twice daily, take 2-minute movement breaks every hour, and schedule a 10-minute planning slot to reduce cognitive load."
    if "fitness" in q_lower or "exercise" in q_lower:
        return "Target 150 minutes of moderate activity weekly, add 2 strength sessions, and keep 1 low-intensity recovery day."
    return "Keep it simple: set one tiny habit for today, reflect for 2 minutes, and celebrate the win."

def page_coach():
    st.header("Coach")
    st.caption("Ask your coach for tips. Uses OpenAI if a key is configured; otherwise returns a local heuristic.")

    prompt = st.text_area("Your question", placeholder="How can I improve my sleep this week?", height=120)
    c1, c2 = st.columns([1, 3])
    with c1:
        run_btn = st.button("Ask Coach")
    with c2:
        model = st.selectbox("Model", ["openai:gpt-4o-mini", "local:heuristic"], index=0)

    if run_btn and prompt.strip() != "":
        with st.spinner("Thinking..."):
            if model.startswith("openai"):
                client = get_openai_client()
                if client is None:
                    st.warning("OpenAI unavailable or API key missing. Falling back to local heuristic.")
                    answer = local_coach(prompt)
                else:
                    try:
                        # Adjust if your SDK differs; this is for openai>=1.0 style
                        resp = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a concise, evidence-based wellness coach."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.4,
                        )
                        answer = resp.choices[0].message.content
                    except Exception as e:
                        st.error("OpenAI error: " + str(e))
                        answer = local_coach(prompt)
            else:
                answer = local_coach(prompt)
        st.success("Coach Reply")
        st.write(answer)

def page_settings():
    st.header("Settings")
    st.toggle("Dark mode (Streamlit native)", value=True, help="Theme is mostly controlled by CSS here.")
    st.text_input("OpenAI API Key", type="password", help="Prefer environment variable OPENAI_API_KEY or Streamlit Secrets.")
    st.write("Version:", "1.0.0")

# -------------------- Login Flow --------------------
def page_login():
    st.title("Welcome to AI Wellness Coach Pro")
    st.caption("Sign in to continue. This demo uses a simple local check.")

    with st.form("login_form"):
        u = st.text_input("Email")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign In")
    if ok:
        if len(u.strip()) > 0 and len(p) >= 3:
            st.session_state.logged_in = True
            st.success("Signed in.")
            st.rerun()
        else:
            st.error("Invalid credentials. Use any non-empty email and a 3+ char password (demo).")

# -------------------- Main Router --------------------
def main_app():
    build_sidebar()
    page = st.session_state.nav
    if page == "Dashboard":
        page_dashboard()
    elif page == "Journal":
        page_journal()
    elif page == "Coach":
        page_coach()
    elif page == "Settings":
        page_settings()
    else:
        page_dashboard()

# Entry point
if not st.session_state.logged_in:
    build_sidebar()
    page_login()
else:
    main_app()
