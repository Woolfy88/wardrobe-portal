import streamlit as st

st.set_page_config(page_title="Soft-Close Fitting", layout="wide")
st.title("Soft-Close Fitting Guides")

st.write(
    "Use the guides below for installing soft-close mechanisms on different door types."
)

st.divider()

# -------------------------------------------------
# Aluminium doors
# -------------------------------------------------
st.subheader("How to fit soft-close Aluminium doors")

st.video("https://www.youtube.com/watch?v=hL4D4J8At94")

st.markdown(
    """
**Key points:**
- Check track alignment before fitting soft-close units
- Ensure correct handed units are used
- Test door travel before final tightening
"""
)

st.divider()

# -------------------------------------------------
# Steel doors
# -------------------------------------------------
st.subheader("How to fit soft-close on steel doors")

st.video("https://www.youtube.com/watch?v=va3QC579djY")

st.markdown(
    """
**Key points:**
- Confirm steel door compatibility
- Fix brackets securely before engaging dampers
- Check smooth operation across full door travel
"""
)

st.info(
    "If doors do not soft-close correctly, re-check track level, damper position, and door alignment."
)
