import streamlit as st

st.set_page_config(page_title="Product Info", layout="wide")
st.title("Product Information")

st.write(
    "Use this page to view product details, reference images, and installation notes."
)

st.divider()

# -----------------------------------
# Aluminium doors
# -----------------------------------
st.subheader("Aluminium Doors")

st.image(
    "assets/product_info/aluminium_door.png",
    caption="Aluminium sliding door system",
    use_column_width=True,
)

st.markdown(
    """
- Lightweight aluminium frame  
- Suitable for soft-close systems  
- Available in multiple finishes  
"""
)

st.divider()

# -----------------------------------
# Steel doors
# -----------------------------------
st.subheader("Steel Doors")

st.image(
    "assets/product_info/steel_door.png",
    caption="Steel framed sliding door",
    use_column_width=True,
)

st.markdown(
    """
- Heavier-duty construction  
- Requires correct soft-close specification  
- Ensure track is level before install  
"""
)

st.divider()

# -----------------------------------
# Soft-close units
# -----------------------------------
st.subheader("Soft-Close Units")

st.image(
    "assets/product_info/soft_close_unit.jpg",
    caption="Soft-close damper unit (example)",
    use_column_width=True,
)

st.markdown(
    """
- Ensure correct handed unit is used  
- Check door weight rating  
- Test before final fix  
"""
)
