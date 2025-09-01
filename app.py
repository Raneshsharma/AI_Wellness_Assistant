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
    """Injects CSS and HTML for a YouTube video background on the login page."""
    video_id = "XMwzUDoBuIY"  # Extracted from your link
    video_html = f"""
    <style>
        /* Hide Streamlit elements for cleaner look */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        /* Make the main app container transparent over the video */
        [data-testid="stAppViewContainer"] > .main {{
            background: none;
            padding-top: 2rem;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(0,0,0,0);
        }}
        
        /* Container to hold the video and ensure it covers the screen */
        .video-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            z-index: -100;
        }}
        
        /* Style the iframe to cover the container, maintaining aspect ratio */
        .video-container iframe {{
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100vw;
            height: 56.25vw; /* 16:9 Aspect Ratio */
            min-height: 100vh;
            min-width: 177.77vh; /* 16:9 Aspect Ratio */
            transform: translate(-50%, -50%);
            filter: brightness(0.3) contrast(1.2); /* Dim and enhance contrast */
        }}
        
        /* Enhanced login container styling */
        .login-container {{
            background: linear-gradient(135deg, rgba(0,0,0,0.8) 0%, rgba(21, 32, 42, 0.9) 100%);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
            padding: 2rem;
            margin: 2rem auto;
            max-width: 500px;
        }}
        
        /* Welcome text styling */
        .welcome-title {{
            text-align: center;
            color: #fafafb;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            background: linear-gradient(45deg, #e74c3c, #f39c12, #e74c3c);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 3s ease-in-out infinite;
        }}
        
        .welcome-subtitle {{
            text-align: center;
            color: #dedee4;
            font-size: 1.2rem;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
        }}
        
        @keyframes gradientShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        
        /* Enhanced button styling */
        .stButton>button {{
            border: 2px solid transparent;
            color: #fafafb;
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            transition: all 0.3s ease-in-out;
            width: 100%;
            height: 3rem;
            border-radius: 15px;
            font-weight: 600;
            font-size: 1.1rem;
            box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
            background: linear-gradient(45deg, #c0392b, #e74c3c);
        }}
        
        /* Form styling */
        .stTextInput > div > div > input {{
            background-color: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            color: #fafafb;
            padding: 0.75rem;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: #e74c3c;
            box-shadow: 0 0 10px rgba(231, 76, 60, 0.3);
        }}
        
        /* Tab buttons styling */
        .tab-button {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px 10px 0 0;
            color: #fafafb;
            padding: 1rem;
            margin: 0 0.25rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .tab-button.active {{
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            border-bottom: 1px solid #e74c3c;
        }}
    </style>
    <div class="video-container">
        <iframe
            src="https://www.youtube.com/embed/{video_id}?autoplay=1&loop=1&mute=1&controls=0&playlist={video_id}&showinfo=0&autohide=1&modestbranding=1&rel=0"
            frameborder="0"
            allow="autoplay; encrypted-media"
            allowfullscreen>
        </iframe>
    </div>
    """
    st.markdown(video_html, unsafe_allow_html=True)

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

    **Your Task:**
    Generate a comprehensive 7-day wellness plan tailored to their specific goals.
    For each meal (Breakfast, Lunch, Dinner, Snack) and exercise, provide:
    1. The name in bold (e.g., **Breakfast: Scrambled Eggs**).
    2. Clear, actionable instructions with portion sizes and timing.
    3. Nutritional highlights and benefits.
    Do NOT include image prompts.
    Make the plan realistic, achievable, and scientifically sound.
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
    """Displays the enhanced login and sign-up page with video background."""
    # Always inject video background when login page loads
    inject_video_background()
    
    # Create centered login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Welcome header
        st.markdown('<div class="welcome-title">AI Wellness Coach Pro</div>', unsafe_allow_html=True)
        st.markdown('<div class="welcome-subtitle">Transform Your Health Journey</div>', unsafe_allow_html=True)
        
        # Tab-like navigation
        if 'page' not in st.session_state:
            st.session_state.page = 'Login'

        col_login, col_signup = st.columns(2)
        with col_login:
            if st.button("🔑 Login", use_container_width=True, key="login_tab"):
                st.session_state.page = 'Login'
        with col_signup:
            if st.button("🚀 Sign Up", use_container_width=True, key="signup_tab"):
                st.session_state.page = 'Sign Up'
        
        st.divider()

        # Using a placeholder for user management
        if 'user_db' not in st.session_state:
            st.session_state.user_db = {"demo": "demo123", "admin": "admin123"} 
        
        if st.session_state.page == 'Login':
            st.markdown("### 🔐 Welcome Back")
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                col_submit, col_demo = st.columns([2, 1])
                with col_submit:
                    submitted = st.form_submit_button("Login", use_container_width=True)
                with col_demo:
                    demo_login = st.form_submit_button("Demo", use_container_width=True)
                    
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
                        st.success("Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
            
            st.info("💡 **Demo Account:** Username: `demo` | Password: `demo123`")

        elif st.session_state.page == 'Sign Up':
            st.markdown("### 🌟 Create Your Profile")
            with st.form("signup_form"):
                new_username = st.text_input("👤 Choose Username", placeholder="Enter desired username")
                new_password = st.text_input("🔒 Choose Password", type="password", placeholder="Create a secure password")
                confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if submitted:
                    if not new_username or not new_password:
                        st.error("❌ Please fill out all fields.")
                    elif len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters long.")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match!")
                    elif new_username in st.session_state.user_db:
                        st.error("❌ Username already exists!")
                    else:
                        st.session_state.user_db[new_username] = new_password
                        st.success(f"✅ Account created for '{new_username}'! Please login.")
                        st.session_state.page = 'Login'
                        time.sleep(2)
                        st.rerun()
        
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
            
            # Enhanced chart
            goal_df = pd.DataFrame({
                'week': [df['week'].min(), df['week'].max()],
                'weight': [st.session_state.goal_weight, st.session_state.goal_weight]
            })

            base = alt.Chart().add_selection(
                alt.selection_interval(bind='scales')
            )

            line = base.mark_line(
                point=alt.OverlayMarkDef(filled=True, size=100),
                color='#e74c3c',
                strokeWidth=3
            ).encode(
                x=alt.X('week:Q', title='Week'),
                y=alt.Y('weight:Q', title='Weight (kg)', scale=alt.Scale(zero=False)),
                tooltip=['week:Q', 'weight:Q']
            ).properties(
                title=alt.TitleParams('Weight Progress vs. Goal', fontSize=16, color='#fafafb')
            )

            goal_line = base.mark_line(
                strokeDash=[5,5], 
                color='#f39c12',
                strokeWidth=2
            ).encode(
                x='week:Q',
                y='weight:Q'
            )

            chart_data = df
            goal_chart_data = goal_df
            
            combined_chart = alt.layer(
                line.data(chart_data),
                goal_line.data(goal_chart_data)
            ).resolve_scale(color='independent')
            
            st.altair_chart(combined_chart.interactive(), use_container_width=True)
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

            selected_day_index = int(selected_day_str.split()[1]) - 1
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
                for i, (name, instructions) in enumerate(day_plan["diet"]):
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        st.markdown(instructions.strip())
                        
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            query = f"healthy recipe {name.split(':')[-1].strip()}"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("📺 Recipe Video", yt_url, use_container_width=True)
                        
                        with btn_col2:
                            if st.button("🔄 Alternative", key=f"swap_diet_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Finding alternatives..."):
                                    alt_prompt = f"Suggest a healthy alternative to {name} with similar nutritional value for a {diet_preference} {fitness_goal.lower()} plan."
                                    alternative = generate_api_call(alt_prompt)
                                    if alternative:
                                        st.success(f"💡 Alternative: {alternative}")
                        
                        with btn_col3:
                            if st.button("📊 Nutrition", key=f"nutrition_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Analyzing nutrition..."):
                                    nutrition_prompt = f"Provide detailed nutritional information for: {name} - {instructions[:100]}..."
                                    nutrition_info = generate_api_call(nutrition_prompt)
                                    if nutrition_info:
                                        st.info(nutrition_info)
            
            with exercise_tab:
                st.markdown("### 💪 Today's Workout Routine")
                for i, (name, instructions) in enumerate(day_plan["exercise"]):
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        st.markdown(instructions.strip())
                        
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        with btn_col1:
                            query = f"how to do {name.strip()} exercise tutorial"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("🎥 Exercise Video", yt_url, use_container_width=True)
                        
                        with btn_col2:
                            if st.button("🔄 Alternative", key=f"swap_exercise_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Finding alternatives..."):
                                    alt_prompt = f"Suggest an alternative exercise to {name} that targets similar muscle groups and fits a {fitness_goal.lower()} routine."
                                    alternative = generate_api_call(alt_prompt)
                                    if alternative:
                                        st.success(f"💡 Alternative: {alternative}")
                        
                        with btn_col3:
                            if st.button("📋 Form Tips", key=f"form_{selected_day_index}_{i}", use_container_width=True):
                                with st.spinner("Getting form tips..."):
                                    form_prompt = f"Provide proper form and technique tips for: {name}"
                                    form_tips = generate_api_call(form_prompt)
                                    if form_tips:
                                        st.info(form_tips)
            
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
