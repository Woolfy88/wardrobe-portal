import streamlit as st

st.set_page_config(page_title="Field Aware Videos", layout="wide")

st.title("📱 Field Aware Videos")
st.caption("Quick screen recordings for installers and drivers.")

VIDEOS = {
    "Field Aware – mobile walkthrough": "1-74Pi2gtH1cwTGhF60XV6VZJnKOGvHHy",
}

def drive_view_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"

video_title = st.selectbox("Choose a video", list(VIDEOS.keys()))
file_id = VIDEOS[video_title]

st.subheader(video_title)

st.info("Tap below to watch the video (opens in Google Drive).")
st.link_button(
    "▶ Watch video",
    drive_view_url(file_id),
    use_container_width=True,
)
