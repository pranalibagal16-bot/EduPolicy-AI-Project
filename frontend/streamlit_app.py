
import os
import requests
import streamlit as st

API = os.getenv(
    "API_URL",
    "https://edupolicy-ai-backend.onrender.com"
)

st.set_page_config(
    page_title="EduPolicy AI",
    page_icon="📚",
    layout="wide"
)


# ---------- API Helper ----------
def get_error_message(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail", str(data))
        return str(data)
    except (ValueError, requests.exceptions.JSONDecodeError):
        return response.text[:500] or "Empty response from backend."


def call(method, path, **kw):
    headers = {
        "Authorization": f"Bearer {st.session_state.get('token', '')}"
    }

    try:
        response = requests.request(
            method,
            API + path,
            headers=headers,
            timeout=120,
            **kw
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Backend connection error: {e}")
        st.stop()

    if response.status_code == 401 and "token" in st.session_state:
        st.session_state.clear()
        st.rerun()

    return response


# ---------- Sources ----------
def show_sources(sources):
    if not sources:
        return

    with st.expander(f"Sources ({len(sources)})"):
        for source in sources:
            if source.get("page"):
                location = f"Page {source['page']}"
            else:
                location = f"Section: {source.get('section') or 'N/A'}"

            st.markdown(
                f"**{source.get('document', 'Unknown document')}** "
                f"- {location} "
                f"(similarity {source.get('score', 'N/A')})"
            )

            st.caption(source.get("snippet", ""))


# ---------- Login ----------
if "token" not in st.session_state:
    st.title("📚 EduPolicy AI")

    st.caption(
        "Demo logins: admin / admin123 (upload and delete) "
        "| student / student123 (ask questions)"
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log in", type="primary"):
        try:
            response = requests.post(
                API + "/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=120
            )
        except requests.exceptions.RequestException as e:
            st.error(f"Cannot connect to backend: {e}")
            st.stop()

        if response.ok:
            try:
                data = response.json()
                st.session_state.update(data)
                st.rerun()
            except ValueError:
                st.error(
                    "Login response was not valid JSON: "
                    + response.text[:500]
                )
        else:
            st.error(
                f"Login failed ({response.status_code}): "
                f"{get_error_message(response)}"
            )

    st.stop()


# ---------- User Role ----------
is_admin = st.session_state.get("role") == "admin"


# ---------- Sidebar ----------
with st.sidebar:
    st.write(
        f"👤 **{st.session_state.get('username', 'User')}** "
        f"({st.session_state.get('role', 'unknown')})"
    )

    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.subheader("Documents")

    # Upload documents
    if is_admin:
        uploaded_files = st.file_uploader(
            "Upload PDF / DOCX",
            type=["pdf", "docx"],
            accept_multiple_files=True
        )

        if uploaded_files and st.button("Process uploads"):
            for uploaded_file in uploaded_files:
                with st.spinner(
                    f"Processing {uploaded_file.name}..."
                ):
                    response = call(
                        "POST",
                        "/documents",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue()
                            )
                        }
                    )

                if response.ok:
                    try:
                        data = response.json()
                        chunks = data.get("chunks", "Processed")
                        st.success(
                            f"{uploaded_file.name}: {chunks} chunks"
                        )
                    except ValueError:
                        st.error(
                            f"{uploaded_file.name}: Backend returned "
                            f"an invalid response. "
                            f"Status: {response.status_code}. "
                            f"Response: {response.text[:500]}"
                        )
                else:
                    st.error(
                        f"{uploaded_file.name}: Upload failed. "
                        f"Status: {response.status_code}. "
                        f"Response: {get_error_message(response)}"
                    )

    # Load documents
    docs_response = call("GET", "/documents")

    if docs_response.ok:
        try:
            documents = docs_response.json()
            if not isinstance(documents, list):
                st.error("Unexpected response while loading documents.")
                documents = []
        except ValueError:
            st.error(
                "Could not read documents: "
                + docs_response.text[:500]
            )
            documents = []
    else:
        st.error(
            f"Could not load documents: "
            f"{docs_response.status_code} - "
            f"{get_error_message(docs_response)}"
        )
        documents = []

    if not documents:
        st.info(
            "No documents yet."
            if is_admin
            else "Ask an admin to upload some documents."
        )

    for document in documents:
        col1, col2 = st.columns([4, 1])

        col1.write(
            f"📄 **{document.get('filename', 'Unknown')}**\n\n"
            f"{document.get('pages', 0)} pages/sections, "
            f"{document.get('chunks', 0)} chunks"
        )

        if is_admin and col2.button(
            "🗑",
            key=f"delete_{document.get('id')}"
        ):
            delete_response = call(
                "DELETE",
                f"/documents/{document['id']}"
            )

            if delete_response.ok:
                st.success("Document deleted.")
                st.rerun()
            else:
                st.error(
                    f"Delete failed: "
                    f"{get_error_message(delete_response)}"
                )

    selected_documents = st.multiselect(
        "Search only in",
        [document.get("filename", "") for document in documents]
    )

    doc_ids = [
        document["id"]
        for document in documents
        if document.get("filename") in selected_documents
    ] or None

    st.divider()

    if st.button("Clear chat history"):
        history_response = call("DELETE", "/history")

        if history_response.ok:
            st.success("Chat history cleared.")
            st.rerun()
        else:
            st.error(
                f"Could not clear history: "
                f"{get_error_message(history_response)}"
            )


# ---------- Chat ----------
st.title("📚 EduPolicy AI")
st.caption("Ask questions based on your uploaded documents.")


# Load chat history
history_response = call("GET", "/history")

if history_response.ok:
    try:
        history = history_response.json()
        if isinstance(history, list):
            for message in history:
                st.chat_message("user").write(
                    message.get("question", "")
                )

                with st.chat_message("assistant"):
                    st.write(message.get("answer", ""))
                    show_sources(message.get("sources", []))
        else:
            st.error("Unexpected chat history response.")
    except ValueError:
        st.error(
            "Could not read chat history: "
            + history_response.text[:500]
        )
else:
    st.error(
        f"Could not load chat history: "
        f"{history_response.status_code} - "
        f"{get_error_message(history_response)}"
    )


# Ask a question
question = st.chat_input(
    "Ask a question about the uploaded documents..."
)

if question:
    st.chat_message("user").write(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):
            response = call(
                "POST",
                "/ask",
                json={
                    "question": question,
                    "doc_ids": doc_ids
                }
            )

        if response.ok:
            try:
                answer_data = response.json()
                st.write(answer_data.get("answer", "No answer returned."))
                show_sources(answer_data.get("sources", []))
            except ValueError:
                st.error(
                    "Backend returned an invalid response: "
                    + response.text[:500]
                )
        else:
            st.error(
                f"Question failed ({response.status_code}): "
                f"{get_error_message(response)}"
            )
