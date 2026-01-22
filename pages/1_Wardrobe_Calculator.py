import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ============================================================
# SETTINGS
# ============================================================
ENABLE_PIN = False  # set True to enable PIN
CALCULATOR_PIN = "1966"

# IMPORTANT: set_page_config must be the first Streamlit command
st.set_page_config(page_title="Wardrobe Calculator", layout="wide")

# ============================================================
# PAGE-LEVEL PIN
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


def overlaps_count(num_doors: int) -> int:
    n = max(int(num_doors), 1)
    if n == 2:
        return 1
    if n in (3, 4):
        return 2
    if n == 5:
        return 4
    return max(n - 1, 0)


# ============================================================
# DIAGRAM DRAWING FUNCTION
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
    dropdown_rel = dropdown_height_mm / opening_height_mm if dropdown_height_mm > 0 else 0

    usable_rel_height = max(1 - bottom_rel - dropdown_rel, 0)
    raw_door_rel = door_height_mm / opening_height_mm if door_height_mm > 0 else 0
    door_h_rel = min(raw_door_rel, usable_rel_height)

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.45, 1.45)
    ax.set_ylim(-0.25, 1.20)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2))

    ax.add_patch(Rectangle((0, bottom_rel), side_rel, 1 - bottom_rel, fill=True, alpha=0.25))
    ax.add_patch(Rectangle((1 - side_rel, bottom_rel), side_rel, 1 - bottom_rel, fill=True, alpha=0.25))

    ax.add_patch(Rectangle((side_rel, 0), 1 - 2 * side_rel, bottom_rel, fill=True, alpha=0.25))

    if dropdown_rel > 0:
        ax.add_patch(Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, fill=True, alpha=0.25))

    door_width_mm = max(float(door_width_mm), 0)
    door_width_rel = door_width_mm / opening_width_mm if opening_width_mm > 0 else 0

    total_doors_span = num_doors * door_width_rel
    available_span = 1 - 2 * side_rel
    if total_doors_span > available_span and total_doors_span > 0:
        door_width_rel *= (available_span / total_doors_span)

    x_start = side_rel
    for _ in range(num_doors):
        ax.add_patch(
            Rectangle((x_start, bottom_rel), door_width_rel, door_h_rel, fill=False, linestyle="--", linewidth=1)
        )
        x_start += door_width_rel

    ax.annotate(
        "Side liners fixings -\n"
        "200mm in from either end\n"
        "and then two in the middle\n"
        "of the liner (equally spaced),\n"
        "so 4x fixings in total.",
        xy=(side_rel / 2, 0.5),
        xytext=(-0.34, 0.72),
        fontsize=8,
        ha="right",
        va="center",
        bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="black", lw=1),
    )

    ax.annotate(
        "Sub-cill to floor - fixing every 500mm\n"
        "Sub-cill to carpet - fixing every 200mm",
        xy=(0.5, bottom_rel / 2),
        xytext=(0.5, -0.20),
        fontsize=8,
        ha="center",
        va="top",
        bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="black", lw=1),
    )

    ax.annotate(
        "Bottom track fixing - 50-80mm in from ends\n"
        "and then every 800mm of track span.",
        xy=(0.5, bottom_rel + 0.02),
        xytext=(1.28, bottom_rel + 0.18),
        fontsize=8,
        ha="left",
        va="center",
        bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="black", lw=1),
        arrowprops=dict(arrowstyle="->", lw=1.3),
    )

    ax.annotate("", xy=(-0.20, 0), xytext=(-0.20, 1), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(-0.27, 0.5, f"{int(opening_height_mm)}mm", rotation=90, fontsize=9, ha="center", va="center")

    ax.annotate("", xy=(0, -0.06), xytext=(1, -0.06), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(0.5, -0.10, f"{int(opening_width_mm)}mm", fontsize=9, ha="center", va="top")

    return fig


# ============================================================
# DEFAULT / EMPTY INPUT TABLE (START BLANK)
# ============================================================
DEFAULT_EMPTY = pd.DataFrame([{
    "Opening": "",
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": HOUSEBUILDER_OPTIONS[0],
    "Door_System": DOOR_SYSTEM_OPTIONS[0],
    "Door_Style": DOOR_STYLE_OPTIONS[0],
    "Fixed_Door_Width_mm": 762,
}])


def reset_inputs():
    st.session_state["openings_df"] = DEFAULT_EMPTY.copy()
    if "openings_table" in st.session_state:
        st.session_state["openings_table"] = DEFAULT_EMPTY.copy()


if "openings_df" not in st.session_state:
    reset_inputs()

# ============================================================
# SIDEBAR CONSTANTS
# ============================================================
st.sidebar.subheader("System constants")
st.sidebar.write(f"Bottom liner: **{BOTTOM_LINER_THICKNESS} mm**")
st.sidebar.write(f"Trackset allowance: **{TRACKSET_HEIGHT} mm**")
st.sidebar.write(f"Base side liner thickness: **{BASE_SIDE_LINER_THICKNESS} mm** (made-to-measure mode)")
st.sidebar.write(f"Max custom door height: **{MAX_DOOR_HEIGHT} mm**")
st.sidebar.write(f"Max dropdown allowed: **{MAX_DROPDOWN_LIMIT} mm**")
st.sidebar.write(f"Fixed door height: **{FIXED_DOOR_HEIGHT} mm**")

# ============================================================
# 1. ENTER OPENING (START BLANK + RESET BUTTON)
# ============================================================
st.subheader("1. Enter opening")

c_reset, _ = st.columns([1, 5])
with c_reset:
    st.button("Reset opening", on_click=reset_inputs, use_container_width=True)

edited_df = st.data_editor(
    st.session_state["openings_df"],
    num_rows="fixed",
    use_container_width=True,
    key="openings_table",
    column_config={
        "Opening": st.column_config.TextColumn("Opening"),
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2, max_value=10, step=1),
        "Housebuilder": st.column_config.SelectboxColumn("Housebuilder", options=HOUSEBUILDER_OPTIONS),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (mm) (fixed only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
            default=762,
        ),
    },
)

st.session_state["openings_df"] = edited_df

# ============================================================
# CALCULATION FUNCTION
# ============================================================
def calculate_for_row(row: pd.Series) -> pd.Series:
    if pd.isna(row.get("Width_mm")) or pd.isna(row.get("Height_mm")):
        return pd.Series({
            "Issue": "—",
            "Height_Status": "Enter width + height to calculate.",
            "Width_Status": "Enter width + height to calculate.",
        })

    width = max(float(row["Width_mm"]), 1)
    height = max(float(row["Height_mm"]), 1)
    doors = max(int(row.get("Doors", 2)), 1)

    hb = row.get("Housebuilder", HOUSEBUILDER_OPTIONS[0])
    hb_rule = HOUSEBUILDER_RULES.get(hb, {"dropdown": 108, "side_liner": BASE_SIDE_LINER_THICKNESS})
    hb_dropdown = int(hb_rule["dropdown"])
    hb_side_liner = float(hb_rule["side_liner"])

    door_system = row.get("Door_System", DOOR_SYSTEM_OPTIONS[0])
    door_style = row.get("Door_Style", DOOR_STYLE_OPTIONS[0])

    overlap_per_meeting = int(DOOR_STYLE_OVERLAP.get(door_style, 35))
    n_overlaps = overlaps_count(doors)
    total_overlap = n_overlaps * overlap_per_meeting

    height_stack_base = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT

    if door_system == "Fixed 2223mm doors":
        door_height = FIXED_DOOR_HEIGHT

        door_width = float(row.get("Fixed_Door_Width_mm", 762))
        if int(door_width) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_width = 762

        dropdown_raw = height - height_stack_base - door_height
        dropdown_h = dropdown_raw
        height_status = "OK"
        if dropdown_raw < 0:
            dropdown_h = 0
            height_status = "Opening too small (height) for fixed door + bottom liner + trackset."
        elif dropdown_raw > MAX_DROPDOWN_LIMIT:
            dropdown_h = MAX_DROPDOWN_LIMIT
            height_status = f"Dropdown needed is {int(dropdown_raw)}mm – exceeds max {MAX_DROPDOWN_LIMIT}mm."

        door_span = doors * door_width

        if hb_side_liner != BASE_SIDE_LINER_THICKNESS:
            side_thk = hb_side_liner
            width_status = "OK (builder side liners locked)"
            net_width = width - 2 * side_thk
            span_diff = door_span - (net_width + total_overlap)
            if abs(span_diff) > 5:
                width_status = "Check width (builder side liners locked)"
        else:
            side_thk = (width + total_overlap - door_span) / 2
            width_status = "OK"
            if side_thk < 0:
                side_thk = 0
                width_status = "Opening too small (width) for selected fixed doors + overlaps."
            net_width = width - 2 * side_thk
            span_diff = door_span - (net_width + total_overlap)

        build_out_per_side = side_thk
        issue_flag = "✅ OK" if (height_status == "OK" and width_status.startswith("OK")) else "🔴 Check"

        return pd.Series({
            "Door_Height_mm": int(round(door_height)),
            "Door_Width_mm": int(round(door_width)),
            "Doors_Used": int(doors),
            "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
            "Overlaps_Count": int(n_overlaps),
            "Total_Overlap_mm": int(total_overlap),
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Liner_Thickness_mm": round(side_thk, 1),
            "Required_Liner_Buildout_Per_Side_mm": round(build_out_per_side, 1),
            "Net_Width_mm": int(round(net_width)),
            "Door_Span_mm": int(round(door_span)),
            "Span_Diff_mm": round(span_diff, 1),
            "Bottom_Liner_Length_mm": int(round(net_width)),
            "Side_Liner_Length_mm": int(round(height)),
            "Dropdown_Length_mm": int(round(net_width)),
            "Height_Status": height_status,
            "Width_Status": width_status,
            "Applied_Builder_Dropdown_mm": hb_dropdown,
            "Applied_Builder_SideLiner_mm": hb_side_liner,
            "Issue": issue_flag,
        })

    # Made to measure doors
    dropdown_h = min(hb_dropdown, MAX_DROPDOWN_LIMIT)
    side_thk = hb_side_liner
    net_width = width - 2 * side_thk

    raw_door_height = height - height_stack_base - dropdown_h
    dropdown_needed_for_max = (height - height_stack_base) - MAX_DOOR_HEIGHT

    if 0 <= raw_door_height <= MAX_DOOR_HEIGHT:
        final_door_h = raw_door_height
        height_status = "OK"
    elif raw_door_height < 0:
        final_door_h = 0
        height_status = "Opening too small (height) once bottom liner + trackset + dropdown applied."
    else:
        final_door_h = MAX_DOOR_HEIGHT
        if dropdown_needed_for_max <= MAX_DROPDOWN_LIMIT:
            height_status = f"Too tall – need about {int(dropdown_needed_for_max)}mm dropdown."
        else:
            height_status = f"Too tall even at max {MAX_DROPDOWN_LIMIT}mm dropdown."

    door_width = (net_width + total_overlap) / doors if doors > 0 else 0
    door_span = doors * door_width

    width_status = "OK"
    if net_width <= 0:
        width_status = "Opening too small (width) once side liners applied."

    issue_flag = "✅ OK" if (height_status == "OK" and width_status == "OK") else "🔴 Check"

    return pd.Series({
        "Door_Height_mm": int(round(final_door_h)),
        "Door_Width_mm": int(round(door_width)),
        "Doors_Used": int(doors),
        "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
        "Overlaps_Count": int(n_overlaps),
        "Total_Overlap_mm": int(total_overlap),
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Liner_Thickness_mm": round(side_thk, 1),
        "Required_Liner_Buildout_Per_Side_mm": round(max(side_thk - BASE_SIDE_LINER_THICKNESS, 0), 1),
        "Net_Width_mm": int(round(net_width)),
        "Door_Span_mm": int(round(door_span)),
        "Span_Diff_mm": 0.0,
        "Bottom_Liner_Length_mm": int(round(net_width)),
        "Side_Liner_Length_mm": int(round(height)),
        "Dropdown_Length_mm": int(round(net_width)),
        "Height_Status": height_status,
        "Width_Status": width_status,
        "Applied_Builder_Dropdown_mm": hb_dropdown,
        "Applied_Builder_SideLiner_mm": hb_side_liner,
        "Issue": issue_flag,
    })


# ============================================================
# 2. CALCULATED RESULTS (HIDDEN BY DEFAULT)
# ============================================================
st.subheader("2. Calculated results")

calcs = edited_df.apply(calculate_for_row, axis=1)
results_df = pd.concat([edited_df.reset_index(drop=True), calcs.reset_index(drop=True)], axis=1)

with st.expander("Show calculated table", expanded=False):
    st.dataframe(results_df, use_container_width=True)

if "Issue" in results_df.columns and (results_df["Issue"] == "🔴 Check").any():
    st.warning("One or more checks failed. Review Height/Width status and span difference.")

if results_df.get("Issue", pd.Series(["—"])).iloc[0] != "—":
    csv = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")

# ============================================================
# 3. VISUALISE OPENING
# ============================================================
st.subheader("3. Visualise opening")

row = results_df.iloc[0]

if pd.isna(row.get("Width_mm")) or pd.isna(row.get("Height_mm")):
    st.info("Enter width and height in Section 1 to generate results and the diagram.")
    st.stop()

hb = row["Housebuilder"]
door_system = row["Door_System"]
dropdown = int(row.get("Dropdown_Height_mm", 0))

if door_system == "Made to measure doors":
    if hb in ["Story", "Strata", "Jones Homes"]:
        banner_html = f"""
        <div style="font-size:22px; font-weight:900; margin-bottom:8px;">
            CUSTOMER SPECIFICATION – MADE TO MEASURE DOORS
        </div>
        • Housebuilder <b>{hb}</b> mandates a <b>fixed 50mm dropdown</b><br>
        • <b>Total side build-out per side is fixed at 50mm</b><br>
        • This 50mm build-out <b>includes the 18mm T-liner</b><br>
        • Door sizes are calculated to suit the remaining opening<br><br>
        <b>No adjustment is permitted on dropdown or side build-out.</b>
        """
    else:
        banner_html = f"""
        <div style="font-size:22px; font-weight:900; margin-bottom:8px;">
            CUSTOMER SPECIFICATION – MADE TO MEASURE DOORS
        </div>
        • Housebuilder <b>{hb}</b> mandates a <b>fixed {dropdown}mm dropdown</b><br>
        • Standard <b>18mm T-liners</b> are applied per side<br>
        • Door sizes are calculated to suit the net opening<br><br>
        <b>Dropdown is fixed by the builder and must not be altered.</b>
        """
else:
    banner_html = f"""
    <div style="font-size:22px; font-weight:900; margin-bottom:8px;">
        CUSTOMER SPECIFICATION – FIXED 2223mm DOORS
    </div>
    • Doors are supplied at a <b>fixed height of 2223mm</b><br>
    • Dropdown is <b>calculated</b> from the remaining opening height<br>
    • Side liner build-out may <b>increase</b> to suit door widths and overlaps<br>
    • Housebuilder dropdown rules do <b>not</b> apply in this mode<br><br>
    <b>Final dropdown and liner sizes must be checked before order.</b>
    """

st.markdown(
    f"""
    <div style="
        border: 2px solid #1f2937;
        background-color: #f9fafb;
        padding: 16px;
        margin-bottom: 18px;
        border-radius: 10px;
    ">
        {banner_html}
    </div>
    """,
    unsafe_allow_html=True
)

fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_thk_mm=row.get("Side_Liner_Thickness_mm", 0),
    dropdown_height_mm=row.get("Dropdown_Height_mm", 0),
    door_height_mm=row.get("Door_Height_mm", 0),
    num_doors=row.get("Doors_Used", 2),
    door_width_mm=row.get("Door_Width_mm", 0),
)

col1, col2 = st.columns([2, 1])

with col1:
    st.pyplot(fig)

with col2:
    st.markdown("#### Summary")
    st.write(f"**Opening:** {row.get('Opening','')}")
    st.write(f"**Housebuilder:** {row['Housebuilder']}")
    st.write(f"**Door system:** {row['Door_System']}")
    st.write(f"**Door style:** {row['Door_Style']}")
    st.write(f"**Issue:** {row.get('Issue', '—')}")
    st.write(f"**Height status:** {row.get('Height_Status', '')}")
    st.write(f"**Width status:** {row.get('Width_Status', '')}")
    st.write("---")
    st.write(f"**Doors:** {int(row.get('Doors_Used', 0))}")
    st.write(f"**Door height:** {int(row.get('Door_Height_mm', 0))} mm")
    st.write(f"**Door width (each):** {int(row.get('Door_Width_mm', 0))} mm")
    st.write("---")
    st.write(f"**Overlap per meeting:** {int(row.get('Overlap_Per_Meeting_mm', 0))} mm")
    st.write(f"**Overlaps count:** {int(row.get('Overlaps_Count', 0))}")
    st.write(f"**Total overlap applied:** {int(row.get('Total_Overlap_mm', 0))} mm")
    st.write("---")
    st.write(f"**Net width:** {int(row.get('Net_Width_mm', 0))} mm")
    st.write(f"**Door span:** {int(row.get('Door_Span_mm', 0))} mm")
    if row["Door_System"] == "Fixed 2223mm doors":
        st.write(f"**Span difference:** {row.get('Span_Diff_mm', 0)} mm")
    st.write("---")
    st.write(f"**Side liner thickness (each):** {row.get('Side_Liner_Thickness_mm', 0)} mm")
    st.write(f"**Dropdown height:** {int(row.get('Dropdown_Height_mm', 0))} mm")
    st.caption(f"Height stack includes bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm).")
