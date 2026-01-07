import streamlit as st
from pathlib import Path
import re
from typing import List, Dict, Tuple

from pypdf import PdfReader

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Portal Assistant", layout="wide")
st.title("Portal Assistant")

st.caption(
    "Ask questions about wardrobes, installations, or company guidance. "
    "This assistant returns matching approved documents for download (no excerpts)."
)

# -----------------------------
# Knowledge base location
# -----------------------------
KB_PATH = Path("knowledge_base")

SUPPORTED_DOC_EXTS = (".md", ".pdf")


# -----------------------------
# Load documents (cached)
# -----------------------------
@st.cache_data
def load_documents() -> List[Dict]:
    """
    Loads approved docs from knowledge_base/:
      - .md (markdown)
      - .pdf (text-based PDFs only; scanned PDFs may return empty text)
    Returns list of dicts: {name, kind, path, text_lower, extracted_ok}
    """
    docs: List[Dict] = []
    if not KB_PATH.exists():
        return docs

    # Markdown
    for file in sorted(KB_PATH.glob("*.md")):
        text = file.read_text(encoding="utf-8", errors="ignore")
        docs.append(
            {
                "name": file.name,
                "kind": "md",
                "path": file,
                "text_lower": (text or "").lower(),
                "extracted_ok": True,
            }
        )

    # PDF
    for file in sorted(KB_PATH.glob("*.pdf")):
        extracted_pages: List[str] = []
        try:
            reader = PdfReader(str(file))
            for page in reader.pages:
                extracted_pages.append(page.extract_text() or "")
            text = "\n".join(extracted_pages).strip()
        except Exception:
            text = ""

        docs.append(
            {
                "name": file.name,
                "kind": "pdf",
                "path": file,
                "text_lower": (text or "").lower(),
                "extracted_ok": len((text or "").strip()) >= 50,  # heuristic
            }
        )

    return docs


documents = load_documents()


# -----------------------------
# Search logic (doc-locked)
# -----------------------------
def tokenize(question: str) -> List[str]:
    """Simple tokeniser: words length >= 3."""
    q = question.lower()
    words = re.findall(r"\b\w+\b", q)
    return [w for w in words if len(w) >= 3]


def find_matching_docs(question: str, top_k: int = 5) -> Tuple[str, List[Dict]]:
    """
    Returns:
      - response text
      - list of matched doc dicts (with score), highest first
    """
    if not isinstance(question, str) or not question.strip():
        return "I couldn’t understand that. Please try again.", []

    if not documents:
        return (
            "No approved documents are loaded.\n\n"
            "Create a `knowledge_base/` folder at the repo root and add `.md` and/or `.pdf` files."
        ), []

    query_words = tokenize(question)
    if not query_words:
        return "Please ask a more specific question (at least a few words).", []

    scored: List[Dict] = []
    qset = set(query_words)

    for doc in documents:
        text_lower = doc["text_lower"]
        score = sum(1 for w in qset if w in text_lower)
        if score > 0:
            scored.append({**doc, "score": score})

    if not scored:
        return (
            "I couldn’t find anything relevant in the approved documents.\n\n"
            "Please check with the office or update the knowledge base."
        ), []

    scored.sort(key=lambda d: (d["score"], d["name"]), reverse=True)
    top = scored[:top_k]

    msg = (
        "I found relevant approved document(s). Download the best match below:\n\n"
        "*(No excerpts are shown — only the source documents.)*"
    )
    return msg, top


def file_bytes_and_mime(path: Path) -> Tuple[bytes, str]:
    """
    Reads file bytes and returns (bytes, mime_type).
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return path.read_bytes(), "application/pdf"
    if suffix == ".md":
        return path.read_bytes(), "text/markdown"
    # fallback
    return path.read_bytes(), "application/octet-stream"


# -----------------------------
# Chat state + display
# -----------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        # Render any document download buttons attached to assistant messages
        for d in msg.get("docs", []):
            st.markdown(f"**{d['name']}**  (match score: {d['score']})")
            try:
                data, mime = file_bytes_and_mime(Path(d["path"]))
                st.download_button(
                    label=f"Download {d['name']}",
                    data=data,
                    file_name=d["name"],
                    mime=mime,
                    key=f"dl_{msg.get('id','')}_{d['name']}",
                    use_container_width=True,
                )
            except Exception:
                st.warning(f"Could not prepare download for {d['name']}.")
            st.divider()


# -----------------------------
# Input (TEXT + AUDIO)
# -----------------------------
query = st.chat_input("Ask a question (type or use voice)", accept_audio=True)

if query:
    # Handle audio vs text input safely
    if isinstance(query, str):
        user_text = query
    else:
        user_text = getattr(query, "text", "")  # audio → transcription

    user_text = (user_text or "").strip()

    if user_text:
        st.session_state.chat.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        reply, matched_docs = find_matching_docs(user_text, top_k=5)

        # Store docs (with path as str for session serializability)
        stored_docs = []
        for d in matched_docs:
            stored_docs.append(
                {
                    "name": d["name"],
                    "score": d["score"],
                    "path": str(d["path"]),
                }
            )

        # Add a stable-ish id for download button keys
        msg_id = str(len(st.session_state.chat))
        st.session_state.chat.append(
            {"role": "assistant", "content": reply, "docs": stored_docs, "id": msg_id}
        )

        with st.chat_message("assistant"):
            st.write(reply)
            for d in stored_docs:
                st.markdown(f"**{d['name']}**  (match score: {d['score']})")
                try:
                    data, mime = file_bytes_and_mime(Path(d["path"]))
                    st.download_button(
                        label=f"Download {d['name']}",
                        data=data,
                        file_name=d["name"],
                        mime=mime,
                        key=f"dl_live_{msg_id}_{d['name']}",
                        use_container_width=True,
                    )
                except Exception:
                    st.warning(f"Could not prepare download for {d['name']}.")
                st.divider()
    else:
        msg = "I couldn’t capture any text from that. Please try again or type your question."
        st.session_state.chat.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant"):
            st.write(msg)


# -----------------------------
# Sidebar diagnostics & actions
# -----------------------------
with st.sidebar:
    st.header("Knowledge Base")

    st.write(f"Docs loaded: **{len(documents)}**")

    md_count = sum(1 for d in documents if d["kind"] == "md")
    pdf_count = sum(1 for d in documents if d["kind"] == "pdf")
    st.write(f"- Markdown: **{md_count}**")
    st.write(f"- PDF: **{pdf_count}**")

    # Warn about scanned PDFs / empty extraction
    empty_pdfs = [d["name"] for d in documents if d["kind"] == "pdf" and not d["extracted_ok"]]
    if empty_pdfs:
        st.warning(
            "Some PDFs appear to have little/no extractable text (likely scanned images). "
            "They may not match searches well.\n\n"
            + "\n".join([f"- {n}" for n in empty_pdfs])
        )

    st.divider()

    if st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()
