import streamlit as st

# -----------------------------
# PAGE CONFIG (MUST BE FIRST)
# -----------------------------
st.set_page_config(
    page_title="Installer Portal",
    layout="wide"
)

# -----------------------------
# PIN PROTECTION
# -----------------------------
CORRECT_PIN = "1966"  # <-- CHANGE THIS

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# -----------------------------
# LOGIN SCREEN
# -----------------------------
if not st.session_state.authenticated:
    st.title("Installer Portal")

    pin = st.text_input("Enter PIN", type="password")

    if pin:
        if pin == CORRECT_PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN")

    st.stop()

# -----------------------------
# MAIN APP (AFTER LOGIN)
# -----------------------------
st.title("Installer Portal")

st.markdown(
    """
Welcome. Use the left-hand menu to open the relevant section.
"""
)

st.info("Tip: On mobile, open the ☰ menu (top-left) to switch sections.")
