import os
import streamlit as st

from ingest import ingest_pdfs
from rag import ask, stats

st.set_page_config(page_title="Quarterly Results RAG", layout="wide")
st.title("Quarterly Financial Reports — Ask Anything")
st.caption("Upload quarterly results PDFs, index them, then ask questions in plain English.")

with st.sidebar:
    st.header("1. Upload & Index")
    uploaded_files = st.file_uploader(
        "Upload one or more PDF files", type="pdf", accept_multiple_files=True
    )

    if st.button("Index documents", disabled=not uploaded_files):
        with st.spinner("Reading, chunking, and embedding..."):
            os.makedirs("data", exist_ok=True)
            saved_paths = []
            for f in uploaded_files:
                path = os.path.join("data", f.name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
                saved_paths.append(path)

            n_files, n_chunks = ingest_pdfs(saved_paths)
            st.success(f"{n_files} files processed, {n_chunks} chunks stored.")

    st.divider()
    st.header("Collection stats")
    try:
        s = stats()
        st.write(f"**Chunks stored:** {s['total_chunks']}")
        st.write(f"**Embedding model:** {s['embedding_model']}")
        st.write(f"**LLM model:** {s['llm_model']}")
    except Exception:
        st.write("No collection yet — index some PDFs first.")

st.header("2. Ask a question")
question = st.text_input(
    "Your question",
    placeholder="What was total revenue in the most recent quarter?",
)
top_k = st.slider("Number of chunks to retrieve", 2, 8, 4)

if st.button("Get answer", type="primary", disabled=not question):
    with st.spinner("Retrieving and answering..."):
        result = ask(question, top_k=top_k)

    st.subheader("Answer")
    st.write(result["answer"])

    st.subheader("Sources")
    if result["sources"]:
        for s in result["sources"]:
            st.write(f"📄 {s['file']} — page {s['page']}")
    else:
        st.write("No sources retrieved.")
