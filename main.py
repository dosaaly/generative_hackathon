import streamlit as st  # type: ignore
import pdfplumber  # type: ignore
import re
from collections import Counter
import math

st.set_page_config(page_title="OkuLM", layout="wide")
st.title("OkuLM — Окуу талдоосу")

kyrgyz_stopwords = {
    'мен', 'сен', 'ал', 'болуп', 'бар', 'жана', 'менин', 'сенин', 'алар', 'үшүн', 'үчүн',
    'же', 'бул', 'бир', 'эмес', 'да', 'аны', 'мене', 'өзгөрт', 'үч', 'ары', 'өз', 'көп', 'аз',
    'үчүн', 'үч', 'сөз', 'бүт', 'айт', 'бол', 'эми', 'кайсы', 'канча', 'кайда', 'кантип',
    'эле', 'аннан', 'анын', 'үчүн', 'бардык'
}

sentence_split_re = re.compile(r'(?<=[.!?\n])\s+')
word_re = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def local_summarize_short(text: str, max_chars: int = 1000) -> str:
    if not text or not text.strip():
        return ""
    sentences = sentence_split_re.split(text.strip())
    tokens = [w.lower() for w in word_re.findall(text)]
    freqs = Counter(w for w in tokens if len(w) > 2 and w not in kyrgyz_stopwords)
    if not freqs:
        s = ' '.join(sentences[:5])
        return s[:max_chars]
    sent_scores = []
    for s in sentences:
        s_tokens = [w.lower() for w in word_re.findall(s)]
        score = sum(freqs.get(w, 0) for w in s_tokens)
        sent_scores.append((score, s))
    sent_scores.sort(key=lambda x: x[0], reverse=True)
    summary_parts = []
    total = 0
    for _, s in sent_scores:
        piece = s.strip()
        if not piece:
            continue
        if total + len(piece) + 1 > max_chars:
            continue
        summary_parts.append(piece)
        total += len(piece) + 1
        if total >= max_chars:
            break
    if not summary_parts and sentences:
        return sentences[0][:max_chars]
    return ' '.join(summary_parts)[:max_chars]


def extract_candidate_terms(text: str, max_items: int = 5):
    tokens = [w.lower() for w in word_re.findall(text)]
    uni_counts = Counter()
    for t in tokens:
        if len(t) > 2 and t not in kyrgyz_stopwords:
            uni_counts[t] += 1
    bi_counts = Counter()
    tri_counts = Counter()
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if a not in kyrgyz_stopwords and b not in kyrgyz_stopwords and len(a) > 1 and len(b) > 1:
            bi = f"{a} {b}"
            bi_counts[bi] += 1
    for i in range(len(tokens) - 2):
        a, b, c = tokens[i], tokens[i + 1], tokens[i + 2]
        if all(x not in kyrgyz_stopwords and len(x) > 1 for x in (a, b, c)):
            tri = f"{a} {b} {c}"
            tri_counts[tri] += 1
    candidates = []
    for term, cnt in tri_counts.items():
        score = cnt * (3 ** 1.5)
        candidates.append((score, term))
    for term, cnt in bi_counts.items():
        score = cnt * (2 ** 1.3)
        candidates.append((score, term))
    for term, cnt in uni_counts.items():
        score = cnt * 1.0
        candidates.append((score, term))
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    selected = []
    for _, term in candidates:
        if term in seen:
            continue
        seen.add(term)
        selected.append(term)
        if len(selected) >= max_items:
            break
    return selected, {'unigrams': uni_counts, 'bigrams': bi_counts, 'trigrams': tri_counts}


def find_definition_for_term(term: str, sentences: list, text: str) -> str:
    pattern_inline = re.compile(r'\b' + re.escape(term) + r'\b\s*[\-:—–]\s*([^\n]+)', re.IGNORECASE)
    m = pattern_inline.search(text)
    if m:
        return m.group(1).strip()[:400]
    for s in sentences:
        if re.search(r'\b' + re.escape(term) + r'\b', s, re.IGNORECASE):
            subparts = re.split(r'[\-:—–]', s)
            if len(subparts) > 1:
                candidate = subparts[1].strip()
                if candidate:
                    return candidate[:400]
            cues = ['деп аталат', 'деп саналат', 'аталат', 'бул']
            for cue in cues:
                if cue in s.lower():
                    return s.strip()[:400]
            return s.strip()[:400]
    return ""


def analyze_study_text(text: str, max_items: int = 5) -> dict:
    if not text or not text.strip():
        return {"error": "empty_text", "message": "Документтеги текст бош."}
    overview = local_summarize_short(text, max_chars=1200)
    sentences = sentence_split_re.split(text.strip())
    selected, counts = extract_candidate_terms(text, max_items=max_items)
    definitions = {}
    explanations = {}
    for term in selected:
        def_text = find_definition_for_term(term, sentences, text)
        definitions[term] = def_text
        if def_text:
            explanations[term] = local_summarize_short(def_text + ' ' + ' '.join(sentences[max(0, sentences.index(def_text) - 1):min(len(sentences), sentences.index(def_text) + 2)]), max_chars=600) if def_text in sentences else local_summarize_short(def_text, max_chars=600)
        else:
            context = ''
            for i, s in enumerate(sentences):
                if re.search(r'\b' + re.escape(term) + r'\b', s, re.IGNORECASE):
                    start = max(0, i - 1)
                    end = min(len(sentences), i + 2)
                    context = ' '.join(sentences[start:end])
                    break
            explanations[term] = local_summarize_short(context or term, max_chars=600)
    return {"overview": overview, "definitions": definitions, "explanations": explanations}


def tokenize(text: str):
    return [w.lower() for w in word_re.findall(text) if len(w) > 1]


def get_sentence_scores_for_question(question: str, text: str, top_k: int = 5):
    tokens = tokenize(text)
    total_tokens = max(1, len(tokens))
    freqs = Counter(tokens)
    sentences = sentence_split_re.split(text.strip())
    q_tokens = [w for w in tokenize(question) if w not in kyrgyz_stopwords]
    if not q_tokens:
        return []
    idf = {}
    for w, c in freqs.items():
        idf[w] = math.log((total_tokens + 1) / (1 + c))
    sent_scores = []
    for i, s in enumerate(sentences):
        s_tokens = [w for w in tokenize(s)]
        score = 0.0
        for qt in q_tokens:
            if qt in s_tokens:
                score += idf.get(qt, 0.0)
        for phrase_len in (3, 2):
            q_phrases = [' '.join(q_tokens[j:j+phrase_len]) for j in range(len(q_tokens)-phrase_len+1)]
            for qp in q_phrases:
                if qp and qp in s.lower():
                    score += 1.0 * phrase_len
        sent_scores.append((score, i, s))
    sent_scores.sort(key=lambda x: x[0], reverse=True)
    top = [s for sc, i, s in sent_scores if sc > 0][:top_k]
    if not top:
        top = [s for _, _, s in sent_scores][:min(top_k, len(sent_scores))]
    return top


def answer_question_local(question: str, doc_text: str, max_sentences: int = 3) -> dict:
    if not doc_text or not doc_text.strip():
        return {"answer": "Документтин тексти жок.", "sources": []}
    sentences = sentence_split_re.split(doc_text.strip())
    top = get_sentence_scores_for_question(question, doc_text, top_k=10)
    if not top:
        overview = local_summarize_short(doc_text, max_chars=600)
        return {"answer": overview or "Кечиресиз, жооп табылган жок.", "sources": []}
    answer = ' '.join(top[:max_sentences])
    sources = top[:max_sentences]
    return {"answer": answer, "sources": sources}

with st.sidebar:
    st.header("Документ жүктөө")
    uploaded_file = st.file_uploader("PDF жүктөө (биринчи 5 бет колдонулат)", type="pdf")
    st.markdown("---")
    st.write("This is a demo prototype designed to showcase the app's main features. Outputs may be uninformative or incorrect on purpose because this version does not include a trained AI model yet.")
    st.markdown("---")

if uploaded_file:
    try:
        opener = getattr(pdfplumber, "open")
        with opener(uploaded_file) as pdf:
            pages_to_read = min(5, len(pdf.pages))
            full_text = "\n".join([pdf.pages[i].extract_text() or "" for i in range(pages_to_read)])
    except Exception as e:
        st.error(f"PDF окууда ката болду: {e}")
        full_text = ""
    if not full_text.strip():
        st.warning("PDF файлынын биринчи беттеринен текст алынган жок. Тексты бар PDF жүктөңүз.")
    else:
        st.session_state['doc_text'] = full_text
        st.success(f"PDFтен {len(full_text)} символ жүктөлдү.")

if 'doc_text' in st.session_state:
    st.markdown('<div style="display:flex;align-items:center;gap:12px"><h2 style="margin:0">📘 Документ</h2><span style="color:#6c757d">(биринчи 5 беттен алынган текст)</span></div>', unsafe_allow_html=True)
    with st.expander("Алынган текстти алдын ала көрүү"):
        st.text_area("Алынган текст ( биринчи 20000 символ )", value=st.session_state['doc_text'][:20000], height=240, key="preview_text", disabled=True)
        st.write(f"Алынган узундук: {len(st.session_state['doc_text'])} символ")

    st.markdown("---")
    st.markdown('<h3>🔎 Окуу талдоосу — Жеңил режим</h3>', unsafe_allow_html=True)
    left, right = st.columns([3, 1])
    with right:
        max_items = st.number_input("Көрсөтө турган терминдер", min_value=1, max_value=20, value=5, step=1)
        run = st.button("Талдоону баштоо")
        if st.button("Анализди тазалоо"):
            st.session_state.pop('analysis_result', None)
            st.session_state.pop('run_analysis', None)
            st.success("Анализ тазаланды")
    with left:
        st.info("Натыйжалар жеңил форматта көрсөтүлөт: кыскача, эң маанилүү терминдер жана алардын аныктамалары.")

    if run:
        st.session_state['run_analysis'] = True
    if st.session_state.get('run_analysis'):
        with st.spinner('Талдоо жүргүзүлүүдө...'):
            result = analyze_study_text(st.session_state['doc_text'], max_items=int(max_items))
            st.session_state['analysis_result'] = result
    result = st.session_state.get('analysis_result')
    if result:
        overview = result.get('overview', '')
        definitions = result.get('definitions', {})
        explanations = result.get('explanations', {})
        st.markdown('<div style="background:#f7f9fb;padding:12px;border-radius:8px">', unsafe_allow_html=True)
        st.markdown('### ✨ Кыскача')
        st.write(overview)
        st.download_button("Кыскачаны жүктөө (.txt)", overview or "", file_name="overview.txt")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('### 📌 Маанилүү терминдер')
        if definitions:
            for term, def_text in definitions.items():
                with st.expander(f"{term}"):
                    if def_text:
                        st.write('**Аныктама:**')
                        st.write(def_text)
                    expl = explanations.get(term, '')
                    if expl:
                        st.write('**Түшүндүрмө:**')
                        st.write(expl)
                    if not def_text and not expl:
                        st.write('Бул термин үчүн кошумча маалымат табылган жок.')
        else:
            st.write('Маанилүү терминдер табылган жок.')

    st.markdown('---')

else:
    st.info("Баштоо үчүн сол жактан PDF жүктөңүз.")
