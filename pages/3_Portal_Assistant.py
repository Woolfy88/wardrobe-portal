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
    "Answers come only from approved documents in the knowledge base."
)

# -----------------------------
# Knowledge base location
# -----------------------------
KB_PATH = Path("knowledge_base")

SUPPORTED_IMAGE_EXTS = (".png", ".jpg", ".jpeg")


# -----------------------------
# Load documents (cached)
# -----------------------------
@st.cache_data
def load_documents() -> List[Dict]:
    """
    Loads approved docs from knowledge_base/:
      - .md (markdown)
      - .pdf (text-based PDFs only; scanned PDFs may return empty text)
    Returns list of dicts: {name, kind, text, text_lower}
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
                "text": text,
                "text_lower": text.lower(),
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
                "text": text,
                "text_lower": text.lower(),
            }
        )

    return docs


documents = load_documents()


# -----------------------------
# Diagram extraction (explicit references only)
# -----------------------------
def find_referenced_images(doc_text: str) -> List[Path]:
    """
    Finds image filenames explicitly referenced in the document text, one per line.
    Example line in markdown:
        Diagram: hanging_double.png
    or just:
        hanging_double.png
    """
    images: List[Path] = []
    for line in doc_text.splitlines():
        line = line.strip()

        # Extract a filename that ends with an image extension
        # Accept either "Diagram: file.png" or plain "file.png"
        m = re.search(r"([A-Za-z0-9_\-./ ]+\.(?:png|jpg|jpeg))$", line, flags=re.IGNORECASE)
        if not m:
            continue

        filename = m.group(1).strip()
        # Normalise any spaces (optional) - keep as is but resolve in KB_PATH
        img_path = KB_PATH / filename
        if img_path.exists() and img_path.suffix.lower() in SUPPORTED_IMAGE_EXTS:
            images.append(img_path)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in images:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


# -----------------------------
# Search + answer logic (doc-locked)
# -----------------------------
def tokenize(question: str) -> List[str]:
    """
    Simple tokeniser: words length >= 3.
    """
    q = question.lower()
    words = re.findall(r"\b\w+\b", q)
    return [w for w in words if len(w) >= 3]


def extract_snippets(doc_name: str, doc_text: str, query_words: List[str], max_snippets: int = 4) -> List[str]:
    """
    Pull sentence-level snippets containing any query word.
    """
    if not doc_text.strip():
        return []

    sentences = re.split(r"(?<=[.!?])\s+", doc_text)
    hits = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        s_lower = s_clean.lower()
        if any(w in s_lower for w in query_words):
            # Collapse whitespace
            s_clean = re.sub(r"\s+", " ", s_clean)
            hits.append(s_clean)

    # Deduplicate snippets
    uniq = []
    seen = set()
    for h in hits:
        if h not in seen:
            uniq.append(h)
            seen.add(h)
        if len(uniq) >= max_snippets:
            break

    return uniq


def answer_from_docs(question: str) -> Tuple[str, List[Path]]:
    """
    Returns:
      - response text (string)
      - list of image Paths to display (diagrams)
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

    # Rank docs by simple score: count of distinct query words present
    scored = []
    for doc in documents:
        text_lower = doc["text_lower"]
        score = sum(1 for w in set(query_words) if w in text_lower)
        if score > 0:
            scored.append((score, doc))

    if not scored:
        return (
            "I couldn’t find an answer to that in the approved documents.\n\n"
            "Please check with the office or update the knowledge base."
        ), []

    scored.sort(key=lambda x: x[0], reverse=True)
    top_docs = [d for _, d in scored[:3]]

    # Build response from snippets only (no freeform)
    lines = []
    images: List[Path] = []

    lines.append("Here’s what I found in the approved documents:\n")

    for doc in top_docs:
        snippets = extract_snippets(doc["name"], doc["text"], query_words, max_snippets=4)
        if not snippets:
            continue

        lines.append(f"**{doc['name']}**")
        for snip in snippets:
            lines.append(f"- {snip}")

        # Collect any explicitly referenced images in this doc
        images.extend(find_referenced_images(doc["text"]))
        lines.append("")  # blank line

    if len(lines) <= 2:
        return (
            "I found related documents, but nothing directly answering your question.\n\n"
            "You may need to add clearer guidance to the knowledge base."
        ), []

    # Deduplicate images
    seen = set()
    unique_images = []
    for p in images:
        if p not in seen:
            unique_images.append(p)
            seen.add(p)

    return "\n".join(lines).strip(), unique_images


# -----------------------------
# Chat state + display
# -----------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        # If we stored images with a message, show them
        for img in msg.get("images", []):
            try:
                st.image(str(img), use_container_width=True)
            except Exception:
                pass


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

        reply, imgs = answer_from_docs(user_text)

        st.session_state.chat.append({"role": "assistant", "content": reply, "images": imgs})
        with st.chat_message("assistant"):
            st.write(reply)
            for img in imgs:
                st.image(str(img), use_container_width=True)
    else:
        # If transcription failed / empty
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
    empty_pdfs = [
        d["name"] for d in documents
        if d["kind"] == "pdf" and len((d["text"] or "").strip()) < 50
    ]
    if empty_pdfs:
        st.warning(
            "Some PDFs appear to have little/no extractable text (likely scanned images). "
            "Convert them to text-based PDFs or create a Markdown version.\n\n"
            + "\n".join([f"- {n}" for n in empty_pdfs])
        )

    st.divider()
    st.caption("Diagrams: reference image filenames in your docs (e.g. `Diagram: hanging_double.png`).")

    if st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()
