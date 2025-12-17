import streamlit as st

st.set_page_config(page_title="Product Info", layout="wide")
st.title("Product Information")

st.write(
    "Use this page to view product details, reference images, and installation notes."
)

st.divider()

# -----------------------------------
# Aura Stanchions
# -----------------------------------
st.subheader("Aura Stanchions")

st.image(
    "assets/product_info/aura.jpg",
    caption="Aura Stanchion System",
    use_column_width=True,
)

st.markdown(
    """
"""
)

st.divider()

# -----------------------------------
# Door Types
# -----------------------------------
st.subheader("Door Types")

st.image(
    "assets/product_info/Door Types.jpg",
    caption="Our Types Of Doors",
    use_column_width=True,
)

st.markdown(
    """

"""
)

st.divider()

# -----------------------------------
#  Woodwork Colours
# -----------------------------------
st.subheader("Soft-Close Units")

st.image(
    "assets/product_info/Colours.jpg",
    caption="Our Woodwork Colours",
    use_column_width=True,
)

st.markdown(
    """

"""
)
