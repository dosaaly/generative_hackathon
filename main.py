import streamlit as st  # type: ignore
import pdfplumber  # type: ignore
import re
from collections import Counter
import math

st.set_page_config(page_title="OkuLM", layout="wide")
st.title("OkuLM — Окуу талдоосу")

K_STOP = {
    'мен', 'сен', 'ал', 'болуп', 'бар', 'жана', 'менин', 'сенин', 'алар', 'үшүн', 'үчүн',
    'же', 'бул', 'бир', 'эмес', 'да', 'аны', 'мене', 'өз', 'көп', 'аз', 'сөз', 'айт', 'бол',
    'эми', 'кайсы', 'канча', 'кайда', 'кантип', 'анан', 'анын', 'бардык'
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
            # fallback: use the sentence context
            ctx = ''
            for i, s in enumerate(sents):
                if re.search(r'\b' + re.escape(t) + r'\b', s, re.IGNORECASE):
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
    max_items = st.slider("Эң көп элементтер", 1, 20, 5)
    if st.button("Окуу талдоосун түзүү"):
        res = analyze(st.session_state['doc_text'], max_items=max_items)
        if 'error' in res:
            st.error("Документтеги текст бош. PDFти текшерип кайра жүктөңүз.")
        else:
            st.markdown("### Кыскача")
            st.write(res['overview'])
            st.markdown("### Маанилүү терминдер")
            if res['definitions']:
                for term, d in res['definitions'].items():
                    exp = res['explanations'].get(term, '')
                    with st.expander(f"{term}"):
                        if exp:
                            st.write('**Түшүндүрмө:**')
                            st.write(exp)
                        if d:
                            st.write('**Аныктама:**')
                            st.write(d)
                        if not d and not exp:
                            st.write('Бул термин үчүн кошумча маалымат табылган жок.')
            else:
                st.write('Маанилүү терминдер табылган жок.')
else:
    st.info("Баштоо үчүн сол жактан PDF жүктөңүз.")
