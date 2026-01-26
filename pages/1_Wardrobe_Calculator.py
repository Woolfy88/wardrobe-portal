import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ============================================================
# SETTINGS
# ============================================================
ENABLE_PIN = False
CALCULATOR_PIN = "1966"

st.set_page_config(page_title="Wardrobe Calculator", layout="wide")

# ============================================================
# PAGE-LEVEL PIN (OPTIONAL)
# ============================================================
if ENABLE_PIN:
    if "calc_authenticated" not in st.session_state:
        st.session_state.calc_authenticated = False

    if not st.session_state.calc_authenticated:
        st.title("Wardrobe Calculator")
        pin = st.text_input("Enter PIN", type="password")
        if pin:
            if pin == CALCULATOR_PIN:
                st.session_state.calc_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN")
        st.stop()

st.header("Wardrobe Door & Liner Calculator")

# ============================================================
# CONSTANTS
# ============================================================
BOTTOM_LINER_THICKNESS = 36
TRACKSET_HEIGHT = 54
FIXED_SIZED_DOOR_HEIGHT = 2223

BASE_SIDE_LINER_THICKNESS = 18
MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

HOUSEBUILDER_RULES = {
    "Non-client specific wardrobe": {"dropdown": 0, "locked_total_per_side": None},
    "Avant": {"dropdown": 90, "locked_total_per_side": None},
    "Homes By Honey": {"dropdown": 90, "locked_total_per_side": None},
    "Bloor": {"dropdown": 108, "locked_total_per_side": None},
    "Story": {"dropdown": 50, "locked_total_per_side": 68},
    "Strata": {"dropdown": 50, "locked_total_per_side": 68},
    "Jones Homes": {"dropdown": 50, "locked_total_per_side": 68},
}
HOUSEBUILDER_OPTIONS = list(HOUSEBUILDER_RULES.keys())

DOOR_STYLE_OVERLAP = {
    "Classic": 35,
    "Shaker": 75,
    "Heritage": 25,
    "Contour": 36,
}
DOOR_STYLE_OPTIONS = list(DOOR_STYLE_OVERLAP.keys())

DROPDOWN_SELECT_OPTIONS = ["Auto", "0", "18", "50", "90", "108"]

FLOORPLAN_ONLY_HOUSEBUILDERS = {"Avant", "Homes By Honey", "Bloor"}


# ============================================================
# HELPERS
# ============================================================
def overlaps_count(num_doors: int) -> int:
    if num_doors == 2:
        return 1
    if num_doors in (3, 4):
        return 2
    if num_doors == 5:
        return 4
    return max(num_doors - 1, 0)


def parse_dropdown_select(val):
    if val is None or str(val).lower().startswith("auto"):
        return True, 0
    return False, int(val)


def fmt_side(total: float, t: float) -> str:
    if t <= 0:
        return f"{int(total)}mm (18mm side liner)"
    return f"{int(total)}mm (18 + {int(t)} T-liner)"


def side_desc(l, r, lt, rt, ep):
    if ep == 2:
        return "2x end panels (18mm each side)"
    if ep == 1:
        return "1x end panel (18mm)"
    return f"Left: {fmt_side(l, lt)} | Right: {fmt_side(r, rt)}"


# ============================================================
# DIAGRAM (with fixing notes)
# ============================================================
def draw_wardrobe_diagram(
    opening_width_mm,
    opening_height_mm,
    bottom_thk_mm,
    side_left_mm,
    side_right_mm,
    dropdown_height_mm,
    door_height_mm,
    num_doors,
    door_width_mm,
):
    ow = max(opening_width_mm, 1)
    oh = max(opening_height_mm, 1)

    side_rel = side_left_mm / ow
    bottom_rel = bottom_thk_mm / oh
    dropdown_rel = dropdown_height_mm / oh if dropdown_height_mm else 0

    door_h_rel = door_height_mm / oh if door_height_mm else 0

    fig, ax = plt.subplots(figsize=(5, 7))
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))

    if dropdown_rel:
        ax.add_patch(Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, alpha=0.15))

    # Doors
    span = 1 - 2 * side_rel
    door_w_rel = (door_width_mm / ow) if door_width_mm else span / num_doors
    if num_doors * door_w_rel > span:
        door_w_rel *= span / (num_doors * door_w_rel)

    x = side_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_w_rel, door_h_rel, fill=False, linestyle="--"))
        x += door_w_rel

    # Dimensions
    ax.annotate("", (0, -0.12), (1, -0.12), arrowprops=dict(arrowstyle="<->"))
    ax.text(0.5, -0.16, f"Opening width: {ow}mm", ha="center")

    ax.annotate("", (-0.18, 0), (-0.18, 1), arrowprops=dict(arrowstyle="<->"))
    ax.text(-0.22, 0.5, f"Opening height: {oh}mm", rotation=90, va="center")

    if dropdown_rel:
        ax.annotate("", (1.08, 1 - dropdown_rel), (1.08, 1), arrowprops=dict(arrowstyle="<->"))
        ax.text(1.12, 1 - dropdown_rel / 2, f"Dropdown: {dropdown_height_mm}mm", rotation=90, va="center")

    return fig


# ============================================================
# INPUT TABLE
# ============================================================
seed = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Non-client specific wardrobe",
    "Door_Style": "Classic",
    "Dropdown_Select": "Auto",
    "End_Panels": 0,
}])

if "seed" not in st.session_state:
    st.session_state.seed = seed.copy()

edited_df = st.data_editor(
    st.session_state.seed,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Housebuilder": st.column_config.SelectboxColumn(options=HOUSEBUILDER_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn(options=DOOR_STYLE_OPTIONS),
        "Dropdown_Select": st.column_config.SelectboxColumn(options=DROPDOWN_SELECT_OPTIONS),
        "End_Panels": st.column_config.SelectboxColumn(options=[0, 1, 2]),
    },
)

row = edited_df.iloc[0]
if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
    st.stop()

# ============================================================
# CALCULATION
# ============================================================
is_auto, user_dd = parse_dropdown_select(row["Dropdown_Select"])
hb = row["Housebuilder"]
hb_rule = HOUSEBUILDER_RULES[hb]

dropdown = (
    0 if is_auto and hb == "Non-client specific wardrobe"
    else hb_rule["dropdown"] if is_auto
    else user_dd
)

height_stack = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT
door_height = row["Height_mm"] - height_stack - dropdown

side_total = hb_rule["locked_total_per_side"] or 18
net_width = row["Width_mm"] - (side_total * 2)

overlap = overlaps_count(row["Doors"]) * DOOR_STYLE_OVERLAP[row["Door_Style"]]
door_width = (net_width + overlap) / row["Doors"]

# ============================================================
# VISUAL OUTPUT
# ============================================================
st.subheader("Visualise opening")

# ✅ PATCH APPLIED HERE
st.info(f"Trackset height: **{TRACKSET_HEIGHT}mm**")
if hb in {"Bloor", "Avant", "Homes By Honey"}:
    st.info(f"Fixed sized door height: **{FIXED_SIZED_DOOR_HEIGHT}mm**")

fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_left_mm=side_total,
    side_right_mm=side_total,
    dropdown_height_mm=dropdown,
    door_height_mm=0 if hb in FLOORPLAN_ONLY_HOUSEBUILDERS else door_height,
    num_doors=row["Doors"],
    door_width_mm=0 if hb in FLOORPLAN_ONLY_HOUSEBUILDERS else door_width,
)

st.pyplot(fig)
