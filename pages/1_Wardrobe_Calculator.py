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

BASE_SIDE_LINER_THICKNESS = 18
T_LINER_50_PLUS_SIDE_18 = 68  # 50mm T-liner + 18mm side liner

MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400  # not used here but kept for compatibility

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

DOOR_SYSTEM_OPTIONS = [
    "Made to measure doors",
    "Fixed 2223mm doors",
]

# Client rules
# - Avant / Homes By Honey: dropdown 90, side liner 18 each side
# - Bloor: dropdown 108, side liner 18 each side
# - Story / Strata / Jones Homes: dropdown 50, liners are 68mm each side (50 T-liner + 18 side liner)
HOUSEBUILDER_RULES = {
    "Avant": {"dropdown": 90, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Homes By Honey": {"dropdown": 90, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Bloor": {"dropdown": 108, "side_liner": BASE_SIDE_LINER_THICKNESS},
    "Story": {"dropdown": 50, "side_liner": T_LINER_50_PLUS_SIDE_18},
    "Strata": {"dropdown": 50, "side_liner": T_LINER_50_PLUS_SIDE_18},
    "Jones Homes": {"dropdown": 50, "side_liner": T_LINER_50_PLUS_SIDE_18},
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


def side_thicknesses(hb: str, end_panels: int):
    """
    Returns (left_thk, right_thk) in mm.

    Default:
      - both sides = HOUSEBUILDER_RULES[hb]["side_liner"]

    End panels:
      - 0: no change
      - 1: one side becomes 18mm, the other remains housebuilder rule
      - 2: both sides become 18mm

    (We don't care left/right, so for 1 we arbitrarily apply 18mm on the right.)
    """
    base = int(HOUSEBUILDER_RULES[hb]["side_liner"])

    end_panels = int(end_panels or 0)
    end_panels = max(0, min(end_panels, 2))

    if end_panels == 2:
        return (BASE_SIDE_LINER_THICKNESS, BASE_SIDE_LINER_THICKNESS)
    if end_panels == 1:
        return (base, BASE_SIDE_LINER_THICKNESS)
    return (base, base)


# ============================================================
# DIAGRAM
# ============================================================
def draw_wardrobe_diagram(
    opening_width_mm,
    opening_height_mm,
    bottom_thk_mm,
    left_thk_mm,
    right_thk_mm,
    dropdown_height_mm,
    door_height_mm,
    num_doors,
    door_width_mm,
):
    if not opening_width_mm or not opening_height_mm:
        fig, ax = plt.subplots(figsize=(4, 7))
        ax.axis("off")
        return fig

    opening_width_mm = float(opening_width_mm)
    opening_height_mm = float(opening_height_mm)

    left_rel = left_thk_mm / opening_width_mm
    right_rel = right_thk_mm / opening_width_mm
    bottom_rel = bottom_thk_mm / opening_height_mm
    dropdown_rel = (dropdown_height_mm / opening_height_mm) if dropdown_height_mm else 0

    usable_height_rel = max(1 - bottom_rel - dropdown_rel, 0)
    door_rel = min((door_height_mm / opening_height_mm), usable_height_rel)

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.4, 1.4)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    # Opening outline
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))

    # Side liners and bottom liner
    ax.add_patch(Rectangle((0, bottom_rel), left_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((1 - right_rel, bottom_rel), right_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((left_rel, 0), 1 - left_rel - right_rel, bottom_rel, alpha=0.25))

    # Dropdown (top)
    if dropdown_rel:
        ax.add_patch(
            Rectangle(
                (left_rel, 1 - dropdown_rel),
                1 - left_rel - right_rel,
                dropdown_rel,
                alpha=0.25,
            )
        )

    # Doors (dashed)
    door_width_rel = float(door_width_mm) / opening_width_mm
    available = 1 - left_rel - right_rel
    total_span = num_doors * door_width_rel

    if total_span > available and total_span > 0:
        door_width_rel *= available / total_span

    x = left_rel
    for _ in range(int(num_doors)):
        ax.add_patch(
            Rectangle(
                (x, bottom_rel),
                door_width_rel,
                door_rel,
                fill=False,
                linestyle="--",
            )
        )
        x += door_width_rel

    return fig


# ============================================================
# EMPTY INPUT ROW
# ============================================================
EMPTY_ROW = pd.DataFrame(
    [
        {
            "Opening": "",
            "Width_mm": None,
            "Height_mm": None,
            "Doors": 2,
            "Housebuilder": HOUSEBUILDER_OPTIONS[0],
            "Door_System": DOOR_SYSTEM_OPTIONS[0],
            "Door_Style": DOOR_STYLE_OPTIONS[0],
            "Fixed_Door_Width_mm": 762,
            "End_Panels": 0,  # NEW: 0/1/2
        }
    ]
)


def reset_inputs():
    st.session_state["openings_df"] = EMPTY_ROW.copy()
    st.session_state["openings_table"] = EMPTY_ROW.copy()


if "openings_df" not in st.session_state:
    reset_inputs()

# ============================================================
# 1. ENTER OPENING
# ============================================================
st.subheader("1. Enter opening")

st.button("Reset opening", on_click=reset_inputs)

edited_df = st.data_editor(
    st.session_state["openings_df"],
    num_rows="fixed",
    key="openings_table",
    use_container_width=True,
    column_config={
        "Opening": st.column_config.TextColumn("Opening"),
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2, max_value=10),
        "Housebuilder": st.column_config.SelectboxColumn(
            "Housebuilder",
            options=HOUSEBUILDER_OPTIONS,
            required=True,
        ),
        "Door_System": st.column_config.SelectboxColumn(
            "Door system",
            options=DOOR_SYSTEM_OPTIONS,
            required=True,
        ),
        "Door_Style": st.column_config.SelectboxColumn(
            "Door style",
            options=DOOR_STYLE_OPTIONS,
            required=True,
        ),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (fixed only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
        ),
        "End_Panels": st.column_config.SelectboxColumn(
            "End panels (0/1/2)",
            options=[0, 1, 2],
        ),
    },
)

st.session_state["openings_df"] = edited_df

# ============================================================
# CALCULATION
# ============================================================
def calculate(row):
    if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
        return pd.Series({"Issue": "—"})

    width = float(row["Width_mm"])
    height = float(row["Height_mm"])
    doors = int(row["Doors"])

    hb = row["Housebuilder"]
    rules = HOUSEBUILDER_RULES[hb]
    dropdown_default = int(rules["dropdown"])

    end_panels = int(row.get("End_Panels", 0) or 0)
    left_thk, right_thk = side_thicknesses(hb, end_panels)

    overlaps = overlaps_count(doors) * DOOR_STYLE_OVERLAP[row["Door_Style"]]
    net_width = width - (left_thk + right_thk)

    if row["Door_System"] == "Fixed 2223mm doors":
        door_h = FIXED_DOOR_HEIGHT
        dropdown_h = max(height - (BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT + door_h), 0)

        door_w = int(row["Fixed_Door_Width_mm"])
        span_required = doors * door_w

        issue = "✅ OK" if (net_width + overlaps) >= span_required else "🔴 Check"
        span = span_required
    else:
        dropdown_h = dropdown_default
        door_h = min(height - (BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT + dropdown_h), MAX_DOOR_HEIGHT)
        door_w = (net_width + overlaps) / doors
        span = net_width + overlaps
        issue = "✅ OK"

    return pd.Series(
        {
            "Door_Height_mm": int(door_h),
            "Door_Width_mm": int(door_w),
            "Doors_Used": doors,
            "Dropdown_Height_mm": int(dropdown_h),
            "End_Panels": end_panels,
            "Left_Liner_Thickness_mm": int(left_thk),
            "Right_Liner_Thickness_mm": int(right_thk),
            "Net_Width_mm": int(net_width),
            "Door_Span_mm": int(span),
            "Issue": issue,
        }
    )


results = pd.concat([edited_df, edited_df.apply(calculate, axis=1)], axis=1)

# ============================================================
# 2. CALCULATED RESULTS (HIDDEN)
# ============================================================
st.subheader("2. Calculated results")
with st.expander("Show calculated table"):
    st.dataframe(results, use_container_width=True)

# ============================================================
# 3. VISUALISE OPENING
# ============================================================
st.subheader("3. Visualise opening")

row = results.iloc[0]
if pd.isna(row["Width_mm"]):
    st.info("Enter an opening above to generate the diagram.")
    st.stop()

hb = row["Housebuilder"]
dropdown = int(row["Dropdown_Height_mm"])
end_panels = int(row.get("End_Panels", 0) or 0)

left_thk = int(row["Left_Liner_Thickness_mm"])
right_thk = int(row["Right_Liner_Thickness_mm"])

# Installer-friendly banner
if row["Door_System"] == "Made to measure doors":
    if hb in ["Story", "Strata", "Jones Homes"]:
        msg = f"""
        • Fit a <b>50mm dropdown</b> (fixed by the client’s specification)<br>
        • Default liners are <b>68mm per side</b> (50mm T-liner + 18mm side liner)<br>
        • End panels selected: <b>{end_panels}</b> → liners are <b>{left_thk}mm</b> and <b>{right_thk}mm</b><br>
        • Doors are made to suit what remains after dropdown and liners<br><br>
        <b>Do not adjust dropdown or liner rules on site</b>
        """
    else:
        msg = f"""
        • Fit a <b>{dropdown}mm dropdown</b> (fixed by the client’s specification)<br>
        • Default liners are <b>18mm per side</b> unless end panels are selected<br>
        • End panels selected: <b>{end_panels}</b> → liners are <b>{left_thk}mm</b> and <b>{right_thk}mm</b><br>
        • Doors are made to measure to suit the net opening<br><br>
        <b>Do not change the dropdown height</b>
        """
else:
    msg = f"""
    • Doors are <b>fixed at 2223mm high</b><br>
    • Dropdown is calculated from remaining height (currently <b>{dropdown}mm</b>)<br>
    • Liners per side are currently <b>{left_thk}mm</b> and <b>{right_thk}mm</b> (end panels: {end_panels})<br><br>
    <b>Confirm dropdown and liner sizes before ordering</b>
    """

st.markdown(
    f"""
    <div style="border:2px solid #1f2937; background:#f9fafb;
                padding:16px; border-radius:10px; font-size:16px;">
        {msg}
    </div>
    """,
    unsafe_allow_html=True,
)

fig = draw_wardrobe_diagram(
    row["Width_mm"],
    row["Height_mm"],
    BOTTOM_LINER_THICKNESS,
    left_thk,
    right_thk,
    row["Dropdown_Height_mm"],
    row["Door_Height_mm"],
    row["Doors_Used"],
    row["Door_Width_mm"],
)

st.pyplot(fig)
