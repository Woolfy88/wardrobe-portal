import streamlit as st

st.set_page_config(page_title="Field Aware Videos", layout="wide")

st.title("📱 Field Aware Videos")
st.caption("Screen recordings for installers/drivers (hosted on Google Drive).")

# -------------------------------------------------------------------
# Google Drive video IDs (from: https://drive.google.com/file/d/<ID>/view)
# -------------------------------------------------------------------
VIDEOS = {
    "Field Aware – mobile walkthrough": "1-74Pi2gtH1cwTGhF60XV6VZJnKOGvHHy",
}

def drive_direct_download_url(file_id: str) -> str:
    # Often works best for Streamlit embedded playback
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def drive_view_url(file_id: str) -> str:
    # Reliable fallback if Drive streaming is awkward
    return f"https://drive.google.com/file/d/{file_id}/view"

# -------------------------
# UI
# -------------------------
video_title = st.selectbox("Choose a video", list(VIDEOS.keys()))
file_id = VIDEOS[video_title]

st.subheader(video_title)

# Try embedded playback
st.video(drive_direct_download_url(file_id))

# Fallback option
with st.expander("If the video doesn’t play"):
    st.write("Open it directly in Google Drive instead:")
    st.link_button("Open video in Drive", drive_view_url(file_id))
