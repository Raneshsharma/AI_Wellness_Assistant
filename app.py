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

# --- API Key Configuration ---
# The API key is securely accessed from Streamlit's Secrets manager
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("🚨 OPENAI_API_KEY not found in Streamlit Secrets! Please add it in your app's settings.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- Helper Functions ---

@st.cache_data(show_spinner=False)
def generate_image(prompt):
    """Generates an image using DALL-E 3 based on a descriptive prompt."""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Create a vibrant, high-quality, photorealistic image for a wellness app: {prompt}. Ensure there is no text in the image.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None

def parse_plan(plan_text):
    """Parses the AI's response into sections and items with image prompts."""
    sections = {
        "calories": "Could not determine calorie target.",
        "diet": [],
        "exercise": [],
        "motivation": "Motivational tip not found.",
        "disclaimer": "Disclaimer not found."
    }
    calorie_match = re.search(r"### Estimated Daily Calorie Target ###\s*(.*?)\s*(?=\n###|$)", plan_text, re.DOTALL)
    diet_section_match = re.search(r"### Detailed Diet Plan ###\s*(.*?)\s*(?=\n###|$)", plan_text, re.DOTALL)
    exercise_section_match = re.search(r"### Detailed Exercise Plan ###\s*(.*?)\s*(?=\n###|$)", plan_text, re.DOTALL)
    motivation_match = re.search(r"### Motivational Tip ###\s*(.*?)\s*(?=\n###|$)", plan_text, re.DOTALL)
    disclaimer_match = re.search(r"### Disclaimer ###\s*(.*?)\s*(?=\n###|$)", plan_text, re.DOTALL)

    if calorie_match: sections["calories"] = calorie_match.group(1).strip()
    if motivation_match: sections["motivation"] = motivation_match.group(1).strip()
    if disclaimer_match: sections["disclaimer"] = disclaimer_match.group(1).strip()

    if diet_section_match:
        diet_text = diet_section_match.group(1)
        sections["diet"] = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)\s*\[Image Prompt:\s*(.*?)\]", diet_text, re.DOTALL)

    if exercise_section_match:
        exercise_text = exercise_section_match.group(1)
        sections["exercise"] = re.findall(r"\*\*\s*(.*?)\s*\*\*\s*\n(.*?)\s*\[Image Prompt:\s*(.*?)\]", exercise_text, re.DOTALL)

    return sections

def generate_wellness_plan(age, gender, height, weight, diet_preference, fitness_goal):
    """Constructs a prompt that asks for image prompts and calls the OpenAI API."""
    prompt = f"""
    Act as an expert wellness coach. A user has provided their details for a personalized plan.
    Your response MUST be structured with the following exact Markdown headings:
    ### Estimated Daily Calorie Target ###
    ### Detailed Diet Plan ###
    ### Detailed Exercise Plan ###
    ### Motivational Tip ###
    ### Disclaimer ###

    **User's Details:**
    - Age: {age}, Gender: {gender}, Height: {height} cm, Weight: {weight} kg
    - Preference: {diet_preference}, Goal: {fitness_goal}

    **Your Task:**
    Generate a one-day wellness plan.
    Under "Detailed Diet Plan", for each meal (Breakfast, Lunch, Dinner, Snack), provide:
    1. The meal name in bold (e.g., **Breakfast: Scrambled Eggs**).
    2. The instructions.
    3. An image prompt on a new line in the format: [Image Prompt: A detailed, photorealistic description of the meal].

    Under "Detailed Exercise Plan", for each exercise (Warm-up, main exercises, Cool-down), provide:
    1. The exercise name in bold (e.g., **Warm-up: Jumping Jacks**).
    2. The instructions.
    3. An image prompt on a new line in the format: [Image Prompt: A clear, simple illustration of a person doing the exercise, white background].

    The disclaimer must state this is not medical advice.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert wellness coach who provides structured wellness plans with image prompts."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# --- UI Layout ---

# Sidebar
with st.sidebar:
    st.header("👤 Your Details")
    age = st.slider("Age", 16, 100, 25)
    gender = st.selectbox("Gender", ("Male", "Female"))
    height = st.slider("Height (cm)", 100, 250, 170)
    weight = st.slider("Weight (kg)", 30, 200, 70)
    st.header("🥗 Your Preferences")
    diet_preference = st.selectbox("Dietary Preference", ("No Preference", "Vegetarian", "Vegan", "Keto"))
    fitness_goal = st.selectbox("Primary Fitness Goal", ("Lose Weight", "Gain Muscle", "Maintain Weight", "Improve Endurance"))
    submit_button = st.button(label='✨ Generate My Plan!', use_container_width=True)

# Main Page
st.title("AI Wellness Coach 💪")
st.markdown("Your personalized visual guide to a healthier you. Fill in your details in the sidebar to get started!")

if submit_button:
    with st.spinner("Your AI coach is crafting the perfect plan... (This may take a minute)"):
        full_plan = generate_wellness_plan(age, gender, height, weight, diet_preference, fitness_goal)
        if full_plan:
            st.session_state.plan_sections = parse_plan(full_plan)
        else:
            st.session_state.plan_sections = None

if 'plan_sections' in st.session_state and st.session_state.plan_sections:
    sections = st.session_state.plan_sections

    st.header("🎯 Your Daily Calorie Target")
    calorie_number = re.search(r'\d[\d,]*', sections["calories"])
    if calorie_number:
        st.metric(label="Estimated Calories", value=calorie_number.group(0))
    st.markdown(sections["calories"])

    st.header("📅 Your Personalized Plan")
    tab1, tab2 = st.tabs(["🍎 Diet Plan", "🏋️ Exercise Plan"])

    with tab1:
        for name, instructions, img_prompt in sections["diet"]:
            st.subheader(name)
            col1, col2 = st.columns([1,1])
            with col1:
                st.markdown(instructions)
            with col2:
                with st.spinner("🎨 Generating meal image..."):
                    image_url = generate_image(img_prompt)
                    if image_url:
                        st.image(image_url, use_container_width=True) # <-- UPDATED
            st.divider()

    with tab2:
        for name, instructions, img_prompt in sections["exercise"]:
            st.subheader(name)
            col1, col2 = st.columns([1,1])
            with col1:
                st.markdown(instructions)
            with col2:
                with st.spinner("🎨 Generating exercise image..."):
                    image_url = generate_image(img_prompt)
                    if image_url:
                        st.image(image_url, use_container_width=True) # <-- UPDATED
            st.divider()

    st.info(sections["motivation"])
    st.warning(sections["disclaimer"], icon="⚠️")

