import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os

st.set_page_config(page_title="Wardrobe Calculator", layout="wide")
st.title("Wardrobe Door & Liner Calculator")

# -----------------------------
# SYSTEM CONSTANTS
# -----------------------------
BOTTOM_LINER_THICKNESS = 36
SIDE_LINER_THICKNESS = 18
MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

OVERLAP_TOLERANCES = {2: 75, 3: 150, 4: 150}
DEFAULT_FIXED_OVERLAP_TOLERANCE = 150

TOP_LINER_OPTIONS = {
    "108mm Dropdown": 108,
    "90mm Dropdown": 90,
    "No dropdown (0mm)": 0,
}

CUSTOM_DOOR_OVERLAP_MM = 25

DOOR_SYSTEM_OPTIONS = [
    "Custom (calculated panels)",
    "Fixed 2223mm doors",
]


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

    # Dropdown
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

    # Dimensions
    ax.annotate("", xy=(-0.20, 0), xytext=(-0.20, 1), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(-0.27, 0.5, f"{int(opening_height_mm)}mm", rotation=90, fontsize=9, ha="center", va="center")

    ax.annotate("", xy=(0, -0.06), xytext=(1, -0.06), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(0.5, -0.10, f"{int(opening_width_mm)}mm", fontsize=9, ha="center", va="top")

    return fig


# ============================================================
# CALCULATION FUNCTION
# ============================================================
def calculate_for_row(row: pd.Series) -> pd.Series:
    # defensively handle blanks coming from the editor
    width = max(float(row.get("Width_mm") or 1), 1)
    height = max(float(row.get("Height_mm") or 1), 1)
    doors = max(int(float(row.get("Doors") or 1)), 1)

    door_system = row.get("Door_System", DOOR_SYSTEM_OPTIONS[0])

    if door_system == "Fixed 2223mm doors":
        door_height = FIXED_DOOR_HEIGHT

        door_width = float(row.get("Fixed_Door_Width_mm") or 762)
        if door_width not in FIXED_DOOR_WIDTH_OPTIONS:
            door_width = 762

        dropdown_h_raw = height - BOTTOM_LINER_THICKNESS - door_height
        dropdown_h = dropdown_h_raw
        height_status = "OK"

        if dropdown_h_raw < 0:
            dropdown_h = 0
            height_status = "Opening too small for 2223mm door + 36mm bottom liner."
        elif dropdown_h_raw > MAX_DROPDOWN_LIMIT:
            dropdown_h = MAX_DROPDOWN_LIMIT
            height_status = f"Dropdown needed is {int(dropdown_h_raw)}mm – exceeds max {MAX_DROPDOWN_LIMIT}mm."

        tol = OVERLAP_TOLERANCES.get(doors, DEFAULT_FIXED_OVERLAP_TOLERANCE)

        door_span = doors * door_width
        side_thk_raw = (width - door_span + tol) / 2
        side_thk = max(side_thk_raw, 0.0)

        net_width = width - 2 * side_thk
        span_diff = door_span - (net_width + tol)
        build_out_per_side = max(side_thk - SIDE_LINER_THICKNESS, 0)

        issue_flag = "✅ OK" if height_status == "OK" else "🔴 Check height"

        return pd.Series(
            {
                "Door_Height_mm": int(round(door_height)),
                "Door_Width_mm": int(round(door_width)),
                "Doors_Used": int(doors),
                "Dropdown_Height_mm": int(round(dropdown_h)),
                "Side_Liner_Thickness_mm": round(side_thk, 1),
                "Required_Buildout_Per_Side_mm": round(build_out_per_side, 1),
                "Net_Width_mm": int(round(net_width)),
                "Door_Span_mm": int(round(door_span)),
                "Overlap_Tolerance_mm": int(round(tol)),
                "Span_Diff_mm": round(span_diff, 1),
                "Bottom_Liner_Length_mm": int(round(net_width)),
                "Side_Liner_Length_mm": int(round(height)),
                "Dropdown_Length_mm": int(round(net_width)),
                "Height_Status": height_status,
                "Issue": issue_flag,
            }
        )

    # Custom mode
    net_width = width - 2 * SIDE_LINER_THICKNESS

    option = row.get("Top_Liner_Option") or "108mm Dropdown"
    selected_dropdown = TOP_LINER_OPTIONS.get(option, 108)
    dropdown_h = min(selected_dropdown, MAX_DROPDOWN_LIMIT)

    base_usable_height = height - BOTTOM_LINER_THICKNESS
    raw_door_height = max(base_usable_height - dropdown_h, 0)

    dropdown_needed_for_max = base_usable_height - MAX_DOOR_HEIGHT

    if raw_door_height <= MAX_DOOR_HEIGHT:
        final_door_h = raw_door_height
        height_status = "OK"
    else:
        final_door_h = MAX_DOOR_HEIGHT
        if dropdown_needed_for_max <= MAX_DROPDOWN_LIMIT:
            height_status = f"Too tall – need about {int(dropdown_needed_for_max)}mm dropdown."
        else:
            height_status = f"Too tall even at max {MAX_DROPDOWN_LIMIT}mm dropdown."

    door_width = (net_width + (doors - 1) * CUSTOM_DOOR_OVERLAP_MM) / doors if doors > 0 else 0
    door_span = doors * door_width
    total_overlap = (doors - 1) * CUSTOM_DOOR_OVERLAP_MM

    issue_flag = "✅ OK" if height_status == "OK" else "🔴 Check height"

    return pd.Series(
        {
            "Door_Height_mm": int(round(final_door_h)),
            "Door_Width_mm": int(round(door_width)),
            "Doors_Used": int(doors),
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Liner_Thickness_mm": float(SIDE_LINER_THICKNESS),
            "Required_Buildout_Per_Side_mm": 0.0,
            "Net_Width_mm": int(round(net_width)),
            "Door_Span_mm": int(round(door_span)),
            "Overlap_Tolerance_mm": int(round(total_overlap)),
            "Span_Diff_mm": 0.0,
            "Bottom_Liner_Length_mm": int(round(net_width)),
            "Side_Liner_Length_mm": int(round(height)),
            "Dropdown_Length_mm": int(round(net_width)),
            "Height_Status": height_status,
            "Issue": issue_flag,
        }
    )


# ============================================================
# UI
# ============================================================
st.subheader("1. Enter openings")

# Reset button (clears the data editor's stored value)
if st.button("Reset table", type="secondary"):
    # data_editor stores its value under the widget key
    if "openings_table" in st.session_state:
        del st.session_state["openings_table"]
    st.rerun()

# Start blank (but with the correct columns)
blank_df = pd.DataFrame(
    columns=[
        "Job",
        "Opening",
        "Width_mm",
        "Height_mm",
        "Doors",
        "Door_System",
        "Top_Liner_Option",
        "Fixed_Door_Width_mm",
    ]
)

edited_df = st.data_editor(
    blank_df,
    num_rows="dynamic",
    use_container_width=True,
    key="openings_table",
    column_config={
        "Job": st.column_config.TextColumn("Job"),
        "Opening": st.column_config.TextColumn("Opening"),
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Number of doors", min_value=1, max_value=10, step=1),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Top_Liner_Option": st.column_config.SelectboxColumn(
            "Top liner option (custom only)",
            options=list(TOP_LINER_OPTIONS.keys()),
        ),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (mm) (fixed mode)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
        ),
    },
)

# --- Calculate once (no big calculated table) ---
if edited_df is not None and len(edited_df) > 0:
    # Drop completely empty rows (common when user adds a row but hasn't typed yet)
    working_df = edited_df.copy().dropna(how="all")

    if len(working_df) == 0:
        st.info("Add at least one opening to calculate sizes and view diagrams.")
    else:
        # Fill sensible defaults so partially-complete rows don't crash calc
        working_df["Doors"] = working_df["Doors"].fillna(1)
        working_df["Door_System"] = working_df["Door_System"].fillna(DOOR_SYSTEM_OPTIONS[0])
        working_df["Top_Liner_Option"] = working_df["Top_Liner_Option"].fillna("108mm Dropdown")
        working_df["Fixed_Door_Width_mm"] = working_df["Fixed_Door_Width_mm"].fillna(762)
        working_df["Job"] = working_df["Job"].fillna("")
        working_df["Opening"] = working_df["Opening"].fillna("")

        calcs = working_df.apply(calculate_for_row, axis=1)
        results_df = pd.concat([working_df.reset_index(drop=True), calcs], axis=1)

        if (results_df["Height_Status"] != "OK").any():
            st.warning("Some openings need checking. Review Height Status / Dropdown values.")

        csv = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")

        problem_rows = results_df[results_df["Issue"] != "✅ OK"]
        if not problem_rows.empty:
            st.markdown("#### Openings to check")
            st.dataframe(problem_rows, use_container_width=True)

        st.subheader("2. Visualise an opening")

        options = [
            f"{i}: {row.get('Job','')} – {row.get('Opening','')} ({row['Issue']}, {row['Door_System']})"
            for i, row in results_df.iterrows()
        ]
        selection = st.selectbox("Choose opening", options)
        idx = int(selection.split(":")[0])
        row = results_df.iloc[idx]

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

            if row["Door_System"] == "Fixed 2223mm doors":
                st.markdown("**Fixed-size dropdown example**")

                image_paths = [
                    "fixed_dropdown_example.jpg",
                    "assets/product_info/fixed_dropdown_example.jpg.JPG",
                ]

                for path in image_paths:
                    if os.path.exists(path):
                        st.image(path, use_container_width=True)
                        st.markdown(
                            """
                            <div style="
                                border: 1px solid #ddd;
                                padding: 8px 10px;
                                border-radius: 4px;
                                font-size: 0.9em;
                                background-color: #f9f9f9;
                                margin-top: 4px;
                            ">
                                Example photo of a fixed-size door dropdown.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        break
                else:
                    st.info(
                        "Dropdown example image not found. "
                        "Checked: fixed_dropdown_example.jpg and "
                        "assets/product_info/fixed_dropdown_example.jpg.JPG"
                    )

        with col2:
            st.markdown("#### Summary")
            st.write(f"**Door system:** {row['Door_System']}")
            st.write(f"**Issue:** {row['Issue']}")
            st.write(f"**Height status:** {row['Height_Status']}")
            st.write("---")
            st.write(f"**Doors:** {int(row['Doors_Used'])}")
            st.write(f"**Door height:** {int(row['Door_Height_mm'])} mm")
            st.write(f"**Door width (each):** {int(row['Door_Width_mm'])} mm")
            st.write(f"**Door span:** {int(row['Door_Span_mm'])} mm")
            st.write(f"**Net width:** {int(row['Net_Width_mm'])} mm")
            st.write(f"**Side liner thickness (each):** {row['Side_Liner_Thickness_mm']} mm")
            st.write(f"**Build-out per side:** {row['Required_Buildout_Per_Side_mm']} mm")
            st.write(f"**Overlap / tolerance:** {int(row['Overlap_Tolerance_mm'])} mm")
            if row["Door_System"] == "Fixed 2223mm doors":
                st.write(f"**Span difference:** {row['Span_Diff_mm']} mm")
            st.write(f"**Dropdown height:** {int(row['Dropdown_Height_mm'])} mm")

else:
    st.info("Add at least one opening to calculate sizes and view diagrams.")
