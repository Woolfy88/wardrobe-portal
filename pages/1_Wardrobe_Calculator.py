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
TRACKSET_HEIGHT = 54  # keep visible for ALL clients
FIXED_SIZED_DOOR_HEIGHT = 2313  # keep visible for ALL clients

BASE_SIDE_LINER_THICKNESS = 18
MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

HOUSEBUILDER_RULES = {
    "Non-client specific wardrobe": {"dropdown": 0, "locked_total_per_side": None},
    "Avant": {"dropdown": 90, "locked_total_per_side": None},
    "Homes By Honey": {"dropdown": 90, "locked_total_per_side": None},
    "Bloor": {"dropdown": 108, "locked_total_per_side": None},  # floorplan-only
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

# Hide calculated door sizes for these clients (must use Field Aware floor plan)
FLOORPLAN_ONLY_HOUSEBUILDERS = {"Avant", "Homes By Honey", "Bloor"}


# ============================================================
# HELPERS
# ============================================================
def overlaps_count(num_doors: int) -> int:
    n = max(int(num_doors), 1)
    if n == 2:
        return 1
    if n in (3, 4):
        return 2
    if n == 5:
        return 4
    return max(n - 1, 0)


def parse_dropdown_select(val) -> tuple[bool, int]:
    if val is None:
        return True, 0
    s = str(val).strip()
    if s.lower().startswith("auto") or s == "":
        return True, 0
    try:
        return False, int(float(s))
    except Exception:
        return True, 0


def fmt_side(total: float, t: float) -> str:
    if t <= 0:
        return f"{int(round(total))}mm (18mm side liner)"
    return f"{int(round(total))}mm (18 + {int(round(t))} T-liner)"


def side_desc(left_total, right_total, left_t, right_t, end_panels: int) -> str:
    if end_panels >= 2:
        return "2x end panels (18mm each side)"
    if end_panels == 1:
        if abs(left_total - 18.0) < 0.01 and abs(left_t) < 0.01:
            return f"Left: 18mm end panel | Right: {fmt_side(right_total, right_t)}"
        if abs(right_total - 18.0) < 0.01 and abs(right_t) < 0.01:
            return f"Left: {fmt_side(left_total, left_t)} | Right: 18mm end panel"
        return f"1x end panel | Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"
    return f"Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"


# ============================================================
# DIAGRAM (minimal dims + FIXING NOTES)
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
    ow = max(float(opening_width_mm), 1)
    oh = max(float(opening_height_mm), 1)

    left_rel = max(float(side_left_mm), 0) / ow
    right_rel = max(float(side_right_mm), 0) / ow
    bottom_rel = max(float(bottom_thk_mm), 0) / oh
    dropdown_rel = (max(float(dropdown_height_mm), 0) / oh) if dropdown_height_mm else 0

    usable_h_rel = max(1 - bottom_rel - dropdown_rel, 0)
    door_h_rel = (max(float(door_height_mm), 0) / oh) if door_height_mm else 0
    door_h_rel = min(door_h_rel, usable_h_rel)

    fig, ax = plt.subplots(figsize=(5, 7))
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    # Opening outline
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))

    # Context shading only
    ax.add_patch(Rectangle((0, bottom_rel), left_rel, 1 - bottom_rel, alpha=0.15))
    ax.add_patch(Rectangle((1 - right_rel, bottom_rel), right_rel, 1 - bottom_rel, alpha=0.15))
    ax.add_patch(Rectangle((left_rel, 0), 1 - left_rel - right_rel, bottom_rel, alpha=0.15))

    if dropdown_rel:
        ax.add_patch(Rectangle((left_rel, 1 - dropdown_rel), 1 - left_rel - right_rel, dropdown_rel, alpha=0.15))

    # -----------------------------
    # DOORS (dashed)
    # -----------------------------
    num_doors = max(int(num_doors), 1)
    span = max(1 - left_rel - right_rel, 0)

    door_width_mm = max(float(door_width_mm or 0), 0.0)
    if door_width_mm > 0:
        door_w_rel = door_width_mm / ow
        total = num_doors * door_w_rel
        if total > span and total > 0:
            door_w_rel *= (span / total)
    else:
        door_w_rel = span / num_doors if num_doors else span

    x = left_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_w_rel, door_h_rel, fill=False, linestyle="--", lw=1.2))
        x += door_w_rel

    # ============================================================
    # MINIMAL DIMENSIONS ONLY
    # ============================================================
    def dim_h(x0, x1, y, text):
        ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=1.4))
        ax.text((x0 + x1) / 2, y + 0.02, text, ha="center", va="bottom", fontsize=9)

    def dim_v(x, y0, y1, text):
        ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", lw=1.4))
        ax.text(x + 0.02, (y0 + y1) / 2, text, ha="left", va="center", rotation=90, fontsize=9)

    dim_h(0, 1, -0.12, f"Opening width: {int(round(ow))}mm")
    dim_v(-0.18, 0, 1, f"Opening height: {int(round(oh))}mm")

    if dropdown_rel > 0:
        dim_v(1.08, 1 - dropdown_rel, 1, f"Dropdown: {int(round(dropdown_height_mm))}mm")

    # ============================================================
    # FIXING NOTES
    # ============================================================
    note_box = dict(boxstyle="round,pad=0.45", fc="white", ec="black", lw=1)

    if dropdown_rel > 0:
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
            bbox=note_box,
            arrowprops=dict(arrowstyle="->", lw=1.3),
        )

    ax.annotate(
        "Side liners fixings -\n"
        "200mm in from either end\n"
        "and then two in the middle\n"
        "of the liner (equally spaced),\n"
        "so 4x fixings in total.",
        xy=(max(left_rel, 0.02) / 2, 0.5),
        xytext=(-0.34, 0.72),
        fontsize=8,
        ha="right",
        va="center",
        bbox=note_box,
    )

    ax.annotate(
        "Sub-cill to floor - fixing every 500mm\n"
        "Sub-cill to carpet - fixing every 200mm",
        xy=(0.5, bottom_rel / 2 if bottom_rel > 0 else 0.02),
        xytext=(0.5, -0.20),
        fontsize=8,
        ha="center",
        va="top",
        bbox=note_box,
    )

    ax.annotate(
        "Bottom track fixing - 50-80mm in from ends\n"
        "and then every 800mm of track span.",
        xy=(0.5, min(bottom_rel + 0.02, 0.08)),
        xytext=(1.28, min(bottom_rel + 0.18, 0.30)),
        fontsize=8,
        ha="left",
        va="center",
        bbox=note_box,
        arrowprops=dict(arrowstyle="->", lw=1.3),
    )

    return fig


# ============================================================
# DEFAULT ROW (BLANK ON LOAD)
# ============================================================
EMPTY_ROW = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Non-client specific wardrobe",
    "Door_Style": "Classic",
    "Dropdown_Select": "Auto",
    "End_Panels": 0,
}])


def reset_inputs():
    if "openings_table" in st.session_state:
        del st.session_state["openings_table"]
    st.session_state["openings_seed"] = EMPTY_ROW.copy()


if "openings_seed" not in st.session_state:
    st.session_state["openings_seed"] = EMPTY_ROW.copy()

# ============================================================
# 1. ENTER OPENING
# ============================================================
st.subheader("1. Enter opening")
st.button("Reset opening", on_click=reset_inputs)

edited_df = st.data_editor(
    st.session_state["openings_seed"],
    num_rows="fixed",
    key="openings_table",
    use_container_width=True,
    column_config={
        "Width_mm": st.column_config.NumberColumn("Width (mm)", min_value=300, step=10),
        "Height_mm": st.column_config.NumberColumn("Height (mm)", min_value=300, step=10),
        "Doors": st.column_config.NumberColumn("Doors", min_value=2, max_value=10, step=1),
        "Housebuilder": st.column_config.SelectboxColumn("Housebuilder", options=HOUSEBUILDER_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "Dropdown_Select": st.column_config.SelectboxColumn("Dropdown (mm)", options=DROPDOWN_SELECT_OPTIONS),
        "End_Panels": st.column_config.SelectboxColumn("End panels (count)", options=[0, 1, 2]),
    },
)

row_in = edited_df.iloc[0]
if pd.isna(row_in.get("Width_mm")) or pd.isna(row_in.get("Height_mm")):
    st.info("Enter width and height above to generate results and the diagram.")
    st.stop()

# ============================================================
# CALCULATION
# ============================================================
def calculate(row: pd.Series) -> pd.Series:
    warnings: list[str] = []
    errors: list[str] = []

    width = float(row["Width_mm"])
    height = float(row["Height_mm"])
    doors = int(row.get("Doors", 2))

    hb = row.get("Housebuilder", "Non-client specific wardrobe")
    hb_rule = HOUSEBUILDER_RULES.get(hb, HOUSEBUILDER_RULES["Non-client specific wardrobe"])
    hb_required_dropdown = int(hb_rule["dropdown"])
    locked_total = hb_rule.get("locked_total_per_side")

    end_panels = int(row.get("End_Panels", 0) or 0)
    door_style = row.get("Door_Style", "Classic")

    # Dropdown selection
    is_auto, user_dd = parse_dropdown_select(row.get("Dropdown_Select", "Auto"))

    # ---- KEY CHANGE:
    # For Non-client specific wardrobe, there is NO "expected dropdown" check.
    # Just use whatever is selected. Auto defaults to 0.
    dropdown_type_status = "OK"
    if hb != "Non-client specific wardrobe":
        if not is_auto and user_dd != hb_required_dropdown:
            dropdown_type_status = f"Housebuilder expects {hb_required_dropdown}mm dropdown (selected {user_dd}mm)"
            warnings.append(dropdown_type_status)

    # Applied dropdown:
    if hb == "Non-client specific wardrobe":
        dropdown_h = 0 if is_auto else user_dd
    else:
        dropdown_h = hb_required_dropdown if is_auto else user_dd

    dropdown_h = max(0, min(int(dropdown_h), MAX_DROPDOWN_LIMIT))

    # Side build-out totals:
    if locked_total is not None and end_panels == 0:
        left_total = right_total = float(locked_total)
        left_t = right_t = max(left_total - 18.0, 0.0)
    else:
        left_total = right_total = 18.0
        left_t = right_t = 0.0

    # End panels simplified view
    if end_panels >= 1:
        left_total = right_total = 18.0
        left_t = right_t = 0.0

    net_width = width - left_total - right_total
    if net_width <= 0:
        errors.append("Opening too small (width) after side deductions.")

    overlap_per_meeting = int(DOOR_STYLE_OVERLAP.get(door_style, 25))
    total_overlap = overlaps_count(doors) * overlap_per_meeting

    height_stack = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT
    raw_door_h = height - height_stack - dropdown_h
    door_h = max(min(raw_door_h, MAX_DOOR_HEIGHT), 0)
    if door_h <= 0:
        errors.append("Opening too small (height) after bottom/track/dropdown deductions.")

    door_w = (net_width + total_overlap) / doors if doors else 0
    door_span = doors * door_w
    coverage = door_span - total_overlap

    if net_width > 0:
        delta = coverage - net_width
        if abs(delta) > 2:
            warnings.append(f"Coverage mismatch vs net width by {int(round(delta))}mm (rounding/inputs).")

    width_status = "OK" if net_width > 0 else "Opening too small (width)"
    height_status = "OK" if door_h > 0 else "Opening too small (height)"
    issue = "🔴 Check" if (errors or warnings) else "✅ OK"

    return pd.Series({
        "Door_Height_mm": int(round(door_h)),
        "Door_Width_mm": int(round(door_w)),
        "Doors_Used": doors,
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Dropdown_Type_Status": dropdown_type_status,
        "Side_Left_Total_mm": round(left_total, 1),
        "Side_Right_Total_mm": round(right_total, 1),
        "T_Liner_Left_mm": round(left_t, 1) if left_t else "",
        "T_Liner_Right_mm": round(right_t, 1) if right_t else "",
        "Side_Description": side_desc(left_total, right_total, left_t, right_t, end_panels),
        "Net_Width_mm": int(round(net_width)),
        "Overlap_Per_Meeting_mm": overlap_per_meeting,
        "Overlaps_Count": overlaps_count(doors),
        "Total_Overlap_mm": int(round(total_overlap)),
        "Door_Span_mm": int(round(door_span)),
        "Coverage_mm": int(round(coverage)),
        "Width_Status": width_status,
        "Height_Status": height_status,
        "Warnings": " | ".join(warnings),
        "Errors": " | ".join(errors),
        "Issue": issue,
    })


calcs = edited_df.apply(calculate, axis=1)
results = pd.concat([edited_df.reset_index(drop=True), calcs.reset_index(drop=True)], axis=1)

# ============================================================
# 2. CALCULATED RESULTS (HIDDEN)
# ============================================================
st.subheader("2. Calculated results")
with st.expander("Show calculated table", expanded=False):
    st.dataframe(results, use_container_width=True)

csv = results.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")

# ============================================================
# 3. VISUALISE OPENING + BANNERS (DISPLAY BLOCK FOR FLOORPLAN CLIENTS)
# ============================================================
st.subheader("3. Visualise opening")

row = results.iloc[0]
hb = row["Housebuilder"]
floorplan_only = hb in FLOORPLAN_ONLY_HOUSEBUILDERS

st.info(f"Trackset height: **{TRACKSET_HEIGHT}mm** | Fixed sized door height: **{FIXED_SIZED_DOOR_HEIGHT}mm**")

if hb == "Bloor":
    st.markdown(
        """
**Bloor specification – follow Field Aware floor plan**

This job is **Bloor**. The final opening sizes, build-out and fitting approach must be taken from the
**client floor plan in Field Aware**.

- **Installer to check Field Aware floor plan** for sizes and how to fit.
"""
    )

if hb in {"Avant", "Homes By Honey"}:
    st.markdown(
        """
**Avant / Homes By Honey – follow Field Aware floor plan (fixed sizes & framework)**

This job is **Avant / Homes By Honey**. The wardrobe is based on **fixed sized doors and framework**.
The final sizes, build-out, and fitting approach must be taken from the **client floor plan in Field Aware**.

- **Installer to check Field Aware floor plan** for sizes and how to fit.
- Fixed sized doors and framework apply.
- An **extra end panel** will have been added where dropdowns or T-liners are larger than standard liners.
"""
    )

# Only show warnings/errors for non-floorplan clients
if not floorplan_only:
    errs = str(row.get("Errors", "")).strip()
    warns = str(row.get("Warnings", "")).strip()

    if errs:
        for msg in errs.split(" | "):
            if msg.strip():
                st.error(msg.strip())

    if warns:
        for msg in warns.split(" | "):
            if msg.strip():
                st.warning(msg.strip())

door_style = row.get("Door_Style", "Classic")
doors_used = int(row.get("Doors_Used", 2))
dropdown = int(row.get("Dropdown_Height_mm", 0))

left_total = float(row.get("Side_Left_Total_mm", 18))
right_total = float(row.get("Side_Right_Total_mm", 18))

diagram_left = 18.0 if floorplan_only else left_total
diagram_right = 18.0 if floorplan_only else right_total

door_h_for_diagram = 0 if floorplan_only else row.get("Door_Height_mm", 0)
door_w_for_diagram = 0 if floorplan_only else row.get("Door_Width_mm", 0)

fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_left_mm=diagram_left,
    side_right_mm=diagram_right,
    dropdown_height_mm=dropdown,
    door_height_mm=door_h_for_diagram,
    num_doors=doors_used,
    door_width_mm=door_w_for_diagram,
)

col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)

with col2:
    st.markdown("#### Summary")
    st.write(f"**Housebuilder:** {hb}")
    st.write(f"**Door style:** {door_style}")
    st.write(f"**Doors:** {doors_used}")
    st.write(f"**Dropdown applied:** {dropdown} mm")
    st.write("---")

    if floorplan_only:
        st.info("Calculated door sizes are hidden for this client. Use the Field Aware floor plan for sizes and fit.")
    else:
        st.write(f"**Door height:** {int(row.get('Door_Height_mm', 0))} mm")
        st.write(f"**Door width (each):** {row.get('Door_Width_mm', 0)} mm")
        st.write("---")
        st.write(f"**Side build-out:** {row.get('Side_Description','')}")
        st.write(f"**Net opening width:** {row.get('Net_Width_mm','—')} mm")
        st.write(f"**Total overlap:** {row.get('Total_Overlap_mm','—')} mm")

    st.caption(
        f"Height deductions: bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm) + dropdown."
    )
