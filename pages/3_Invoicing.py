import streamlit as st

st.set_page_config(page_title="Invoicing", layout="wide")
st.title("Invoicing")

st.markdown("Add your invoicing process here.")

st.markdown("### Checklist")
st.checkbox("Job number included")
st.checkbox("Site address included")
st.checkbox("Photos uploaded (if required)")
st.checkbox("Variations agreed and noted")

st.markdown("### Where to send invoices")
st.markdown("- Email: accounts@yourcompany.com (replace)")
st.markdown("- Portal: https://example.com (replace)")
