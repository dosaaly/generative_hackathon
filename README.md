Kyrgyz AI learning assistant — Demo Prototype

Purpose
This repository contains a small Streamlit prototype that extracts a short summary from an uploaded PDF and generates an audio version of the summary using Google Text-to-Speech (gTTS). The goal is to provide a lightweight demo of document summarization and audio output in Kyrgyz or other languages supported by gTTS.

What it uses

- Python 3.10+ (recommended environment: Conda)  
- Streamlit — simple web UI for the demo  
- pdfplumber — PDF text extraction  
- gTTS — Google Text-to-Speech for audio generation  
- python-dotenv — load environment variables from a .env file  
- requests — small utility library (not strictly required, included for convenience)  
- scipy — used for audio handling if needed

How to run (local development)

1. Create and activate a python environment using conda or venv
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. (Optional) Create a `.env` file in the repository root to set environment variables. Example:
```
TTS_LANG=ky
```
4. Run the Streamlit app:
```bash
streamlit run main.py
```
How it works
- Upload a PDF in the sidebar. The app extracts text from the first five pages.
- Click "Generate Summary" to produce a short extractive summary using a simple frequency-based heuristic.
- Click "Generate Audio Overview" to synthesize speech using gTTS. The audio is returned as an MP3 stream and played in the browser.

Notes and limitations

- This prototype is intentionally minimal. The summarization algorithm is extractive and not tuned for high-quality results. For production, connect an LLM or a proper summarization model.
- gTTS uses Google TTS and requires an internet connection. It is used here as a simple, free TTS option.
- The app should be run in a Python environment that has the listed dependencies installed. Use the provided `requirements.txt` file.

Tech stack

- Streamlit: lightweight web UI framework for Python, used to build the app and serve it locally.  
- pdfplumber: extract text from PDF files.  
- gTTS: Google Text-to-Speech Python wrapper to synthesize audio from text.  
- python-dotenv: simple loader for environment variables from a `.env` file.  
- SciPy: used for potential audio handling (included in requirements for completeness). 

License

This repository is a demo prototype and does not include any licensing beyond the included dependencies' licenses.

