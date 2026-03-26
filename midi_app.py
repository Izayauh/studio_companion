import streamlit as st
import os
import re
import subprocess
from pathlib import Path
from chord_to_midi import normalize_chord, voice_chord, generate_midi

# Try to import music21 for live chord validation
try:
    from music21 import harmony
    HAS_MUSIC21 = True
except ImportError:
    HAS_MUSIC21 = False

# ─── Page Config ─────────────────────────────────────────────────

st.set_page_config(
    page_title="MIDI Generator",
    page_icon="🎹",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Dark Theme CSS (AudioCipher-inspired) ───────────────────────

st.markdown("""
<style>
    /* ── Global ── */
    .stApp {
        background: linear-gradient(180deg, #0d0d1a 0%, #131325 100%);
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* ── Main card container ── */
    .main-card {
        background: linear-gradient(145deg, #1a1a2e 0%, #16162a 100%);
        border-radius: 24px;
        padding: 2.5rem 2rem 2rem;
        margin: 0 auto;
        max-width: 520px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 1px rgba(255,255,255,0.08) inset;
        border: 1px solid rgba(255,255,255,0.06);
    }

    /* ── Title ── */
    .app-title {
        text-align: center;
        font-size: 1.6rem;
        font-weight: 700;
        color: #e8e8f0;
        letter-spacing: 2px;
        margin-bottom: 0.25rem;
    }
    .app-subtitle {
        text-align: center;
        font-size: 0.8rem;
        color: #6a6a8a;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }

    /* ── Section labels ── */
    .section-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #7a7a9a;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
        margin-top: 1.2rem;
    }

    /* ── Chord input styling ── */
    .stTextArea textarea {
        background: #0e0e1a !important;
        border: 1px solid #2a2a4a !important;
        border-radius: 12px !important;
        color: #e0e0f0 !important;
        font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace !important;
        font-size: 1.05rem !important;
        padding: 1rem !important;
        letter-spacing: 0.5px;
    }
    .stTextArea textarea:focus {
        border-color: #5a4fcf !important;
        box-shadow: 0 0 12px rgba(90, 79, 207, 0.25) !important;
    }
    .stTextArea label {
        display: none !important;
    }

    /* ── Sliders ── */
    .stSlider > div > div > div {
        background: #5a4fcf !important;
    }
    .stSlider label {
        color: #8a8aa8 !important;
        font-size: 0.75rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* ── Selectbox ── */
    .stSelectbox label {
        color: #8a8aa8 !important;
        font-size: 0.75rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    .stSelectbox > div > div {
        background: #0e0e1a !important;
        border: 1px solid #2a2a4a !important;
        border-radius: 10px !important;
        color: #e0e0f0 !important;
    }

    /* ── Generate button ── */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #5a4fcf 0%, #7b68ee 100%);
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.85rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        margin-top: 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(90, 79, 207, 0.4) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #6b5fd9 0%, #8b78f8 100%) !important;
        box-shadow: 0 6px 30px rgba(90, 79, 207, 0.6) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(1px);
    }

    /* ── Download button ── */
    .stDownloadButton > button {
        width: 100%;
        background: #1a1a2e !important;
        color: #8a8aaa !important;
        border: 1px solid #2a2a4a !important;
        border-radius: 14px !important;
        padding: 0.85rem 2rem !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    .stDownloadButton > button:hover {
        background: #222240 !important;
        border-color: #3a3a5a !important;
        color: #c0c0d0 !important;
    }

    /* ── Open Folder button (primary action) ── */
    button[data-testid="stBaseButton-secondary"][kind="secondary"] {
        background: linear-gradient(135deg, #1e8a4a 0%, #22a854 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 20px rgba(30, 138, 74, 0.4) !important;
    }

    /* ── Chord validation chips ── */
    .chord-valid {
        display: inline-block;
        background: rgba(34, 168, 84, 0.15);
        border: 1px solid rgba(34, 168, 84, 0.4);
        color: #4ade80;
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-family: 'SF Mono', 'Consolas', monospace;
        margin: 0.2rem;
    }
    .chord-invalid {
        display: inline-block;
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #f87171;
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-family: 'SF Mono', 'Consolas', monospace;
        margin: 0.2rem;
    }

    /* ── File path display ── */
    .file-path {
        background: #0e0e1a;
        border: 1px solid #2a2a4a;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        color: #8a8aaa;
        font-family: 'SF Mono', 'Consolas', monospace;
        font-size: 0.8rem;
        margin-top: 0.75rem;
        word-break: break-all;
    }

    /* ── Success message ── */
    .success-msg {
        text-align: center;
        color: #4ade80;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 1px;
        margin-top: 1rem;
    }

    /* ── Divider ── */
    .subtle-divider {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin: 1.5rem 0;
    }

    /* ── Hide Streamlit defaults ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* ── Expander styling ── */
    .streamlit-expanderHeader {
        color: #8a8aa8 !important;
        font-size: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── Chord Validation ────────────────────────────────────────────

def validate_chord(chord_name: str) -> tuple[bool, str]:
    """Validate a single chord. Returns (is_valid, normalized_name)."""
    if not chord_name.strip():
        return False, ""
    normalized = normalize_chord(chord_name.strip())
    if not HAS_MUSIC21:
        return True, normalized  # Can't validate without music21, assume OK
    try:
        cs = harmony.ChordSymbol(normalized)
        if cs.pitches:
            return True, normalized
        return False, normalized
    except Exception:
        return False, normalized


def parse_chord_input(raw_input: str) -> list[str]:
    """Parse comma or space separated chord input into a clean list."""
    # Support comma, pipe, or multi-space separation
    chords = re.split(r'[,|]+', raw_input)
    return [c.strip() for c in chords if c.strip()]


# ─── Output Directory ────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "midi_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def build_filename(chords: list[str], bpm: int, rhythm: str) -> str:
    """
    Auto-generate a descriptive filename from the chord progression.
    Example: Fm9-Dbmaj7-Eb6-C7b9_72bpm_neosoulpush.mid
    If > 6 chords, truncates with count: Fm9-Dbmaj7-+4more_72bpm_neosoulpush.mid
    """
    max_chords_in_name = 6

    # Clean chord names for filesystem safety
    safe = [re.sub(r'[^\w#\-]', '', c) for c in chords]

    if len(safe) <= max_chords_in_name:
        chord_part = "-".join(safe)
    else:
        shown = safe[:2]
        remaining = len(safe) - 2
        chord_part = f"{'-'.join(shown)}-plus{remaining}more"

    rhythm_clean = rhythm.replace("_", "")
    name = f"{chord_part}_{bpm}bpm_{rhythm_clean}.mid"

    # If file already exists, add a counter
    path = OUTPUT_DIR / name
    if path.exists():
        counter = 2
        while True:
            numbered = f"{chord_part}_{bpm}bpm_{rhythm_clean}_{counter}.mid"
            if not (OUTPUT_DIR / numbered).exists():
                name = numbered
                break
            counter += 1

    return name


# ─── App UI ──────────────────────────────────────────────────────

st.markdown('<div class="main-card">', unsafe_allow_html=True)

st.markdown('<div class="app-title">MIDI Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Chord Progression to MIDI</div>', unsafe_allow_html=True)

# ── Chord Input ──
st.markdown('<div class="section-label">Chords</div>', unsafe_allow_html=True)

chord_input = st.text_area(
    "chords",
    value="Fm9, Dbmaj7, Eb6, C7b9",
    height=80,
    placeholder="Enter chords separated by commas: Fm9, Dbmaj7, Eb6, C7b9",
    label_visibility="collapsed",
)

# Live validation
chords = parse_chord_input(chord_input)
if chords:
    chips_html = ""
    all_valid = True
    valid_chords = []
    for chord in chords:
        is_valid, normalized = validate_chord(chord)
        if is_valid:
            chips_html += f'<span class="chord-valid">{chord}</span> '
            valid_chords.append(chord)
        else:
            chips_html += f'<span class="chord-invalid">{chord}</span> '
            all_valid = False
    st.markdown(chips_html, unsafe_allow_html=True)

st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

# ── Controls ──
col1, col2 = st.columns(2)

with col1:
    bpm = st.slider("BPM", min_value=50, max_value=180, value=72, step=1)

with col2:
    rhythm = st.selectbox(
        "Rhythm",
        options=["neo_soul_push", "syncopated", "ballad", "straight"],
        format_func=lambda x: {
            "neo_soul_push": "Neo-Soul Push",
            "syncopated": "Syncopated",
            "ballad": "Ballad",
            "straight": "Straight (Pads)",
        }[x],
    )

swing = st.slider("Swing", min_value=50, max_value=75, value=58, step=1,
                   help="50% = straight, 58-62% = Dilla zone, 66% = triplet")

st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

# ── Generate ──
if st.button("Generate MIDI", use_container_width=True):
    if not chords:
        st.error("Enter at least one chord.")
    elif not all_valid:
        st.error("Fix the highlighted chords before generating.")
    else:
        output_filename = build_filename(chords, bpm, rhythm)
        output_path = str(OUTPUT_DIR / output_filename)

        input_data = {
            "chords": chords,
            "bpm": bpm,
            "rhythm": rhythm,
            "swing": float(swing),
        }

        with st.spinner(""):
            result = generate_midi(input_data, output_path=output_path)

        if result:
            st.session_state["last_generated"] = output_path
            st.session_state["last_filename"] = output_filename

# ── Output Section (persistent after generate) ──
if "last_generated" in st.session_state:
    output_path = st.session_state["last_generated"]
    output_filename = st.session_state["last_filename"]

    if Path(output_path).exists():
        st.markdown(
            f'<div class="success-msg">{output_filename}</div>',
            unsafe_allow_html=True,
        )

        # Primary action: open folder for drag-and-drop
        abs_folder = str(OUTPUT_DIR.resolve())

        col_open, col_dl = st.columns([3, 2])

        with col_open:
            if st.button("Open in Explorer", use_container_width=True,
                         key="open_folder"):
                # Open and select the file in Windows Explorer
                abs_file = str(Path(output_path).resolve())
                subprocess.Popen(["explorer", "/select,", abs_file])

        with col_dl:
            with open(output_path, "rb") as f:
                midi_bytes = f.read()
            st.download_button(
                label="Download",
                data=midi_bytes,
                file_name=output_filename,
                mime="audio/midi",
                use_container_width=True,
            )

        st.markdown(
            f'<div class="file-path">{abs_folder}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Add this folder to Ableton's Places sidebar — drag .mid files straight onto tracks.")

st.markdown('</div>', unsafe_allow_html=True)
