
import streamlit as st
from pypdf import PdfReader
from docx import Document
import io
import re

st.set_page_config(
    page_title="EduPolicy AI",
    page_icon="📚",
    layout="wide"
)

st.title("📚 EduPolicy AI")
st.subheader("Intelligent Document Question Answering System")
st.write(
    "Upload PDF or DOCX documents and ask questions "
    "based on their content."
)

st.divider()

uploaded_files = st.file_uploader(
    "Upload PDF or DOCX documents",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

documents = []

if uploaded_files:
    st.success(f"{len(uploaded_files)} document(s) uploaded.")

    for file in uploaded_files:
        text = ""

        try:
            if file.name.lower().endswith(".pdf"):
                pdf = PdfReader(io.BytesIO(file.getvalue()))

                for page_number, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        documents.append({
                            "name": file.name,
                            "page": page_number,
                            "text": page_text
                        })

            elif file.name.lower().endswith(".docx"):
                doc = Document(io.BytesIO(file.getvalue()))
                text = "\n".join(
                    paragraph.text
                    for paragraph in doc.paragraphs
                    if paragraph.text.strip()
                )

                if text.strip():
                    documents.append({
                        "name": file.name,
                        "page": "N/A",
                        "text": text
                    })

        except Exception as error:
            st.error(f"Could not read {file.name}: {error}")

    st.write("### Uploaded Documents")
    for file in uploaded_files:
        st.write(f"📄 {file.name}")

st.divider()

question = st.text_input(
    "Ask a question about your documents:"
)

if st.button("Find Answer"):
    if not uploaded_files:
        st.warning("Please upload a PDF or DOCX document first.")

    elif not question.strip():
        st.warning("Please enter a question.")

    elif not documents:
        st.warning("No readable text was found in the uploaded documents.")

    else:
        question_words = set(
            re.findall(r"\b[a-z0-9]+\b", question.lower())
        )

        stop_words = {
            "what", "is", "the", "a", "an", "of", "in",
            "to", "for", "on", "and", "are", "does",
            "do", "tell", "me", "about", "please"
        }

        question_words -= stop_words
        matches = []

        for item in documents:
            text = item["text"]
            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                sentence_words = set(
                    re.findall(r"\b[a-z0-9]+\b", sentence.lower())
                )

                score = len(question_words & sentence_words)

                if score > 0:
                    matches.append((score, sentence, item))

        if not matches:
            st.warning(
                "I could not find this information in the uploaded documents."
            )
        else:
            matches.sort(key=lambda item: item[0], reverse=True)
            best_score = matches[0][0]

            answer_sentences = []
            sources = []

            for score, sentence, item in matches:
                if score < best_score:
                    break

                if sentence not in answer_sentences:
                    answer_sentences.append(sentence)

                source = f"{item['name']} — Page {item['page']}"
                if source not in sources:
                    sources.append(source)

            st.markdown("### Answer")
            st.write(" ".join(answer_sentences[:3]))

            st.markdown("### Source")
            for source in sources:
                st.write(f"📄 {source}")

