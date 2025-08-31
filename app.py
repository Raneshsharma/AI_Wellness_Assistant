import streamlit as st
import re
import hashlib
from openai import OpenAI
from datetime import datetime

# ============================
# Initialize API Client
# ============================
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

def set_api_key():
    st.session_state.api_key = st.session_state.get("temp_api_key", "")

if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
else:
    client = None

# ============================
# User DB Simulation
# ============================
if "user_db" not in st.session_state:
    st.session_state.user_db = {"demo": hashlib.sha256("123".encode()).hexdigest()}

# ============================
# Helper Functions
# ============================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_api_call(system_prompt, user_input, model="gpt-4.1-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content


def parse_weekly_plan(text):
    days = re.findall(r"Day (\d+):(.+?)(?=Day|$)", text, re.S)
    plan = {f"Day {d}": content.strip() for d, content in days}
    return plan


# ============================
# UI Styling
# ============================
st.set_page_config(page_title="AI Wellness Coach", page_icon="🥦", layout="wide")
st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #e0e0e0; }
        .stCard { background: #1c1f26; padding: 20px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        .metric-card { background: #22252b; border-radius: 16px; padding: 20px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ============================
# Navigation State
# ============================
if "page" not in st.session_state:
    st.session_state.page = "Login"

# ============================
# Login / Signup Pages
# ============================
def login_page():
    st.title("🔑 Login to AI Wellness Coach")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in st.session_state.user_db and st.session_state.user_db[username] == hash_password(password):
            st.session_state["username"] = username
            st.session_state.page = "Dashboard"
            st.rerun()
        else:
            st.error("❌ Invalid username or password")


def signup_page():
    st.title("📝 Sign Up")
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    if st.button("Sign Up"):
        if username in st.session_state.user_db:
            st.error("⚠️ Username already exists")
        else:
            st.session_state.user_db[username] = hash_password(password)
            st.success("✅ Account created! Please login.")
            st.session_state.page = "Login"
            st.rerun()


# ============================
# Dashboard
# ============================
def dashboard():
    st.title("🏠 Wellness Dashboard")
    st.write(f"👋 Welcome, **{st.session_state['username']}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Weight", "72 kg", "-0.5 kg")
    with col2:
        st.metric("Calories Today", "2,100 kcal", "-200 kcal")
    with col3:
        st.metric("Sleep", "7.5 hrs", "+0.5 hr")

    st.markdown("---")
    st.subheader("📊 Weekly Meal Plan")
    if st.button("Generate Plan"):
        with st.spinner("AI is generating your plan..."):
            plan = generate_api_call(
                "You are a nutrition coach.",
                "Create a 7-day Indian diet plan with meals and calories"
            )
            parsed = parse_weekly_plan(plan)
            for day, meals in parsed.items():
                with st.expander(day):
                    st.write(meals)

    st.markdown("---")
    st.subheader("🥗 Recommended Recipes")
    recipes = [
        {"title": "Grilled Paneer Salad", "img": "https://source.unsplash.com/400x250/?salad", "url": "https://youtube.com/results?search_query=grilled+paneer+salad"},
        {"title": "Oats Poha", "img": "https://source.unsplash.com/400x250/?oats", "url": "https://youtube.com/results?search_query=oats+poha"}
    ]
    cols = st.columns(len(recipes))
    for idx, r in enumerate(recipes):
        with cols[idx]:
            st.markdown(f"<div class='stCard'><img src='{r['img']}' width='100%' style='border-radius:12px;'><h4>{r['title']}</h4><a href='{r['url']}' target='_blank'>▶️ Watch Recipe</a></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🛒 Shopping List")
    shopping = {"Produce": ["Spinach", "Tomatoes"], "Protein": ["Paneer", "Tofu"], "Grains": ["Oats", "Rice"]}
    cols = st.columns(3)
    for idx, (cat, items) in enumerate(shopping.items()):
        with cols[idx]:
            st.markdown(f"<div class='stCard'><h4>{cat}</h4><ul>{''.join([f'<li>{i}</li>' for i in items])}</ul></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 AI Health Chat")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        role = "🧑‍💻" if msg["role"] == "user" else "🤖"
        st.write(f"{role}: {msg['content']}")

    if prompt := st.chat_input("Ask me anything about your health!"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=st.session_state.messages,
                stream=True,
            )
            response_text = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.get("content", "")
                response_text += delta
                st.write(delta)
            st.session_state.messages.append({"role": "assistant", "content": response_text})


# ============================
# Page Router
# ============================
if st.session_state.page == "Login":
    login_page()
elif st.session_state.page == "Signup":
    signup_page()
elif st.session_state.page == "Dashboard":
    dashboard()

