import streamlit as st
import os
from openai import OpenAI
import time
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Wellness Coach",
    page_icon="💪",
    layout="wide"
)

# --- Animated Background & New Dark Theme CSS ---
# Injects CSS to create a beautiful, moving gradient background and sets a new dark theme based on the provided palette.
page_bg_img = """
<style>
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

/* Make text in all headers and subheaders light using Text-100 */
h1, h2, h3, h4, h5, h6 {
    color: #fafafb;
}

/* Style the sidebar for dark theme using Background-300 */
[data-testid="stSidebar"] {
    background-color: rgba(21, 32, 42, 0.7); /* Background-300 with transparency */
}

/* Style the chat messages for dark theme using Background-300 */
[data-testid="stChatMessage"] {
    background-color: rgba(21, 32, 42, 0.8); /* Background-300 with transparency */
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
}

/* Ensure metric labels are visible using Text-300 */
[data-testid="stMetricLabel"] {
    color: #dedee4;
}

/* Make Streamlit buttons more visible using Text-100 and Accent-100 */
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
.stButton>button:active {
    border: 1px solid #e74c3c;
    color: #e74c3c;
    background-color: rgba(231, 76, 60, 0.2);
}


/* Improve visibility of tabs using Background-200 and Accent-100 */
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    background-color: rgba(13, 19, 25, 0.5); /* Background-200 with transparency */
    border-radius: 4px 4px 0px 0px;
    gap: 1px;
    padding-top: 10px;
    padding-bottom: 10px;
    transition: all 0.2s ease-in-out;
}
.stTabs [aria-selected="true"] {
    background-color: #e74c3c; /* Accent-100 */
    color: #fafafb; /* Text-100 */
    font-weight: bold;
}

/* Style the bordered containers to look like cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: rgba(21, 32, 42, 0.5); /* Background-300 with transparency */
    border-radius: 0.5rem;
    padding: 1.5rem;
    border: 1px solid rgba(62, 88, 113, 0.3); /* Primary-200 with transparency */
}

</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)


# --- API Key Configuration ---
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("🚨 OPENAI_API_KEY not found in Streamlit Secrets! Please add it in your app's settings.")
    st.stop()
client = OpenAI(api_key=api_key)

# --- Helper Functions ---

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
        # Updated regex to find bolded title and the following instructions
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
    
# --- UI Layout ---

# Sidebar (controls the plan generator)
with st.sidebar:
    st.header("👤 Your Details")
    age = st.slider("Age", 16, 100, 25)
    gender = st.selectbox("Gender", ("Male", "Female"))
    height = st.slider("Height (cm)", 100, 250, 170)
    weight = st.slider("Weight (kg)", 30, 200, 70)
    st.header("🥗 Your Preferences")
    diet_preference = st.selectbox("Dietary Preference", ("No Preference", "Vegetarian", "Vegan", "Keto"))
    fitness_goal = st.selectbox("Primary Fitness Goal", ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance"))
    submit_button = st.button(label='✨ Generate My 7-Day Plan!', use_container_width=True)

# Main Page
st.title("AI Wellness Coach Pro 💪")

# --- Main Tabs for App Features ---
plan_tab, chat_tab = st.tabs(["📅 Plan Generator", "💬 AI Health Chat"])

# --- Plan Generator Tab ---
with plan_tab:
    st.header("Your Personalized 7-Day Plan")
    st.markdown("Fill in your details in the sidebar and click the button to generate your unique wellness guide!")

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

        # --- Dashboard Metrics ---
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
                            with st.spinner("Finding a tasty alternative..."):
                                prompt = f"Suggest a single alternative meal for '{name}' with a similar calorie count and dietary profile ({diet_preference}). Structure the response exactly like this: **New Meal Name**\nInstructions..."
                                alternative = generate_api_call(prompt)
                                if alternative:
                                    new_item = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*)", alternative, re.DOTALL)[0]
                                    st.session_state.weekly_plan[selected_day_index]["diet"][i] = new_item
                                    st.rerun()

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
                             with st.spinner("Finding a different exercise..."):
                                prompt = f"Suggest a single alternative exercise for '{name}' that targets similar muscle groups. Structure the response exactly like this: **New Exercise Name**\nInstructions..."
                                alternative = generate_api_call(prompt)
                                if alternative:
                                    new_item = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*)", alternative, re.DOTALL)[0]
                                    st.session_state.weekly_plan[selected_day_index]["exercise"][i] = new_item
                                    st.rerun()

        st.warning(f"**Disclaimer:** {day_plan['disclaimer']}", icon="⚠️")

# --- AI Health Chat Tab ---
with chat_tab:
    st.header("Your Personal AI Health Assistant")
    st.markdown("Ask me anything about fitness, nutrition, or your wellness plan!")

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! How can I help you on your wellness journey today?"}
        ]

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="💪" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What's on your mind?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant", avatar="💪"):
            # Create the system prompt with context
            system_prompt = {
                "role": "system",
                "content": """You are a friendly and knowledgeable AI Health Coach.
                Your expertise is in fitness, nutrition, and general wellness.
                Provide supportive and informative answers. You are not a medical doctor.
                Always conclude your responses with a gentle reminder for the user to consult with a healthcare professional
                for any medical advice or diagnosis."""
            }
            messages_for_api = [system_prompt] + st.session_state.messages
            
            # Generate and stream the response
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_api,
                stream=True,
            )
            response = st.write_stream(stream)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

