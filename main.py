import streamlit as st
import pdfplumber
import io
import re
import os
from dotenv import load_dotenv
from gtts import gTTS

load_dotenv()

st.set_page_config(page_title="Kyrgyz AI learning assistant", layout="wide")
st.title("Kyrgyz AI learning assistant — Summary + Audio")


def summarize_text(text: str, num_points: int = 5) -> str:
    if not text or not text.strip():
        return ""
    sentences = re.split(r'(?<=[.!?\n])\s+', text.strip())
    words = re.findall(r"\w+", text.lower())
    stopwords = {"the", "and", "or", "a", "an", "to", "of", "in", "on", "for", "is", "it", "this"}
    freqs = {}
    for w in words:
        if len(w) <= 2 or w in stopwords:
            continue
        freqs[w] = freqs.get(w, 0) + 1
    if not freqs:
        chosen = sentences[:num_points]
        return "\n\n".join([f"- {s.strip()}" for s in chosen if s.strip()])
    sent_scores = []
    for s in sentences:
        s_words = re.findall(r"\w+", s.lower())
        score = 0
        for w in s_words:
            score += freqs.get(w, 0)
        sent_scores.append((score, s))
    sent_scores.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s for _, s in sent_scores[:num_points]]
    top_sentences_in_order = [s for s in sentences if s in top_sentences]
    bullets = [f"- {s.strip()}" for s in top_sentences_in_order if s.strip()]
    if len(bullets) < num_points:
        for s in sentences:
            if f"- {s.strip()}" not in bullets and s.strip():
                bullets.append(f"- {s.strip()}")
            if len(bullets) >= num_points:
                break
    return "\n\n".join(bullets)


def generate_audio_bytes(text: str) -> tuple[io.BytesIO | None, list]:
    attempts = []
    preferred_lang = 'ky'
    try:
        tts = gTTS(text=text, lang=preferred_lang)
        mp3_io = io.BytesIO()
        tts.write_to_fp(mp3_io)
        mp3_io.seek(0)
        attempts.append({'url': 'gTTS', 'shape': 'success', 'ok': True, 'lang': preferred_lang})
        return mp3_io, attempts
    except Exception as e:
        attempts.append({'url': 'gTTS', 'shape': 'error', 'ok': False, 'note': str(e), 'lang': preferred_lang})
        if preferred_lang != 'en':
            try:
                tts = gTTS(text=text, lang='en')
                mp3_io = io.BytesIO()
                tts.write_to_fp(mp3_io)
                mp3_io.seek(0)
                attempts.append({'url': 'gTTS', 'shape': 'fallback_en', 'ok': True})
                return mp3_io, attempts
            except Exception as e2:
                attempts.append({'url': 'gTTS', 'shape': 'fallback_en', 'ok': False, 'note': str(e2)})
        return None, attempts


with st.sidebar:
    st.header("Upload Document")
    uploaded_file = st.file_uploader("Upload PDF (first 5 pages will be used)", type="pdf")
    st.markdown("---")
    st.write("This demo creates a simple extractive summary and an audio version using gTTS. Audio will be generated in Kyrgyz by default with English fallback.")
    st.markdown("---")

if uploaded_file:
    try:
        opener = getattr(pdfplumber, "open")
        with opener(uploaded_file) as pdf:
            pages_to_read = min(5, len(pdf.pages))
            full_text = "\n".join([pdf.pages[i].extract_text() or "" for i in range(pages_to_read)])
    except Exception as e:
        st.error(f"Could not read PDF: {e}")
        full_text = ""
    if not full_text.strip():
        st.warning("Uploaded PDF contains no extractable text in the first pages.")
    else:
        st.session_state['doc_text'] = full_text
        st.success(f"Loaded {len(full_text)} characters from the uploaded PDF.")

if 'doc_text' in st.session_state:
    st.subheader("Summary")
    num_points = st.slider("Number of bullet points", 1, 8, 5)
    if st.button("Generate Summary"):
        with st.spinner("Generating summary..."):
            summary = summarize_text(st.session_state['doc_text'], num_points=num_points)
            if summary:
                st.session_state['summary'] = summary
                st.markdown(summary)
            else:
                st.error("Could not generate a summary.")
    elif 'summary' in st.session_state:
        st.markdown(st.session_state['summary'])
    st.markdown("---")
    st.subheader("Audio")
    if 'summary' in st.session_state:
        if st.button("Generate Audio for Summary"):
            with st.spinner("Synthesizing audio via gTTS..."):
                audio_io, attempts = generate_audio_bytes(st.session_state['summary'])
                if audio_io:
                    st.audio(audio_io, format='audio/mp3')
                else:
                    st.error("Audio generation failed. See attempts in logs.")
                    with st.expander("Audio attempt log"):
                        for a in attempts:
                            st.write(a)
    else:
        st.info("Generate the summary first, then press 'Generate Audio for Summary'.")
else:
    st.info("Upload a PDF on the left to get started.")
