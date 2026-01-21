import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="Wardrobe Calculator", layout="wide")
st.header("Wardrobe Door & Liner Calculator")

# ============================================================
# SYSTEM CONSTANTS
# ============================================================
BOTTOM_LINER_THICKNESS = 36
TRACKSET_HEIGHT = 54
BASE_SIDE_LINER_THICKNESS = 18
MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

DOOR_SYSTEM_OPTIONS = [
    "Custom (calculated panels)",
    "Fixed 2223mm doors",
]

HOUSEBUILDER_RULES = {
    "Avant": {"dropdown": 90, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Homes By Honey": {"dropdown": 90, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Bloor": {"dropdown": 108, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Story": {"dropdown": 50, "side_liner": 50},
    "Strata": {"dropdown": 50, "side_liner": 50},
    "Jones Homes": {"dropdown": 50, "side_liner": 50},
}

HOUSEBUILDER_OPTIONS = list(HOUSEBUILDER_RULES.keys())

DOOR_STYLE_OVERLAP = {
    "Classic": 35,
    "Shaker": 75,
    "Heritage": 25,
    "Contour": 36,
}

def overlaps_count(doors: int) -> int:
    if doors == 2:
        return 1
    if doors in (3, 4):
        return 2
    if doors == 5:
        return 4
    return max(doors - 1, 0)

# ============================================================
# DEFAULT DATA (ONE ROW)
# ============================================================
DEFAULT_DATA = pd.DataFrame([{
    "Job": "Job 1",
    "Opening": "Wardrobe A",
    "Width_mm": 2200,
    "Height_mm": 2600,
    "Doors": 3,
    "Housebuilder": "Bloor",
    "Door_System": "Custom (calculated panels)",
    "Door_Style": "Classic",
    "Fixed_Door_Width_mm": 762,
}])

if "openings_df" not in st.session_state:
    st.session_state["openings_df"] = DEFAULT_DATA.copy()

# ============================================================
# DATA ENTRY
# ============================================================
st.subheader("1. Enter opening")

edited_df = st.data_editor(
    st.session_state["openings_df"],
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2, max_value=10),
        "Housebuilder": st.column_config.SelectboxColumn("Housebuilder", options=HOUSEBUILDER_OPTIONS),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=list(DOOR_STYLE_OVERLAP.keys())),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (mm)", options=FIXED_DOOR_WIDTH_OPTIONS
        ),
    },
)

# ============================================================
# CALCULATION
# ============================================================
def calculate(row):
    width = float(row["Width_mm"])
    height = float(row["Height_mm"])
    doors = int(row["Doors"])

    hb = row["Housebuilder"]
    hb_rule = HOUSEBUILDER_RULES[hb]
    dropdown = hb_rule["dropdown"]
    side_liner = hb_rule["side_liner"]

    overlap_pm = DOOR_STYLE_OVERLAP[row["Door_Style"]]
    overlaps = overlaps_count(doors)
    total_overlap = overlaps * overlap_pm

    height_stack = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT

    if row["Door_System"] == "Custom (calculated panels)":
        door_height = height - height_stack - dropdown
        door_height = min(door_height, MAX_DOOR_HEIGHT)

        net_width = width - 2 * side_liner
        door_width = (net_width + total_overlap) / doors

        return pd.Series({
            "Dropdown_mm": dropdown,
            "Side_Liner_mm": side_liner,
            "Door_Height_mm": int(round(door_height)),
            "Door_Width_mm": int(round(door_width)),
            "Total_Overlap_mm": total_overlap,
            "Net_Width_mm": int(round(net_width)),
            "Issue": "OK" if door_height > 0 else "Check height",
        })

    # Fixed system
    door_width = row["Fixed_Door_Width_mm"]
    door_span = doors * door_width
    dropdown_req = height - height_stack - FIXED_DOOR_HEIGHT

    side_req = (width + total_overlap - door_span) / 2
    if hb_rule["side_liner"] != BASE_SIDE_LINER_THICKNESS:
        side_req = side_liner

    net_width = width - 2 * side_req

    return pd.Series({
        "Dropdown_mm": int(round(dropdown_req)),
        "Side_Liner_mm": round(side_req, 1),
        "Door_Height_mm": FIXED_DOOR_HEIGHT,
        "Door_Width_mm": door_width,
        "Total_Overlap_mm": total_overlap,
        "Net_Width_mm": int(round(net_width)),
        "Issue": "OK" if dropdown_req >= 0 else "Opening too small",
    })

results = pd.concat([edited_df, edited_df.apply(calculate, axis=1)], axis=1)
st.subheader("2. Results")
st.dataframe(results, use_container_width=True)

csv = results.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "wardrobe_results.csv")
