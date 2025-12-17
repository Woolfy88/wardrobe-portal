import streamlit as st

# -----------------------------
# PIN PROTECTION
# -----------------------------
CORRECT_PIN = "1966"  # <-- CHANGE THIS

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.set_page_config(page_title="Installer Portal", layout="centered")
    st.title("Installer Portal")

    pin = st.text_input("Enter PIN", type="password")

    if pin:
        if pin == CORRECT_PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN")

    st.stop()


st.set_page_config(page_title="Installer Portal", layout="wide")
st.title("Installer Portal")

st.markdown(
    """
Welcome. Use the left menu to open:
- **Wardrobe Calculator**
- **Office System**
- **Invoicing**
- **Toolbox Talks**
"""
)

st.info("Tip: On mobile, open the ☰ menu (top-left) to switch sections.")

