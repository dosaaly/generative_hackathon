Kyrgyz AI learning assistant — Demo Prototype

Purpose
This repository contains a small Streamlit prototype that extracts a short summary from an uploaded PDF and generates an audio version of the summary using Google Text-to-Speech (gTTS). The project has been updated to remove any external ChatGPT/OpenAI API calls and to run entirely locally using a simple extractive summarizer.

Summary of recent code changes (what was changed and why)

- Local-only analysis
  - The app now always calls the built-in `analyze(text, max_items=...)` function. This is an extractive, frequency-based summarizer and term extractor (same algorithm as before).
  - Output structure returned by `analyze()` is a dict: {"overview": str, "definitions": {term: def}, "explanations": {term: explanation}}.

- Chat behavior (demo chat)
  - The in-app chat remains in the UI but no longer forwards messages to any external service.
  - The assistant responds with a constant demo message: "Бул демо-чат. Толук версияда модель документтин мазмунуна жараша жооп берет." (Kyrgyz). This is intentional and documented.

- gTTS (audio) handling
  - The top-level import of `gTTS` was removed. Instead the app performs a runtime import check when the user requests audio playback.
  - If `gTTS` is not installed, the app shows a clear message explaining how to enable audio (install `gTTS`). This avoids import errors when the package is missing.
  - Audio generation remains the same (short overview, language fallback to `ru` if `ky` unsupported).

- UI and small fixes
  - Minor indentation and chat message append fixes were applied so the constant assistant response is displayed correctly and persisted in session state.
  - The streamlit toggle for "ChatGPT API" was removed and replaced by a single workflow that uses local analysis.

What remains the same

- The app still extracts text from the first five pages of an uploaded PDF using `pdfplumber`.
- The summarization algorithm is the same frequency-based extractive summary used previously.
- Flashcards and the UI for viewing definitions/explanations are unchanged in behavior (they use the output of the local `analyze()` function).

Updated dependency guidance

- The app no longer requires any OpenAI or ChatGPT-related packages or an API key.
- Recommended Python dependencies for the current local-only version:
  - streamlit
  - pdfplumber
  - gTTS (optional; only required if you want audio) - install with `pip install gTTS`

Example minimal requirements.txt (update your environment accordingly)

```
streamlit
pdfplumber
gTTS
```

Running the app (local development)

1. Create and activate a Python environment (recommended: Python 3.10+).
2. Install dependencies (use the minimal list above or your existing environment):

```bash
pip install -r requirements.txt
```

3. Run the Streamlit app locally:

```bash
streamlit run main.py
```
Notes and limitations

This prototype is intentionally minimal. The summarization algorithm is extractive and not tuned for high-quality results. For production, connect an LLM or a proper summarization model.
gTTS uses Google TTS and requires an internet connection. It is used here as a simple, free TTS option. 
The app should be run in a Python environment that has the listed dependencies installed. Use the provided requirements.txt file.

License
This repository is a demo prototype and does not include any licensing beyond the included dependencies' licenses.
