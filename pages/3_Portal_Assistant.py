import streamlit as st
from pathlib import Path
import re

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Portal Assistant", layout="wide")
st.title("Portal Assistant")

st.caption(
    "Ask questions about wardrobes, installations, or company guidance. "
    "Answers come only from approved documents."
)

# -----------------------------
# Knowledge base location
# -----------------------------
KB_PATH = Path("knowledge_base")

# -----------------------------
# Load documents (cached)
# -----------------------------
@st.cache_data
def load_documents():
    docs = []
    if not KB_PATH.exists():
        return docs

    for file in KB_PATH.glob("*.md"):
        text = file.read_text(encoding="utf-8", errors="ignore")
        docs.append(
            {
                "name": file.name,
                "text": text,
                "text_lower": text.lower(),
            }
        )
    return docs

documents = load_documents()

# -----------------------------
# Chat session state
# -----------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []

# -----------------------------
# Display chat history
# -----------------------------
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -----------------------------
# Chat input (TEXT + AUDIO)
# -----------------------------
query = st.chat_input(
    "Ask a question (you can type or use voice)",
    accept_audio=True
)

# -----------------------------
# Core logic: answer only from docs
# -----------------------------
def answer_from_docs(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        return "I couldn’t understand that. Please try again."

    q = question.lower()
    words = [w for w in re.findall(r"\b\w+\b", q) if len(w) > 2]

    if not words:
        return "Please ask a more specific question."

    matched_snippets = []

    for doc in documents:
        for sentence in re.split(r"(?<=[.!?])\s+", doc["text"]):
            s_lower = sentence.lower()
            if any(word in s_lower for word in words):
                matched_snippets.append(
                    {
                        "doc": doc["name"],
                        "text": sentence.strip(),
                    }
                )

    if not matched_snippets:
        return (
            "I couldn’t find an answer to that in the approved documents.\n\n"
            "Please check with the office or update the knowledge base."
        )

    response = "Here’s what I found in the approved documents:\n\n"
    for item in matched_snippets[:5]:
        response += f"- **{item['doc']}**: {item['text']}\n"

    return response

# -----------------------------
# Handle user input safely
# -----------------------------
if query:
    # IMPORTANT: handle audio vs text input
    if isinstance(query, str):
        user_text = query
    else:
        user_text = query.text  # audio → transcription

    # Store + display user message
    st.session_state.chat.append(
        {"role": "user", "content": user_text}
    )
    with st.chat_message("user"):
        st.write(user_text)

    # Generate response
    reply = answer_from_docs(user_text)

    # Store + display assistant response
    st.session_state.chat.append(
        {"role": "assistant", "content": reply}
    )
    with st.chat_message("assistant"):
        st.write(reply)

# -----------------------------
# Sidebar info (optional)
# -----------------------------
with st.sidebar:
    st.header("About")
    st.write(
        "This assistant only answers questions using approved company documents.\n\n"
        "If a question cannot be answered, the documents may need updating."
    )

    st.divider()
    st.write(f"Documents loaded: **{len(documents)}**")

    if st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()
