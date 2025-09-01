import streamlit as st
import os
from openai import OpenAI
import time
import re
import pandas as pd
import altair as alt

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Wellness Coach Pro",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Functions ---

def apply_css(css_style):
    """Applies a CSS style block to the Streamlit app."""
    st.markdown(f"<style>{css_style}</style>", unsafe_allow_html=True)

def inject_video_background():
    """Injects CSS and HTML for an animated background on the login page."""
    background_css = """
    <style>
        /* Hide Streamlit elements for cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Animated gradient background */
        [data-testid="stAppViewContainer"] > .main {
            background: linear-gradient(-45deg, #0f1419, #1a252f, #15202a, #0d1117, #2c1810, #1a1a2e);
            background-size: 400% 400%;
            animation: gradientMove 15s ease infinite;
            padding-top: 2rem;
            min-height: 100vh;
        }
        
        @keyframes gradientMove {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        
        /* Floating particles effect */
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: -1;
        }
        
        .particle {
            position: absolute;
            display: block;
            pointer-events: none;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: #e74c3c;
            opacity: 0.6;
            animation: float 6s infinite ease-in-out;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.6; }
            50% { transform: translateY(-20px) rotate(180deg); opacity: 1; }
        }
        
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
        }
        
        /* Enhanced login container styling */
        .login-container {
            background: linear-gradient(135deg, rgba(0,0,0,0.85) 0%, rgba(21, 32, 42, 0.9) 50%, rgba(15, 20, 25, 0.85) 100%);
            backdrop-filter: blur(15px);
            border-radius: 25px;
            border: 2px solid rgba(231, 76, 60, 0.3);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(231, 76, 60, 0.1);
            padding: 3rem;
            margin: 2rem auto;
            max-width: 550px;
            position: relative;
            overflow: hidden;
        }
        
        .login-container::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, #e74c3c, #f39c12, #e74c3c, #c0392b);
            background-size: 400% 400%;
            border-radius: 25px;
            z-index: -1;
            animation: borderGlow 4s ease infinite;
        }
        
        @keyframes borderGlow {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        /* Welcome text styling */
        .welcome-title {
            text-align: center;
            color: #fafafb;
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.8);
            background: linear-gradient(45deg, #e74c3c, #f39c12, #e74c3c);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 3s ease-in-out infinite;
        }
        
        .welcome-subtitle {
            text-align: center;
            color: #dedee4;
            font-size: 1.3rem;
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            font-weight: 300;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        /* Enhanced button styling */
        .stButton>button {
            border: 2px solid transparent;
            color: #fafafb;
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            transition: all 0.4s ease-in-out;
            width: 100%;
            height: 3.5rem;
            border-radius: 18px;
            font-weight: 700;
            font-size: 1.1rem;
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            position: relative;
            overflow: hidden;
        }
        
        .stButton>button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        
        .stButton>button:hover::before {
            left: 100%;
        }
        
        .stButton>button:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(231, 76, 60, 0.5);
            background: linear-gradient(45deg, #c0392b, #e74c3c);
        }
        
        /* Form styling */
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: #fafafb;
            padding: 1rem;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #e74c3c;
            box-shadow: 0 0 15px rgba(231, 76, 60, 0.4);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .stTextInput > div > div > input::placeholder {
            color: rgba(250, 250, 251, 0.6);
        }
    </style>
    <div class="particles">
        <div class="particle" style="left: 10%; animation-delay: 0s;"></div>
        <div class="particle" style="left: 20%; animation-delay: 1s;"></div>
        <div class="particle" style="left: 30%; animation-delay: 2s;"></div>
        <div class="particle" style="left: 40%; animation-delay: 3s;"></div>
        <div class="particle" style="left: 50%; animation-delay: 4s;"></div>
        <div class="particle" style="left: 60%; animation-delay: 5s;"></div>
        <div class="particle" style="left: 70%; animation-delay: 6s;"></div>
        <div class="particle" style="left: 80%; animation-delay: 1.5s;"></div>
        <div class="particle" style="left: 90%; animation-delay: 2.5s;"></div>
    </div>
    """
    st.markdown(background_css, unsafe_allow_html=True)

def get_main_app_css():
    """Returns enhanced CSS for the main application with improved styling."""
    return """
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main animated background using improved palette */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(-45deg, #0f1419, #1a252f, #15202a, #0d1117);
        animation: gradient 20s ease infinite;
        background-size: 400% 400%;
        color: #fafafb;
        min-height: 100vh;
    }

    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

    /* Typography improvements */
    h1, h2, h3, h4, h5, h6 { 
        color: #fafafb; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    h1 {
        background: linear-gradient(45deg, #e74c3c, #f39c12);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, rgba(21, 32, 42, 0.9) 0%, rgba(15, 20, 25, 0.9) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(231, 76, 60, 0.3);
    }
    
    /* Chat message styling */
    [data-testid="stChatMessage"] { 
        background: rgba(21, 32, 42, 0.8);
        border-radius: 15px;
        border: 1px solid rgba(62, 88, 113, 0.3);
        backdrop-filter: blur(5px);
    }
    
    /* Metrics styling */
    [data-testid="stMetricLabel"] { color: #dedee4; }
    [data-testid="stMetricValue"] { 
        color: #e74c3c; 
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Enhanced button styling */
    .stButton>button {
        border: 2px solid transparent;
        color: #fafafb;
        background: linear-gradient(45deg, #e74c3c, #c0392b);
        transition: all 0.3s ease-in-out;
        border-radius: 10px;
        font-weight: 600;
        height: 2.8rem;
        box-shadow: 0 4px 15px rgba(231, 76, 60, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
        background: linear-gradient(45deg, #c0392b, #e74c3c);
    }
    
    /* Tab styling */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #e74c3c, #c0392b);
        color: #fafafb;
        border-radius: 10px 10px 0 0;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="false"] {
        background: rgba(255, 255, 255, 0.1);
        color: #dedee4;
        border-radius: 10px 10px 0 0;
    }
    
    /* Container styling */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, rgba(21, 32, 42, 0.8) 0%, rgba(15, 20, 25, 0.8) 100%);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 2rem;
        border: 1px solid rgba(62, 88, 113, 0.4);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(231, 76, 60, 0.5);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }
    
    /* Input styling */
    .stSlider > div > div > div {
        background-color: rgba(231, 76, 60, 0.3);
    }
    
    .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* Link button styling */
    .stLinkButton > a {
        background: linear-gradient(45deg, #3498db, #2980b9);
        color: white;
        text-decoration: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        display: inline-block;
        width: 100%;
        text-align: center;
    }
    
    .stLinkButton > a:hover {
        background: linear-gradient(45deg, #2980b9, #3498db);
        transform: translateY(-1px);
    }
    
    /* Chart styling */
    .vega-embed {
        background: rgba(21, 32, 42, 0.8);
        border-radius: 15px;
        padding: 1rem;
        border: 1px solid rgba(62, 88, 113, 0.3);
    }
    
    /* Warning/Info styling */
    .stAlert {
        background: rgba(231, 76, 60, 0.1);
        border: 1px solid rgba(231, 76, 60, 0.3);
        border-radius: 10px;
    }
    
    /* Success message styling */
    .stSuccess {
        background: rgba(46, 204, 113, 0.1);
        border: 1px solid rgba(46, 204, 113, 0.3);
        border-radius: 10px;
    }
    
    /* Loading spinner */
    .stSpinner {
        color: #e74c3c;
    }
    """

def parse_weekly_plan(plan_text):
    """Parses a 7-day plan into a structured list of dictionaries."""
    days = re.split(r"##\s*Day\s*\d+\s*##", plan_text)[1:]
    parsed_plan = []
    disclaimer = re.search(r"### Disclaimer ###\s*(.*?)\s*(?=\n##|$)", plan_text, re.DOTALL)
    disclaimer_text = disclaimer.group(1).strip() if disclaimer else "Standard disclaimer not found."

    for day_content in days:
        day_data = {
            "calories": re.search(r"### Estimated Daily Calorie Target ###\s*(.*?)\s*(?=\n###|$)", day_content, re.DOTALL),
            "diet": re.search(r"### Detailed Diet Plan ###\s*(.*?)\s*(?=\n###|$)", day_content, re.DOTALL),
            "exercise": re.search(r"### Detailed Exercise Plan ###\s*(.*?)\s*(?=\n###|$)", day_content, re.DOTALL),
            "motivation": re.search(r"### Motivational Tip ###\s*(.*?)\s*(?=\n###|$)", day_content, re.DOTALL),
        }
        day_plan = {k: v.group(1).strip() if v else "" for k, v in day_data.items()}
        day_plan["disclaimer"] = disclaimer_text
        day_plan["diet"] = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", day_plan.get("diet", ""), re.DOTALL)
        day_plan["exercise"] = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", day_plan.get("exercise", ""), re.DOTALL)
        parsed_plan.append(day_plan)
    return parsed_plan

def generate_api_call(prompt, model="gpt-4o"):
    """Generic function to call the OpenAI API for non-streaming responses."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert wellness coach with extensive knowledge in nutrition, fitness, and mental health."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred with the AI: {e}")
        return None

def generate_wellness_plan(age, gender, height, weight, diet_preference, fitness_goal):
    """Constructs a prompt for a full 7-day plan without image prompts."""
    prompt = f"""
    Act as an expert wellness coach. A user has provided their details for a personalized plan.
    Your response MUST be structured for a full 7-day week.
    Start with a general disclaimer under the heading "### Disclaimer ###".
    Then, for each day from 1 to 7, use a main heading "## Day X ##".
    Under each day, provide the following exact Markdown subheadings:
    ### Estimated Daily Calorie Target ###
    ### Detailed Diet Plan ###
    ### Detailed Exercise Plan ###
    ### Motivational Tip ###

    **User's Details:**
    - Age: {age}, Gender: {gender}, Height: {height} cm, Weight: {weight} kg
    - Preference: {diet_preference}, Goal: {fitness_goal}

    **CRITICAL REQUIREMENTS:**
    
    For the Diet Plan section:
    - Provide at least 4 meals per day (Breakfast, Lunch, Snack, Dinner)
    - Format: **Meal Name: Specific Dish**
    - Follow with detailed preparation instructions and portion sizes
    - Example: **Breakfast: Overnight Oats**
    Mix 1/2 cup rolled oats with 1/2 cup almond milk, 1 tbsp chia seeds...
    
    For the Exercise Plan section:
    - Provide at least 4-5 exercises per day
    - Format: **Exercise Name: Specific Movement**
    - Include sets, reps, duration, and form cues
    - Example: **Cardio: Brisk Walking**
    30 minutes at moderate pace, maintain good posture, swing arms naturally...
    
    **Warm-up: Dynamic Stretching**
    5-10 minutes of arm circles, leg swings, and light movements...
    
    **Strength: Push-ups**
    3 sets of 8-12 repetitions, keep body straight, lower chest to floor...
    
    Make the plan comprehensive, realistic, and scientifically sound.
    Ensure both diet AND exercise sections are fully populated for each day.
    """
    return generate_api_call(prompt)

def create_enhanced_header():
    """Creates an enhanced header with gradient text and icons."""
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">💪 AI Wellness Coach Pro</h1>
            <p style="font-size: 1.2rem; color: #dedee4; margin: 0;">Your Personal Journey to Better Health</p>
        </div>
    """, unsafe_allow_html=True)

# --- Main Application Logic ---

def login_page():
    """Displays the enhanced login and sign-up page with animated background."""
    # Always inject animated background when login page loads
    inject_video_background()
    
    # Create centered login container
    st.markdown('<br><br>', unsafe_allow_html=True)  # Add some top spacing
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Welcome header
        st.markdown('<div class="welcome-title">💪 AI Wellness Coach Pro</div>', unsafe_allow_html=True)
        st.markdown('<div class="welcome-subtitle">✨ Transform Your Health Journey Today</div>', unsafe_allow_html=True)
        
        # Tab-like navigation with enhanced styling
        if 'page' not in st.session_state:
            st.session_state.page = 'Login'

        col_login, col_signup = st.columns(2)
        with col_login:
            login_style = "🔑 Login" if st.session_state.page == 'Login' else "🔓 Login"
            if st.button(login_style, use_container_width=True, key="login_tab"):
                st.session_state.page = 'Login'
        with col_signup:
            signup_style = "🚀 Sign Up" if st.session_state.page == 'Sign Up' else "📝 Sign Up"
            if st.button(signup_style, use_container_width=True, key="signup_tab"):
                st.session_state.page = 'Sign Up'
        
        st.markdown('<br>', unsafe_allow_html=True)

        # Enhanced user management with demo accounts
        if 'user_db' not in st.session_state:
            st.session_state.user_db = {
                "demo": "demo123", 
                "admin": "admin123",
                "user": "password123"
            } 
        
        if st.session_state.page == 'Login':
            st.markdown("### 🔐 Welcome Back, Champion!")
            st.markdown("Ready to continue your wellness journey?")
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                
                col_submit, col_demo = st.columns([3, 1])
                with col_submit:
                    submitted = st.form_submit_button("🚀 Login", use_container_width=True)
                with col_demo:
                    demo_login = st.form_submit_button("🎮 Demo", use_container_width=True)
                    
                if demo_login:
                    username = "demo"
                    password = "demo123"
                    submitted = True
                    
                if submitted:
                    if username in st.session_state.user_db and st.session_state.user_db[username] == password:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        # Initialize user-specific data
                        if 'goal_weight' not in st.session_state:
                            st.session_state.goal_weight = 75
                        if 'weight_log' not in st.session_state:
                            st.session_state.weight_log = []
                        st.success("✅ Login successful! Welcome back!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
            
            # Demo account info with better styling
            st.markdown("""
                <div style="background: rgba(46, 204, 113, 0.1); padding: 1rem; border-radius: 10px; 
                           border: 1px solid rgba(46, 204, 113, 0.3); margin-top: 1rem;">
                    <h4 style="color: #2ecc71; margin: 0 0 0.5rem 0;">🎮 Try Demo Account</h4>
                    <p style="margin: 0; color: #dedee4;">
                        <strong>Username:</strong> demo<br>
                        <strong>Password:</strong> demo123
                    </p>
                </div>
            """, unsafe_allow_html=True)

        elif st.session_state.page == 'Sign Up':
            st.markdown("### 🌟 Join the Wellness Revolution!")
            st.markdown("Create your account and start your transformation today.")
            
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
                        st.session_state.user_db[new_username] = new_password
                        st.success(f"🎉 Welcome to the family, {new_username}! Please login to continue.")
                        st.session_state.page = 'Login'
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
            
            # Password requirements
            st.markdown("""
                <div style="background: rgba(52, 152, 219, 0.1); padding: 1rem; border-radius: 10px; 
                           border: 1px solid rgba(52, 152, 219, 0.3); margin-top: 1rem;">
                    <h4 style="color: #3498db; margin: 0 0 0.5rem 0;">🔒 Password Requirements</h4>
                    <p style="margin: 0; color: #dedee4;">
                        • At least 6 characters long<br>
                        • Choose something memorable but secure
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def main_app():
    """The enhanced main application interface."""
    apply_css(get_main_app_css())

    # Enhanced sidebar
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: linear-gradient(45deg, #e74c3c, #c0392b); 
                        border-radius: 15px; margin-bottom: 1rem;">
                <h2 style="color: white; margin: 0;">👋 Welcome</h2>
                <h3 style="color: #fafafb; margin: 0;">{st.session_state.username}!</h3>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ['user_db']: 
                    del st.session_state[key]
            st.rerun()
        
        st.divider()

        # Enhanced user details section
        st.markdown("### 👤 Your Details")
        age = st.slider("🎂 Age", 16, 100, 25, help="Your current age")
        gender = st.selectbox("⚧ Gender", ("Male", "Female", "Other"))
        height = st.slider("📏 Height (cm)", 100, 250, 170, help="Your height in centimeters")
        weight = st.slider("⚖️ Weight (kg)", 30, 200, 70, help="Your current weight in kilograms")
        
        st.markdown("### 🎯 Your Preferences")
        diet_preference = st.selectbox("🥗 Dietary Preference", 
                                     ("No Preference", "Vegetarian", "Vegan", "Keto", "Paleo", "Mediterranean"))
        fitness_goal = st.selectbox("🏆 Primary Fitness Goal", 
                                   ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance", "General Wellness"))
        
        st.divider()
        
        # Enhanced generate button
        submit_button = st.button(
            label='✨ Generate My 7-Day Plan!', 
            use_container_width=True,
            help="Click to generate your personalized wellness plan"
        )

    # Enhanced main header
    create_enhanced_header()

    # Main Tabs with enhanced styling
    profile_tab, plan_tab, chat_tab = st.tabs(["📊 Profile & Progress", "📅 Plan Generator", "💬 AI Health Chat"])

    # --- Enhanced Profile & Progress Tab ---
    with profile_tab:
        st.markdown(f"## 📈 Your Wellness Dashboard")
        
        # Stats overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            bmi = weight / ((height/100) ** 2)
            st.metric("BMI", f"{bmi:.1f}", help="Body Mass Index")
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
            with st.container(border=True):
                st.markdown("### 🎯 Set Your Goal")
                st.session_state.goal_weight = st.number_input(
                    "Goal Weight (kg)", 
                    min_value=30, 
                    max_value=200, 
                    value=st.session_state.get('goal_weight', 75),
                    help="Set your target weight"
                )

        with prof_col2:
            with st.container(border=True):
                st.markdown("### ✍️ Log Your Progress")
                current_weight = st.number_input(
                    "Today's Weight (kg)", 
                    min_value=30, 
                    max_value=200, 
                    value=weight,
                    help="Enter your current weight"
                )
                if st.button("📝 Log Weight", use_container_width=True):
                    week_num = len(st.session_state.get('weight_log', [])) + 1
                    if 'weight_log' not in st.session_state:
                        st.session_state.weight_log = []
                    st.session_state.weight_log.append({"week": week_num, "weight": current_weight})
                    st.success(f"✅ Logged {current_weight}kg for Week {week_num}!")
                    st.balloons()

        st.divider()
        st.markdown("### 📊 Your Journey Visualization")
        
        if st.session_state.get('weight_log'):
            df = pd.DataFrame(st.session_state.weight_log)
            
            # Create a simple and reliable line chart
            base_chart = alt.Chart(df).mark_line(
                point=True,
                color='#e74c3c',
                strokeWidth=3
            ).encode(
                x=alt.X('week:O', title='Week'),
                y=alt.Y('weight:Q', title='Weight (kg)'),
                tooltip=['week:O', 'weight:Q']
            ).properties(
                title='Your Weight Progress',
                width='container',
                height=400
            )

            # Add goal line if we have data
            goal_weight = st.session_state.goal_weight
            goal_rule = alt.Chart(pd.DataFrame({'goal': [goal_weight]})).mark_rule(
                color='#f39c12',
                strokeDash=[5, 5],
                strokeWidth=2
            ).encode(
                y='goal:Q',
                tooltip=alt.value(f'Goal: {goal_weight} kg')
            )

            # Combine the charts
            final_chart = base_chart + goal_rule
            
            st.altair_chart(final_chart, use_container_width=True)
        else:
            st.info("📈 Log your weight to see your progress chart here!")

    # --- Enhanced Plan Generator Tab ---
    with plan_tab:
        st.markdown("## 📅 Your Personalized Wellness Plan")
        st.info("💡 Your details are pre-filled from the sidebar. Click the generate button to create your unique 7-day wellness guide!")

        if "plan_generated" not in st.session_state:
            st.session_state.plan_generated = False

        if submit_button:
            with st.spinner("🤖 Your AI coach is crafting the perfect 7-day plan... This may take a moment!"):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
                
                full_plan = generate_wellness_plan(age, gender, height, weight, diet_preference, fitness_goal)
                if full_plan:
                    st.session_state.weekly_plan = parse_weekly_plan(full_plan)
                    st.session_state.plan_generated = True
                    st.session_state.shopping_list = None
                    st.success("✅ Your personalized plan is ready!")
                    st.balloons()
                else:
                    st.error("❌ Failed to generate plan. Please try again.")
                    st.session_state.plan_generated = False

        if st.session_state.plan_generated and "weekly_plan" in st.session_state:
            weekly_plan = st.session_state.weekly_plan
            
            # Enhanced day selector and shopping list
            col1, col2 = st.columns([3,1])
            with col1:
                day_options = [f"📅 Day {i+1}" for i in range(len(weekly_plan))]
                selected_day_str = st.selectbox(
                    "Select a day to view:", 
                    day_options, 
                    label_visibility="collapsed", 
                    key="day_selector"
                )
            with col2:
                if st.button("🛒 Generate Shopping List", use_container_width=True):
                    diet_plan_text = "\n".join([
                        f"Day {i+1}:\n" + "\n".join([item[1] for item in day['diet']]) 
                        for i, day in enumerate(weekly_plan)
                    ])
                    with st.spinner("📝 Analyzing your diet plan..."):
                        prompt = f"""Based on the following 7-day diet plan, create a comprehensive shopping list 
                        organized by category (Produce, Protein, Dairy, Pantry, Frozen, etc.). 
                        Include quantities and prioritize fresh, healthy ingredients:\n\n{diet_plan_text}"""
                        st.session_state.shopping_list = generate_api_call(prompt)

            if st.session_state.get("shopping_list"):
                with st.expander("🛒 Your Consolidated Shopping List", expanded=True):
                    st.markdown(st.session_state.shopping_list)

            # Extract day number from selected string (handles "📅 Day X" format)
            try:
                selected_day_index = day_options.index(selected_day_str)
            except ValueError:
                selected_day_index = 0  # Default to first day if parsing fails
            day_plan = weekly_plan[selected_day_index]
            
            # Enhanced day dashboard
            st.markdown(f"## 📊 Dashboard for Day {selected_day_index + 1}")
            
            dash_col1, dash_col2, dash_col3 = st.columns(3)
            with dash_col1:
                with st.container(border=True):
                    st.markdown("### 🎯 Daily Calories")
                    calorie_match = re.search(r'\d[\d,]*', day_plan["calories"])
                    calories = calorie_match.group(0) if calorie_match else "N/A"
                    st.metric("Target Calories", calories)
            
            with dash_col2:
                with st.container(border=True):
                    st.markdown("### 🏃‍♂️ Exercises")
                    exercise_count = len(day_plan["exercise"])
                    st.metric("Total Exercises", exercise_count)
            
            with dash_col3:
                with st.container(border=True):
                    st.markdown("### 🍽️ Meals")
                    meal_count = len(day_plan["diet"])
                    st.metric("Total Meals", meal_count)
            
            # Motivational tip
            with st.container(border=True):
                st.markdown("### 💡 Today's Motivation")
                st.info(day_plan['motivation'])
            
            st.divider()
            
            # Enhanced tabs for diet and exercise
            diet_tab, exercise_tab = st.tabs(["🍎 Diet Plan", "🏋️ Exercise Plan"])
            
            with diet_tab:
                st.markdown("### 🍽️ Today's Nutritious Meals")
                
                if not day_plan["diet"]:
                    st.warning("No meals found in the diet plan. Please regenerate your plan.")
                
                for i, (name, instructions) in enumerate(day_plan["diet"]):
                    with st.container(border=True):
                        # Meal header
                        st.markdown(f"### {name}")
                        st.markdown(instructions.strip())
                        
                        # Macros section - always show
                        with st.expander("📊 Nutritional Macros", expanded=False):
                            macro_col1, macro_col2 = st.columns(2)
                            with macro_col1:
                                with st.spinner("Calculating macros..."):
                                    macro_prompt = f"""
                                    Calculate the approximate macronutrients for this meal: {name} - {instructions[:150]}
                                    
                                    Provide the response in this exact format:
                                    Calories: [number]
                                    Protein: [number]g
                                    Carbs: [number]g  
                                    Fat: [number]g
                                    Fiber: [number]g
                                    """
                                    macros = generate_api_call(macro_prompt)
                                    if macros:
                                        st.markdown(f"**Estimated Macros:**\n\n{macros}")
                                    else:
                                        st.info("Unable to calculate macros at this time.")
                            
                            with macro_col2:
                                # Key nutrients
                                nutrient_prompt = f"List the top 3 key nutrients and health benefits of: {name}"
                                nutrients = generate_api_call(nutrient_prompt)
                                if nutrients:
                                    st.markdown(f"**Key Benefits:**\n\n{nutrients}")
                        
                        # Action buttons
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        
                        with btn_col1:
                            # YouTube recipe button
                            meal_name = name.split(':')[-1].strip()
                            query = f"how to make {meal_name} healthy recipe"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("🎥 Recipe Video", yt_url, use_container_width=True)
                        
                        with btn_col2:
                            # Alternative meal
                            if st.button("🔄 Alternative", key=f"swap_diet_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Finding alternatives..."):
                                    alt_prompt = f"Suggest a healthy alternative to {name} with similar nutritional value for a {diet_preference} {fitness_goal.lower()} plan. Include brief preparation instructions."
                                    alternative = generate_api_call(alt_prompt)
                                    if alternative:
                                        st.success(f"💡 **Alternative Meal:**\n\n{alternative}")
                        
                        with btn_col3:
                            # Cooking tips
                            if st.button("👨‍🍳 Cooking Tips", key=f"tips_diet_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Getting cooking tips..."):
                                    tips_prompt = f"Provide 3-4 practical cooking tips and techniques for preparing: {name}"
                                    cooking_tips = generate_api_call(tips_prompt)
                                    if cooking_tips:
                                        st.info(f"**Cooking Tips:**\n\n{cooking_tips}")
            
            with exercise_tab:
                st.markdown("### 💪 Today's Workout Routine")
                
                if not day_plan["exercise"] or len(day_plan["exercise"]) == 0:
                    st.warning("⚠️ No exercises found in today's plan. Let me generate some for you!")
                    
                    # Generate exercises if none exist
                    if st.button("🏋️ Generate Today's Exercises", use_container_width=True):
                        with st.spinner("Creating your workout routine..."):
                            exercise_prompt = f"""
                            Create a detailed exercise plan for someone with these goals: {fitness_goal}.
                            
                            Format your response with exercise names in bold followed by instructions:
                            **Warm-up: Light Stretching**
                            5-10 minutes of light stretching focusing on major muscle groups.
                            
                            **Exercise 1: Push-ups**
                            3 sets of 10-15 repetitions. Keep your body straight and lower yourself until your chest nearly touches the floor.
                            
                            Include 4-5 exercises with sets, reps, and proper form instructions.
                            """
                            new_exercises = generate_api_call(exercise_prompt)
                            if new_exercises:
                                # Parse the generated exercises
                                exercise_matches = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)(?=\n\*\*|\Z)", new_exercises, re.DOTALL)
                                if exercise_matches:
                                    day_plan["exercise"] = exercise_matches
                                    st.success("✅ Exercises generated! Check below:")
                                    st.rerun()
                
                for i, (name, instructions) in enumerate(day_plan["exercise"]):
                    with st.container(border=True):
                        st.markdown(f"### {name}")
                        st.markdown(instructions.strip())
                        
                        # Exercise details in expandable section
                        with st.expander("📋 Exercise Details & Form Tips", expanded=False):
                            detail_col1, detail_col2 = st.columns(2)
                            
                            with detail_col1:
                                with st.spinner("Getting form tips..."):
                                    form_prompt = f"Provide proper form and safety tips for: {name}. Include common mistakes to avoid."
                                    form_tips = generate_api_call(form_prompt)
                                    if form_tips:
                                        st.markdown(f"**Proper Form:**\n\n{form_tips}")
                            
                            with detail_col2:
                                with st.spinner("Finding muscle groups..."):
                                    muscle_prompt = f"What muscle groups does {name} target? List primary and secondary muscles worked."
                                    muscles = generate_api_call(muscle_prompt)
                                    if muscles:
                                        st.markdown(f"**Muscles Targeted:**\n\n{muscles}")
                        
                        # Action buttons
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        
                        with btn_col1:
                            # YouTube tutorial
                            exercise_name = name.split(':')[-1].strip()
                            query = f"how to do {exercise_name} proper form tutorial"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("🎥 Exercise Tutorial", yt_url, use_container_width=True)
                        
                        with btn_col2:
                            # Alternative exercise
                            if st.button("🔄 Alternative", key=f"swap_exercise_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Finding alternatives..."):
                                    alt_prompt = f"Suggest an alternative exercise to {name} that targets similar muscle groups and fits a {fitness_goal.lower()} routine. Include sets and reps."
                                    alternative = generate_api_call(alt_prompt)
                                    if alternative:
                                        st.success(f"💡 **Alternative Exercise:**\n\n{alternative}")
                        
                        with btn_col3:
                            # Modification options
                            if st.button("⚙️ Modifications", key=f"mod_exercise_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Finding modifications..."):
                                    mod_prompt = f"Provide beginner and advanced modifications for: {name}"
                                    modifications = generate_api_call(mod_prompt)
                                    if modifications:
                                        st.info(f"**Exercise Modifications:**\n\n{modifications}")
            
            # Enhanced disclaimer
            st.warning(f"⚠️ **Important Disclaimer:** {day_plan['disclaimer']}", icon="⚠️")

    # --- Enhanced AI Health Chat Tab ---
    with chat_tab:
        st.markdown("## 🤖 Your Personal AI Health Assistant")
        st.info("💬 Ask me anything about fitness, nutrition, wellness, or your personalized plan!")
        
        # Initialize chat
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "Hello! 👋 I'm your AI Health Coach! I'm here to help you with:\n\n• Fitness and exercise advice\n• Nutrition guidance\n• Wellness tips\n• Questions about your personalized plan\n• Motivation and support\n\nWhat would you like to know today?"
            }]
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about your health and fitness journey..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            # Generate assistant response
            with st.chat_message("assistant", avatar="🤖"):
                system_prompt = {
                    "role": "system", 
                    "content": """You are an expert AI Health Coach with extensive knowledge in:
                    - Fitness and exercise science
                    - Nutrition and dietetics
                    - Mental wellness and motivation
                    - Injury prevention and recovery
                    - Lifestyle optimization
                    
                    Provide helpful, evidence-based advice while being encouraging and supportive. 
                    Always remind users to consult healthcare professionals for medical concerns.
                    Keep responses conversational, practical, and actionable."""
                }
                
                messages_for_api = [system_prompt] + st.session_state.messages
                
                try:
                    stream = client.chat.completions.create(
                        model="gpt-4o", 
                        messages=messages_for_api, 
                        stream=True,
                        max_tokens=1000,
                        temperature=0.7
                    )
                    response = st.write_stream(stream)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_response = f"I apologize, but I'm having trouble connecting right now. Error: {str(e)}"
                    st.error(error_response)
                    st.session_state.messages.append({"role": "assistant", "content": error_response})
        
        # Chat controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = [{
                    "role": "assistant", 
                    "content": "Chat cleared! How can I help you with your wellness journey today?"
                }]
                st.rerun()
        
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
                tip = tips[len(st.session_state.messages) % len(tips)]
                st.info(f"**Daily Tip:** {tip}")

# --- Entry Point ---
# API Key Configuration with enhanced error handling
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception as e:
        api_key = None

if not api_key:
    st.error("""
    🚨 **OpenAI API Key Required**
    
    Please set your OpenAI API key:
    1. As an environment variable: `OPENAI_API_KEY`
    2. In Streamlit Secrets (for cloud deployment)
    
    Get your API key from: https://platform.openai.com/api-keys
    """)
    st.stop()

try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Route to appropriate page
if st.session_state.logged_in:
    main_app()
else:
    login_page()
