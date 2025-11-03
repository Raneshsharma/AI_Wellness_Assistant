import os
import json
import time
import hashlib
import datetime as dt
import pandas as pd
import altair as alt
import streamlit as st

# Optional OpenAI import (app works without it)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# ============== Page Config ==============
st.set_page_config(
    page_title="AI Wellness Coach Pro",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============== CSS & Theme ==============
def apply_css(css_style: str) -> None:
    st.markdown("<style>" + css_style + "</style>", unsafe_allow_html=True)

def ensure_sidebar_shown():
    css = """
    /* Keep sidebar visible and styled */
    [data-testid="stSidebar"]{
      background: linear-gradient(180deg, rgba(21,32,42,0.9) 0%, rgba(15,20,25,0.9) 100%);
      backdrop-filter: blur(10px);
      border-right: 1px solid rgba(231,76,60,0.25);
    }
    /* Soft gradient main background */
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
    /* Login container styling */
    .login-card{
      max-width: 460px;
      margin: 8vh auto;
      padding: 32px 26px;
      border-radius: 16px;
      background: rgba(20,26,33,0.82);
      border: 1px solid rgba(255,255,255,0.06);
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
      backdrop-filter: blur(10px);
      color: #e8eaed;
      text-align: center;
    }
    .login-title{
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .login-sub{
      opacity: 0.8;
      margin-bottom: 18px;
    }
    /* Buttons */
    .stButton > button{
      background: linear-gradient(90deg,#e74c3c,#f39c12);
      color: white;
      border: none;
      border-radius: 10px;
      padding: 0.5rem 1rem;
      box-shadow: 0 6px 16px rgba(231,76,60,0.35);
    }
    .stButton > button:hover{
      filter: brightness(1.08);
      transform: translateY(-1px);
    }
    /* Cards, alerts, metrics */
    .block-container{padding-top: 2rem;}
    .stMetric, .stAlert, .stTextInput, .stSelectbox, .stNumberInput, .stSlider{
      border-radius: 10px;
    }
    #MainMenu{visibility:hidden;}
    footer{visibility:hidden;}
    """
    apply_css(css)

ensure_sidebar_shown()

# ============== Utilities & Security ==============
def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return sha256_hash(plain) == hashed

def sanitize_text(s: str) -> str:
    if not isinstance(s, str):
        return s
    return s.replace("<", "&lt;").replace(">", "&gt;")

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

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
        return OpenAI(api_key=api_key)
    except Exception:
        return None

# Cache the 7-day plan generation to reduce costs for same prompt/settings
@st.cache_data(show_spinner=False)
def cached_generate_api_call(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.4, seed: int = 1234):
    client = get_openai_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            seed=seed,
            messages=[
                {"role": "system", "content": "You are an expert registered dietitian and certified personal trainer. Always provide safe, evidence-based, and practical guidance."},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content
        return content
    except Exception as e:
        return "ERROR::" + str(e)

def stream_chat_to_ui(prompt: str, system: str = "You are a concise, evidence-based AI health coach."):
    client = get_openai_client()
    if client is None:
        # Local fallback simulated stream
        ph = st.empty()
        text = ("No OpenAI key found. Local guidance: Focus on consistent routines, "
                "prioritize sleep, hydrate, and build habits gradually.")
        out = ""
        for ch in text:
            out += ch
            ph.markdown(out)
            time.sleep(0.01)
        return out

    placeholder = st.empty()
    full_text = ""
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            stream=True,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        for chunk in stream:
            delta = ""
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if delta:
                full_text += delta
                placeholder.markdown(sanitize_text(full_text))
        return full_text
    except Exception as e:
        st.error("Streaming error: " + str(e))
        return ""

# ============== Plan Parsing ==============
def parse_weekly_plan(ai_text: str):
    """
    Expect JSON like:
    {
      "disclaimer": "...",
      "week_plan": [
         {
           "day": "Day 1",
           "calories": 2100,
           "meals": [{"name": "...","recipe":"...","portion":"..."}, ...],
           "exercises": [{"name":"...","sets":3,"reps":"10-12","cues":"..."}, ...],
           "motivation": "..."
         },
         ...
      ]
    }
    Fallback: attempts to parse minimal structure if JSON fails.
    """
    if not ai_text:
        return {"disclaimer": "Consult a healthcare professional for personalized advice.", "week_plan": []}
    text = ai_text.strip()
    if text.startswith("ERROR::"):
        return {"disclaimer": "AI generation error. Please try again later.", "week_plan": []}
    # Try extract JSON block if wrapped in markdown fences
    try:
        # direct JSON
        data = json.loads(text)
        return data
    except Exception:
        pass
    # Try extract between code fences
    try:
        if "```" in text:
            parts = text.split("```")
            for p in parts:
                p2 = p.strip()
                if p2.startswith("{") and p2.endswith("}"):
                    return json.loads(p2)
    except Exception:
        pass
    # Minimal fallback: build simple structure
    fallback_days = []
    for i in range(1, 8):
        fallback_days.append({
            "day": f"Day {i}",
            "calories": 2000,
            "meals": [
                {"name": "Oatmeal & berries", "recipe": "Cook oats, top with berries, chia.", "portion": "1 bowl"},
                {"name": "Greek yogurt & nuts", "recipe": "Mix yogurt, almonds, honey.", "portion": "1 cup"},
                {"name": "Chicken salad bowl", "recipe": "Grilled chicken, greens, olive oil.", "portion": "1 bowl"},
                {"name": "Salmon & quinoa", "recipe": "Bake salmon, quinoa, veggies.", "portion": "1 plate"},
            ],
            "exercises": [
                {"name": "Squats", "sets": 3, "reps": "10-12", "cues": "Neutral spine, knees track toes."},
                {"name": "Push-ups", "sets": 3, "reps": "8-12", "cues": "Braced core, full range."},
                {"name": "RDLs", "sets": 3, "reps": "8-10", "cues": "Hip hinge, flat back."},
                {"name": "Plank", "sets": 3, "reps": "30-45s", "cues": "Glutes on, ribs down."},
                {"name": "Brisk walk", "sets": 1, "reps": "20-30 min", "cues": "Nasal breathing pace."},
            ],
            "motivation": "Small steps daily compound into big wins."
        })
    return {
        "disclaimer": "This plan is educational and not medical advice. Consult a professional.",
        "week_plan": fallback_days
    }

# ============== State ==============
if "users" not in st.session_state:
    # demo user (password: demo123)
    st.session_state.users = {
        "demo@demo.com": {
            "password": sha256_hash("demo123"),
            "created": str(dt.datetime.utcnow())
        }
    }
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None
if "plans_generated" not in st.session_state:
    st.session_state.plans_generated = 0
if "weight_history" not in st.session_state:
    # week-based historical tracking
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday())  # Monday
    st.session_state.weight_history = pd.DataFrame({
        "week_start": [start - dt.timedelta(weeks=i) for i in range(6)][::-1],
        "weight": [75, 74.8, 74.5, 74.2, 74.0, 73.9],
    })
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of dicts with role/user

if "plan_data" not in st.session_state:
    st.session_state.plan_data = None

if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"

# ============== Sidebar: Personalization ==============
def build_sidebar():
    with st.sidebar:
        st.title("AI Wellness Coach Pro")
        st.caption("Personal coaching, habits, and insights")

        st.subheader("Profile & Goals")
        age = st.slider("Age", 16, 100, 30, key="age")
        gender = st.selectbox("Gender", ["Female", "Male", "Non-binary", "Prefer not to say"], key="gender")
        height_cm = st.slider("Height (cm)", 120, 220, 175, key="height_cm")
        weight_kg = st.slider("Current Weight (kg)", 30, 200, 75, key="weight_kg")
        target_weight_kg = st.slider("Target Weight (kg)", 30, 200, 70, key="target_weight_kg")
        diet_pref = st.selectbox("Diet Preference", ["None", "Vegetarian", "Vegan", "Pescatarian", "Keto", "Mediterranean"], key="diet_pref")
        fitness_goal = st.selectbox("Fitness Goal", ["Lose Weight", "Gain Weight", "Maintain Weight", "Endurance", "Wellness"], key="fitness_goal")

        # BMI
        h_m = height_cm / 100.0
        bmi = round(weight_kg / (h_m * h_m), 1) if h_m > 0 else 0
        st.metric("BMI", bmi)

        st.divider()
        st.caption("Sidebar is always visible.")
        st.caption("Built by Julius · https://julius.ai")

# ============== Auth Pages ==============
def page_login_signup():
    build_sidebar()
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Welcome to AI Wellness Coach Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sign in or create an account to continue.</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Login", "Sign Up", "Demo Login"])
    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            login_btn = st.form_submit_button("Login")
        if login_btn:
            if email in st.session_state.users and verify_password(password, st.session_state.users[email]["password"]):
                st.session_state.logged_in = True
                st.session_state.email = email
                st.success("Logged in successfully.")
                safe_rerun()
            else:
                st.error("Invalid credentials.")

    with tabs[1]:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            signup_btn = st.form_submit_button("Create Account")
        if signup_btn:
            if not email or "@" not in email:
                st.error("Please enter a valid email.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif email in st.session_state.users:
                st.error("Email already registered.")
            else:
                st.session_state.users[email] = {
                    "password": sha256_hash(password),
                    "created": str(dt.datetime.utcnow()),
                }
                st.success("Account created. Please log in.")
                time.sleep(0.6)
                safe_rerun()

    with tabs[2]:
        if st.button("Login as Demo User"):
            st.session_state.logged_in = True
            st.session_state.email = "demo@demo.com"
            st.success("Logged in as demo user.")
            safe_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============== Pages ==============
def page_dashboard():
    build_sidebar()
    st.header("📊 Profile & Progress Dashboard")

    # High-level metrics
    h = st.session_state.height_cm / 100.0
    bmi = round(st.session_state.weight_kg / (h * h), 1) if h > 0 else 0
    delta_w = round(st.session_state.weight_kg - st.session_state.target_weight_kg, 1)
    c1, c2, c3 = st.columns(3)
    c1.metric("BMI", bmi)
    c2.metric("Plans Generated", st.session_state.plans_generated)
    c3.metric("Current vs Goal (kg)", delta_w)

    st.subheader("Weight Log (Weekly)")
    cA, cB = st.columns([1, 2])
    with cA:
        new_w = st.number_input("Add Weight (kg)", min_value=30.0, max_value=300.0, value=float(st.session_state.weight_kg), step=0.1, key="new_weight_val")
        if st.button("Add To This Week"):
            today = dt.date.today()
            week_start = today - dt.timedelta(days=today.weekday())
            df = st.session_state.weight_history.copy()
            if (df.week_start == week_start).any():
                df.loc[df.week_start == week_start, "weight"] = new_w
            else:
                df = pd.concat([df, pd.DataFrame({"week_start": [week_start], "weight": [new_w]})], ignore_index=True)
            df = df.sort_values("week_start")
            st.session_state.weight_history = df
            st.success("Logged.")
            safe_rerun()
    with cB:
        df = st.session_state.weight_history.copy()
        df = df.sort_values("week_start")
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("week_start:T", title="Week Start"),
            y=alt.Y("weight:Q", title="Weight (kg)"),
            tooltip=["week_start", "weight"]
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

def _build_plan_prompt():
    age = st.session_state.age
    gender = st.session_state.gender
    height_cm = st.session_state.height_cm
    weight_kg = st.session_state.weight_kg
    target = st.session_state.target_weight_kg
    diet_pref = st.session_state.diet_pref
    fitness_goal = st.session_state.fitness_goal
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1) if h_m > 0 else 0

    prompt = f"""
Generate a structured 7-day wellness plan as STRICT JSON with this schema:

{{
  "disclaimer": "string (safety and medical disclaimer)",
  "week_plan": [
    {{
      "day": "Day 1",
      "calories": number,
      "meals": [
        {{"name":"string","recipe":"string","portion":"string"}},
        ...
      ],
      "exercises": [
        {{"name":"string","sets":number,"reps":"string","cues":"string"}},
        ...
      ],
      "motivation": "string"
    }},
    ... up to Day 7
  ]
}}

User profile:
- Age: {age}
- Gender: {gender}
- Height: {height_cm} cm
- Current weight: {weight_kg} kg
- Target weight: {target} kg
- BMI: {bmi}
- Diet preference: {diet_pref}
- Fitness goal: {fitness_goal}

Guidance:
- Each day include: a calorie target; at least 4 meals with recipes and portion sizes; 4–5 exercises with sets/reps and concise form cues; and 1 motivational tip.
- Calorie target should align with the fitness goal safely.
- Keep meals practical with ingredients common to most grocery stores.
- Keep exercise programming balanced and scalable.
- Output ONLY valid JSON, no markdown fences or commentary.
"""
    return prompt

def page_plan_generator():
    build_sidebar()
    st.header("🗓️ Plan Generator")
    st.write("Personalized, AI-generated 7-day plan with meals, exercises, and motivation. Includes an automatic disclaimer.")

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Generate 7-Day Plan"):
            with st.spinner("Generating plan..."):
                prompt = _build_plan_prompt()
                content = cached_generate_api_call(prompt)
                if content is None or (isinstance(content, str) and content.startswith("ERROR::")):
                    st.warning("OpenAI not available or error occurred. Using fallback plan.")
                    parsed = parse_weekly_plan(None)
                else:
                    parsed = parse_weekly_plan(content)
                st.session_state.plan_data = parsed
                st.session_state.plans_generated += 1
                st.success("Plan generated.")
        if st.button("Clear Plan"):
            st.session_state.plan_data = None
            st.info("Cleared plan.")

    with c2:
        if st.session_state.plan_data:
            plan = st.session_state.plan_data
            days = [d.get("day", f"Day {i+1}") for i, d in enumerate(plan.get("week_plan", []))]
            if not days:
                st.info("No plan days available yet.")
                return
            day_name = st.selectbox("Select Day", days)
            day = next((d for d in plan["week_plan"] if d.get("day") == day_name), plan["week_plan"][0])

            st.subheader(day.get("day", "Day"))
            st.metric("Daily Calorie Target", day.get("calories", "N/A"))

            st.markdown("#### Meals")
            for m in day.get("meals", []):
                st.markdown(f"- {sanitize_text(m.get('name',''))} — Portion: {sanitize_text(m.get('portion',''))}")
                st.caption(sanitize_text(m.get("recipe","")).strip())

            st.markdown("#### Exercises")
            for ex in day.get("exercises", []):
                name = sanitize_text(ex.get("name", ""))
                sets = ex.get("sets", "N/A")
                reps = sanitize_text(ex.get("reps", ""))
                cues = sanitize_text(ex.get("cues", ""))
                st.markdown(f"- {name}: {sets} sets × {reps}")
                st.caption(cues)

            st.markdown("#### Motivation")
            st.info(sanitize_text(day.get("motivation", "")))

            st.markdown("---")
            st.caption("Disclaimer")
            st.warning(sanitize_text(plan.get("disclaimer", "This plan is for educational purposes only.")))
        else:
            st.info("Click Generate to create a 7-day plan.")

def page_chat():
    build_sidebar()
    st.header("🤖 AI Health Chat")

    # Trim to last 10 messages
    if len(st.session_state.chat_history) > 20:
        st.session_state.chat_history = st.session_state.chat_history[-20:]

    with st.container():
        for msg in st.session_state.chat_history[-10:]:
            if msg["role"] == "user":
                st.markdown(f"**You:** {sanitize_text(msg['content'])}")
            else:
                st.markdown(f"**Coach:** {sanitize_text(msg['content
