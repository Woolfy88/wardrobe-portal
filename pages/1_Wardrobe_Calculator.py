import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ============================================================
# PAGE CONFIG
# ============================================================
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
    "Made to measure doors",
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
DOOR_STYLE_OPTIONS = list(DOOR_STYLE_OVERLAP.keys())


def overlaps_count(n: int) -> int:
    if n == 2:
        return 1
    if n in (3, 4):
        return 2
    if n == 5:
        return 4
    return max(n - 1, 0)


# ============================================================
# DIAGRAM
# ============================================================
def draw_wardrobe_diagram(
    opening_width_mm,
    opening_height_mm,
    bottom_thk_mm,
    side_thk_mm,
    dropdown_height_mm,
    door_height_mm,
    num_doors,
    door_width_mm,
):
    side_rel = side_thk_mm / opening_width_mm
    bottom_rel = bottom_thk_mm / opening_height_mm
    dropdown_rel = dropdown_height_mm / opening_height_mm if dropdown_height_mm else 0

    usable_rel_height = max(1 - bottom_rel - dropdown_rel, 0)
    door_h_rel = min(door_height_mm / opening_height_mm, usable_rel_height)

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.4, 1.4)
    ax.set_ylim(-0.2, 1.2)

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))
    ax.add_patch(Rectangle((0, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((1 - side_rel, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((side_rel, 0), 1 - 2 * side_rel, bottom_rel, alpha=0.25))

    if dropdown_rel:
        ax.add_patch(Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, alpha=0.25))

    door_width_rel = door_width_mm / opening_width_mm
    available_span = 1 - 2 * side_rel
    total_span = num_doors * door_width_rel
    if total_span > available_span:
        door_width_rel *= available_span / total_span

    x = side_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_width_rel, door_h_rel, fill=False, ls="--"))
        x += door_width_rel

    ax.text(0.5, -0.08, f"{int(opening_width_mm)}mm", ha="center")
    ax.text(-0.25, 0.5, f"{int(opening_height_mm)}mm", rotation=90, va="center")

    return fig


# ============================================================
# INPUT TABLE (ONE ROW)
# ============================================================
DEFAULT = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Bloor",
    "Door_System": "Made to measure doors",
    "Door_Style": "Classic",
    "Fixed_Door_Width_mm": 762,  # Only used if Avant
}])

if "df" not in st.session_state:
    st.session_state.df = DEFAULT.copy()

def reset():
    st.session_state.df = DEFAULT.copy()

st.subheader("1. Enter opening")
st.button("Reset opening", on_click=reset)

st.caption("Fixed door width is **only used when Housebuilder = Avant**.")

df = st.data_editor(
    st.session_state.df,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2, max_value=10),
        "Housebuilder": st.column_config.SelectboxColumn("Housebuilder", options=HOUSEBUILDER_OPTIONS),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (Avant only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
        ),
    },
)
st.session_state.df = df

row = df.iloc[0]

# ============================================================
# CALCULATION
# ============================================================
st.subheader("2. Calculated results")

if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
    st.info("Enter width and height to calculate.")
    st.stop()

width = row["Width_mm"]
height = row["Height_mm"]
doors = int(row["Doors"])
hb = row["Housebuilder"]
door_system = row["Door_System"]
door_style = row["Door_Style"]

hb_rule = HOUSEBUILDER_RULES[hb]
dropdown = hb_rule["dropdown"]
side_thk = hb_rule["side_liner"]

overlap = DOOR_STYLE_OVERLAP[door_style]
total_overlap = overlaps_count(doors) * overlap
height_stack = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT

if door_system == "Fixed 2223mm doors":
    door_height = FIXED_DOOR_HEIGHT
    door_width = row["Fixed_Door_Width_mm"] if hb == "Avant" else 762
    dropdown_h = max(min(height - height_stack - door_height, MAX_DROPDOWN_LIMIT), 0)
    net_width = width - 2 * side_thk
else:
    dropdown_h = min(dropdown, MAX_DROPDOWN_LIMIT)
    door_height = min(height - height_stack - dropdown_h, MAX_DOOR_HEIGHT)
    net_width = width - 2 * side_thk
    door_width = (net_width + total_overlap) / doors

results = pd.DataFrame([{
    "Door height (mm)": int(door_height),
    "Door width (mm)": int(door_width),
    "Dropdown (mm)": int(dropdown_h),
    "Side liner (mm)": side_thk,
    "Net width (mm)": int(net_width),
}])

with st.expander("Show calculated table"):
    st.dataframe(results, use_container_width=True)

# ============================================================
# BANNER (MARKDOWN – NO HTML)
# ============================================================
st.subheader("3. Visualise opening")

if door_system == "Made to measure doors":
    if hb in ["Story", "Strata", "Jones Homes"]:
        banner = f"""
### CUSTOMER SPECIFICATION – MADE TO MEASURE DOORS
- Housebuilder **{hb}** mandates a **fixed 50mm dropdown**
- **Total side build-out per side is fixed at 50mm (includes 18mm T-liner)**
- Door sizes are calculated to suit the remaining opening

**No adjustment is permitted.**
"""
    else:
        banner = f"""
### CUSTOMER SPECIFICATION – MADE TO MEASURE DOORS
- Housebuilder **{hb}** mandates a **fixed {dropdown}mm dropdown**
- Standard **18mm T-liners** per side
- Door sizes calculated to suit net opening

**Dropdown must not be altered.**
"""
else:
    banner = """
### CUSTOMER SPECIFICATION – FIXED 2223mm DOORS
- Door height fixed at **2223mm**
- Dropdown calculated from remaining opening
- Side build-out may vary

**Final sizes must be checked before order.**
"""

st.info(banner)

# ============================================================
# DIAGRAM
# ============================================================
fig = draw_wardrobe_diagram(
    opening_width_mm=width,
    opening_height_mm=height,
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_thk_mm=side_thk,
    dropdown_height_mm=dropdown_h,
    door_height_mm=door_height,
    num_doors=doors,
    door_width_mm=door_width,
)

st.pyplot(fig)
