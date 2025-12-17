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
    "Made To Measure",
    "Fixed 2223mm doors",
]


# ============================================================
# DIAGRAM DRAWING FUNCTION
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

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2))

    ax.add_patch(Rectangle((0, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((1 - side_rel, bottom_rel), side_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((side_rel, 0), 1 - 2 * side_rel, bottom_rel, alpha=0.25))

    if dropdown_rel > 0:
        ax.add_patch(Rectangle((side_rel, 1 - dropdown_rel), 1 - 2 * side_rel, dropdown_rel, alpha=0.25))

    door_width_rel = door_width_mm / opening_width_mm if opening_width_mm else 0
    available_span = 1 - 2 * side_rel
    if num_doors * door_width_rel > available_span:
        door_width_rel *= available_span / (num_doors * door_width_rel)

    x = side_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_width_rel, door_h_rel, fill=False, linestyle="--"))
        x += door_width_rel

    ax.text(0.5, -0.10, f"{int(opening_width_mm)}mm", ha="center")
    ax.text(-0.30, 0.5, f"{int(opening_height_mm)}mm", rotation=90, va="center")

    return fig


# ============================================================
# CALCULATION FUNCTION
# ============================================================
def calculate_for_row(row: pd.Series) -> pd.Series:
    width = max(float(row.get("Width_mm") or 1), 1)
    height = max(float(row.get("Height_mm") or 1), 1)
    doors = max(int(float(row.get("Doors") or 1)), 1)
    door_system = row.get("Door_System", DOOR_SYSTEM_OPTIONS[0])

    if door_system == "Fixed 2223mm doors":
        door_width = float(row.get("Fixed_Door_Width_mm") or 762)
        if door_width not in FIXED_DOOR_WIDTH_OPTIONS:
            door_width = 762

        dropdown_raw = height - BOTTOM_LINER_THICKNESS - FIXED_DOOR_HEIGHT
        dropdown = max(0, min(dropdown_raw, MAX_DROPDOWN_LIMIT))

        tol = OVERLAP_TOLERANCES.get(doors, DEFAULT_FIXED_OVERLAP_TOLERANCE)
        door_span = doors * door_width
        side_thk = max((width - door_span + tol) / 2, 0)

        net_width = width - 2 * side_thk
        build_out = max(side_thk - SIDE_LINER_THICKNESS, 0)

        status = "OK" if dropdown_raw >= 0 else "Opening too small for fixed doors"

        return pd.Series({
            "Door_Height_mm": FIXED_DOOR_HEIGHT,
            "Door_Width_mm": door_width,
            "Doors_Used": doors,
            "Dropdown_Height_mm": dropdown,
            "Side_Liner_Thickness_mm": round(side_thk, 1),
            "Required_Buildout_Per_Side_mm": round(build_out, 1),
            "Net_Width_mm": int(net_width),
            "Door_Span_mm": int(door_span),
            "Overlap_Tolerance_mm": tol,
            "Height_Status": status,
            "Issue": "✅ OK" if status == "OK" else "🔴 Check height",
        })

    # Made To Measure
    net_width = width - 2 * SIDE_LINER_THICKNESS
    dropdown = TOP_LINER_OPTIONS.get(row.get("Top_Liner_Option") or "108mm Dropdown", 108)

    usable_height = height - BOTTOM_LINER_THICKNESS - dropdown
    door_height = min(usable_height, MAX_DOOR_HEIGHT)

    door_width = (net_width + (doors - 1) * CUSTOM_DOOR_OVERLAP_MM) / doors

    return pd.Series({
        "Door_Height_mm": int(door_height),
        "Door_Width_mm": int(door_width),
        "Doors_Used": doors,
        "Dropdown_Height_mm": dropdown,
        "Side_Liner_Thickness_mm": SIDE_LINER_THICKNESS,
        "Required_Buildout_Per_Side_mm": 0,
        "Net_Width_mm": int(net_width),
        "Door_Span_mm": int(door_width * doors),
        "Overlap_Tolerance_mm": (doors - 1) * CUSTOM_DOOR_OVERLAP_MM,
        "Height_Status": "OK",
        "Issue": "✅ OK",
    })


# ============================================================
# UI
# ============================================================
st.subheader("1. Enter openings")

if st.button("Reset table"):
    if "openings_table" in st.session_state:
        del st.session_state["openings_table"]
    st.rerun()

blank_df = pd.DataFrame(
    columns=[
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
    key="openings_table",
    use_container_width=True,
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Doors", min_value=1, step=1),
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Top_Liner_Option": st.column_config.SelectboxColumn("Top liner (MTM only)", options=list(TOP_LINER_OPTIONS)),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (Fixed 2223 only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
        ),
    },
)

if edited_df is not None and not edited_df.dropna(how="all").empty:
    df = edited_df.dropna(how="all").copy()
    df["Doors"] = df["Doors"].fillna(1)
    df["Door_System"] = df["Door_System"].fillna(DOOR_SYSTEM_OPTIONS[0])
    df["Top_Liner_Option"] = df["Top_Liner_Option"].fillna("108mm Dropdown")
    df["Fixed_Door_Width_mm"] = df["Fixed_Door_Width_mm"].fillna(762)

    df.loc[df["Door_System"] != "Fixed 2223mm doors", "Fixed_Door_Width_mm"] = pd.NA

    results = pd.concat([df.reset_index(drop=True), df.apply(calculate_for_row, axis=1)], axis=1)

    st.subheader("2. Visualise an opening")

    labels = [
        f"{i}: {int(r['Width_mm'])} x {int(r['Height_mm'])} – {r['Door_System']} ({r['Issue']})"
        for i, r in results.iterrows()
    ]
    sel = st.selectbox("Choose opening", labels)
    idx = int(sel.split(":")[0])
    row = results.iloc[idx]

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

    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "wardrobe_results.csv")
else:
    st.info("Add at least one opening to calculate and visualise.")
