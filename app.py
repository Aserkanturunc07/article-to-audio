import re
import io
import os
from pathlib import Path
import streamlit as st
from gtts import gTTS

IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_CLOUD_DEPLOY")
DEFAULT_SAVE_FOLDER = str(Path.home() / "Desktop" / "Article Audio")

LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Mandarin)": "zh",
}


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


# ── UI ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Article to Audio", page_icon="🎙️", layout="centered")

st.title("🎙️ Article to Audio")
st.caption("Paste any article and convert it to an MP3 audio file.")

article_text = st.text_area(
    "Paste your article here",
    height=300,
    placeholder="Paste the full text of your article here...",
)

col1, col2 = st.columns([2, 1])
with col1:
    language = st.selectbox("Language", list(LANGUAGES.keys()))
with col2:
    speed = st.selectbox("Speed", ["Normal", "Slow"])

if not IS_CLOUD:
    with st.expander("Save location (local)"):
        save_folder = st.text_input("Folder", value=DEFAULT_SAVE_FOLDER)
else:
    save_folder = None

if st.button("Convert to Audio", type="primary", use_container_width=True):
    if not article_text.strip():
        st.warning("Please paste some article text first.")
    else:
        with st.spinner("Converting..."):
            cleaned = clean_text(article_text)
            if not cleaned:
                st.error("No readable text found after cleanup.")
            else:
                title = extract_title(article_text)
                filename = slugify(title) + ".mp3"

                tts = gTTS(text=cleaned, lang=LANGUAGES[language], slow=(speed == "Slow"))
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)

                if not IS_CLOUD and save_folder:
                    output_dir = Path(save_folder)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / filename
                    counter = 1
                    while output_path.exists():
                        output_path = output_dir / (slugify(title) + f"_{counter}.mp3")
                        counter += 1
                    output_path.write_bytes(audio_buffer.getvalue())
                    st.success(f"Saved as **{output_path.name}**")
                    st.code(str(output_path), language=None)
                else:
                    st.success(f"Ready: **{filename}**")

                audio_buffer.seek(0)
                st.audio(audio_buffer, format="audio/mp3")
                st.download_button(
                    label="Download MP3",
                    data=audio_buffer.getvalue(),
                    file_name=filename,
                    mime="audio/mpeg",
                    use_container_width=True,
                )
