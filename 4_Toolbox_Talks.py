import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Toolbox Talks", layout="wide")
st.title("Toolbox Talks Library")

st.write("Download the latest toolbox talks below:")

talks_dir = Path("assets/toolbox_talks")

pdf_files = sorted(talks_dir.glob("*.pdf"))

if not pdf_files:
    st.info("No toolbox talk PDFs found.")
else:
    for pdf_path in pdf_files:
        display_name = pdf_path.stem.replace("_", " ").replace("-", " ")
        with open(pdf_path, "rb") as f:
            st.download_button(
                label=f"📄 {display_name}",
                data=f,
                file_name=pdf_path.name,
                mime="application/pdf",
            )
