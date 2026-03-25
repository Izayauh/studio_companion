import streamlit as st
import google.generativeai as genai
import os
import time
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Studio Companion",
    page_icon="🎧",
    layout="centered"
)

# Styling
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.2rem;
        opacity: 0.8;
        text-align: center;
        margin-bottom: 2rem;
    }
    div.stSpinner > div {
        text-align: center;
        align-items: center;
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">🎧 Studio Companion</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI A&R • Vibes • Technical Feedback</div>', unsafe_allow_html=True)

# Sidebar for API Key
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Try to load from env or session state
    api_key = st.text_input("Gemini API Key", type="password", help="Get from aistudio.google.com/app/apikey")
    
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
        genai.configure(api_key=api_key)
        st.success("API Key loaded!")
    else:
        st.warning("Please enter API Key")

# Main content
uploaded_file = st.file_uploader("Drop your track (MP3, WAV, M4A)", type=['mp3', 'wav', 'm4a', 'flac', 'ogg'])

if uploaded_file and api_key:
    st.audio(uploaded_file, format='audio/mp3')
    
    # Save temp file
    temp_path = Path(f"temp_{uploaded_file.name}")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.divider()
    st.subheader("Choose Your Feedback Mode")
    
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    mode = None
    
    with col1:
        if st.button("👹 Ruthless A&R"):
            mode = "Ruthless A&R"
    with col2:
        if st.button("🫂 Studio Buddy"):
            mode = "Supportive Studio Buddy"
    with col3:
        if st.button("🎛️ Technical Engineer"):
            mode = "Technical Engineer"
    with col4:
        if st.button("✨ Vibe Check"):
            mode = "Vibe Check"

    if mode:
        with st.status(f"🎧 {mode} is listening...", expanded=True) as status:
            try:
                # Upload to Gemini
                st.write("Uploading audio to Gemini...")
                audio_file = genai.upload_file(path=temp_path)
                
                # Wait for processing
                while audio_file.state.name == "PROCESSING":
                    time.sleep(1)
                    audio_file = genai.get_file(audio_file.name)
                
                if audio_file.state.name == "FAILED":
                    st.error("Audio processing failed.")
                    st.stop()
                
                st.write("Selecting best audio model...")
                
                # Smart Model Selection for 2026
                target_models = [
                    'gemini-2.0-pro-exp-01-28', # Experimental Pro
                    'gemini-2.0-flash',         # Fast & Good
                    'gemini-1.5-pro',           # Old Faithful
                    'gemini-1.5-flash'          # Backup
                ]
                
                selected_model = None
                
                # Try to list models and pick the best available one
                try:
                    available_models = [m.name for m in genai.list_models()]
                    # Look for Pro models first
                    for m in available_models:
                        if 'gemini-2.0-pro' in m:
                            selected_model = m
                            break
                    if not selected_model:
                        for m in available_models:
                            if 'gemini-2.0-flash' in m:
                                selected_model = m
                                break
                except:
                    pass
                
                # Fallback to hardcoded list if listing fails
                if not selected_model:
                    selected_model = 'gemini-2.0-flash' # Default to Flash 2.0 (usually available)

                st.write(f"Using model: `{selected_model}`")
                model = genai.GenerativeModel(selected_model)
                
                prompts = {
                    "Ruthless A&R": """You are a ruthless, high-level A&R executive at a major label. You don't care about feelings, you care about hits. 
                    Listen to this track critically.
                    1. Is this marketable? Who is the audience?
                    2. What is the weakest part of the song? (Be specific: flow, beat, mix, lyrics)
                    3. Does the hook hit? If not, why?
                    4. Give it a brutally honest rating out of 10 for commercial potential.
                    5. One specific change that would make it sell.
                    Don't hold back. Use industry slang but keep it professional and cutting.""",

                    "Supportive Studio Buddy": """You are the artist's best friend and collaborator in the studio. You believe in their vision 100%.
                    Listen to this track.
                    1. What is the absolute best moment? Hype them up about it.
                    2. How does the track make you feel emotionally?
                    3. Compare it to a great artist (e.g. "This gives me Cudi vibes mixed with...")
                    4. One gentle suggestion to take it to the next level (e.g. "Maybe add some reverb on that vocal...")
                    5. Validate the effort. Remind them why they do this.
                    Keep the energy high, warm, and encouraging.""",

                    "Technical Engineer": """You are a senior mixing and mastering engineer. You focus on the sonics.
                    Analyze the audio waveform and production.
                    1. How is the balance? (Vocals vs beat, low end vs high end)
                    2. Comment on the dynamic range and energy curve.
                    3. Instrumentation breakdown — what are you hearing?
                    4. Any technical flaws? (Clipping, mud, sibilance, timing issues)
                    5. One mix tip to improve clarity.
                    Be objective, technical, and precise.""",

                    "Vibe Check": """You are a vibe curator for a high-end playlist or blog. You focus on atmosphere and aesthetic.
                    1. Describe the aesthetic in 3 words.
                    2. What setting does this song belong in? (Late night drive, gym, rainy window, club)
                    3. Color palette — what colors does the sound evoke?
                    4. What story is the sound telling, independent of lyrics?
                    5. Should I save this to my rotation?"""
                }
                
                response = model.generate_content([prompts[mode], audio_file])
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                
                st.markdown("### Feedback")
                st.markdown(response.text)
                
                # Cleanup
                temp_path.unlink()
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Tip: Check your API key has access to Gemini 2.0/1.5 models in AI Studio.")

elif not api_key:
    st.info("👈 Enter your Gemini API Key in the sidebar to start.")
