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

MIN_T_LINER_THICKNESS = 50  # if build-out > 18, T-liner is at least 50mm

MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

DOOR_SYSTEM_OPTIONS = ["", "Fixed 2223mm doors", "Made to measure doors"]

HOUSEBUILDER_RULES = {
    "Non-client specific wardrobe": {"dropdown": 0, "locked_total_per_side": None},
    "Avant": {"dropdown": 90, "locked_total_per_side": None},
    "Homes By Honey": {"dropdown": 90, "locked_total_per_side": None},
    "Bloor": {"dropdown": 108, "locked_total_per_side": None},  # guidance-only
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


def normalized_door_system(val: str) -> str:
    if val is None:
        return "Fixed 2223mm doors"
    v = str(val).strip()
    return "Fixed 2223mm doors" if v == "" else v


def apply_t_liner_rule(total_per_side_needed: float) -> tuple[float, float]:
    """
    Input total build-out per side required (including the 18mm side liner).
    Output: (total_per_side, t_liner_thickness)
      - If <=18 => (18, 0)
      - Else t = max(total-18, 50), total=18+t
    """
    total_per_side_needed = float(total_per_side_needed)
    if total_per_side_needed <= BASE_SIDE_LINER_THICKNESS:
        return float(BASE_SIDE_LINER_THICKNESS), 0.0

    extra_needed = total_per_side_needed - BASE_SIDE_LINER_THICKNESS
    t = max(extra_needed, float(MIN_T_LINER_THICKNESS))
    total = BASE_SIDE_LINER_THICKNESS + t
    return float(total), float(t)


def fmt_side(total: float, t: float) -> str:
    if t <= 0:
        return f"{int(round(total))}mm (18mm side liner)"
    return f"{int(round(total))}mm (18 + {int(round(t))} T-liner)"


def side_desc(left_total, right_total, left_t, right_t, end_panels: int) -> str:
    if end_panels >= 2:
        return "2x end panels (18mm each side)"
    if end_panels == 1:
        # assume end panel is LEFT for wording consistency
        if abs(left_total - 18.0) < 0.01 and abs(left_t) < 0.01:
            return f"Left: 18mm end panel | Right: {fmt_side(right_total, right_t)}"
        if abs(right_total - 18.0) < 0.01 and abs(right_t) < 0.01:
            return f"Left: {fmt_side(left_total, left_t)} | Right: 18mm end panel"
        return f"1x end panel | Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"
    return f"Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"


def solve_buildout_for_fixed(width_mm: float, door_span_mm: float, total_overlap_mm: float,
                            end_panels: int, locked_total_per_side: float | None):
    """
    Solve required build-out totals so:
      net_width + total_overlap == door_span
      net_width = width - left_total - right_total
    => left_total + right_total = width + total_overlap - door_span

    End panels:
      - 2 => 18/18 fixed
      - 1 => left 18 fixed, right takes remainder (T-liner rule applies)
      - 0 => split evenly (T-liner rule applies)

    Locked:
      - if locked_total_per_side is set and end_panels==0 => force both sides to locked
    """
    width_mm = float(width_mm)

    # end panels hard override
    if end_panels >= 2:
        left_total = right_total = 18.0
        left_t = right_t = 0.0
        net_width = width_mm - left_total - right_total
        ok = (net_width + total_overlap_mm) >= door_span_mm
        status = "OK" if ok else "Opening too small for chosen fixed doors"
        return left_total, right_total, left_t, right_t, status

    # locked client build-out
    if locked_total_per_side is not None and end_panels == 0:
        left_total = right_total = float(locked_total_per_side)
        left_t = right_t = max(left_total - 18.0, 0.0)
        net_width = width_mm - left_total - right_total
        ok = (net_width + total_overlap_mm) >= door_span_mm
        status = "OK" if ok else "Check width (client build-out locked)"
        return left_total, right_total, left_t, right_t, status

    total_buildout_required = (width_mm + total_overlap_mm) - door_span_mm

    # Minimum combined build-out is 36 (18+18) unless you have end panels (still 36)
    if total_buildout_required < 36:
        left_total = right_total = 18.0
        left_t = right_t = 0.0
        return left_total, right_total, left_t, right_t, "Opening too small for chosen fixed doors + overlaps"

    if end_panels == 1:
        left_total = 18.0
        left_t = 0.0
        right_needed = max(total_buildout_required - left_total, 18.0)
        right_total, right_t = apply_t_liner_rule(right_needed)
        return left_total, right_total, left_t, right_t, "OK"

    per_side_needed = total_buildout_required / 2.0
    left_total, left_t = apply_t_liner_rule(per_side_needed)
    right_total, right_t = apply_t_liner_rule(per_side_needed)
    return left_total, right_total, left_t, right_t, "OK"


# ============================================================
# DIAGRAM
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

    fig, ax = plt.subplots(figsize=(4, 7))
    ax.set_xlim(-0.4, 1.4)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")
    ax.set_aspect("equal")

    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=2))
    ax.add_patch(Rectangle((0, bottom_rel), left_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((1 - right_rel, bottom_rel), right_rel, 1 - bottom_rel, alpha=0.25))
    ax.add_patch(Rectangle((left_rel, 0), 1 - left_rel - right_rel, bottom_rel, alpha=0.25))

    if dropdown_rel:
        ax.add_patch(Rectangle((left_rel, 1 - dropdown_rel), 1 - left_rel - right_rel, dropdown_rel, alpha=0.25))

    num_doors = max(int(num_doors), 1)
    span = max(1 - left_rel - right_rel, 0)

    if door_width_mm and float(door_width_mm) > 0:
        door_w_rel = float(door_width_mm) / ow
        total = num_doors * door_w_rel
        if total > span and total > 0:
            door_w_rel *= (span / total)
    else:
        door_w_rel = span / num_doors if num_doors else span

    x = left_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_w_rel, door_h_rel, fill=False, linestyle="--"))
        x += door_w_rel

    return fig


# ============================================================
# DEFAULT ROW (BLANK ON LOAD)
# ============================================================
EMPTY_ROW = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Non-client specific wardrobe",
    "Door_System": "",
    "Door_Style": "Classic",
    "Fixed_Door_Width_mm": 762,
    "End_Panels": 0,
}])


def reset_inputs():
    # Reset safely: delete widget state so Streamlit rebuilds from the seed DF
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

# IMPORTANT:
# Always feed a REAL DataFrame (seed) into data_editor.
# Never feed st.session_state["openings_table"] back into data_editor.
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
        "Door_System": st.column_config.SelectboxColumn("Door system", options=DOOR_SYSTEM_OPTIONS),
        "Door_Style": st.column_config.SelectboxColumn("Door style", options=DOOR_STYLE_OPTIONS),
        "Fixed_Door_Width_mm": st.column_config.SelectboxColumn(
            "Fixed door width (fixed only)",
            options=FIXED_DOOR_WIDTH_OPTIONS,
            default=762,
        ),
        "End_Panels": st.column_config.SelectboxColumn("End panels (count)", options=[0, 1, 2], default=0),
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
    width = float(row["Width_mm"])
    height = float(row["Height_mm"])
    doors = int(row.get("Doors", 2))

    hb = row.get("Housebuilder", "Non-client specific wardrobe")
    hb_rule = HOUSEBUILDER_RULES.get(hb, HOUSEBUILDER_RULES["Non-client specific wardrobe"])
    hb_dropdown_rule = int(hb_rule["dropdown"])
    locked_total = hb_rule.get("locked_total_per_side")

    end_panels = int(row.get("End_Panels", 0) or 0)
    door_style = row.get("Door_Style", "Classic")

    overlap_per_meeting = int(DOOR_STYLE_OVERLAP.get(door_style, 35))
    overlaps_cnt = overlaps_count(doors)
    total_overlap = overlaps_cnt * overlap_per_meeting

    height_stack_base = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT
    door_system = normalized_door_system(row.get("Door_System", ""))

    # BLOOR: guidance-only
    if hb == "Bloor":
        left_total = right_total = 18.0
        net_width = width - left_total - right_total
        return pd.Series({
            "Door_System_Resolved": "Fixed 2223mm doors",
            "Door_Height_mm": FIXED_DOOR_HEIGHT,
            "Door_Width_mm": "",
            "Doors_Used": doors,
            "Dropdown_Height_mm": 108,
            "Side_Left_Total_mm": left_total,
            "Side_Right_Total_mm": right_total,
            "T_Liner_Left_mm": "",
            "T_Liner_Right_mm": "",
            "Side_Description": "Refer to floor plan (build-out per drawing)",
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": "",
            "Overlaps_Count": "",
            "Total_Overlap_mm": "",
            "Door_Span_mm": "",
            "Width_Status": "",
            "Height_Status": "",
            "Issue": "ℹ️ Refer to floor plan",
        })

    # FIXED: solve build-out to make doors fit aperture
    if door_system == "Fixed 2223mm doors":
        door_h = FIXED_DOOR_HEIGHT
        door_w = float(row.get("Fixed_Door_Width_mm", 762))
        if int(door_w) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_w = 762
        door_span = doors * door_w

        left_total, right_total, left_t, right_t, width_status = solve_buildout_for_fixed(
            width_mm=width,
            door_span_mm=door_span,
            total_overlap_mm=total_overlap,
            end_panels=end_panels,
            locked_total_per_side=locked_total,
        )

        net_width = width - left_total - right_total

        dropdown_raw = height - height_stack_base - door_h
        dropdown_h = max(dropdown_raw, 0.0)
        if dropdown_raw > MAX_DROPDOWN_LIMIT:
            dropdown_h = float(MAX_DROPDOWN_LIMIT)

        height_status = "OK"
        if (height - height_stack_base) < door_h:
            height_status = "Opening too small (height) for fixed door + bottom liner + trackset"

        issue = "✅ OK" if (width_status == "OK" and height_status == "OK") else "🔴 Check"

        return pd.Series({
            "Door_System_Resolved": door_system,
            "Door_Height_mm": int(round(door_h)),
            "Door_Width_mm": int(round(door_w)),
            "Doors_Used": doors,
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Left_Total_mm": round(left_total, 1),
            "Side_Right_Total_mm": round(right_total, 1),
            "T_Liner_Left_mm": round(left_t, 1),
            "T_Liner_Right_mm": round(right_t, 1),
            "Side_Description": side_desc(left_total, right_total, left_t, right_t, end_panels),
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": overlap_per_meeting,
            "Overlaps_Count": overlaps_cnt,
            "Total_Overlap_mm": int(round(total_overlap)),
            "Door_Span_mm": int(round(door_span)),
            "Width_Status": width_status,
            "Height_Status": height_status,
            "Issue": issue,
        })

    # MADE TO MEASURE
    dropdown_h = min(hb_dropdown_rule, MAX_DROPDOWN_LIMIT)

    # side totals for MTM: locked clients get locked totals; otherwise 18/18 (end panels override)
    if locked_total is not None and end_panels == 0:
        left_total = right_total = float(locked_total)
        left_t = right_t = max(left_total - 18.0, 0.0)
    else:
        left_total = right_total = 18.0
        left_t = right_t = 0.0

        if end_panels >= 2:
            left_total = right_total = 18.0
        elif end_panels == 1:
            left_total = right_total = 18.0

    net_width = width - left_total - right_total

    raw_door_h = height - height_stack_base - dropdown_h
    door_h = max(min(raw_door_h, MAX_DOOR_HEIGHT), 0)
    door_w = (net_width + total_overlap) / doors if doors else 0

    width_status = "OK" if net_width > 0 else "Opening too small (width)"
    height_status = "OK" if door_h > 0 else "Opening too small (height)"
    issue = "✅ OK" if (width_status == "OK" and height_status == "OK") else "🔴 Check"

    return pd.Series({
        "Door_System_Resolved": door_system,
        "Door_Height_mm": int(round(door_h)),
        "Door_Width_mm": int(round(door_w)),
        "Doors_Used": doors,
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Left_Total_mm": round(left_total, 1),
        "Side_Right_Total_mm": round(right_total, 1),
        "T_Liner_Left_mm": round(left_t, 1),
        "T_Liner_Right_mm": round(right_t, 1),
        "Side_Description": side_desc(left_total, right_total, left_t, right_t, end_panels),
        "Net_Width_mm": int(round(net_width)),
        "Overlap_Per_Meeting_mm": overlap_per_meeting,
        "Overlaps_Count": overlaps_cnt,
        "Total_Overlap_mm": int(round(total_overlap)),
        "Door_Span_mm": int(round(net_width + total_overlap)),
        "Width_Status": width_status,
        "Height_Status": height_status,
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
# 3. VISUALISE OPENING
# ============================================================
st.subheader("3. Visualise opening")

row = results.iloc[0]
hb = row["Housebuilder"]
door_system = row.get("Door_System_Resolved", normalized_door_system(row.get("Door_System", "")))
door_style = row.get("Door_Style", "Classic")
doors_used = int(row.get("Doors_Used", 2))

dropdown = int(row.get("Dropdown_Height_mm", 0))
left_total = float(row.get("Side_Left_Total_mm", 18))
right_total = float(row.get("Side_Right_Total_mm", 18))

if hb == "Bloor":
    st.markdown(
        """
**Bloor specification – follow Field Aware floor plan**

This job is **Bloor**. The final opening width/height and any build-out needed must be taken from the
**client floor plan in Field Aware** to make the wardrobe product work with the aperture.

- **Door height is fixed at 2223mm**
- **Dropdown is fixed at 108mm**
- Overlap guidance (for information only):
  - **Classic:** 35mm per meeting
  - **Shaker:** 75mm per meeting

**Do not rely on calculated spans or overlap maths for Bloor — use the Field Aware floor plan as the source of truth.**
"""
    )
else:
    st.markdown(
        f"""
**Installer guidance**

- Door system: **{door_system}**
- Door style: **{door_style}**
- Dropdown applied: **{dropdown}mm**
- Side build-out: **{row.get("Side_Description","")}**
"""
    )

fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_left_mm=left_total,
    side_right_mm=right_total,
    dropdown_height_mm=dropdown,
    door_height_mm=FIXED_DOOR_HEIGHT if hb == "Bloor" else row.get("Door_Height_mm", 0),
    num_doors=doors_used,
    door_width_mm=0 if hb == "Bloor" else row.get("Door_Width_mm", 0),
)

col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)

with col2:
    st.markdown("#### Summary")
    st.write(f"**Housebuilder:** {hb}")
    st.write(f"**Door system:** {door_system}")
    st.write(f"**Door style:** {door_style}")
    st.write(f"**End panels:** {int(row.get('End_Panels', 0) or 0)}")
    st.write(f"**Issue:** {row.get('Issue','—')}")
    st.write("---")
    st.write(f"**Doors:** {doors_used}")
    st.write(f"**Door height:** {int(row.get('Door_Height_mm', FIXED_DOOR_HEIGHT))} mm")
    if hb == "Bloor":
        st.write("**Door width (each):** Refer to floor plan")
    else:
        st.write(f"**Door width (each):** {row.get('Door_Width_mm', 0)} mm")
    st.write("---")
    st.write(f"**Dropdown height:** {dropdown} mm")
    st.write(f"**Side build-out totals:** {left_total}mm (left), {right_total}mm (right)")
    st.write(f"**T-liners:** L {row.get('T_Liner_Left_mm','')}mm | R {row.get('T_Liner_Right_mm','')}mm")
    st.caption(
        f"Height stack includes bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm)."
    )
