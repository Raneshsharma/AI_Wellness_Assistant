# app.py
"""
AI Wellness Coach Pro - single-file Streamlit app (copy-paste ready)

Features:
- Robust sidebar forcing (CSS + ensure_sidebar_shown)
- Safe programmatic rerun across Streamlit versions (safe_rerun)
- Hashed demo users stored in session_state
- Sanitized AI outputs to avoid XSS
- Cached non-streamed API calls to reduce cost
- Streaming-friendly handler with safe extraction (best-effort for multiple SDK shapes)
- Resilient weekly-plan parser tolerant of format variations

USAGE:
- Save as app.py
- Set OPENAI_API_KEY in env or Streamlit secrets
- Run with: streamlit run app.py
"""

import os
import re
import html
import hashlib
from typing import Optional, List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt
from openai import OpenAI

# ---------------- Page config ----------------
st.set_page_config(page_title="AI Wellness Coach Pro", page_icon="💪", layout="wide", initial_sidebar_state="expanded")

# ---------------- Utilities ----------------
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def safe_text(ai_text: Optional[str]) -> str:
    """Escape HTML in AI outputs to avoid XSS while showing content as readable text."""
    if ai_text is None:
        return ""
    return html.escape(ai_text)

def trim_chat_history(messages: List[Dict[str, str]], keep_last: int = 10) -> List[Dict[str, str]]:
    if not messages:
        return messages
    head = []
    tail = messages[-keep_last:]
    if messages and messages[0].get("role") in ("assistant", "system"):
        head = [messages[0]]
    if head and head[0] in tail:
        return tail
    return head + tail

def safe_rerun():
    """Attempt to rerun app across Streamlit versions; fallback to user refresh notice."""
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass
    try:
        if hasattr(st, "rerun"):
            st.rerun()
            return
    except Exception:
        pass
    try:
        from streamlit.runtime.scriptrunner.script_runner import RerunException
        raise RerunException()
    except Exception:
        st.warning("Couldn't programmatically rerun the app in this Streamlit version. Please refresh the page (F5).")
        return

def ensure_sidebar_shown():
    """
    Force Streamlit to render the sidebar DOM early by writing a tiny element into it.
    This guarantees CSS selectors find the sidebar and prevents it from being missing.
    """
    try:
        st.sidebar.markdown("<div style='min-height:1px;opacity:0.01'></div>", unsafe_allow_html=True)
    except Exception:
        pass

# ---------------- OpenAI helpers ----------------
@st.cache_data(show_spinner=False)
def cached_generate_api_call(prompt: str, model: str = "gpt-4o", max_tokens: int = 800, temperature: float = 0.7) -> Optional[str]:
    """Cached wrapper around generate_api_call to reduce repeated costs for identical prompts."""
    return generate_api_call(prompt, model=model, max_tokens=max_tokens, temperature=temperature, use_cache=False)

def generate_api_call(prompt: str, model: str = "gpt-4o", max_tokens: int = 800, temperature: float = 0.7, use_cache: bool = True) -> Optional[str]:
    """Non-streamed API call with robust content extraction for multiple SDK response shapes."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert wellness coach with extensive knowledge in nutrition, fitness, and mental health."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
    except Exception as e:
        st.error(f"AI call failed: {e}")
        return None

    # Try common shapes
    content = None
    try:
        choice = resp.choices[0]
        if hasattr(choice, "message"):
            msg = choice.message
            if isinstance(msg, dict):
                content = msg.get("content")
            else:
                content = getattr(msg, "content", None)
    except Exception:
        content = None

    if not content:
        try:
            content = resp.choices[0].text
        except Exception:
            content = None

    if not content:
        try:
            content = str(resp)
        except Exception:
            content = None

    return content

def stream_chat_to_ui(messages_for_api: List[Dict[str, str]], model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """
    Stream the API response and append chunks to UI placeholder as they arrive.
    Returns accumulated final string. Best-effort extraction for multiple SDK chunk shapes.
    """
    accumulated = ""
    placeholder = st.empty()
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages_for_api,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature
        )
    except Exception as e:
        st.error(f"Streaming call failed: {e}")
        return ""

    try:
        for chunk in stream:
            text_piece = None
            try:
                # Common shapes: chunk.delta.content or chunk.choices[0].delta.content
                if hasattr(chunk, "delta"):
                    delta = getattr(chunk, "delta")
                    if isinstance(delta, dict):
                        text_piece = delta.get("content") or (delta.get("message") or {}).get("content")
                    else:
                        text_piece = getattr(delta, "content", None)
                else:
                    if hasattr(chunk, "choices"):
                        c = chunk.choices[0]
                        if hasattr(c, "delta"):
                            d = c.delta
                            if isinstance(d, dict):
                                text_piece = d.get("content")
                            else:
                                text_piece = getattr(d, "content", None)
            except Exception:
                text_piece = None

            if not text_piece:
                try:
                    if hasattr(chunk, "content"):
                        text_piece = getattr(chunk, "content", None)
                except Exception:
                    text_piece = None

            if not text_piece:
                try:
                    if hasattr(chunk, "choices"):
                        text_piece = getattr(chunk.choices[0], "text", None)
                except Exception:
                    text_piece = None

            if text_piece:
                accumulated += text_piece
                placeholder.markdown(safe_text(accumulated))
        return accumulated
    except Exception as e:
        st.error(f"Error while streaming response: {e}")
        return accumulated

# ---------------- Weekly plan parser ----------------
def parse_weekly_plan(plan_text: str) -> List[Dict[str, Any]]:
    """
    Robust parser that tolerates variation in headings and formatting.
    Returns list of up to 7 day dicts with keys: calories, diet [(name,instr)], exercise [(name,instr)], motivation, disclaimer
    """
    if not plan_text:
        return []

    text = plan_text.replace("\r\n", "\n")

    disc_match = re.search(r"(?is)(?:###\s*Disclaimer\s*###|###\s*Disclaimer\s*|Disclaimer\s*:)(.*?)(?=\n##\s*Day|\n#\s*Day|\n## Day|\Z)", text)
    disclaimer_text = disc_match.group(1).strip() if disc_match else "Please consult a professional before starting any new diet or exercise program."

    # Split by common "Day" headings
    day_blocks = re.split(r"(?im)(?:^##\s*Day\s*\d+\s*##|^##\s*Day\s*\d+|^#\s*Day\s*\d+|\n##\s*Day\s*\d+\s*##)", text)
    day_blocks = [b.strip() for b in day_blocks if b.strip()]

    parsed = []
    for block in day_blocks[:7]:
        cal_match = re.search(r"(?is)###\s*Estimated\s*Daily\s*Calorie\s*Target\s*###\s*(.*?)(?=\n###|\Z)", block)
        calories = cal_match.group(1).strip() if cal_match else ""
        diet_raw_match = re.search(r"(?is)###\s*Detailed\s*Diet\s*Plan\s*###\s*(.*?)(?=\n###|\Z)", block)
        diet_raw = diet_raw_match.group(1).strip() if diet_raw_match else ""
        exercise_raw_match = re.search(r"(?is)###\s*Detailed\s*Exercise\s*Plan\s*###\s*(.*?)(?=\n###|\Z)", block)
        exercise_raw = exercise_raw_match.group(1).strip() if exercise_raw_match else ""
        motivation_match = re.search(r"(?is)###\s*Motivational\s*Tip\s*###\s*(.*?)(?=\n###|\Z)", block)
        motivation = motivation_match.group(1).strip() if motivation_match else ""

        def extract_items(raw_text: str):
            items = []
            if not raw_text:
                return items
            # Primary pattern: **Name: Title**\nInstructions...
            pattern = re.findall(r"\*\*\s*([^:*]+?)(?:\s*[:\-]\s*([^*].*?))?\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", raw_text, re.DOTALL)
            if pattern:
                for name, title, instr in pattern:
                    display_name = (title.strip() if title else name.strip())
                    items.append((display_name, instr.strip()))
                return items
            # fallback: line-by-line grouping
            lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
            temp_name = None
            temp_text = []
            for ln in lines:
                bmatch = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", ln)
                if bmatch:
                    if temp_name:
                        items.append((temp_name, "\n".join(temp_text).strip()))
                    temp_name = bmatch.group(1).strip()
                    remainder = bmatch.group(2).strip()
                    temp_text = [remainder] if remainder else []
                else:
                    colon_match = re.match(r"^([A-Za-z ]{3,30})\s*:\s*(.*)$", ln)
                    if colon_match:
                        if temp_name:
                            items.append((temp_name, "\n".join(temp_text).strip()))
                        temp_name = colon_match.group(1).strip()
                        temp_text = [colon_match.group(2).strip()] if colon_match.group(2).strip() else []
                    else:
                        if temp_name:
                            temp_text.append(ln)
                        else:
                            temp_name = "Item"
                            temp_text = [ln]
            if temp_name:
                items.append((temp_name, "\n".join(temp_text).strip()))
            return items

        diet_items = extract_items(diet_raw)
        exercise_items = extract_items(exercise_raw)

        parsed.append({
            "calories": calories,
            "diet": diet_items,
            "exercise": exercise_items,
            "motivation": motivation,
            "disclaimer": disclaimer_text
        })

    while len(parsed) < 7:
        parsed.append({"calories": "", "diet": [], "exercise": [], "motivation": "", "disclaimer": disclaimer_text})

    return parsed

# ---------------- CSS / UI ----------------
def apply_css(css: str):
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def inject_video_background():
    css = """
    <style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .login-container { padding: 2rem; border-radius: 12px; max-width: 720px; margin: 0 auto; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def get_main_app_css() -> str:
    # Strong CSS to force sidebar visible and prevent overlap
    return """
    /* keep Streamlit chrome minimal */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { visibility: hidden !important; }

    [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        height: 100vh !important;
        width: 320px !important;
        max-width: 40vw !important;
        z-index: 99999 !important;
        background: linear-gradient(180deg, rgba(21,32,42,0.98), rgba(15,20,25,0.98)) !important;
        padding: 1rem 0.8rem !important;
        overflow-y: auto !important;
        box-shadow: 2px 0 18px rgba(0,0,0,0.5) !important;
        transform: none !important;
    }

    @media (min-width: 900px) {
        [data-testid="stAppViewContainer"] > .main {
            margin-left: 340px !important;
            transition: margin-left 0.15s ease !important;
            z-index: 1 !important;
        }
    }

    @media (max-width: 899px) {
        [data-testid="stAppViewContainer"] > .main {
            margin-left: 0 !important;
        }
        [data-testid="stSidebar"] {
            position: relative !important;
            width: auto !important;
            height: auto !important;
            box-shadow: none !important;
            z-index: 1 !important;
        }
    }

    .login-container, .main, .stApp { z-index: 1 !important; }
    [data-testid="stSidebar"] * { color: #fafafb !important; }
    .stButton>button { border-radius: 8px !important; }
    """

def create_enhanced_header():
    st.markdown("""
        <div style="text-align:center;padding:1rem 0;">
            <h1 style="font-size:2rem;margin-bottom:0.2rem;">💪 AI Wellness Coach Pro</h1>
            <p style="margin:0;color:#999;">Your Personal Journey to Better Health</p>
        </div>
    """, unsafe_allow_html=True)

# ---------------- Pages ----------------
def login_page():
    # ensure sidebar DOM exists so CSS can take effect even on login
    ensure_sidebar_shown()
    inject_video_background()
    st.markdown('<br><br>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center;">💪 AI Wellness Coach Pro</h2>', unsafe_allow_html=True)

        if 'user_db' not in st.session_state:
            st.session_state.user_db = {
                "demo": hash_pw("demo123"),
                "admin": hash_pw("admin123"),
                "user": hash_pw("password123")
            }

        if 'page' not in st.session_state:
            st.session_state.page = 'Login'

        col_login, col_signup = st.columns(2)
        with col_login:
            login_style = "🔑 Login" if st.session_state.page == 'Login' else "🔓 Login"
            if st.button(login_style, use_container_width=True, key="login_tab"):
                st.session_state.page = 'Login'
                safe_rerun()
        with col_signup:
            signup_style = "🚀 Sign Up" if st.session_state.page == 'Sign Up' else "📝 Sign Up"
            if st.button(signup_style, use_container_width=True, key="signup_tab"):
                st.session_state.page = 'Sign Up'
                safe_rerun()

        st.markdown('<br>', unsafe_allow_html=True)

        if st.session_state.page == 'Login':
            st.markdown("### 🔐 Welcome Back, Champion!")
            with st.form("login_form"):
                username = st.text_input("👤 Username")
                password = st.text_input("🔒 Password", type="password")
                col_submit, col_demo = st.columns([3,1])
                with col_submit:
                    submitted = st.form_submit_button("🚀 Login", use_container_width=True)
                with col_demo:
                    demo_login = st.form_submit_button("🎮 Demo", use_container_width=True)
                if demo_login:
                    username = "demo"
                    password = "demo123"
                    submitted = True
                if submitted:
                    if username in st.session_state.user_db and hash_pw(password) == st.session_state.user_db[username]:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.setdefault('goal_weight', 75)
                        st.session_state.setdefault('weight_log', [])
                        st.success("✅ Login successful! Redirecting...")
                        safe_rerun()
                    else:
                        st.error("❌ Invalid credentials.")
            st.markdown("""
                <div style="background: rgba(46,204,113,0.07); padding:0.8rem; border-radius:6px; margin-top:0.5rem;">
                    <strong>Demo account:</strong> demo / demo123
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 🌟 Create account")
            with st.form("signup_form"):
                new_username = st.text_input("👤 Choose Username")
                new_password = st.text_input("🔒 Password", type="password")
                confirm_password = st.text_input("🔒 Confirm Password", type="password")
                submitted = st.form_submit_button("🎯 Create Account", use_container_width=True)
                if submitted:
                    if not new_username or not new_password:
                        st.error("Fill all fields.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 chars.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif new_username in st.session_state.user_db:
                        st.error("Username exists.")
                    else:
                        st.session_state.user_db[new_username] = hash_pw(new_password)
                        st.success("Account created. Please login.")
                        st.session_state.page = 'Login'
                        safe_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

def main_app():
    # Ensure sidebar is present in DOM BEFORE applying CSS
    ensure_sidebar_shown()
    apply_css(get_main_app_css())

    with st.sidebar:
        st.markdown(f"""
            <div style="text-align:center;padding:1rem;background:linear-gradient(45deg,#e74c3c,#c0392b);border-radius:8px;">
                <h3 style="color:white;margin:0;">👋 Welcome</h3>
                <p style="color:#fff;margin:0;">{html.escape(st.session_state.get('username','User'))}</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            preserved = {'user_db': st.session_state.get('user_db')}
            st.session_state.clear()
            st.session_state.update(preserved)
            safe_rerun()

        st.divider()
        st.markdown("### 👤 Your Details")
        age = st.slider("🎂 Age", 16, 100, int(st.session_state.get('age', 25)))
        gender = st.selectbox("⚧ Gender", ("Male", "Female", "Other"))
        height = st.slider("📏 Height (cm)", 100, 250, int(st.session_state.get('height', 170)))
        weight = st.slider("⚖️ Weight (kg)", 30, 200, int(st.session_state.get('weight', 70)))
        st.session_state.update({'age': age, 'gender': gender, 'height': height, 'weight': weight})

        st.markdown("### 🎯 Preferences")
        diet_preference = st.selectbox("🥗 Diet", ("No Preference", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean"))
        fitness_goal = st.selectbox("🏆 Goal", ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance", "General Wellness"))

        st.divider()
        generate_button = st.button("✨ Generate My 7-Day Plan!", use_container_width=True)

    create_enhanced_header()

    profile_tab, plan_tab, chat_tab = st.tabs(["📊 Profile & Progress", "📅 Plan Generator", "💬 AI Health Chat"])

    # ---------- Profile Tab ----------
    with profile_tab:
        st.markdown("## 📈 Dashboard")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            bmi = weight / ((height/100) ** 2) if height > 0 else 0
            st.metric("BMI", f"{bmi:.1f}")
        with col2:
            st.metric("Plans Generated", len(st.session_state.get('weight_log', [])))
        with col3:
            st.metric("Current Weight", f"{weight} kg")
        with col4:
            goal = st.session_state.get('goal_weight', 75)
            st.metric("To Goal", f"{(weight - goal):+.1f} kg")

        st.divider()
        st.markdown("### ✍️ Log Progress")
        current_weight = st.number_input("Today's Weight (kg)", min_value=30.0, max_value=200.0, value=float(weight))
        if st.button("📝 Log Weight"):
            st.session_state.setdefault('weight_log', []).append({"week": len(st.session_state.get('weight_log', [])) + 1, "weight": float(current_weight)})
            st.success("Logged weight.")

        st.divider()
        st.markdown("### 📊 Progress Chart")
        if st.session_state.get('weight_log'):
            df = pd.DataFrame(st.session_state.weight_log)
            chart = alt.Chart(df).mark_line(point=True).encode(x=alt.X('week:O'), y=alt.Y('weight:Q'), tooltip=['week', 'weight']).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Log weight to see chart.")

    # ---------- Plan Generator Tab ----------
    with plan_tab:
        st.markdown("## 📅 Plan Generator")
        st.info("Your sidebar inputs prefill the generation. Click to generate.")
        if generate_button:
            with st.spinner("Generating 7-day plan..."):
                prompt = f"""
                Act as an expert wellness coach. Provide a full 7-day plan with:
                ### Disclaimer ###
                For each day: ## Day X ## with subheadings:
                ### Estimated Daily Calorie Target ###
                ### Detailed Diet Plan ###
                ### Detailed Exercise Plan ###
                ### Motivational Tip ###
                User: Age {age}, Gender {gender}, Height {height} cm, Weight {weight} kg. Diet: {diet_preference}. Goal: {fitness_goal}.
                Diet: 4 meals/day (Breakfast, Lunch, Snack, Dinner) each with **Meal Name: Specific Dish** and prep/portions.
                Exercise: 4-5 exercises/day with sets/reps/duration/form cues.
                """
                full_plan = generate_api_call(prompt)
                if full_plan:
                    st.session_state.weekly_plan_raw = full_plan
                    st.session_state.weekly_plan = parse_weekly_plan(full_plan)
                    st.success("Plan generated.")
                else:
                    st.error("Failed to generate plan.")

        if st.session_state.get('weekly_plan'):
            weeks = st.session_state.weekly_plan
            day_idx = st.selectbox("Select day", list(range(len(weeks))), format_func=lambda i: f"📅 Day {i+1}")
            day = weeks[day_idx]
            st.markdown(f"### Day {day_idx+1} - Calories: {safe_text(day.get('calories',''))}")
            st.markdown("#### Meals")
            if day['diet']:
                for name, instr in day['diet']:
                    st.markdown(f"**{html.escape(name)}**")
                    st.markdown(safe_text(instr))
            else:
                st.info("No meal data.")

            st.markdown("#### Exercises")
            if day['exercise']:
                for name, instr in day['exercise']:
                    st.markdown(f"**{html.escape(name)}**")
                    st.markdown(safe_text(instr))
            else:
                st.info("No exercise data.")

            st.warning(f"⚠️ Disclaimer: {safe_text(day.get('disclaimer',''))}")

    # ---------- Chat Tab ----------
    with chat_tab:
        st.markdown("## 🤖 AI Health Chat")
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your AI Health Coach. Ask me anything."}]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(safe_text(msg["content"]))

        user_input = st.chat_input("Ask about fitness, nutrition, or your plan...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.messages = trim_chat_history(st.session_state.messages, keep_last=10)
            system_prompt = {"role": "system", "content": "You are an expert AI Health Coach; be practical, evidence-based, and cautious."}
            messages_for_api = [system_prompt] + st.session_state.messages[-10:]
            with st.chat_message("assistant", avatar="🤖"):
                reply = stream_chat_to_ui(messages_for_api)
                if reply:
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    err = "Sorry — couldn't get a reply right now."
                    st.session_state.messages.append({"role": "assistant", "content": err})
                    st.error(err)

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = [{"role": "assistant", "content": "Chat cleared. How can I help?"}]
            safe_rerun()

# ---------------- Entry point ----------------
api_key = os.environ.get("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None)
if not api_key:
    st.error("OpenAI API key required. Set OPENAI_API_KEY env var or Streamlit secrets.")
    st.stop()

try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

st.session_state.setdefault('logged_in', False)

# Route to pages
if st.session_state.logged_in:
    main_app()
else:
    login_page()
