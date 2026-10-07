import os, requests, streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="EduPolicy AI", page_icon="📚", layout="wide")


def call(method, path, **kw):
    headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    try:
        r = requests.request(method, API + path, headers=headers, timeout=120, **kw)
    except requests.ConnectionError:
        st.error("Cannot reach the backend. Is `uvicorn backend.main:app` running?")
        st.stop()
    if r.status_code == 401 and "token" in st.session_state:
        st.session_state.clear(); st.rerun()
    return r


def show_sources(sources):
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            loc = f"page {s['page']}" if s.get("page") else f"section: {s.get('section') or 'n/a'}"
            st.markdown(f"**{s['document']}** - {loc} (similarity {s['score']})")
            st.caption(s["snippet"] + "...")


# ---------- Login ----------
if "token" not in st.session_state:
    st.title("📚 EduPolicy AI")
    st.caption("Demo logins: admin / admin123 (can upload & delete)  |  student / student123 (ask only)")
    u = st.text_input("Username"); p = st.text_input("Password", type="password")
    if st.button("Log in", type="primary"):
        try:
            r = requests.post(API + "/auth/login", json={"username": u, "password": p})
        except requests.ConnectionError:
            st.error("Cannot reach the backend. Start it with: uvicorn backend.main:app --reload"); st.stop()
        if r.ok:
            st.session_state.update(r.json()); st.rerun()
        else:
            st.error(r.json().get("detail", "Login failed"))
    st.stop()

is_admin = st.session_state["role"] == "admin"

# ---------- Sidebar: documents ----------
with st.sidebar:
    st.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
    if st.button("Log out"):
        st.session_state.clear(); st.rerun()
    st.divider()
    st.subheader("Documents")
    if is_admin:
        files = st.file_uploader("Upload PDF / DOCX", type=["pdf", "docx"], accept_multiple_files=True)
        if files and st.button("Process uploads"):
            for f in files:
                with st.spinner(f"Processing {f.name}..."):
                    r = call("POST", "/documents", files={"file": (f.name, f.getvalue())})
                if r.ok:
                    st.success(f"{f.name}: {r.json()['chunks']} chunks")
                else:
                    st.error(f"{f.name}: {r.json().get('detail')}")
            st.rerun()
    docs = call("GET", "/documents").json()
    if not docs:
        st.info("No documents yet." + ("" if is_admin else " Ask an admin to upload some."))
    for d in docs:
        c1, c2 = st.columns([4, 1])
        c1.write(f"📄 {d['filename']}  \n<small>{d['pages']} pages/sections, {d['chunks']} chunks</small>", unsafe_allow_html=True)
        if is_admin and c2.button("🗑", key=f"del{d['id']}"):
            call("DELETE", f"/documents/{d['id']}"); st.rerun()
    selected = st.multiselect("Search only in", [d["filename"] for d in docs])
    doc_ids = [d["id"] for d in docs if d["filename"] in selected] or None
    st.divider()
    if st.button("Clear chat history"):
        call("DELETE", "/history"); st.rerun()

# ---------- Chat ----------
st.title("📚 EduPolicy AI")
for m in call("GET", "/history").json():
    st.chat_message("user").write(m["question"])
    with st.chat_message("assistant"):
        st.write(m["answer"]); show_sources(m["sources"])

if q := st.chat_input("Ask a question about the uploaded documents..."):
    st.chat_message("user").write(q)
    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):
            r = call("POST", "/ask", json={"question": q, "doc_ids": doc_ids})
        if r.ok:
            st.write(r.json()["answer"]); show_sources(r.json()["sources"])
        else:
            st.error(r.json().get("detail", "Error"))
