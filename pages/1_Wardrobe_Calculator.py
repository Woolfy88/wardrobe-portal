import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="Wardrobe Calculator", layout="wide")
st.header("Wardrobe Door & Liner Calculator")


# ============================================================
# SYSTEM CONSTANTS
# ============================================================
BOTTOM_LINER_THICKNESS = 36        # 2 x 18mm
TRACKSET_HEIGHT = 54               # trackset allowance (mm)
SIDE_LINER_THICKNESS = 18          # base liner board thickness (mm) for custom mode
MAX_DOOR_HEIGHT = 2500             # custom doors max height
MAX_DROPDOWN_LIMIT = 400           # absolute max dropdown allowed

# Fixed door system
FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]  # installer selects

# Door systems
DOOR_SYSTEM_OPTIONS = [
    "Custom (calculated panels)",
    "Fixed 2223mm doors",
]

# Custom dropdown options (fixed deductions)
TOP_LINER_OPTIONS = {
    "108mm Dropdown": 108,
    "90mm Dropdown": 90,
    "No dropdown (0mm)": 0,
}

# Door style overlaps (mm per meeting)
DOOR_STYLE_OVERLAP = {
    "Classic": 35,
    "Shaker": 75,
    "Heritage": 25,
    "Contour": 36,
}
DOOR_STYLE_OPTIONS = list(DOOR_STYLE_OVERLAP.keys())


def overlaps_count(num_doors: int) -> int:
    """
    Overlap-count rules (as agreed):
      - 2 doors -> 1 overlap
      - 3 doors -> 2 overlaps
      - 4 doors -> 2 overlaps
      - 5 doors -> 4 overlaps
    Fallback (if ever used): doors - 1
    """
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
    """Draw wardrobe front elevation with fixings notes and dimension arrows."""
    opening_width_mm = max(opening_width_mm, 1)
    opening_height_mm = max(opening_height_mm, 1)
    num_doors = max(int(num_doors), 1)
    side_thk_mm = max(float(side_thk_mm), 0)

    side_rel = side_thk_mm / opening_width_mm
    bottom_rel = bottom_thk_mm / opening_height_mm
    dropdown_rel = dropdown_height_mm / opening_height_mm if dropdown_height_mm > 0 else 0
    door_h_rel = door_height_mm / opening_height_mm if door_height_mm > 0 else 0

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.45, 1.45)
    ax.set_ylim(-0.25, 1.20)
    ax.set_aspect("equal")
    ax.axis("off")

    # Opening outline
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2))

    # Side liners
    ax.add_patch(Rectangle((0, bottom_rel), side_rel, 1 - bottom_rel, fill=True, alpha=0.25))
    ax.add_patch(Rectangle((1 - side_rel, bottom_rel), side_rel, 1 - bottom_rel, fill=True, alpha=0.25))

    # Bottom liner
    ax.add_patch(Rectangle((side_rel, 0), 1 - 2 * side_rel, bottom_rel, fill=True, alpha=0.25))

    # Dropdown (top liner)
    if dropdown_rel > 0:
        ax.add_patch(Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, fill=True, alpha=0.25))
        ax.annotate(
            "Drop-down to be fixed using\n"
            "metal stretcher brackets.\n"
            "2x into side liners and\n"
            "brackets every 600mm.",
            xy=(0.5, 1 - dropdown_rel / 2),
            xytext=(1.28, 1 - dropdown_rel / 2),
            fontsize=8,
            ha="left",
            va="center",
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="black", lw=1),
            arrowprops=dict(arrowstyle="->", lw=1.3),
        )

    # Doors (dashed)
    door_width_mm = max(float(door_width_mm), 0)
    door_width_rel = door_width_mm / opening_width_mm if opening_width_mm > 0 else 0

    total_doors_span = num_doors * door_width_rel
    available_span = 1 - 2 * side_rel
    if total_doors_span > available_span and total_doors_span > 0:
        door_width_rel *= (available_span / total_doors_span)

    x_start = side_rel
    for _ in range(num_doors):
        ax.add_patch(
            Rectangle(
                (x_start, bottom_rel),
                door_width_rel,
                door_h_rel,
                fill=False,
                linestyle="--",
                linewidth=1,
            )
        )
        x_start += door_width_rel

    # Side liner fixing note (NO ARROW)
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

    # Sub-cill note (NO ARROW)
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

    # Bottom track note (WITH ARROW)
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

    # Dimension arrows + mm labels
    ax.annotate("", xy=(-0.20, 0), xytext=(-0.20, 1), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(-0.27, 0.5, f"{int(opening_height_mm)}mm", rotation=90, fontsize=9, ha="center", va="center")

    ax.annotate("", xy=(0, -0.06), xytext=(1, -0.06), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(0.5, -0.10, f"{int(opening_width_mm)}mm", fontsize=9, ha="center", va="top")

    return fig


# ============================================================
# DEFAULT DATA (ONE ROW ONLY)
# ============================================================
DEFAULT_DATA = pd.DataFrame([
    {
        "Job": "Job 1",
        "Opening": "Wardrobe A",
        "Width_mm": 2200,
        "Height_mm": 2600,
        "Doors": 3,
        "Door_System": "Custom (calculated panels)",
        "Door_Style": "Classic",
        "Top_Liner_Option": "108mm Dropdown",   # custom only
        "Fixed_Door_Width_mm": 762,             # fixed only
    }
])

if "openings_df" not in st.session_state:
    st.session_state["openings_df"] = DEFAULT_DATA.copy()


# ============================================================
# SIDEBAR CONSTANTS
# ============================================================
st.sidebar.subheader("System constants")
st.sidebar.write(f"Bottom liner: **{BOTTOM_LINER_THICKNESS} mm**")
st.sidebar.write(f"Trackset allowance: **{TRACKSET_HEIGHT} mm**")
st.sidebar.write(f"Base side liner thickness: **{SIDE_LINER_THICKNESS} mm** (custom mode)")
st.sidebar.write(f"Max custom door height: **{MAX_DOOR_HEIGHT} mm**")
st.sidebar.write(f"Max dropdown allowed: **{MAX_DROPDOWN_LIMIT} mm**")
st.sidebar.write(f"Fixed door height: **{FIXED_DOOR_HEIGHT} mm**")


# ============================================================
# TABLE EDITOR (ONE ROW)
# ============================================================
st.subheader("1. Enter opening")

edited_df = st.data_editor(
    st.session_state["openings_df"],
    num_rows="fixed",  # one row only
    use_container_width=True,
    key="openings_table",
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Number of doors", min_value=2, max_value=10, step=1),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "Top_Liner_Option": st.column_config.SelectboxColumn(
            "Top liner option (custom only)",
            options=list(TOP_LINER_OPTIONS.keys()),
            default="108mm Dropdown",
        ),
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
    width = max(float(row["Width_mm"]), 1)
    height = max(float(row["Height_mm"]), 1)
    doors = max(int(row["Doors"]), 1)

    door_system = row.get("Door_System", DOOR_SYSTEM_OPTIONS[0])
    door_style = row.get("Door_Style", "Classic")
    overlap_per_meeting = int(DOOR_STYLE_OVERLAP.get(door_style, 35))
    n_overlaps = overlaps_count(doors)
    total_overlap = n_overlaps * overlap_per_meeting

    # Common: bottom liner length is based on net width (varies by system)
    # Height stack always includes bottom liner + trackset
    height_stack_base = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT

    if door_system == "Fixed 2223mm doors":
        # Door height fixed; dropdown is what "fills the rest"
        door_height = FIXED_DOOR_HEIGHT

        door_width = float(row.get("Fixed_Door_Width_mm", 762))
        if int(door_width) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_width = 762

        dropdown_raw = height - height_stack_base - door_height
        height_status = "OK"
        dropdown_h = dropdown_raw

        if dropdown_raw < 0:
            dropdown_h = 0
            height_status = "Opening too small (height) for 2223mm door + bottom liner + trackset."
        elif dropdown_raw > MAX_DROPDOWN_LIMIT:
            dropdown_h = MAX_DROPDOWN_LIMIT
            height_status = f"Dropdown needed is {int(dropdown_raw)}mm – exceeds max {MAX_DROPDOWN_LIMIT}mm."

        door_span = doors * door_width

        # Solve required side-liner thickness (each side) to suit door span and total overlap
        # Target: net_width + total_overlap == door_span
        # net_width = width - 2*side_thk  => width - 2*side_thk + total_overlap == door_span
        # => side_thk = (width + total_overlap - door_span) / 2
        side_thk = (width + total_overlap - door_span) / 2
        # Allow zero minimum (can't have negative liner thickness)
        width_status = "OK"
        if side_thk < 0:
            side_thk = 0
            width_status = "Opening too small (width) for selected fixed doors + overlaps."

        net_width = width - 2 * side_thk
        span_diff = door_span - (net_width + total_overlap)  # should be ~0 when solved, unless clamped

        build_out_per_side = side_thk  # required build-out per side (variable by design)
        issue_flag = "✅ OK" if (height_status == "OK" and width_status == "OK") else "🔴 Check"

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
            "Issue": issue_flag,
        })

    # ==========================
    # Custom (Calculated Panels)
    # ==========================
    side_thk = SIDE_LINER_THICKNESS
    net_width = width - 2 * side_thk

    option = row.get("Top_Liner_Option", "108mm Dropdown")
    dropdown_selected = int(TOP_LINER_OPTIONS.get(option, 108))
    dropdown_h = min(dropdown_selected, MAX_DROPDOWN_LIMIT)

    # Door height uses height stack including trackset
    raw_door_height = height - height_stack_base - dropdown_h

    dropdown_needed_for_max = (height - height_stack_base) - MAX_DOOR_HEIGHT

    if raw_door_height <= MAX_DOOR_HEIGHT:
        final_door_h = raw_door_height
        height_status = "OK"
    else:
        final_door_h = MAX_DOOR_HEIGHT
        if dropdown_needed_for_max <= MAX_DROPDOWN_LIMIT:
            height_status = f"Too tall – need about {int(dropdown_needed_for_max)}mm dropdown."
        else:
            height_status = f"Too tall even at max {MAX_DROPDOWN_LIMIT}mm dropdown."

    if raw_door_height < 0:
        final_door_h = 0
        height_status = "Opening too small (height) once bottom liner + trackset + dropdown applied."

    # Width: style-aware total overlap rules
    # Door width = (net_width + total_overlap) / doors
    door_width = (net_width + total_overlap) / doors if doors > 0 else 0
    door_span = doors * door_width  # equals net_width + total_overlap

    issue_flag = "✅ OK" if height_status == "OK" else "🔴 Check"

    return pd.Series({
        "Door_Height_mm": int(round(final_door_h)),
        "Door_Width_mm": int(round(door_width)),
        "Doors_Used": int(doors),
        "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
        "Overlaps_Count": int(n_overlaps),
        "Total_Overlap_mm": int(total_overlap),
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Liner_Thickness_mm": float(side_thk),
        "Required_Liner_Buildout_Per_Side_mm": 0.0,
        "Net_Width_mm": int(round(net_width)),
        "Door_Span_mm": int(round(door_span)),
        "Span_Diff_mm": 0.0,
        "Bottom_Liner_Length_mm": int(round(net_width)),
        "Side_Liner_Length_mm": int(round(height)),
        "Dropdown_Length_mm": int(round(net_width)),
        "Height_Status": height_status,
        "Width_Status": "OK",
        "Issue": issue_flag,
    })


# ============================================================
# RESULTS
# ============================================================
st.subheader("2. Calculated results")

calcs = edited_df.apply(calculate_for_row, axis=1)
results_df = pd.concat([edited_df.reset_index(drop=True), calcs.reset_index(drop=True)], axis=1)

st.dataframe(results_df, use_container_width=True)

if (results_df["Issue"] != "✅ OK").any():
    st.warning("One or more checks failed. Review Height/Width status and span difference.")

csv = results_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")


# ============================================================
# VISUALISATION
# ============================================================
st.subheader("3. Visualise opening")

row = results_df.iloc[0]

fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_thk_mm=row["Side_Liner_Thickness_mm"],
    dropdown_height_mm=row["Dropdown_Height_mm"],
    door_height_mm=row["Door_Height_mm"],
    num_doors=row["Doors_Used"],
    door_width_mm=row["Door_Width_mm"],
)

col1, col2 = st.columns([2, 1])

with col1:
    st.pyplot(fig)

with col2:
    st.markdown("#### Summary")
    st.write(f"**Door system:** {row['Door_System']}")
    st.write(f"**Door style:** {row['Door_Style']}")
    st.write(f"**Issue:** {row['Issue']}")
    st.write(f"**Height status:** {row['Height_Status']}")
    st.write(f"**Width status:** {row['Width_Status']}")
    st.write("---")
    st.write(f"**Doors:** {int(row['Doors_Used'])}")
    st.write(f"**Door height:** {int(row['Door_Height_mm'])} mm")
    st.write(f"**Door width (each):** {int(row['Door_Width_mm'])} mm")
    st.write(f"**Overlap per meeting:** {int(row['Overlap_Per_Meeting_mm'])} mm")
    st.write(f"**Overlaps count:** {int(row['Overlaps_Count'])}")
    st.write(f"**Total overlap applied:** {int(row['Total_Overlap_mm'])} mm")
    st.write("---")
    st.write(f"**Net width:** {int(row['Net_Width_mm'])} mm")
    st.write(f"**Door span:** {int(row['Door_Span_mm'])} mm")
    if row["Door_System"] == "Fixed 2223mm doors":
        st.write(f"**Span difference:** {row['Span_Diff_mm']} mm")
        st.write(f"**Side liner thickness (each):** {row['Side_Liner_Thickness_mm']} mm")
        st.write(f"**Required build-out per side:** {row['Required_Liner_Buildout_Per_Side_mm']} mm")
    else:
        st.write(f"**Side liner thickness (each):** {SIDE_LINER_THICKNESS} mm")
    st.write("---")
    st.write(f"**Dropdown height:** {int(row['Dropdown_Height_mm'])} mm")
    st.caption(f"Height stack includes bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm).")
