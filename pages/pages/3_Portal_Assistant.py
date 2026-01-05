import streamlit as st
from pathlib import Path
import re

st.set_page_config(page_title="Portal Assistant", layout="wide")
st.title("Portal Assistant")

st.caption(
    "Ask questions about wardrobes and installations. "
    "Answers are based only on approved company documents."
)

KB_PATH = Path("knowledge_base")

# -----------------------------
# Load knowledge base
# -----------------------------
@st.cache_data
def load_documents():
    docs = []
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
# Chat state
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
    "Ask a question (you can use voice)",
    accept_audio=True
)

# -----------------------------
# Search + answer logic
# -----------------------------
def answer_from_docs(question: str):
    q = question.lower()
    matches = []

    for doc in documents:
        if any(word in doc["text_lower"] for word in q.split()):
            matches.append(doc)

    if not matches:
        return (
            "I couldn’t find an answer to that in the approved documents. "
            "Please check with the office or update the knowledge base."
        )

    # Extract relevant snippets
    snippets = []
    for doc in matches:
        sentences = re.split(r"(?<=[.!?])\s+", doc["text"])
        for s in sentences:
            if any(word in s.lower() for word in q.split()):
                snippets.append((doc["name"], s.strip()))

    if not snippets:
        return (
            "I found related documents, but nothing directly answering your question. "
            "You may need to add guidance to the knowledge base."
        )

    response = "Here’s what I found in the approved documents:\n\n"
    for name, text in snippets[:5]:
        response += f"- **{name}**: {text}\n"

    return response

# -----------------------------
# Handle input
# -----------------------------
if query:
    st.session_state.chat.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    reply = answer_from_docs(query)

    st.session_state.chat.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
