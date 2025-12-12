import streamlit as st  # type: ignore
import pdfplumber  # type: ignore
import re

st.set_page_config(page_title="OkuLM", layout="wide")
st.title("OkuLM — Окуу талдоосу")


def local_summarize_short(text: str, max_chars: int = 1000) -> str:
    if not text or not text.strip():
        return ""
    # Split into sentences and score by term frequency (simple, language-agnostic)
    sentences = re.split(r'(?<=[.!?\n])\s+', text.strip())
    words = re.findall(r"\w+", text.lower())
    freqs = {}
    for w in words:
        if len(w) <= 2:
            continue
        freqs[w] = freqs.get(w, 0) + 1
    if not freqs:
        # fallback to first sentences
        s = ' '.join(sentences[:5])
        return s[:max_chars]
    sent_scores = []
    for s in sentences:
        s_words = re.findall(r"\w+", s.lower())
        score = sum(freqs.get(w, 0) for w in s_words)
        sent_scores.append((score, s))
    sent_scores.sort(key=lambda x: x[0], reverse=True)
    # pick top sentences until max_chars reached
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
    if not summary_parts:
        return sentences[0][:max_chars]
    return ' '.join(summary_parts)[:max_chars]


def analyze_study_text(text: str, max_items: int = 5) -> dict:
    if not text or not text.strip():
        return {"error": "empty_text", "message": "Документтеги текст бош."}
    overview = local_summarize_short(text, max_chars=1200)
    words = re.findall(r"\w+", text.lower())
    kyrgyz_stopwords = {
        'мен', 'сен', 'ал', 'болуп', 'бар', 'жана', 'менин', 'сенин', 'алар', 'үшүн', 'үчүн',
        'же', 'бул', 'бир', 'эмес', 'да', 'аны', 'мене', 'өзгөрт', 'үч', 'ары', 'мене', 'өз', 'көп', 'аз'
    }
    freqs = {}
    for w in words:
        if len(w) <= 2 or w in kyrgyz_stopwords:
            continue
        freqs[w] = freqs.get(w, 0) + 1
    if not freqs:
        return {"overview": overview}
    sorted_terms = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
    candidate_terms = [t for t, _ in sorted_terms]
    seen = set()
    selected = []
    for t in candidate_terms:
        if t in seen:
            continue
        seen.add(t)
        selected.append(t)
        if len(selected) >= max_items:
            break
    sentences = re.split(r'(?<=[.!?\n])\s+', text.strip())
    definitions = {}
    explanations = {}
    for term in selected:
        found_sentence = None
        for s in sentences:
            if re.search(r'\b' + re.escape(term) + r'\b', s, re.IGNORECASE):
                found_sentence = s.strip()
                break
        if found_sentence:
            definitions[term] = found_sentence[:300]
            try:
                idx = sentences.index(found_sentence)
            except ValueError:
                idx = None
            if idx is None:
                context = found_sentence
            else:
                start = max(0, idx - 1)
                end = min(len(sentences), idx + 2)
                context = ' '.join(sentences[start:end])
            explanations[term] = local_summarize_short(context, max_chars=800)
        else:
            definitions[term] = ""
            explanations[term] = ""
    return {"overview": overview, "definitions": definitions, "explanations": explanations}


with st.sidebar:
    st.header("Документ жүктөө")
    uploaded_file = st.file_uploader("PDF жүктөө (биринчи 5 бет колдонулат)", type="pdf")
    st.markdown("---")
    st.write("Бул версия локал ыкма менен иштейт жана сырттагы AI моделдерин колдонбойт.")
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
    with st.expander("Алынган текстти алдын ала көрүү"):
        st.text_area("Алынган текст ( биринчи 20000 символ )", value=st.session_state['doc_text'][:20000], height=300, key="preview_text", disabled=True)
        st.write(f"Алынган узундук: {len(st.session_state['doc_text'])} символ")

    st.subheader("Окуу талдоосу")
    max_items = st.slider("Эң көп элементтер (аныктамалар/түстөмөлөр)", 1, 20, 5)
    if st.button("Окуу талдоосун түзүү"):
        doc_text = st.session_state['doc_text']
        if not doc_text or len(doc_text.strip()) < 30:
            st.error("Текст өтө кыска же бош. PDFте тандалган текст бар экенин текшерип кайра жүктөңүз.")
        else:
            with st.spinner("Талдоо жүргүзүлүүдө..."):
                result = analyze_study_text(doc_text, max_items=max_items)
                if 'error' in result:
                    err = result.get('error')
                    if err == 'empty_text':
                        st.error("Документтеги текст бош. PDFти текшерип кайра жүктөңүз.")
                    else:
                        st.error(f"Ката: {result}")
                else:
                    st.success("Окуу талдоосу даяр.")
                    overview = result.get('overview')
                    if overview:
                        st.markdown("### Кыскача")
                        st.markdown(overview)
                    definitions = result.get('definitions')
                    if definitions:
                        st.markdown("### Аныктамалар")
                        if isinstance(definitions, dict):
                            for term, d in definitions.items():
                                st.markdown(f"**{term}** — {d}")
                        elif isinstance(definitions, list):
                            for item in definitions[:max_items]:
                                st.markdown(f"- {item}")
                    explanations = result.get('explanations')
                    if explanations:
                        st.markdown("### Түшүндүрмөлөр")
                        if isinstance(explanations, dict):
                            for term, txt in explanations.items():
                                st.markdown(f"**{term}**")
                                st.markdown(txt)
                        elif isinstance(explanations, list):
                            for item in explanations[:max_items]:
                                st.markdown(item)
                    if not any(k in result for k in ('overview', 'definitions', 'explanations')):
                        st.markdown("### Модельдин чыгышы")
                        st.markdown(str(result))
    elif 'summary' in st.session_state:
        del st.session_state['summary']
else:
    st.info("Баштоо үчүн сол жактан PDF жүктөңүз.")
