import streamlit as st
import os
from openai import OpenAI
import time
import re
import pandas as pd
import altair as alt

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Wellness Coach",
    page_icon="💪",
    layout="wide"
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
        /* Make the main app container transparent over the video */
        [data-testid="stAppViewContainer"] > .main {{
            background: none;
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
            filter: brightness(0.4); /* Dim the video */
        }}
        /* Style the login form elements on top of the video */
        .stButton>button {{
            border: 2px solid #fafafb;
            color: #fafafb;
            background-color: rgba(0,0,0,0.5);
            transition: all 0.2s ease-in-out;
            width: 100%;
        }}
        .stButton>button:hover {{
            border-color: #e74c3c;
            color: #e74c3c;
        }}
    </style>
    <div class="video-container">
        <iframe
            src="https://www.youtube.com/embed/{video_id}?autoplay=1&loop=1&mute=1&controls=0&playlist={video_id}&showinfo=0&autohide=1&modestbranding=1"
            frameborder="0"
            allow="autoplay; encrypted-media"
            allowfullscreen>
        </iframe>
    </div>
    """
    st.markdown(video_html, unsafe_allow_html=True)


def get_main_app_css():
    """Returns CSS for the main application with the animated dark theme."""
    return """
    /* Main animated background using Background palette */
    [data-testid="stAppViewContainer"] {
        background-image: linear-gradient(-45deg, #040608, #15202a, #0d1319);
        animation: gradient 15s ease infinite;
        background-size: 400% 400%;
        color: #fafafb; /* Use Text-100 for default text */
    }

    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

    h1, h2, h3, h4, h5, h6 { color: #fafafb; }
    [data-testid="stSidebar"] { background-color: rgba(21, 32, 42, 0.7); }
    [data-testid="stChatMessage"] { background-color: rgba(21, 32, 42, 0.8); }
    [data-testid="stMetricLabel"] { color: #dedee4; }
    .stButton>button {
        border: 1px solid #fafafb;
        color: #fafafb;
        background-color: transparent;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        border: 1px solid #e74c3c;
        color: #e74c3c;
        background-color: rgba(231, 76, 60, 0.1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #e74c3c;
        color: #fafafb;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(21, 32, 42, 0.5);
        border-radius: 0.5rem;
        padding: 1.5rem;
        border: 1px solid rgba(62, 88, 113, 0.3);
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
                {"role": "system", "content": "You are an expert wellness coach."},
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
    Generate a comprehensive 7-day wellness plan.
    For each meal (Breakfast, Lunch, Dinner, Snack) and exercise, provide:
    1. The name in bold (e.g., **Breakfast: Scrambled Eggs**).
    2. Clear and concise instructions.
    Do NOT include image prompts.
    """
    return generate_api_call(prompt)
    
# --- Main Application Logic ---

def login_page():
    """Displays the login and sign-up page."""
    inject_video_background()
    st.title("Welcome to AI Wellness Coach Pro 💪")
    
    if 'page' not in st.session_state:
        st.session_state.page = 'Login'

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            st.session_state.page = 'Login'
    with col2:
        if st.button("Sign Up"):
            st.session_state.page = 'Sign Up'
    
    st.divider()

    # Using a placeholder for user management. In a real app, this would be a database.
    if 'user_db' not in st.session_state:
        st.session_state.user_db = {"user": "123"} 
    
    if st.session_state.page == 'Login':
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username in st.session_state.user_db and st.session_state.user_db[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    # Initialize user-specific data
                    if 'goal_weight' not in st.session_state:
                        st.session_state.goal_weight = 75
                    if 'weight_log' not in st.session_state:
                        st.session_state.weight_log = []
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    elif st.session_state.page == 'Sign Up':
        st.header("Create Your Profile")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match!")
                elif new_username in st.session_state.user_db:
                    st.error("Username already exists!")
                elif not new_username or not new_password:
                    st.error("Please fill out all fields.")
                else:
                    st.session_state.user_db[new_username] = new_password
                    st.success(f"Profile for '{new_username}' created successfully! Please go to the Login page.")
                    st.session_state.page = 'Login'
                    time.sleep(2)
                    st.rerun()

def main_app():
    """The main application interface, shown after successful login."""
    apply_css(get_main_app_css())

    # Sidebar for plan generation and logout
    with st.sidebar:
        st.header(f"Welcome, {st.session_state.username}!")
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ['user_db']: # Keep user database
                    del st.session_state[key]
            st.rerun()
        st.divider()

        st.header("👤 Your Details")
        age = st.slider("Age", 16, 100, 25)
        gender = st.selectbox("Gender", ("Male", "Female"))
        height = st.slider("Height (cm)", 100, 250, 170)
        weight = st.slider("Weight (kg)", 30, 200, 70)
        st.header("🥗 Your Preferences")
        diet_preference = st.selectbox("Dietary Preference", ("No Preference", "Vegetarian", "Vegan", "Keto"))
        fitness_goal = st.selectbox("Primary Fitness Goal", ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance"))
        submit_button = st.button(label='✨ Generate My 7-Day Plan!', use_container_width=True)

    st.title("AI Wellness Coach Pro 💪")

    # Main Tabs for App Features
    profile_tab, plan_tab, chat_tab = st.tabs(["📊 Profile & Progress", "📅 Plan Generator", "💬 AI Health Chat"])

    # --- Profile & Progress Tab ---
    with profile_tab:
        st.header(f"Your Wellness Dashboard, {st.session_state.username}")
        
        prof_col1, prof_col2 = st.columns(2)
        with prof_col1:
            with st.container(border=True):
                st.subheader("🎯 Set Your Goal")
                st.session_state.goal_weight = st.number_input("Goal Weight (kg)", min_value=30, max_value=200, value=st.session_state.get('goal_weight', 75))

        with prof_col2:
            with st.container(border=True):
                st.subheader("✍️ Log Your Progress")
                current_weight = st.number_input("Today's Weight (kg)", min_value=30, max_value=200, value=weight)
                if st.button("Log Weight", use_container_width=True):
                    week_num = len(st.session_state.weight_log) + 1
                    st.session_state.weight_log.append({"week": week_num, "weight": current_weight})
                    st.success(f"Logged {current_weight}kg for Week {week_num}!")

        st.divider()
        st.subheader("📈 Your Journey So Far")
        if st.session_state.weight_log:
            df = pd.DataFrame(st.session_state.weight_log)
            
            # Create a dataframe for the goal line
            goal_df = pd.DataFrame({
                'week': [df['week'].min(), df['week'].max()],
                'weight': [st.session_state.goal_weight, st.session_state.goal_weight]
            })

            # User's progress line
            line = alt.Chart(df).mark_line(point=True, color='#e74c3c').encode(
                x=alt.X('week:Q', title='Week'),
                y=alt.Y('weight:Q', title='Weight (kg)', scale=alt.Scale(zero=False)),
                tooltip=['week', 'weight']
            ).properties(
                title='Weight Progress vs. Goal'
            )

            # Goal line
            goal_line = alt.Chart(goal_df).mark_line(strokeDash=[5,5], color='#fafafb').encode(
                x='week:Q',
                y='weight:Q'
            )

            st.altair_chart((line + goal_line).interactive(), use_container_width=True)
        else:
            st.info("Log your weight to see your progress chart here!")


    # --- Plan Generator Tab ---
    with plan_tab:
        st.header("Your Personalized 7-Day Plan")
        st.markdown("Your details are pre-filled from the sidebar. Click the button to generate your unique wellness guide!")

        if "plan_generated" not in st.session_state:
            st.session_state.plan_generated = False

        if submit_button:
            with st.spinner("Your AI coach is crafting the perfect 7-day plan... This will be quick!"):
                full_plan = generate_wellness_plan(age, gender, height, weight, diet_preference, fitness_goal)
                if full_plan:
                    st.session_state.weekly_plan = parse_weekly_plan(full_plan)
                    st.session_state.plan_generated = True
                    st.session_state.shopping_list = None
                else:
                    st.session_state.plan_generated = False

        if st.session_state.plan_generated and "weekly_plan" in st.session_state:
            # Plan Display Logic (copied from previous version)
            weekly_plan = st.session_state.weekly_plan
            col1, col2 = st.columns([3,1])
            with col1:
                day_options = [f"Day {i+1}" for i in range(len(weekly_plan))]
                selected_day_str = st.selectbox("Select a day to view:", day_options, label_visibility="collapsed", key="day_selector")
            with col2:
                if st.button("🛒 Generate Shopping List", use_container_width=True):
                    diet_plan_text = "\n".join([f"Day {i+1}:\n" + "\n".join([item[1] for item in day['diet']]) for i, day in enumerate(weekly_plan)])
                    with st.spinner("Analyzing your diet plan..."):
                        prompt = f"Based on the following 7-day diet plan, create a consolidated shopping list organized by category (e.g., Produce, Protein, Pantry, Dairy):\n\n{diet_plan_text}"
                        st.session_state.shopping_list = generate_api_call(prompt)

            if st.session_state.get("shopping_list"):
                with st.expander("Your Consolidated Shopping List", expanded=True):
                    st.markdown(st.session_state.shopping_list)

            selected_day_index = day_options.index(selected_day_str)
            day_plan = weekly_plan[selected_day_index]
            
            st.header(f"Dashboard for Day {selected_day_index + 1}")
            dash_col1, dash_col2 = st.columns(2)
            with dash_col1:
                with st.container(border=True):
                    st.subheader("🎯 Daily Calorie Target")
                    st.metric(label="Estimated Calories", value=re.search(r'\d[\d,]*', day_plan["calories"]).group(0) if re.search(r'\d[\d,]*', day_plan["calories"]) else "N/A")
            with dash_col2:
                with st.container(border=True):
                    st.subheader("💡 Motivational Tip")
                    st.write(day_plan['motivation'])
            
            st.divider()
            diet_tab, exercise_tab = st.tabs(["🍎 Diet Plan", "🏋️ Exercise Plan"])
            # ... (rest of the diet/exercise display logic remains the same)
            with diet_tab:
                st.subheader("Today's Meals")
                for i, (name, instructions) in enumerate(day_plan["diet"]):
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        st.markdown(instructions.strip())
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            query = f"how to make {name.split(':')[-1].strip()}"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("▶️ Find Recipe on YouTube", yt_url, use_container_width=True)
                        with btn_col2:
                            if st.button("🔄 Suggest Alternative", key=f"swap_diet_{selected_day_index}_{i}", use_container_width=True):
                                # Swap logic here...
                                pass
            with exercise_tab:
                st.subheader("Today's Workout")
                for i, (name, instructions) in enumerate(day_plan["exercise"]):
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        st.markdown(instructions.strip())
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            query = f"how to do {name.strip()}"
                            yt_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            st.link_button("▶️ Watch Tutorial on YouTube", yt_url, use_container_width=True)
                        with btn_col2:
                            if st.button("🔄 Suggest Alternative", key=f"swap_exercise_{selected_day_index}_{i}", use_container_width=True):
                                # Swap logic here...
                                pass
            st.warning(f"**Disclaimer:** {day_plan['disclaimer']}", icon="⚠️")


    # --- AI Health Chat Tab ---
    with chat_tab:
        st.header("Your Personal AI Health Assistant")
        st.markdown("Ask me anything about fitness, nutrition, or your wellness plan!")
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you on your wellness journey today?"}]
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="💪" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
        if prompt := st.chat_input("What's on your mind?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="💪"):
                system_prompt = {"role": "system", "content": """You are a friendly and knowledgeable AI Health Coach. Your expertise is in fitness, nutrition, and general wellness. Provide supportive and informative answers. You are not a medical doctor. Always conclude your responses with a gentle reminder for the user to consult with a healthcare professional for any medical advice or diagnosis."""}
                messages_for_api = [system_prompt] + st.session_state.messages
                stream = client.chat.completions.create(model="gpt-4o", messages=messages_for_api, stream=True)
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- Entry Point ---
# API Key Configuration
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    # This check runs when deployed on Streamlit Cloud
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception as e:
        api_key = None

if not api_key:
    st.error("🚨 OPENAI_API_KEY not found! Please set it as an environment variable or in Streamlit Secrets.")
    st.stop()
    
client = OpenAI(api_key=api_key)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_app()
else:
    login_page()

