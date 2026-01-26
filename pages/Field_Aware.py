import streamlit as st

st.set_page_config(page_title="How To Use Field Aware", layout="wide")

st.title("✅ How To Use Field Aware")
st.caption("Quick guides, documents and screen recordings for installers and drivers.")

# --------------------------------------------------
# Google Drive IDs (from share links: /file/d/<ID>/view)
# --------------------------------------------------
DOCUMENTS = {
    "Field Aware – Quick Reference Guide (PDF)": "1t58voi-XUzyemNUOtPJdiZqYVABWHzgJ",
}

VIDEOS = {
    "Mobile walkthrough": "1-74Pi2gtH1cwTGhF60XV6VZJnKOGvHHy",
    "Declining a job & failure reasons": "1RT1MvKBewo4i0kzfoz0XPcNSqQKZ773O",
}

def drive_view_url(file_id: str) -> str:
    # Reliable link that opens in Google Drive
    return f"https://drive.google.com/file/d/{file_id}/view"

def drive_download_url(file_id: str) -> str:
    # Useful for "Download" buttons
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# --------------------------------------------------
# DOCUMENTS
# --------------------------------------------------
st.header("📄 Documents")

doc_title = st.selectbox("Choose a document", list(DOCUMENTS.keys()))
doc_id = DOCUMENTS[doc_title]

col1, col2 = st.columns(2)
with col1:
    st.link_button("📖 Open document", drive_view_url(doc_id), use_container_width=True)
with col2:
    st.link_button("⬇️ Download", drive_download_url(doc_id), use_container_width=True)

st.divider()

# --------------------------------------------------
# VIDEOS
# --------------------------------------------------
st.header("🎬 Videos")

video_title = st.selectbox("Choose a video", list(VIDEOS.keys()))
video_id = VIDEOS[video_title]

st.subheader(video_title)
st.info("Tap below to watch the video (opens in Google Drive for reliable playback).")

st.link_button("▶ Watch video", drive_view_url(video_id), use_container_width=True)

st.divider()
st.caption(
    "Tip: When you add new files to Drive, share them as “Anyone with the link (Viewer)” then paste the file ID into this page."
)
