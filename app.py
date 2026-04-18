import re
import io
import os
from pathlib import Path
import streamlit as st
from openai import OpenAI

# Detect if running on Streamlit Cloud (no local filesystem)
IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_CLOUD_DEPLOY")
DEFAULT_SAVE_FOLDER = str(Path.home() / "Desktop" / "Article Audio")

VOICES = {
    "Onyx — deep, authoritative (Ray Porter-like)": "onyx",
    "Fable — expressive, storytelling": "fable",
    "Nova — warm, engaging": "nova",
    "Alloy — neutral, clear": "alloy",
    "Echo — smooth, conversational": "echo",
    "Shimmer — soft, calm": "shimmer",
}

CHUNK_SIZE = 4000  # OpenAI TTS max is 4096 chars per request


def get_openai_client():
    # Try Streamlit secrets first (cloud), then env var, then error
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Add it to Streamlit secrets as OPENAI_API_KEY.")
        st.stop()
    return OpenAI(api_key=api_key)


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text)
    text = re.sub(r'`+[^`]*`+', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)
    text = re.sub(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s*\d{4}\)', '', text)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_title(text: str) -> str:
    lines = text.strip().splitlines()
    for line in lines[:5]:
        match = re.match(r'^#{1,2}\s+(.+)', line.strip())
        if match:
            return match.group(1).strip()
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) < 120 and not line.endswith(('.', ',', ';', ':')):
            if line.count('.') <= 1:
                return line
    first_sentence = re.split(r'(?<=[.!?])\s', text.strip())[0]
    return first_sentence[:80].strip()


def slugify(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[\s_-]+', '_', title)
    return title.strip('_')[:80]


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks at sentence boundaries, under `size` chars each."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def text_to_audio(client: OpenAI, text: str, voice: str) -> bytes:
    """Convert text to audio bytes using OpenAI TTS HD, chunking if needed."""
    chunks = chunk_text(text)
    audio_parts = []
    for chunk in chunks:
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=chunk,
        )
        audio_parts.append(response.content)
    return b"".join(audio_parts)


# ── UI ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Article to Audio", page_icon="🎙️", layout="centered")

st.title("🎙️ Article to Audio")
st.caption("Paste any article and convert it to a high-quality MP3 narration.")

article_text = st.text_area(
    "Paste your article here",
    height=300,
    placeholder="Paste the full text of your article here...",
)

voice_label = st.selectbox("Voice", list(VOICES.keys()))

if not IS_CLOUD:
    with st.expander("Save location (local)"):
        save_folder = st.text_input("Folder", value=DEFAULT_SAVE_FOLDER)
else:
    save_folder = None

if st.button("Convert to Audio", type="primary", use_container_width=True):
    if not article_text.strip():
        st.warning("Please paste some article text first.")
    else:
        with st.spinner("Generating audio..."):
            cleaned = clean_text(article_text)
            if not cleaned:
                st.error("No readable text found after cleanup.")
            else:
                title = extract_title(article_text)
                filename = slugify(title) + ".mp3"
                voice = VOICES[voice_label]
                client = get_openai_client()
                audio_bytes = text_to_audio(client, cleaned, voice)

                # Save to local disk when running locally
                if not IS_CLOUD and save_folder:
                    output_dir = Path(save_folder)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / filename
                    counter = 1
                    while output_path.exists():
                        output_path = output_dir / (slugify(title) + f"_{counter}.mp3")
                        counter += 1
                    output_path.write_bytes(audio_bytes)
                    st.success(f"Saved as **{output_path.name}**")
                    st.code(str(output_path), language=None)
                else:
                    st.success(f"Ready: **{filename}**")

                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    label="Download MP3",
                    data=audio_bytes,
                    file_name=filename,
                    mime="audio/mpeg",
                    use_container_width=True,
                )
