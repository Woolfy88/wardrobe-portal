import streamlit as st

st.set_page_config(page_title="Toolbox Talks", layout="wide")
st.title("Toolbox Talks")

with st.expander("Manual handling"):
    st.markdown(
        """
- Assess the load  
- Two-person lifts for heavy doors/panels  
- Bend knees, straight back  
"""
    )

with st.expander("Working at height"):
    st.markdown(
        """
- Use correct steps/platforms  
- Keep area clear  
- Follow site rules  
"""
    )

with st.expander("Power tools & dust"):
    st.markdown(
        """
- Check tools before use  
- Use extraction / masks when cutting boards  
- Keep cables tidy  
"""
    )
