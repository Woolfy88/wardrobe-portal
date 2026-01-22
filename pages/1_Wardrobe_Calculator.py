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
MAX_DOOR_HEIGHT = 2500

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
    # Defensive guards
    opening_width_mm = float(opening_width_mm) if opening_width_mm else 1.0
    opening_height_mm = float(opening_height_mm) if opening_height_mm else 1.0

    side_rel = side_thk_mm / opening_width_mm
    bottom_rel = bottom_thk_mm / opening_height_mm
    dropdown_rel = dropdown_height_mm / opening_height_mm if dropdown_height_mm else 0
    usable_height_rel = max(1 - bottom_rel - dropdown_rel, 0)
    door_rel = min(door_height_mm / opening_height_mm, usable_height_rel)

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.4, 1.4)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    # Outer opening
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))

    # Side liners + bottom liner
    ax.add_patch(Rectangle((0, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((1 - side_rel, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((side_rel, 0), 1 - 2 * side_rel, bottom_rel, alpha=0.25))

    # Dropdown (if any)
    if dropdown_rel:
        ax.add_patch(
            Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, alpha=0.25)
        )

    # Doors (dashed)
    door_width_rel = door_width_mm / opening_width_mm
    total_span = num_doors * door_width_rel
    available = 1 - 2 * side_rel
    if total_span > available and total_span > 0:
        door_width_rel *= available / total_span

    x = side_rel
    for _ in range(int(num_doors)):
        ax.add_patch(Rectangle((x, bottom_rel), door_width_rel, door_rel, fill=False, linestyle="--"))
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
        # ✅ IMPORTANT FIX: options= is keyword-only in newer Streamlit
        "Housebuilder": st.column_config.SelectboxColumn(
            "Housebuilder",
            options=HOUSEBUILDER_OPTIONS,
        ),
        "Door_System": st.column_config.SelectboxColumn(
            "Door system",
            options=DOOR_SYSTEM_OPTIONS,
        ),
        "Door_Style": st.column_config.SelectboxColumn(
            "Door style",
            options=DOOR_STYLE_OPTIONS,
        ),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (fixed only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
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
    dropdown_spec = float(rules["dropdown"])
    side_thk = float(rules["side_liner"])

    overlap_each = float(DOOR_STYLE_OVERLAP[row["Door_Style"]])
    overlaps_total = overlaps_count(doors) * overlap_each

    net_width = width - 2 * side_thk

    if row["Door_System"] == "Fixed 2223mm doors":
        door_h = FIXED_DOOR_HEIGHT
        dropdown_h = max(height - (BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT + door_h), 0)
        door_w = float(row["Fixed_Door_Width_mm"])
        span = doors * door_w
        issue = "✅ OK" if (net_width + overlaps_total) >= span else "🔴 Check"
    else:
        dropdown_h = dropdown_spec
        door_h = min(height - (BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT + dropdown_h), MAX_DOOR_HEIGHT)
        door_w = (net_width + overlaps_total) / doors
        span = net_width + overlaps_total
        issue = "✅ OK"

    return pd.Series(
        {
            "Door_Height_mm": int(round(door_h)),
            "Door_Width_mm": int(round(door_w)),
            "Doors_Used": doors,
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Liner_Thickness_mm": int(round(side_thk)),
            "Net_Width_mm": int(round(net_width)),
            "Door_Span_mm": int(round(span)),
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
if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
    st.info("Enter an opening above to generate the diagram.")
    st.stop()

# Installer-friendly banner
hb = row["Housebuilder"]
dropdown = row.get("Dropdown_Height_mm", 0)
side_liner = row.get("Side_Liner_Thickness_mm", 0)

if row["Door_System"] == "Made to measure doors":
    if hb in ["Story", "Strata", "Jones Homes"]:
        msg = f"""
        • Fit a **50mm dropdown** (fixed by the client’s specification)<br>
        • Side build-out is **50mm per side including the T-liner**<br>
        • Doors are made to suit what remains after dropdown and liners<br><br>
        **Do not adjust dropdown or side build-out on site**
        """
    else:
        msg = f"""
        • Fit a **{dropdown}mm dropdown** (fixed by the client’s specification)<br>
        • Fit **standard 18mm T-liners** each side<br>
        • Doors are made to measure to suit the net opening<br><br>
        **Do not change the dropdown height**
        """
else:
    msg = f"""
    • Doors are **fixed at 2223mm high**<br>
    • Dropdown is calculated from remaining height (currently **{dropdown}mm**)<br>
    • Side liners may increase to suit door widths (currently **{side_liner}mm each side**)<br><br>
    **Confirm dropdown and liner sizes before ordering**
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
    row["Side_Liner_Thickness_mm"],
    row["Dropdown_Height_mm"],
    row["Door_Height_mm"],
    row["Doors_Used"],
    row["Door_Width_mm"],
)

st.pyplot(fig)
