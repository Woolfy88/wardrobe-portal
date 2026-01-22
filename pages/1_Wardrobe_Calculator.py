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
    n = max(int(n), 1)
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
    opening_width_mm: float,
    opening_height_mm: float,
    bottom_thk_mm: float,
    side_thk_mm: float,
    dropdown_height_mm: float,
    door_height_mm: float,
    num_doors: int,
    door_width_mm: float,
):
    opening_width_mm = max(float(opening_width_mm), 1)
    opening_height_mm = max(float(opening_height_mm), 1)
    num_doors = max(int(num_doors), 1)
    side_thk_mm = max(float(side_thk_mm), 0)

    side_rel = side_thk_mm / opening_width_mm
    bottom_rel = bottom_thk_mm / opening_height_mm
    dropdown_rel = dropdown_height_mm / opening_height_mm if dropdown_height_mm else 0

    usable_rel_height = max(1 - bottom_rel - dropdown_rel, 0)
    raw_door_rel = door_height_mm / opening_height_mm if door_height_mm else 0
    door_h_rel = min(raw_door_rel, usable_rel_height)

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

    door_width_mm = max(float(door_width_mm), 0)
    door_width_rel = door_width_mm / opening_width_mm if opening_width_mm else 0
    available_span = 1 - 2 * side_rel
    total_span = num_doors * door_width_rel
    if total_span > available_span and total_span > 0:
        door_width_rel *= available_span / total_span

    x = side_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_width_rel, door_h_rel, fill=False, ls="--"))
        x += door_width_rel

    ax.text(0.5, -0.08, f"{int(opening_width_mm)}mm", ha="center")
    ax.text(-0.25, 0.5, f"{int(opening_height_mm)}mm", rotation=90, va="center")

    return fig


# ============================================================
# CALCULATION (single opening)
# ============================================================
def calculate(width, height, doors, hb, door_system, door_style, fixed_door_width_mm):
    height_stack = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT

    hb_rule = HOUSEBUILDER_RULES.get(hb, {"dropdown": 108, "side_liner": BASE_SIDE_LINER_THICKNESS})
    hb_dropdown = int(hb_rule["dropdown"])
    side_thk = float(hb_rule["side_liner"])

    overlap = int(DOOR_STYLE_OVERLAP.get(door_style, 35))
    total_overlap = overlaps_count(doors) * overlap

    width = float(width)
    height = float(height)
    doors = int(doors)

    if door_system == "Fixed 2223mm doors":
        door_height = FIXED_DOOR_HEIGHT
        # Only use fixed door width when Avant
        door_width = float(fixed_door_width_mm) if hb == "Avant" else 762.0
        if int(door_width) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_width = 762.0

        dropdown_raw = height - height_stack - door_height
        dropdown_h = max(min(dropdown_raw, MAX_DROPDOWN_LIMIT), 0)

        net_width = width - 2 * side_thk
        # door span and diff (installer check)
        door_span = doors * door_width
        span_diff = door_span - (net_width + total_overlap)

        height_status = "OK" if dropdown_raw >= 0 else "Opening too small for fixed door + bottom + trackset."
        if dropdown_raw > MAX_DROPDOWN_LIMIT:
            height_status = f"Dropdown required {int(dropdown_raw)}mm exceeds max {MAX_DROPDOWN_LIMIT}mm."

        width_status = "OK"
        if net_width <= 0:
            width_status = "Opening too small once side liners applied."

        issue = "✅ OK" if (height_status == "OK" and width_status == "OK" and abs(span_diff) <= 5) else "🔴 Check"

        return {
            "Width_mm": int(round(width)),
            "Height_mm": int(round(height)),
            "Doors": doors,
            "Housebuilder": hb,
            "Door_System": door_system,
            "Door_Style": door_style,
            "Door_Height_mm": int(round(door_height)),
            "Door_Width_mm": int(round(door_width)),
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Liner_Thickness_mm": round(side_thk, 1),
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": overlap,
            "Overlaps_Count": overlaps_count(doors),
            "Total_Overlap_mm": int(total_overlap),
            "Door_Span_mm": int(round(door_span)),
            "Span_Diff_mm": round(span_diff, 1),
            "Height_Status": height_status,
            "Width_Status": width_status,
            "Issue": issue,
            "Fixed_Door_Width_Used": "Yes (Avant)" if hb == "Avant" else "No",
            "Applied_Builder_Dropdown_mm": hb_dropdown,
            "Applied_Builder_SideLiner_mm": side_thk,
        }

    # Made to measure doors
    dropdown_h = min(hb_dropdown, MAX_DROPDOWN_LIMIT)
    net_width = width - 2 * side_thk

    raw_door_height = height - height_stack - dropdown_h
    if raw_door_height < 0:
        door_height = 0
        height_status = "Opening too small once bottom + trackset + dropdown applied."
    else:
        door_height = min(raw_door_height, MAX_DOOR_HEIGHT)
        height_status = "OK" if raw_door_height <= MAX_DOOR_HEIGHT else f"Door height capped at {MAX_DOOR_HEIGHT}mm."

    door_width = (net_width + total_overlap) / doors if doors > 0 else 0
    door_span = doors * door_width

    width_status = "OK" if net_width > 0 else "Opening too small once side liners applied."
    issue = "✅ OK" if (height_status == "OK" and width_status == "OK") else "🔴 Check"

    return {
        "Width_mm": int(round(width)),
        "Height_mm": int(round(height)),
        "Doors": doors,
        "Housebuilder": hb,
        "Door_System": door_system,
        "Door_Style": door_style,
        "Door_Height_mm": int(round(door_height)),
        "Door_Width_mm": int(round(door_width)),
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Liner_Thickness_mm": round(side_thk, 1),
        "Net_Width_mm": int(round(net_width)),
        "Overlap_Per_Meeting_mm": overlap,
        "Overlaps_Count": overlaps_count(doors),
        "Total_Overlap_mm": int(total_overlap),
        "Door_Span_mm": int(round(door_span)),
        "Span_Diff_mm": 0.0,
        "Height_Status": height_status,
        "Width_Status": width_status,
        "Issue": issue,
        "Fixed_Door_Width_Used": "N/A (MTM)",
        "Applied_Builder_Dropdown_mm": hb_dropdown,
        "Applied_Builder_SideLiner_mm": side_thk,
    }


# ============================================================
# MODE TOGGLE
# ============================================================
st.sidebar.subheader("View mode")
lite_mode = st.sidebar.toggle("Installer Lite mode", value=True)

# ============================================================
# LITE MODE UI
# ============================================================
if lite_mode:
    st.subheader("Installer inputs")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        width_mm = st.number_input("Width (mm)", min_value=300, step=10, value=None)
    with c2:
        height_mm = st.number_input("Height (mm)", min_value=300, step=10, value=None)
    with c3:
        doors = st.number_input("Doors", min_value=2, max_value=10, step=1, value=2)

    c4, c5, c6 = st.columns([1, 1, 1])
    with c4:
        hb = st.selectbox("Housebuilder", HOUSEBUILDER_OPTIONS, index=HOUSEBUILDER_OPTIONS.index("Bloor"))
    with c5:
        door_system = st.selectbox("Door system", DOOR_SYSTEM_OPTIONS, index=0)
    with c6:
        door_style = st.selectbox("Door style", DOOR_STYLE_OPTIONS, index=DOOR_STYLE_OPTIONS.index("Classic"))

    fixed_door_width_mm = 762
    if hb == "Avant":
        fixed_door_width_mm = st.selectbox("Fixed door width (Avant only)", FIXED_DOOR_WIDTH_OPTIONS, index=1)
    else:
        st.caption("Fixed door width is only used when Housebuilder = Avant.")

    if width_mm is None or height_mm is None:
        st.info("Enter width and height to generate the installer view.")
        st.stop()

    res = calculate(width_mm, height_mm, doors, hb, door_system, door_style, fixed_door_width_mm)

    # Banner (Markdown only)
    dropdown = int(res["Applied_Builder_Dropdown_mm"])
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

    # Installer summary (big + simple)
    st.subheader("Key outputs")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Door height (mm)", res["Door_Height_mm"])
    k2.metric("Door width each (mm)", res["Door_Width_mm"])
    k3.metric("Dropdown (mm)", res["Dropdown_Height_mm"])
    k4.metric("Side liner each (mm)", res["Side_Liner_Thickness_mm"])

    st.write("")
    s1, s2, s3 = st.columns(3)
    s1.metric("Net width (mm)", res["Net_Width_mm"])
    s2.metric("Total overlap (mm)", res["Total_Overlap_mm"])
    s3.metric("Issue", res["Issue"])

    if door_system == "Fixed 2223mm doors":
        st.caption(f"Span difference check: {res['Span_Diff_mm']}mm (aim ±5mm).  Fixed door width used: {res['Fixed_Door_Width_Used']}")

    # Diagram + short status
    st.subheader("Diagram")
    fig = draw_wardrobe_diagram(
        opening_width_mm=res["Width_mm"],
        opening_height_mm=res["Height_mm"],
        bottom_thk_mm=BOTTOM_LINER_THICKNESS,
        side_thk_mm=res["Side_Liner_Thickness_mm"],
        dropdown_height_mm=res["Dropdown_Height_mm"],
        door_height_mm=res["Door_Height_mm"],
        num_doors=res["Doors"],
        door_width_mm=res["Door_Width_mm"],
    )
    st.pyplot(fig)

    st.write("**Height status:**", res["Height_Status"])
    st.write("**Width status:**", res["Width_Status"])

    st.stop()

# ============================================================
# FULL MODE (your data editor approach)
# ============================================================
st.subheader("1. Enter opening (Full mode)")

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

def reset_full():
    st.session_state.df = DEFAULT.copy()

st.button("Reset opening", on_click=reset_full)
st.caption("Fixed door width is **only used when Housebuilder = Avant**.")

df = st.data_editor(
    st.session_state.df,
    num_rows="fixed",
    use_container_width=True,
    key="openings_table",
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

st.subheader("2. Calculated results")
if pd.isna(row["Width_mm"]) or pd.isna(row["Height_mm"]):
    st.info("Enter width and height to calculate.")
    st.stop()

fixed_w = row["Fixed_Door_Width_mm"]
res = calculate(
    row["Width_mm"], row["Height_mm"], int(row["Doors"]),
    row["Housebuilder"], row["Door_System"], row["Door_Style"],
    fixed_w
)

with st.expander("Show calculated table", expanded=False):
    st.dataframe(pd.DataFrame([res]), use_container_width=True)

csv = pd.DataFrame([res]).to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")

st.subheader("3. Visualise opening")

dropdown = int(res["Applied_Builder_Dropdown_mm"])
hb = res["Housebuilder"]
door_system = res["Door_System"]

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

fig = draw_wardrobe_diagram(
    opening_width_mm=res["Width_mm"],
    opening_height_mm=res["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_thk_mm=res["Side_Liner_Thickness_mm"],
    dropdown_height_mm=res["Dropdown_Height_mm"],
    door_height_mm=res["Door_Height_mm"],
    num_doors=res["Doors"],
    door_width_mm=res["Door_Width_mm"],
)
st.pyplot(fig)
