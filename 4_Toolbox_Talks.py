import streamlit as st
from pathlib import Path

st.title("Toolbox Talks Library")

talks_dir = Path("assets/toolbox_talks")

pdf_files = sorted(talks_dir.glob("*.pdf"))

if not pdf_files:
    st.info("No toolbox talk PDFs found yet.")
else:
    for pdf_path in pdf_files:
        with open(pdf_path, "rb") as f:
            st.download_button(
                label=f"Download: {pdf_path.stem.replace('_',' ')}",
                data=f,
                file_name=pdf_path.name,
                mime="application/pdf",
            )
