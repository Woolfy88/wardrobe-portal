import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ============================================================
# SETTINGS
# ============================================================
st.set_page_config(page_title="Wardrobe Calculator", layout="wide")

st.header("Wardrobe Door & Liner Calculator")

# ============================================================
# CONSTANTS
# ============================================================
BOTTOM_LINER_THICKNESS = 36
TRACKSET_HEIGHT = 54
BASE_SIDE_LINER_THICKNESS = 18

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

DOOR_SYSTEM_OPTIONS = ["", "Fixed 2223mm doors", "Made to measure doors"]

HOUSEBUILDER_RULES = {
    "Avant": {"dropdown": 90, "side_each": 18},
    "Homes By Honey": {"dropdown": 90, "side_each": 18},
    "Bloor": {"dropdown": 108, "side_each": 18},
    "Story": {"dropdown": 50, "side_each": 68},
    "Strata": {"dropdown": 50, "side_each": 68},
    "Jones Homes": {"dropdown": 50, "side_each": 68},
}
HOUSEBUILDER_OPTIONS = list(HOUSEBUILDER_RULES.keys())

DOOR_STYLE_OVERLAP = {
    "Classic": 35,
    "Shaker": 75,
    "Heritage": 25,
    "Contour": 36,
}
DOOR_STYLE_OPTIONS = list(DOOR_STYLE_OVERLAP.keys())


def normalized_door_system(val):
    return "Fixed 2223mm doors" if not val else val


def get_side_thicknesses(housebuilder, end_panels):
    rule = HOUSEBUILDER_RULES[housebuilder]
    base = rule["side_each"]

    if end_panels == 2:
        return 18, 18, "2x end panels (18mm each side)"
    if end_panels == 1:
        return 18, base, "1x end panel (18mm) + 1x build-out"
    return base, base, (
        "68mm build-out each side (50mm T-liner + 18mm side liner)"
        if base == 68 else
        "2x 18mm side liners"
    )


# ============================================================
# DIAGRAM
# ============================================================
def draw_wardrobe_diagram(
    opening_width_mm,
    opening_height_mm,
    side_left_mm,
    side_right_mm,
    dropdown_height_mm,
    door_height_mm,
    doors,
):
    ow = max(opening_width_mm, 1)
    oh = max(opening_height_mm, 1)

    left = side_left_mm / ow
    right = side_right_mm / ow
    bottom = BOTTOM_LINER_THICKNESS / oh
    dropdown = dropdown_height_mm / oh if dropdown_height_mm else 0

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))
    ax.add_patch(Rectangle((0, bottom), left, 1 - bottom, alpha=0.25))
    ax.add_patch(Rectangle((1 - right, bottom), right, 1 - bottom, alpha=0.25))
    ax.add_patch(Rectangle((left, 0), 1 - left - right, bottom, alpha=0.25))

    if dropdown:
        ax.add_patch(Rectangle((left, 1 - dropdown), 1 - left - right, dropdown, alpha=0.25))

    usable_height = 1 - bottom - dropdown
    door_rel = min(door_height_mm / oh, usable_height)

    span = 1 - left - right
    door_w = span / max(doors, 1)

    x = left
    for _ in range(doors):
        ax.add_patch(Rectangle((x, bottom), door_w, door_rel, fill=False, linestyle="--"))
        x += door_w

    return fig


# ============================================================
# DEFAULT / RESET
# ============================================================
EMPTY_ROW = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Bloor",
    "Door_System": "",
    "Door_Style": "Classic",
    "End_Panels": 0,
}])


def reset():
    st.session_state["df"] = EMPTY_ROW.copy()
    if "editor" in st.session_state:
        del st.session_state["editor"]


if "df" not in st.session_state:
    reset()

# ============================================================
# INPUT
# ============================================================
st.subheader("1. Enter opening")
st.button("Reset opening", on_click=reset)

df = st.data_editor(
    st.session_state["df"],
    key="editor",
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2),
        "Housebuilder": st.column_config.SelectboxColumn("Housebuilder", options=HOUSEBUILDER_OPTIONS),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "End_Panels": st.column_config.SelectboxColumn("End panels", options=[0, 1, 2]),
    },
)

st.session_state["df"] = df
row = df.iloc[0]

if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
    st.stop()

hb = row["Housebuilder"]
doors = int(row["Doors"])
door_system = normalized_door_system(row["Door_System"])
dropdown = HOUSEBUILDER_RULES[hb]["dropdown"]
side_l, side_r, side_desc = get_side_thicknesses(hb, int(row["End_Panels"]))

# ============================================================
# BLOOR BANNER (PLAIN TEXT)
# ============================================================
st.subheader("2. Visualise opening")

if hb == "Bloor":
    st.markdown(
        """
**Bloor specification – follow Field Aware floor plan**

This job is **Bloor**. The final opening width, height and any build-out required
must be taken from the **client floor plan in Field Aware** to make the wardrobe
product work with the aperture.

- Door height is **fixed at 2223mm**
- Dropdown is **fixed at 108mm**
- Side build-out shown is **indicative only**
- Overlap guidance (for information only):
  - **Classic:** 35mm per meeting
  - **Shaker:** 75mm per meeting

**Do not rely on calculated spans or overlaps for Bloor.**
"""
    )
else:
    st.markdown(
        f"""
**Installer guidance**

- Dropdown applied: **{dropdown}mm**
- Side build-out: **{side_desc}**
- Door system: **{door_system}**
"""
    )

# ============================================================
# DIAGRAM
# ============================================================
fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    side_left_mm=side_l,
    side_right_mm=side_r,
    dropdown_height_mm=dropdown,
    door_height_mm=FIXED_DOOR_HEIGHT,
    doors=doors,
)

st.pyplot(fig)
