import streamlit as st
import requests
from streamlit_option_menu import option_menu

# ==========================
# CONFIG
# ==========================
API_URL = "http://127.0.0.1:8000"  # FastAPI backend

# ==========================
# CUSTOM CSS
# ==========================
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-size: 16px;
        border-radius: 10px;
        padding: 10px 20px;
        border: none;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #ccc;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================
# SIDEBAR NAVIGATION
# ==========================
with st.sidebar:
    choice = option_menu(
        "AI Wellness Coach",
        ["Home", "Login / Sign Up", "Recipes", "Shopping", "Chat"],
        icons=["house", "person", "book", "cart", "chat"],
        menu_icon="cast",
        default_index=0,
    )

# ==========================
# HOME
# ==========================
if choice == "Home":
    st.title("🏋️‍♀️ AI Wellness Coach")
    st.subheader("Your personal wellness companion")
    st.image(
        "https://img.freepik.com/free-vector/healthy-lifestyle-concept_23-2148491903.jpg",
        use_container_width=True,
    )
    st.write(
        "Track recipes, shopping lists, and chat with your AI coach for fitness & health guidance."
    )

# ==========================
# LOGIN / SIGN UP
# ==========================
elif choice == "Login / Sign Up":
    tab1, tab2 = st.tabs(["🔑 Login", "🆕 Sign Up"])

    with tab1:
        st.header("Login to Your Account")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                response = requests.post(
                    f"{API_URL}/auth/login",
                    json={"email": email, "password": password},
                )
                if response.status_code == 200:
                    st.success("✅ Logged in successfully!")
                else:
                    st.error("❌ Invalid credentials")
            except:
                st.error("⚠️ Backend not reachable")

    with tab2:
        st.header("Create a New Account")
        new_email = st.text_input("Email", key="signup_email")
        new_pass = st.text_input("Password", type="password", key="signup_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")
        if st.button("Sign Up"):
            if new_pass == confirm_pass:
                try:
                    response = requests.post(
                        f"{API_URL}/auth/signup",
                        json={"email": new_email, "password": new_pass},
                    )
                    if response.status_code == 200:
                        st.success("🎉 Account created successfully!")
                    else:
                        st.error("❌ Sign up failed")
                except:
                    st.error("⚠️ Backend not reachable")
            else:
                st.error("❌ Passwords do not match")

# ==========================
# RECIPES
# ==========================
elif choice == "Recipes":
    st.title("🥗 Healthy Recipes")
    st.info("Fetching from **/recipes** API")
    try:
        response = requests.get(f"{API_URL}/recipes")
        if response.status_code == 200:
            recipes = response.json()
            for r in recipes:
                st.subheader(r["title"])
                st.write(r["description"])
                st.write(f"Calories: {r['calories']}")
                st.markdown("---")
        else:
            st.error("No recipes found.")
    except:
        st.error("⚠️ Backend not reachable")

# ==========================
# SHOPPING
# ==========================
elif choice == "Shopping":
    st.title("🛒 Shopping List")
    st.info("Fetching from **/shopping** API")
    try:
        response = requests.get(f"{API_URL}/shopping")
        if response.status_code == 200:
            items = response.json()
            for item in items:
                st.checkbox(item["name"])
        else:
            st.error("No shopping items found.")
    except:
        st.error("⚠️ Backend not reachable")

# ==========================
# CHAT
# ==========================
elif choice == "Chat":
    st.title("💬 AI Chat Coach")
    st.info("Ask your coach about diet, workouts, or wellness.")
    user_input = st.text_input("You: ", "")
    if st.button("Send"):
        if user_input:
            try:
                response = requests.post(f"{API_URL}/chat", json={"message": user_input})
                if response.status_code == 200:
                    reply = response.json().get("reply", "🤖 No response")
                    st.success(f"Coach: {reply}")
                else:
                    st.error("❌ Chat failed")
            except:
                st.error("⚠️ Backend not reachable")
