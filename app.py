import os
import re
import json
import time
import html
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

# ===================== Page Config =====================
st.set_page_config(
    page_title="AI Wellness Coach Pro",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================== CSS & Theme =====================
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
      color: #e8eaed;
    }
    @keyframes gradientShift{
      0%{background-position:0% 50%;}
      50%{background-position:100% 50%;}
      100%{background-position:0% 50%;}
    }
    /* Login container styling */
    .login-card{
      max-width: 520px;
      margin: 10vh auto;
      padding: 28px 24px;
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
      opacity: 0.85;
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
    /* Inputs, metrics */
    .block-container{padding-top: 2rem;}
    .stMetric, .stAlert, .stTextInput, .stSelectbox, .stNumberInput, .stSlider{
      border-radius: 10px;
    }
    #MainMenu{visibility:hidden;}
    footer{visibility:hidden;}
    """
    apply_css(css)

ensure_sidebar_shown()

# ===================== Utilities & Security =====================
def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return sha256_hash(plain) == hashed

def sanitize_text(s: str) -> str:
    if s is None:
        return ""
    return html.escape(str(s)).strip()

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()  # older versions fallback
        except Exception:
            pass

def bmi_calc(weight_kg: float, height_cm: float) -> float:
    try:
        h_m = max(0.3, float(height_cm) / 100.0)
        w = max(1.0, float(weight_kg))
        return round(w / (h_m * h_m), 1)
    except Exception:
        return 0.0

def weight_delta(current_kg: float, goal_kg: float) -> float:
    try:
        return round(float(current_kg) - float(goal_kg), 1)
    except Exception:
        return 0.0

def get_openai_client():
    # Prioritize state key if user sets in Settings
    key = st.session_state.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    if not key or not OPENAI_AVAILABLE:
        return None
    try:
        return OpenAI(api_key=key)
    except Exception:
        return None

# ===================== State Init =====================
def init_state():
    if "users" not in st.session_state:
        # demo user: demo@demo.com / demo
        st.session_state.users = {
            "demo@demo.com": sha256_hash("demo")
        }
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "nav" not in st.session_state:
        st.session_state.nav = "Dashboard"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # list of dicts: {"role": "user"|"assistant", "content": "..."}
    if "weight_log" not in st.session_state:
        st.session_state.weight_log = pd.DataFrame(columns=["date", "weight_kg"])
    if "plan_data" not in st.session_state:
        st.session_state.plan_data = None
    if "plans_generated" not in st.session_state:
        st.session_state.plans_generated = 0
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "age": 30,
            "height_cm": 175,
            "weight_kg": 75.0,
            "gender": "Male",
            "diet_pref": "Balanced",
            "fitness_goal": "Wellness",
            "target_goal_weight": 72.0,
        }
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = None

init_state()

# ===================== Cached API Helpers =====================
@st.cache_data(show_spinner=False, ttl=3600)
def cached_generate_api_call(prompt: str) -> str:
    client = get_openai_client()
    if client is None:
        # Return sentinel so caller can fallback
        return "ERROR::NO_OPENAI"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise wellness planner that outputs strict JSON following the requested schema only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return "ERROR::" + str(e)

# ===================== Plan Parsing & Fallback =====================
def local_week_plan_fallback() -> dict:
    # Deterministic 7-day plan for offline mode
    meals = [
        {"name": "Oatmeal with berries", "portion": "1 bowl", "recipe": "Cook oats in water/milk, top with berries."},
        {"name": "Grilled chicken salad", "portion": "1 plate", "recipe": "Greens + grilled chicken + olive oil."},
        {"name": "Greek yogurt + nuts", "portion": "1 cup", "recipe": "Top with almonds and honey."},
        {"name": "Salmon with quinoa", "portion": "1 plate", "recipe": "Bake salmon, serve with quinoa and veggies."},
    ]
    exercises = [
        {"name": "Brisk walk", "sets": 1, "reps": "25 min", "cues": "Upright posture, steady pace."},
        {"name": "Bodyweight squats", "sets": 3, "reps": "12", "cues": "Knees track toes, neutral spine."},
        {"name": "Push-ups (incline if needed)", "sets": 3, "reps": "8-10", "cues": "Tight core, full range."},
        {"name": "Plank", "sets": 3, "reps": "30-45s", "cues": "Neutral neck, ribs down."},
        {"name": "Stretching", "sets": 1, "reps": "10 min", "cues": "Slow breathing."},
    ]
    week = []
    for i in range(7):
        week.append({
            "day": f"Day {i+1}",
            "calories": 2200 if i % 2 == 0 else 2000,
            "meals": meals,
            "exercises": exercises,
            "motivation": "Small consistent steps beat occasional sprints."
        })
    return {
        "week_plan": week,
        "disclaimer": "This plan is for educational purposes only and does not replace professional medical advice.",
    }

def parse_weekly_plan(text: str) -> dict:
    if not text or text.startswith("ERROR::"):
        return local_week_plan_fallback()
    # Try to extract JSON block if the model wrapped it in markdown
    json_text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", json_text, re.S)
    if fence_match:
        json_text = fence_match.group(1)
    try:
        data = json.loads(json_text)
        # Minimal shape validation
        if "week_plan" in data and isinstance(data["week_plan"], list):
            return data
    except Exception:
        pass
    # Heuristic fallback if not valid JSON
    return local_week_plan_fallback()

def _build_plan_prompt() -> str:
    p = st.session_state.profile
    schema = {
        "type": "object",
        "properties": {
            "week_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string"},
                        "calories": {"type": "integer"},
                        "meals": {"type": "array", "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "portion": {"type": "string"},
                                "recipe": {"type": "string"}
                            },
                            "required": ["name","portion","recipe"]
                        }},
                        "exercises": {"type": "array", "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "string"},
                                "cues": {"type": "string"}
                            },
                            "required": ["name","sets","reps","cues"]
                        }},
                        "motivation": {"type": "string"}
                    },
                    "required": ["day","calories","meals","exercises","motivation"]
                }
            },
            "disclaimer": {"type": "string"}
        },
        "required": ["week_plan", "disclaimer"]
    }
    prompt = f"""
Generate a 7-day wellness plan as strict JSON only (no extra text). Personalize to:
- Age: {p['age']}
- Gender: {p['gender']}
- Height_cm: {p['height_cm']}
- Weight_kg: {p['weight_kg']}
- Diet: {p['diet_pref']}
- Fitness Goal: {p['fitness_goal']}
- Target Goal Weight: {p['target_goal_weight']}

For each day include:
- calories (integer daily target)
- 4+ meals with name, portion, and short recipe with quantities
- 4-5 exercises with sets (integer), reps (e.g., 10-12 or 30s), and form cues (1 sentence)
- motivation tip (1 sentence)

Add a global medical disclaimer string.

JSON schema to follow exactly:
{json.dumps(schema)}
"""
    return prompt

# ===================== Streaming Chat =====================
def stream_chat_to_ui(user_prompt: str) -> str:
    # maintain memory: last 10 messages
    history = st.session_state.chat_history[-10:]
    messages = [{"role": "system", "content": "You are an evidence-based, friendly AI health coach. Keep replies concise and practical."}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    client = get_openai_client()
    if client is None:
        # fallback local heuristic
        return local_coach(user_prompt)

    try:
        placeholder = st.empty()
        full_text = ""
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
            stream=True,
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                full_text += delta
                placeholder.markdown(sanitize_text(full_text))
        return full_text if full_text.strip() else "I am here to help with wellness questions!"
    except Exception as e:
        st.error("Streaming error: " + str(e))
        return local_coach(user_prompt)

def local_coach(q: str) -> str:
    ql = q.lower()
    if "sleep" in ql:
        return "Aim for a consistent sleep window, dim lights 60 minutes before bed, and avoid caffeine after 2 pm. Try 4-7-8 breathing."
    if "stress" in ql:
        return "Use 2-minute box-breathing breaks every few hours, take a short walk, and keep a brief to-do list to reduce cognitive load."
    if "weight" in ql or "fat" in ql:
        return "Focus on protein at each meal, mostly whole foods, and 7-9k daily steps. Keep a small calorie deficit if targeting fat loss."
    if "workout" in ql or "exercise" in ql or "fitness" in ql:
        return "Target 3 strength days with full-body basics and 2 low-intensity cardio sessions. Keep 1-2 rest days."
    return "Keep it simple: pick one small habit for today, do it, and celebrate the win."

# ===================== Sidebar =====================
def build_sidebar():
    with st.sidebar:
        st.title("AI Wellness Coach")
        st.caption("Personal coaching, daily habits, and insights")

        nav = st.radio(
            "Navigation",
            options=["Dashboard", "Plan Generator", "Chat", "Settings"],
            index=["Dashboard", "Plan Generator", "Chat", "Settings"].index(
                st.session_state.nav if st.session_state.nav in ["Dashboard", "Plan Generator", "Chat", "Settings"] else "Dashboard"
            )
        )
        st.session_state.nav = nav

        st.divider()
        st.subheader("Profile")
        p = st.session_state.profile
        p["age"] = st.slider("Age", 10, 100, int(p["age"]))
        p["gender"] = st.selectbox("Gender", ["Male","Female","Non-binary","Prefer not to say"], index=["Male","Female","Non-binary","Prefer not to say"].index(p["gender"]) if p["gender"] in ["Male","Female","Non-binary","Prefer not to say"] else 0)
        p["height_cm"] = st.number_input("Height (cm)", 100, 230, int(p["height_cm"]), step=1)
        p["weight_kg"] = st.number_input("Weight (kg)", 25.0, 300.0, float(p["weight_kg"]), step=0.1)
        p["diet_pref"] = st.selectbox("Diet Preference", ["Balanced","Vegetarian","Vegan","Keto","Paleo","Mediterranean","Other"], index=["Balanced","Vegetarian","Vegan","Keto","Paleo","Mediterranean","Other"].index(p["diet_pref"]) if p["diet_pref"] in ["Balanced","Vegetarian","Vegan","Keto","Paleo","Mediterranean","Other"] else 0)
        p["fitness_goal"] = st.selectbox("Fitness Goal", ["Lose Weight","Gain Weight","Maintain Weight","Endurance","Wellness"], index=["Lose Weight","Gain Weight","Maintain Weight","Endurance","Wellness"].index(p["fitness_goal"]) if p["fitness_goal"] in ["Lose Weight","Gain Weight","Maintain Weight","Endurance","Wellness"] else 4)
        p["target_goal_weight"] = st.number_input("Target Goal Weight (kg)", 25.0, 300.0, float(p["target_goal_weight"]), step=0.1)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_email = None
                safe_rerun()
        with col_b:
            st.caption("Logged in as: " + (st.session_state.user_email or "Guest"))

# ===================== Auth =====================
def login_page():
    build_sidebar()
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Welcome to AI Wellness Coach Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sign in, sign up, or use the demo login to explore.</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Login", "Sign Up", "Demo Login"])

    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
        if submit:
            if email.strip() in st.session_state.users and verify_password(pw, st.session_state.users[email.strip()]):
                st.session_state.logged_in = True
                st.session_state.user_email = email.strip()
                st.success("Signed in.")
                safe_rerun()
            else:
                st.error("Invalid email or password.")

    with tabs[1]:
        with st.form("signup_form"):
            email2 = st.text_input("Email (new)")
            pw2 = st.text_input("Password (min 3 chars)", type="password")
            submit2 = st.form_submit_button("Create Account")
        if submit2:
            if len(email2.strip()) == 0 or len(pw2) < 3:
                st.error("Please provide a valid email and 3+ char password.")
            elif email2.strip() in st.session_state.users:
                st.error("User already exists.")
            else:
                st.session_state.users[email2.strip()] = sha256_hash(pw2)
                st.success("Account created. Please log in.")

    with tabs[2]:
        if st.button("Use Demo Account"):
            st.session_state.logged_in = True
            st.session_state.user_email = "demo@demo.com"
            st.info("Logged in as demo.")
            safe_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ===================== Dashboard =====================
def ensure_weight_log_df():
    if "weight_log" not in st.session_state or not isinstance(st.session_state.weight_log, pd.DataFrame):
        st.session_state.weight_log = pd.DataFrame(columns=["date", "weight_kg"])
    if st.session_state.weight_log.empty:
        # seed with current weight this week
        today = pd.to_datetime(dt.date.today())
        st.session_state.weight_log = pd.DataFrame([{"date": today, "weight_kg": float(st.session_state.profile["weight_kg"])}])

def page_dashboard():
    build_sidebar()
    st.header("📊 Profile & Progress Dashboard")

    p = st.session_state.profile
    bmi = bmi_calc(p["weight_kg"], p["height_cm"])
    delta = weight_delta(p["weight_kg"], p["target_goal_weight"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BMI", str(bmi))
    c2.metric("Plans Generated", str(st.session_state.plans_generated))
    c3.metric("Current Weight (kg)", str(p["weight_kg"]))
    c4.metric("Delta to Goal (kg)", str(delta))

    st.subheader("Log Your Weight")
    ensure_weight_log_df()
    log_date = st.date_input("Date", value=dt.date.today())
    log_weight = st.number_input("Weight (kg)", min_value=25.0, max_value=300.0, value=float(p["weight_kg"]), step=0.1)
    add_btn = st.button("Add Entry")
    if add_btn:
        df = st.session_state.weight_log.copy()
        new_row = {"date": pd.to_datetime(log_date), "weight_kg": float(log_weight)}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = df.sort_values("date").reset_index(drop=True)
        st.session_state.weight_log = df
        st.success("Entry added.")

    df = st.session_state.weight_log.copy()
    if not df.empty:
        st.subheader("Progress Over Time")
        df_plot = df.sort_values("date")
        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("weight_kg:Q", title="Weight (kg)"),
            tooltip=["date:T", "weight_kg:Q"],
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Weekly Trend")
        dfw = df_plot.copy()
        dfw["week"] = dfw["date"].dt.to_period("W").astype(str)
        weekly = dfw.groupby("week", as_index=False)["weight_kg"].mean()
        wchart = alt.Chart(weekly).mark_bar().encode(
            x=alt.X("week:N", sort=None, title="Week"),
            y=alt.Y("weight_kg:Q", title="Avg Weight (kg)"),
            tooltip=["week:N", "weight_kg:Q"],
        ).properties(height=240)
        st.altair_chart(wchart, use_container_width=True)
    else:
        st.info("No weight entries yet. Add your first entry above.")

# ===================== Plan Generator =====================
def page_plan_generator():
    build_sidebar()
    st.header("🗓️ AI-Generated 7-Day Wellness Plan")
    st.caption("Generates meals, exercises, motivation, and includes an automatic disclaimer.")

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Generate 7-Day Plan"):
            with st.spinner("Generating plan..."):
                prompt = _build_plan_prompt()
                content = cached_generate_api_call(prompt)
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
            days = [d.get("day", "Day " + str(i+1)) for i, d in enumerate(plan.get("week_plan", []))]
            if not days:
                st.info("No plan days available yet.")
                return
            view_mode = st.toggle("Show full week at once", value=False)
            if not view_mode:
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
                st.info(sanitize_text(day
                # ... (Previous code up to the incomplete line)

                st.markdown("#### Motivation")
                st.info(sanitize_text(day.get("motivation","")))

                st.caption(f"**Disclaimer:** {sanitize_text(plan.get('disclaimer', 'Consult a health professional before starting any new diet or exercise regimen.'))}")
            
            else: # Show full week at once
                for day in plan.get("week_plan", []):
                    st.markdown("---")
                    st.subheader(f"📅 {day.get('day', 'Day')}")
                    st.metric("Daily Calorie Target", day.get("calories", "N/A"))

                    col_m, col_e = st.columns(2)
                    with col_m:
                        st.markdown("##### Meals")
                        for m in day.get("meals", []):
                            st.markdown(f"**{sanitize_text(m.get('name',''))}** — Portion: {sanitize_text(m.get('portion',''))}")
                            st.caption(sanitize_text(m.get("recipe","")).strip())

                    with col_e:
                        st.markdown("##### Exercises")
                        for ex in day.get("exercises", []):
                            name = sanitize_text(ex.get("name", ""))
                            sets = ex.get("sets", "N/A")
                            reps = sanitize_text(ex.get("reps", ""))
                            cues = sanitize_text(ex.get("cues", ""))
                            st.markdown(f"**{name}**: {sets} sets × {reps}")
                            st.caption(cues)
                    
                    st.info(f"**Motivation:** {sanitize_text(day.get('motivation',''))}")

                st.markdown("---")
                st.caption(f"**Disclaimer:** {sanitize_text(plan.get('disclaimer', 'Consult a health professional before starting any new diet or exercise regimen.'))}")
        else:
            st.info("No plan generated yet. Hit the 'Generate 7-Day Plan' button to create your personalized weekly wellness plan based on your profile settings in the sidebar.")

# ===================== Chat =====================
def page_chat():
    build_sidebar()
    st.header("💬 AI Wellness Coach Chat")
    st.caption("Ask questions about diet, exercise, stress, or general wellness. The coach maintains context.")
    
    # Display chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(sanitize_text(message["content"]))

    # Chat input
    if user_prompt := st.chat_input("Ask your wellness question..."):
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(sanitize_text(user_prompt))

        # Get and stream AI response
        with st.chat_message("assistant"):
            with st.spinner("Coach is thinking..."):
                response_content = stream_chat_to_ui(user_prompt)
        
        # Add assistant message to history
        st.session_state.chat_history.append({"role": "assistant", "content": response_content})
        safe_rerun() # Re-run to update the full history display properly after streaming

    # Clear chat history button
    if st.session_state.chat_history:
        st.divider()
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.info("Chat history cleared.")
            safe_rerun()

# ===================== Settings =====================
def page_settings():
    build_sidebar()
    st.header("⚙️ Settings")
    
    st.subheader("OpenAI API Key (Optional)")
    st.caption("Provide your own key to power the AI features if you are running this app locally without the key set in environment variables.")

    # Get current key, prioritizing the one in session state
    current_key = st.session_state.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")

    new_key = st.text_input(
        "Enter OpenAI API Key", 
        type="password", 
        value=current_key or "",
        placeholder="sk-..."
    )

    if st.button("Save API Key"):
        if new_key:
            st.session_state.openai_api_key = new_key.strip()
            # Clear cache so new client is initialized on next API call
            cached_generate_api_call.clear() 
            st.success("API Key saved.")
        else:
            st.session_state.openai_api_key = None
            cached_generate_api_call.clear() 
            st.warning("API Key cleared. AI features will use local fallbacks if available.")

    if current_key:
        st.markdown(f"**Current Status:** Key is set (Starts with `{'sk-...' if current_key.startswith('sk-') else current_key[:4]}...`).")
    else:
        st.error("OpenAI API Key is not set. AI features will rely on local fallbacks.")
        if not OPENAI_AVAILABLE:
            st.warning("The `openai` package could not be imported. AI features are disabled.")
    
    st.divider()

    st.subheader("User Management")
    st.markdown(f"**Total Registered Users:** `{len(st.session_state.users)}`")
    st.markdown(f"**Current User Email:** `{st.session_state.user_email}`")
    
    if st.button("Factory Reset (Clear All User Data)", help="This will log you out and delete all registered users, weight logs, and chat history."):
        if st.warning("Are you sure? This action is irreversible."):
            st.session_state.clear()
            init_state() # Reinitialize with default state
            st.success("Application state reset.")
            safe_rerun()

# ===================== Main App Logic =====================
if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        # User is logged in, navigate based on session state
        if st.session_state.nav == "Dashboard":
            page_dashboard()
        elif st.session_state.nav == "Plan Generator":
            page_plan_generator()
        elif st.session_state.nav == "Chat":
            page_chat()
        elif st.session_state.nav == "Settings":
            page_settings()
        else:
            # Fallback for unexpected nav state
            st.session_state.nav = "Dashboard"
            safe_rerun()
