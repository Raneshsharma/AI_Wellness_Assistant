# streamlit_app.py
import os
import re
import time
import html
import hashlib
from typing import Optional, List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt

# --- OpenAI client import (same as yours) ---
from openai import OpenAI

# ----------------- Configuration -----------------
st.set_page_config(page_title="AI Wellness Coach Pro", page_icon="💪", layout="wide", initial_sidebar_state="expanded")

# ---------- Utility Helpers ----------

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def safe_text(ai_text: Optional[str]) -> str:
    """Escape any HTML in AI responses to prevent XSS; still allows Markdown characters to show as text."""
    if ai_text is None:
        return ""
    return html.escape(ai_text)

def trim_chat_history(messages: List[Dict[str, str]], keep_last: int = 10) -> List[Dict[str, str]]:
    """Keep only the last `keep_last` messages (plus the initial assistant prompt if present)."""
    if not messages:
        return messages
    # Keep system/assistant welcome + last N
    # We'll treat the first assistant/system message as the base context if length > keep_last
    head = []
    tail = messages[-keep_last:]
    # If first message is assistant with a greeting, keep it
    if messages and messages[0].get("role") in ("assistant", "system"):
        head = [messages[0]]
    # Ensure there is no duplication if tail already contains that head
    if head and head[0] in tail:
        return tail
    return head + tail

# ----------------- OpenAI wrapper with robust extraction & caching -----------------

@st.cache_data(show_spinner=False)
def cached_generate_api_call(prompt: str, model: str = "gpt-4o", max_tokens: int = 800, temperature: float = 0.7) -> Optional[str]:
    """Cached wrapper for non-streamed API calls. Caches by prompt/model to reduce cost for repeated calls."""
    return generate_api_call(prompt, model=model, max_tokens=max_tokens, temperature=temperature, use_cache=False)

def generate_api_call(prompt: str, model: str = "gpt-4o", max_tokens: int = 800, temperature: float = 0.7, use_cache: bool = True) -> Optional[str]:
    """
    Call OpenAI API and attempt to safely extract the text content.
    If use_cache=True it's expected the caller uses cached_generate_api_call instead (decorated).
    """
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

    # Several possible shapes; attempt to extract safely
    content = None
    try:
        # shape: resp.choices[0].message.content (object-like)
        choice = resp.choices[0]
        if hasattr(choice, "message"):
            msg = choice.message
            # msg might be dict-like or object
            if isinstance(msg, dict):
                content = msg.get("content") or msg.get("content", None)
            else:
                content = getattr(msg, "content", None)
    except Exception:
        content = None

    if not content:
        try:
            # older shape: resp.choices[0].text
            content = resp.choices[0].text
        except Exception:
            content = None

    if not content:
        # fallback: string representation
        try:
            content = str(resp)
        except Exception:
            content = None

    return content

def stream_chat_to_ui(messages_for_api: List[Dict[str, str]], model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """
    Stream the API response and display it in the UI as it arrives.
    This function iterates over the streaming generator returned by the SDK and appends content.
    The SDK chunk structure can vary; this function tries common shapes.
    Returns the accumulated final text.
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

    # Iterate and extract incremental content
    try:
        for chunk in stream:
            # chunk may have content in different structures: chunk.delta, chunk.choices[0].delta, etc.
            text_piece = None
            # Try common patterns
            try:
                # Some SDKs return chunk.delta.content
                if hasattr(chunk, "delta"):
                    delta = getattr(chunk, "delta")
                    if isinstance(delta, dict):
                        text_piece = delta.get("content") or delta.get("message", {}).get("content")
                    else:
                        text_piece = getattr(delta, "get", lambda k, d=None: None)("content")
                else:
                    # Some libs return chunk.choices[0].delta.content
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

            # fallback: try chunk.content or chunk.choices[0].text
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
                # show escaped content to avoid HTML injection
                placeholder.markdown(safe_text(accumulated))
        # Final safe return
        return accumulated
    except Exception as e:
        st.error(f"Error while streaming response: {e}")
        return accumulated

# ----------------- Robust parsing of weekly plan -----------------

def parse_weekly_plan(plan_text: str) -> List[Dict[str, Any]]:
    """
    Attempt to parse a 7-day weekly plan with forgiving regexes.
    Returns list of day dicts with keys: calories, diet (list of (name,instructions)), exercise (list of (name,instructions)), motivation, disclaimer
    """
    if not plan_text:
        return []

    # Normalize newlines
    text = plan_text.replace("\r\n", "\n")

    # Extract disclaimer: look for "Disclaimer" heading variants
    disc_match = re.search(r"(?is)(?:###\s*Disclaimer\s*###|###\s*Disclaimer\s*|###\s*Disclaimer\s*:)(.*?)(?=\n##\s*Day|\n#\s*Day|\n## Day|\Z)", text)
    disclaimer_text = disc_match.group(1).strip() if disc_match else "Please consult a professional before starting any new diet or exercise program."

    # Split into day blocks robustly (accept multiple heading styles)
    day_blocks = re.split(r"(?im)(?:^##\s*Day\s*\d+\s*##|^##\s*Day\s*\d+|^#\s*Day\s*\d+|\n##\s*Day\s*\d+\s*##)", text)
    # Filter out empty and the portion before day1 (which might contain disclaimer)
    day_blocks = [b.strip() for b in day_blocks if b.strip()]

    parsed = []
    # Each block hopefully corresponds to one day (take at most 7)
    for block in day_blocks[:7]:
        # calories
        cal_match = re.search(r"(?is)###\s*Estimated\s*Daily\s*Calorie\s*Target\s*###\s*(.*?)(?=\n###|\Z)", block)
        calories = cal_match.group(1).strip() if cal_match else ""

        # diet block raw
        diet_raw_match = re.search(r"(?is)###\s*Detailed\s*Diet\s*Plan\s*###\s*(.*?)(?=\n###|\Z)", block)
        diet_raw = diet_raw_match.group(1).strip() if diet_raw_match else ""

        # exercise raw
        exercise_raw_match = re.search(r"(?is)###\s*Detailed\s*Exercise\s*Plan\s*###\s*(.*?)(?=\n###|\Z)", block)
        exercise_raw = exercise_raw_match.group(1).strip() if exercise_raw_match else ""

        # motivation
        motivation_match = re.search(r"(?is)###\s*Motivational\s*Tip\s*###\s*(.*?)(?=\n###|\Z)", block)
        motivation = motivation_match.group(1).strip() if motivation_match else ""

        # Helper to extract **Name: Description** or **Name** newline description
        def extract_items(raw_text: str):
            items = []
            if not raw_text:
                return items
            # Try to find patterns like **Meal Name: Dish**\ninstructions...
            pattern = re.findall(r"\*\*\s*([^:*]+?)(?:\s*[:\-]\s*([^*].*?))?\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", raw_text, re.DOTALL)
            if pattern:
                for name, title, instr in pattern:
                    display_name = (title.strip() if title else name.strip())
                    items.append((display_name, instr.strip()))
                return items
            # fallback: split on headings or numbered lines
            lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
            # group by lines starting with bold or uppercase meal names
            temp_name = None
            temp_text = []
            for ln in lines:
                # if ln starts with bold markers
                bmatch = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", ln)
                if bmatch:
                    if temp_name:
                        items.append((temp_name, "\n".join(temp_text).strip()))
                    temp_name = bmatch.group(1).strip()
                    remainder = bmatch.group(2).strip()
                    temp_text = [remainder] if remainder else []
                else:
                    # treat lines that look like "Breakfast: " as name lines
                    colon_match = re.match(r"^([A-Za-z ]{3,30})\s*:\s*(.*)$", ln)
                    if colon_match:
                        if temp_name:
                            items.append((temp_name, "\n".join(temp_text).strip()))
                        temp_name = colon_match.group(1).strip()
                        temp_text = [colon_match.group(2).strip()] if colon_match.group(2).strip() else []
                    else:
                        # continuation
                        if temp_name:
                            temp_text.append(ln)
                        else:
                            # put under generic unnamed meal
                            temp_name = "Meal"
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

    # If parsed days < 7, pad with empty days
    while len(parsed) < 7:
        parsed.append({"calories": "", "diet": [], "exercise": [], "motivation": "", "disclaimer": disclaimer_text})

    return parsed

# ----------------- CSS / UI helpers (kept from your file but sanitized use) -----------------

def apply_css(css_style: str):
    st.markdown(f"<style>{css_style}</style>", unsafe_allow_html=True)

def inject_video_background():
    """Injects decorative CSS/HTML. This part is purely presentation; AI outputs are always escaped before insertion elsewhere."""
    background_css = """
    <style>
    /* minimal styling (kept concise to avoid huge block) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAppViewContainer"] > .main { padding-top: 2rem; min-height: 100vh; }
    .login-container{ padding:2rem; border-radius:12px; max-width:650px; margin:0 auto; }
    </style>
    """
    st.markdown(background_css, unsafe_allow_html=True)

def get_main_app_css() -> str:
    return """
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAppViewContainer"] { min-height: 100vh; color: #fafafb; }
    """

# ---------- UI Components ----------

def create_enhanced_header():
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="font-size: 2.4rem; margin-bottom: 0.2rem;">💪 AI Wellness Coach Pro</h1>
            <p style="font-size: 1rem; color: #999; margin: 0;">Your Personal Journey to Better Health</p>
        </div>
    """, unsafe_allow_html=True)

# ----------------- Page: Login -----------------

def login_page():
    inject_video_background()
    st.markdown('<br><br>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center;">💪 AI Wellness Coach Pro</h2>', unsafe_allow_html=True)

        # session_state user_db stored hashed
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
                st.experimental_rerun()
        with col_signup:
            signup_style = "🚀 Sign Up" if st.session_state.page == 'Sign Up' else "📝 Sign Up"
            if st.button(signup_style, use_container_width=True, key="signup_tab"):
                st.session_state.page = 'Sign Up'
                st.experimental_rerun()

        st.markdown('<br>', unsafe_allow_html=True)

        if st.session_state.page == 'Login':
            st.markdown("### 🔐 Welcome Back, Champion!")
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
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
                        # init user-specific
                        st.session_state.setdefault('goal_weight', 75)
                        st.session_state.setdefault('weight_log', [])
                        st.success("✅ Login successful! Redirecting...")
                        # short pause visually without blocking server: use st.experimental_rerun immediately
                        st.experimental_rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
            # show demo account details (safe)
            st.markdown("""
                <div style="background: rgba(46, 204, 113, 0.07); padding: 1rem; border-radius: 8px; margin-top: 0.5rem;">
                    <strong>Demo account:</strong> demo / demo123
                </div>
            """, unsafe_allow_html=True)

        elif st.session_state.page == 'Sign Up':
            st.markdown("### 🌟 Join the Wellness Revolution!")
            with st.form("signup_form"):
                new_username = st.text_input("👤 Choose Username", placeholder="Enter desired username")
                new_password = st.text_input("🔒 Create Password", type="password", placeholder="Create a secure password")
                confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
                submitted = st.form_submit_button("🎯 Create Account", use_container_width=True)
                if submitted:
                    if not new_username or not new_password:
                        st.error("❌ Please fill out all fields.")
                    elif len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters long.")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match!")
                    elif new_username in st.session_state.user_db:
                        st.error("❌ Username already exists! Try a different one.")
                    else:
                        st.session_state.user_db[new_username] = hash_pw(new_password)
                        st.success(f"🎉 Welcome, {new_username}! Please login to continue.")
                        st.session_state.page = 'Login'
                        st.experimental_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ----------------- Main App -----------------

def main_app():
    apply_css(get_main_app_css())

    # Sidebar
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: linear-gradient(45deg, #e74c3c, #c0392b);
                        border-radius: 12px; margin-bottom: 1rem;">
                <h3 style="color: white; margin: 0;">👋 Welcome</h3>
                <p style="color: #fff; margin: 0;">{html.escape(st.session_state.get('username', 'User'))}!</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            # Clear everything except user_db
            preserved = {'user_db': st.session_state.get('user_db')}
            st.session_state.clear()
            st.session_state.update(preserved)
            st.experimental_rerun()

        st.divider()
        st.markdown("### 👤 Your Details")
        age = st.sidebar.slider("🎂 Age", 16, 100, int(st.session_state.get('age', 25)), help="Your current age")
        gender = st.sidebar.selectbox("⚧ Gender", ("Male", "Female", "Other"), index=0)
        height = st.sidebar.slider("📏 Height (cm)", 100, 250, int(st.session_state.get('height', 170)), help="Your height in centimeters")
        weight = st.sidebar.slider("⚖️ Weight (kg)", 30, 200, int(st.session_state.get('weight', 70)), help="Your current weight in kilograms")
        st.session_state.update({'age': age, 'gender': gender, 'height': height, 'weight': weight})

        st.markdown("### 🎯 Your Preferences")
        diet_preference = st.sidebar.selectbox("🥗 Dietary Preference", ("No Preference", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean"))
        fitness_goal = st.sidebar.selectbox("🏆 Primary Fitness Goal", ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance", "General Wellness"))

        st.divider()
        submit_button = st.sidebar.button(label='✨ Generate My 7-Day Plan!', use_container_width=True)

    # Header & Tabs
    create_enhanced_header()
    profile_tab, plan_tab, chat_tab = st.tabs(["📊 Profile & Progress", "📅 Plan Generator", "💬 AI Health Chat"])

    # ---------- Profile Tab ----------
    with profile_tab:
        st.markdown("## 📈 Your Wellness Dashboard")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            bmi = weight / ((height/100) ** 2) if height > 0 else 0
            st.metric("BMI", f"{bmi:.1f}")
        with col2:
            plans_generated = len(st.session_state.get('weight_log', []))
            st.metric("Plans Generated", plans_generated)
        with col3:
            st.metric("Current Weight", f"{weight} kg")
        with col4:
            goal_weight = st.session_state.get('goal_weight', 75)
            diff = weight - goal_weight
            st.metric("Weight to Goal", f"{diff:+.1f} kg")

        st.divider()
        prof_col1, prof_col2 = st.columns(2)
        with prof_col1:
            st.markdown("### 🎯 Set Your Goal")
            st.session_state['goal_weight'] = st.number_input("Goal Weight (kg)", min_value=30, max_value=200, value=st.session_state.get('goal_weight', 75))
        with prof_col2:
            st.markdown("### ✍️ Log Your Progress")
            current_weight = st.number_input("Today's Weight (kg)", min_value=30, max_value=200, value=weight)
            if st.button("📝 Log Weight", use_container_width=True):
                week_num = len(st.session_state.get('weight_log', [])) + 1
                st.session_state.setdefault('weight_log', []).append({"week": week_num, "weight": float(current_weight)})
                st.success(f"✅ Logged {current_weight}kg for Week {week_num}!")

        st.divider()
        st.markdown("### 📊 Your Journey Visualization")
        if st.session_state.get('weight_log'):
            df = pd.DataFrame(st.session_state.weight_log)
            base_chart = alt.Chart(df).mark_line(point=True).encode(
                x=alt.X('week:O', title='Week'),
                y=alt.Y('weight:Q', title='Weight (kg)'),
                tooltip=['week:O', 'weight:Q']
            ).properties(width='container', height=400)
            goal_rule = alt.Chart(pd.DataFrame({'goal': [st.session_state.goal_weight]})).mark_rule(strokeDash=[5,5]).encode(y='goal:Q')
            final_chart = base_chart + goal_rule
            st.altair_chart(final_chart, use_container_width=True)
        else:
            st.info("📈 Log your weight to see your progress chart here!")

    # ---------- Plan Generator Tab ----------
    with plan_tab:
        st.markdown("## 📅 Your Personalized Wellness Plan")
        st.info("💡 Your details are pre-filled from the sidebar. Click the generate button to create your unique 7-day wellness guide!")

        if "plan_generated" not in st.session_state:
            st.session_state.plan_generated = False

        if submit_button:
            with st.spinner("🤖 Generating your personalized 7-day plan (this may take a bit)..."):
                # Build a single comprehensive prompt to avoid many small calls (more efficient)
                prompt = f"""
                Act as an expert wellness coach. Provide a structured 7-day plan. Start with "### Disclaimer ###" then "## Day X ##" for each day.
                Per day include:
                ### Estimated Daily Calorie Target ###
                ### Detailed Diet Plan ###
                ### Detailed Exercise Plan ###
                ### Motivational Tip ###
                Use the user's details:
                Age: {age}, Gender: {gender}, Height: {height} cm, Weight: {weight} kg
                Preference: {diet_preference}, Goal: {fitness_goal}

                For Diet: include at least 4 meals (Breakfast, Lunch, Snack, Dinner) with **Meal Name: Specific Dish** and preparation instructions & portions.
                For Exercise: include 4-5 exercises per day, with sets/reps/duration/form cues.
                Keep responses explicit, realistic, and science-backed.
                """
                full_plan_text = generate_api_call(prompt)
                if full_plan_text:
                    st.session_state.weekly_plan_raw = full_plan_text
                    st.session_state.weekly_plan = parse_weekly_plan(full_plan_text)
                    st.session_state.plan_generated = True
                    st.session_state.shopping_list = None
                    st.success("✅ Your personalized plan is ready!")
                else:
                    st.error("❌ Failed to generate plan. Please try again later.")

        if st.session_state.get('plan_generated') and st.session_state.get('weekly_plan'):
            weekly_plan = st.session_state.weekly_plan
            col1, col2 = st.columns([3,1])
            with col1:
                day_options = [f"📅 Day {i+1}" for i in range(len(weekly_plan))]
                selected_day_index = st.selectbox("Select a day to view:", list(range(len(weekly_plan))), format_func=lambda i: day_options[i])
            with col2:
                if st.button("🛒 Generate Shopping List", use_container_width=True):
                    # Build combined diet text for shopping list creation
                    diet_plan_text = "\n".join([f"Day {i+1}:\n" + "\n".join([mealinstr for _, mealinstr in day['diet']]) for i, day in enumerate(weekly_plan)])
                    shop_prompt = f"Based on the following 7-day diet plan, create a shopping list organized by category with approximate quantities:\n\n{diet_plan_text}"
                    shop_list = generate_api_call(shop_prompt)
                    st.session_state.shopping_list = shop_list

            if st.session_state.get("shopping_list"):
                with st.expander("🛒 Your Consolidated Shopping List", expanded=True):
                    st.markdown(safe_text(st.session_state.shopping_list))

            day_plan = weekly_plan[selected_day_index]
            st.markdown(f"## 📊 Dashboard for Day {selected_day_index + 1}")
            dash_col1, dash_col2, dash_col3 = st.columns(3)
            with dash_col1:
                calorie_match = re.search(r'\d[\d,]*', day_plan.get("calories", "") or "")
                calories = calorie_match.group(0) if calorie_match else "N/A"
                st.metric("Target Calories", calories)
            with dash_col2:
                st.metric("Total Exercises", len(day_plan.get("exercise", [])))
            with dash_col3:
                st.metric("Total Meals", len(day_plan.get("diet", [])))

            with st.container():
                st.markdown("### 💡 Today's Motivation")
                st.info(safe_text(day_plan.get('motivation', "")))

            st.divider()
            diet_tab, exercise_tab = st.tabs(["🍎 Diet Plan", "🏋️ Exercise Plan"])
            with diet_tab:
                st.markdown("### 🍽️ Today's Nutritious Meals")
                if not day_plan["diet"]:
                    st.warning("No meals found in the diet plan. Please regenerate your plan.")
                for i, (name, instructions) in enumerate(day_plan["diet"]):
                    with st.container():
                        st.markdown(f"#### {html.escape(name)}")
                        st.markdown(safe_text(instructions))
                        with st.expander("📊 Nutritional Macros", expanded=False):
                            # Batch macros + nutrients into single call to reduce API hits
                            macro_prompt = f"Calculate approximate macros for: {name}. Provide exactly: Calories: [number]\\nProtein: [g]\\nCarbs: [g]\\nFat: [g]\\nFiber: [g]\\nShort assumptions used."
                            nutrients_prompt = f"List top 3 nutrients and benefits for: {name}."
                            combined_prompt = macro_prompt + "\n\n" + nutrients_prompt
                            combined_resp = cached_generate_api_call(combined_prompt)
                            if combined_resp:
                                st.markdown(safe_text(combined_resp))
                            else:
                                st.info("Unable to calculate macros at this time.")
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            meal_name = name.split(':')[-1].strip()
                            query = f"https://www.youtube.com/results?search_query={meal_name.replace(' ', '+')}+recipe"
                            st.markdown(f"[🎥 Recipe Video]({query})")
                        with btn_col2:
                            if st.button("🔄 Alternative", key=f"swap_diet_{selected_day_index}_{i}"):
                                alt_prompt = f"Suggest a healthy alternative to {name} with similar nutritional value for a {diet_preference} {fitness_goal.lower()} plan. Include brief prep instructions."
                                alternative = generate_api_call(alt_prompt)
                                if alternative:
                                    st.success(safe_text(alternative))
                        with btn_col3:
                            if st.button("👨‍🍳 Cooking Tips", key=f"tips_diet_{selected_day_index}_{i}"):
                                tips_prompt = f"Provide 3-4 practical cooking tips for: {name}"
                                cooking_tips = generate_api_call(tips_prompt)
                                if cooking_tips:
                                    st.info(safe_text(cooking_tips))

            with exercise_tab:
                st.markdown("### 💪 Today's Workout Routine")
                if not day_plan["exercise"]:
                    st.warning("⚠️ No exercises found in today's plan.")
                    if st.button("🏋️ Generate Today's Exercises"):
                        exercise_prompt = f"Create 4-5 exercises for goal: {fitness_goal}. Include sets/reps and form cues."
                        new_exercises = generate_api_call(exercise_prompt)
                        if new_exercises:
                            matches = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", new_exercises, re.DOTALL)
                            if matches:
                                day_plan["exercise"] = matches
                            else:
                                # fallback: put whole text as one exercise
                                day_plan["exercise"] = [("Generated Workout", new_exercises)]
                for i, (name, instructions) in enumerate(day_plan["exercise"]):
                    with st.container():
                        st.markdown(f"#### {html.escape(name)}")
                        st.markdown(safe_text(instructions))
                        with st.expander("📋 Exercise Details & Form Tips", expanded=False):
                            form_prompt = f"List proper form and safety tips for: {name}. Also common mistakes."
                            muscles_prompt = f"What primary and secondary muscle groups does {name} target?"
                            combined = form_prompt + "\n\n" + muscles_prompt
                            combined_resp = cached_generate_api_call(combined)
                            if combined_resp:
                                st.markdown(safe_text(combined_resp))
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            exercise_name = name.split(':')[-1].strip()
                            query = f"https://www.youtube.com/results?search_query={exercise_name.replace(' ', '+')}+tutorial"
                            st.markdown(f"[🎥 Exercise Tutorial]({query})")
                        with btn_col2:
                            if st.button("🔄 Alternative", key=f"swap_exercise_{selected_day_index}_{i}"):
                                alt_prompt = f"Suggest an alternative to {name} targeting similar muscles for a {fitness_goal.lower()} routine. Include sets/reps."
                                alternative = generate_api_call(alt_prompt)
                                if alternative:
                                    st.success(safe_text(alternative))
                        with btn_col3:
                            if st.button("⚙️ Modifications", key=f"mod_exercise_{selected_day_index}_{i}"):
                                mod_prompt = f"Provide beginner and advanced modifications for: {name}"
                                modifications = generate_api_call(mod_prompt)
                                if modifications:
                                    st.info(safe_text(modifications))

            st.warning(f"⚠️ Important Disclaimer: {safe_text(day_plan.get('disclaimer',''))}")

    # ---------- Chat Tab ----------
    with chat_tab:
        st.markdown("## 🤖 Your Personal AI Health Assistant")
        st.info("💬 Ask me anything about fitness, nutrition, wellness, or your personalized plan!")

        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Hello! 👋 I'm your AI Health Coach! I'm here to help you with fitness, nutrition, and motivation. Ask me anything."
            }]

        # Display messages (escaped)
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(safe_text(message["content"]))

        # Chat input
        prompt = st.chat_input("Ask me anything about your health and fitness journey...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            # maintain reasonable chat length
            st.session_state.messages = trim_chat_history(st.session_state.messages, keep_last=10)

            # Build messages for API: keep the system instruction as the first message
            system_prompt = {
                "role": "system",
                "content": ("You are an expert AI Health Coach with knowledge in exercise science, nutrition, mental wellness, "
                            "injury prevention, and lifestyle optimization. Provide evidence-based, practical advice. Remind users to consult professionals.")
            }
            messages_for_api = [system_prompt] + st.session_state.messages[-10:]

            # Streamed response to UI
            with st.chat_message("assistant", avatar="🤖"):
                final_text = stream_chat_to_ui(messages_for_api)
                # Save assistant response into session
                if final_text:
                    st.session_state.messages.append({"role": "assistant", "content": final_text})
                else:
                    err_msg = "Sorry — I couldn't generate a response right now."
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})
                    st.error(err_msg)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": "Chat cleared! How can I help you with your wellness journey today?"
                }]
                st.experimental_rerun()
        with col2:
            if st.button("💡 Quick Tips", use_container_width=True):
                tips = [
                    "💧 Drink at least 8 glasses of water daily",
                    "🚶‍♀️ Take a 10-minute walk after each meal",
                    "😴 Aim for 7-9 hours of quality sleep",
                    "🧘‍♂️ Practice 5 minutes of deep breathing daily",
                    "🥗 Fill half your plate with vegetables",
                    "📱 Take regular breaks from screens"
                ]
                tip = tips[len(st.session_state.get("messages", [])) % len(tips)]
                st.info(f"**Daily Tip:** {tip}")

# ----------------- Entry Point: API Key and Client -----------------

api_key = os.environ.get("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None)
if not api_key:
    st.error("🚨 OpenAI API Key required. Set environment variable OPENAI_API_KEY or Streamlit secrets.")
    st.stop()

# Initialize OpenAI client (wrap in try/except)
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# Session defaults
st.session_state.setdefault('logged_in', False)

# Route
if st.session_state.logged_in:
    main_app()
else:
    login_page()
