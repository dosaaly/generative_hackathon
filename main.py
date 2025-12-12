import streamlit as st  # type: ignore
import pdfplumber  # type: ignore
import re
from collections import Counter
import os
import io

st.set_page_config(page_title="OkuLM", layout="wide")
st.title("OkuLM — Окуу талдоосу")

K_STOP = {
    'мен', 'сен', 'ал', 'болуп', 'бар', 'жана', 'менин', 'сенин', 'алар', 'үшүн', 'үчүн',
    'же', 'бул', 'бир', 'эмес', 'да', 'аны', 'мене', 'өз', 'көп', 'аз', 'сөз', 'айт', 'бол',
    'эми', 'кайсы', 'канча', 'кайда', 'кантип', 'анан', '��нын', 'бардык'
}

SENT_RE = re.compile(r'(?<=[.!?\n])\s+')
WORD_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def read_pdf(file, max_pages=5):
    try:
        with pdfplumber.open(file) as pdf:
            pages = min(max_pages, len(pdf.pages))
            return "\n".join((pdf.pages[i].extract_text() or "") for i in range(pages))
    except Exception:
        return ""


def tokenize(text):
    return [w.lower() for w in WORD_RE.findall(text)]


def summarize(text, max_chars=1000):
    if not text or not text.strip():
        return ""
    sents = SENT_RE.split(text.strip())
    toks = [t for t in tokenize(text) if len(t) > 2 and t not in K_STOP]
    freqs = Counter(toks)
    if not freqs:
        return ' '.join(sents[:3])[:max_chars]
    scored = []
    for s in sents:
        score = sum(freqs.get(w, 0) for w in tokenize(s))
        scored.append((score, s))
    scored.sort(reverse=True)
    out = []
    total = 0
    for _, s in scored:
        part = s.strip()
        if not part:
            continue
        if total + len(part) + 1 > max_chars:
            continue
        out.append(part)
        total += len(part) + 1
        if total >= max_chars:
            break
    return ' '.join(out)[:max_chars] if out else (sents[0][:max_chars] if sents else "")


def extract_terms(text, max_items=5):
    toks = tokenize(text)
    uni = Counter(w for w in toks if len(w) > 2 and w not in K_STOP)
    bi = Counter(' '.join((toks[i], toks[i + 1])) for i in range(len(toks) - 1)
                 if toks[i] not in K_STOP and toks[i + 1] not in K_STOP)
    tri = Counter(' '.join((toks[i], toks[i + 1], toks[i + 2])) for i in range(len(toks) - 2)
                  if toks[i] not in K_STOP and toks[i + 1] not in K_STOP and toks[i + 2] not in K_STOP)
    candidates = []
    candidates += [(cnt * 9, t) for t, cnt in tri.items()]
    candidates += [(cnt * 3, t) for t, cnt in bi.items()]
    candidates += [(cnt, t) for t, cnt in uni.items()]
    candidates.sort(reverse=True)
    seen = set()
    out = []
    for _, term in candidates:
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
        if len(out) >= max_items:
            break
    return out


def find_definition(term, sents, full_text):
    pat = re.compile(r'\b' + re.escape(term) + r'\b\s*[\-:—–]\s*([^\n]+)', re.IGNORECASE)
    m = pat.search(full_text)
    if m:
        return m.group(1).strip()
    for i, s in enumerate(sents):
        if re.search(r'\b' + re.escape(term) + r'\b', s, re.IGNORECASE):
            # prefer clause after dash/colon
            parts = re.split(r'[\-:—–]', s)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            # else return short context
            start = max(0, i - 1)
            return ' '.join(sents[start:min(len(sents), i + 2)]).strip()
    return ""


def analyze(text, max_items=5):
    if not text or not text.strip():
        return {"error": "empty_text"}
    overview = summarize(text, max_chars=1200)
    sents = SENT_RE.split(text.strip())
    terms = extract_terms(text, max_items=max_items)
    defs = {}
    exps = {}
    for t in terms:
        d = find_definition(t, sents, text)
        defs[t] = d
        if d:
            exps[t] = summarize(d + ' ' + ' '.join(sents[max(0, 0):min(len(sents), 3)]), max_chars=500)
        else:
            ctx = ''
            for i, s in enumerate(sents):
                if re.search(r'\\b' + re.escape(t) + r'\\b', s, re.IGNORECASE):
                    start = max(0, i - 1)
                    ctx = ' '.join(sents[start:min(len(sents), i + 2)])
                    break
            exps[t] = summarize(ctx or t, max_chars=500)
    return {"overview": overview, "definitions": defs, "explanations": exps}


with st.sidebar:
    st.header("Документ жүктөө")
    uploaded_file = st.file_uploader("PDF жүктөө (биринчи 5 бет колдонулат)", type="pdf")
    st.markdown("---")
    st.write("This is a demo prototype designed to showcase the app's main features. Outputs may be uninformative or incorrect on purpose because this version does not include a trained AI model yet.")
    st.markdown("---")

if uploaded_file:
    full_text = read_pdf(uploaded_file, max_pages=5)
    if not full_text.strip():
        st.warning("PDFтен текст алынган жок. Ар бир беттен текст ортолуп жатканын текшерип кайра жүктөңүз.")
    else:
        st.session_state['doc_text'] = full_text
        st.success(f"PDFтен {len(full_text)} символ жүктөлдү.")

if 'doc_text' in st.session_state:
    with st.expander("Алынган текстти алдын ала көрүү"):
        st.text_area("Алынган текст ( биринчи 20000 символ )", value=st.session_state['doc_text'][:20000], height=220, key="preview_text", disabled=True)
        st.write(f"Алынган узундук: {len(st.session_state['doc_text'])} символ")

    st.subheader("Окуу талдоосу")
    left, right = st.columns([3, 1])
    with right:
        max_items = st.number_input("Көрсөтө турган терминдер", min_value=1, max_value=20, value=5, step=1)
        run_analysis = st.button("Окуу талдоосун түзүү")

    if run_analysis:
        st.session_state['run_analysis'] = True
        with st.spinner('Талдоо жүргүзүлүүдө...'):
            res = analyze(st.session_state['doc_text'], max_items=max_items)
            st.session_state['analysis_result'] = res

    if 'analysis_result' in st.session_state:
        res = st.session_state['analysis_result']
        if not isinstance(res, dict) or 'error' in res:
            msg = res.get('message', 'Белгисиз ката') if isinstance(res, dict) else 'Натыйжа туура эмес форматта'
            st.error(f"Талдоодон ката кетти: {msg}")
        else:
            st.markdown("### Кыскача")
            overview_text = res.get('overview', '')
            st.write(overview_text)

            st.markdown("### Маанилүү терминдер")
            definitions = res.get('definitions', {}) or {}
            explanations = res.get('explanations', {}) or {}
            if definitions:
                for term, d in definitions.items():
                    exp = explanations.get(term, '')
                    with st.expander(f"{term}"):
                        if exp: st.write(f"**Түшүндүрмө:**\n{exp}")
                        if d: st.write(f"**Аныктама:**\n{d}")
                        if not d and not exp: st.write('Бул термин үчүн кошумча маалымат табылган жок.')
            else:
                st.write('Маанилүү терминдер табылган жок.')

            if overview_text:
                st.markdown("### Аудио обзор")
                if st.button("Аудиону ойнотуу"):
                    with st.spinner("Аудио түзүү..."):
                        try:
                            import importlib
                            spec = importlib.util.find_spec('gtts')
                            if spec is None:
                                st.error("gTTS (text-to-speech) library not installed; install 'gTTS' to enable audio.")
                            else:
                                gtts = importlib.import_module('gtts')
                                gTTS = getattr(gtts, 'gTTS')
                                lang = os.getenv('TTS_LANG', 'ru')
                                text_for_audio = " ".join(overview_text.split()[:25])
                                tts = gTTS(text=text_for_audio, lang=lang)
                                audio_fp = io.BytesIO()
                                tts.write_to_fp(audio_fp)
                                audio_fp.seek(0)
                                st.audio(audio_fp, format='audio/mp3')
                        except Exception as e:
                            st.error(f"Аудио түзүүдө ката кетти: {e}")

            st.markdown("---")
            st.markdown("### 🃏 Флеш-карталар")

            if 'flashcards' not in st.session_state:
                st.session_state.flashcards = []

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Флеш-карталарды түзүү"):
                    if definitions:
                        st.session_state.flashcards = list(definitions.items())
                        st.session_state.card_index = 0
                        st.session_state.card_revealed = False
                        st.rerun()
                    else:
                        st.warning("Флеш-карталар үчүн терминдер табылган жок.")

            if st.session_state.flashcards:
                total_cards = len(st.session_state.flashcards)
                if 'card_index' not in st.session_state:
                    st.session_state.card_index = 0

                st.session_state.card_index %= total_cards
                term, definition = st.session_state.flashcards[st.session_state.card_index]

                nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
                with nav_col1:
                    if st.button("◀️ Артка"):
                        st.session_state.card_index -= 1
                        st.session_state.card_revealed = False
                        st.rerun()
                with nav_col3:
                    if st.button("алдыга ▶️"):
                        st.session_state.card_index += 1
                        st.session_state.card_revealed = False
                        st.rerun()

                with st.container():
                    st.markdown(f"""
                    <div style="border: 1px solid #333; border-radius: 10px; padding: 25px; text-align: center; min-height: 200px; cursor: pointer;" onclick="this.querySelector('button').click();">
                        <h4>{term}</h4>
                    """, unsafe_allow_html=True)

                    if st.session_state.get('card_revealed', False):
                        st.write(definition or "Аныктама табылган жок.")
                        if st.button("Жабуу", key=f"hide_{st.session_state.card_index}"):
                            st.session_state.card_revealed = False
                            st.rerun()
                    else:
                        if st.button("Ачуу", key=f"reveal_{st.session_state.card_index}", help="Click to reveal definition"):
                            st.session_state.card_revealed = True
                            st.rerun()

                    st.caption(f"Карта {st.session_state.card_index + 1}/{total_cards}")
                    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 Чат")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Документ боюнча сурооңузду бериңиз"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = "Бул демо-чат. Толук версияда модель документтин мазмунуна жараша жооп берет."

            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

else:
    st.info("Баштоо үчүн сол жактан PDF жүктөңүз.")
