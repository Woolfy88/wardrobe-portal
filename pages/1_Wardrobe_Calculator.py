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

MIN_T_LINER_THICKNESS = 50  # minimum T-liner if build-out beyond 18mm is required

MAX_DOOR_HEIGHT = 2500
MAX_DROPDOWN_LIMIT = 400

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

DOOR_SYSTEM_OPTIONS = ["", "Fixed 2223mm doors", "Made to measure doors"]

# ============================================================
# HOUSEBUILDER RULES
# ============================================================
# Notes:
# - Non-client specific: no forced dropdown; default side liner = 18mm
# - Story/Strata/Jones: dropdown 50 + locked total build-out per side = 68mm (18 + 50)
# - Bloor: dropdown 108 + fixed door height; guidance-only sizing from floor plan
HOUSEBUILDER_RULES = {
    "Non-client specific wardrobe": {"dropdown": 0, "locked_total_per_side": None},
    "Avant": {"dropdown": 90, "locked_total_per_side": None},
    "Homes By Honey": {"dropdown": 90, "locked_total_per_side": None},
    "Bloor": {"dropdown": 108, "locked_total_per_side": None},  # handled specially (guidance only)
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
    """Treat blank as Fixed 2223mm doors."""
    if val is None:
        return "Fixed 2223mm doors"
    v = str(val).strip()
    return "Fixed 2223mm doors" if v == "" else v


def apply_t_liner_rule(total_per_side_needed: float) -> tuple[float, float]:
    """
    Converts 'total build-out per side needed' into:
    - total_per_side (includes 18mm side liner)
    - t_liner_thickness (extra beyond 18mm)
    Rule:
      - If <= 18 -> total=18, t=0
      - Else t = max(total-18, 50), total=18+t
    """
    total_per_side_needed = float(total_per_side_needed)
    if total_per_side_needed <= BASE_SIDE_LINER_THICKNESS:
        return float(BASE_SIDE_LINER_THICKNESS), 0.0

    extra_needed = total_per_side_needed - BASE_SIDE_LINER_THICKNESS
    t = max(extra_needed, float(MIN_T_LINER_THICKNESS))
    total = BASE_SIDE_LINER_THICKNESS + t
    return float(total), float(t)


def side_description(left_total, right_total, left_t, right_t, end_panels: int) -> str:
    def fmt_side(total, t):
        if t <= 0:
            return f"{int(total)}mm (18mm side liner)"
        return f"{int(total)}mm (18mm + {int(t)}mm T-liner)"

    if end_panels == 2:
        return "2x end panels (18mm each side) – no T-liners"
    if end_panels == 1:
        # One side will be end panel (18) and other may be build-out
        if left_total == 18 and right_total != 18:
            return f"Left: 18mm end panel | Right: {fmt_side(right_total, right_t)}"
        if right_total == 18 and left_total != 18:
            return f"Left: {fmt_side(left_total, left_t)} | Right: 18mm end panel"
        return f"One end panel used | Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"

    return f"Left: {fmt_side(left_total, left_t)} | Right: {fmt_side(right_total, right_t)}"


def compute_sides_for_fixed_doors(
    width_mm: float,
    door_span_mm: float,
    total_overlap_mm: float,
    end_panels: int,
    locked_total_per_side: float | None,
) -> tuple[float, float, float, float, str, str]:
    """
    Returns:
      left_total, right_total, left_t, right_t, width_status, side_desc
    For FIXED doors we *solve* build-out to make the door set fit the aperture.
    End panels:
      - count 2: left=18 right=18 (no solve)
      - count 1: one side fixed 18, other side takes the rest
      - count 0: split evenly both sides
    Locked:
      - if locked_total_per_side is set: force both sides to that (unless end panels override)
    """
    width_mm = float(width_mm)

    # End panels always 18mm total (no T-liner)
    if end_panels >= 2:
        left_total, right_total = 18.0, 18.0
        left_t = right_t = 0.0
        # Check feasibility (informational)
        net_width = width_mm - left_total - right_total
        effective = net_width + total_overlap_mm
        width_status = "OK" if effective >= door_span_mm else "Opening too small for chosen fixed doors"
        desc = side_description(left_total, right_total, left_t, right_t, end_panels)
        return left_total, right_total, left_t, right_t, width_status, desc

    # Locked clients (Story/Strata/Jones) – force total per side = 68 (unless end panel count forces)
    if locked_total_per_side is not None and end_panels == 0:
        left_total = right_total = float(locked_total_per_side)
        left_t = right_t = max(left_total - 18.0, 0.0)
        net_width = width_mm - left_total - right_total
        effective = net_width + total_overlap_mm
        width_status = "OK" if effective >= door_span_mm else "Check width (client build-out locked)"
        desc = side_description(left_total, right_total, left_t, right_t, end_panels)
        return left_total, right_total, left_t, right_t, width_status, desc

    # Solve build-out
    # Required total build-out (both sides together):
    total_buildout_needed = (width_mm + total_overlap_mm) - door_span_mm

    # If negative -> opening too small for door span+overlaps, set minimal sides and flag
    if total_buildout_needed < 0:
        if end_panels == 1:
            # one side end panel 18, other minimal 18
            left_total, right_total = 18.0, 18.0
            left_t = right_t = 0.0
        else:
            left_total, right_total = 18.0, 18.0
            left_t = right_t = 0.0
        desc = side_description(left_total, right_total, left_t, right_t, end_panels)
        return left_total, right_total, left_t, right_t, "Opening too small for chosen fixed doors + overlaps", desc

    # Convert total buildout into per-side needs
    if end_panels == 1:
        # one side fixed at 18 (end panel), other side takes the remainder as TOTAL thickness
        fixed_side = 18.0
        other_total_needed = total_buildout_needed - fixed_side
        other_total_needed = max(other_total_needed, 18.0)  # never below 18 total

        other_total, other_t = apply_t_liner_rule(other_total_needed)

        # Put the end panel on the LEFT for consistency
        left_total, left_t = 18.0, 0.0
        right_total, right_t = other_total, other_t
    else:
        per_side_needed = total_buildout_needed / 2.0
        left_total, left_t = apply_t_liner_rule(per_side_needed)
        right_total, right_t = apply_t_liner_rule(per_side_needed)

    net_width = width_mm - left_total - right_total
    effective = net_width + total_overlap_mm

    # It should now be equal-ish to door span; allow small tolerance
    width_status = "OK" if effective >= door_span_mm - 1 else "Check width"

    desc = side_description(left_total, right_total, left_t, right_t, end_panels)
    return left_total, right_total, left_t, right_t, width_status, desc


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
    opening_width_mm = max(float(opening_width_mm), 1)
    opening_height_mm = max(float(opening_height_mm), 1)

    left_rel = max(float(side_left_mm), 0) / opening_width_mm
    right_rel = max(float(side_right_mm), 0) / opening_width_mm
    bottom_rel = max(float(bottom_thk_mm), 0) / opening_height_mm
    dropdown_rel = (max(float(dropdown_height_mm), 0) / opening_height_mm) if dropdown_height_mm else 0

    usable_height_rel = max(1 - bottom_rel - dropdown_rel, 0)
    raw_door_rel = (max(float(door_height_mm), 0) / opening_height_mm) if door_height_mm else 0
    door_rel = min(raw_door_rel, usable_height_rel)

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
    available_span = 1 - left_rel - right_rel

    # If door_width_mm is 0, draw evenly for visuals
    if door_width_mm and float(door_width_mm) > 0:
        door_width_rel = float(door_width_mm) / opening_width_mm
        total_span = num_doors * door_width_rel
        if total_span > available_span and total_span > 0:
            door_width_rel *= available_span / total_span
    else:
        door_width_rel = available_span / num_doors if num_doors else available_span

    x = left_rel
    for _ in range(num_doors):
        ax.add_patch(Rectangle((x, bottom_rel), door_width_rel, door_rel, fill=False, linestyle="--"))
        x += door_width_rel

    return fig


# ============================================================
# EMPTY INPUT ROW (START BLANK)
# ============================================================
EMPTY_ROW = pd.DataFrame([{
    "Width_mm": None,
    "Height_mm": None,
    "Doors": 2,
    "Housebuilder": "Non-client specific wardrobe",
    "Door_System": "",  # blank default => Fixed doors
    "Door_Style": "Classic",
    "Fixed_Door_Width_mm": 762,
    "End_Panels": 0,  # 0/1/2
}])


def reset_inputs():
    st.session_state["openings_df"] = EMPTY_ROW.copy()
    if "openings_table" in st.session_state:
        del st.session_state["openings_table"]


if "openings_df" not in st.session_state:
    st.session_state["openings_df"] = EMPTY_ROW.copy()

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
        "End_Panels": st.column_config.SelectboxColumn(
            "End panels (count)",
            options=[0, 1, 2],
            default=0,
        ),
    },
)
st.session_state["openings_df"] = edited_df


# ============================================================
# CALCULATION
# ============================================================
def calculate(row: pd.Series) -> pd.Series:
    if pd.isna(row.get("Width_mm")) or pd.isna(row.get("Height_mm")):
        return pd.Series({"Issue": "—"})

    width = float(row["Width_mm"])
    height = float(row["Height_mm"])
    doors = int(row.get("Doors", 2))

    hb = row.get("Housebuilder", "Non-client specific wardrobe")
    hb_rule = HOUSEBUILDER_RULES.get(hb, HOUSEBUILDER_RULES["Non-client specific wardrobe"])
    hb_dropdown_rule = int(hb_rule["dropdown"])
    locked_total_per_side = hb_rule.get("locked_total_per_side", None)

    end_panels = int(row.get("End_Panels", 0) or 0)
    door_style = row.get("Door_Style", "Classic")

    overlap_per_meeting = int(DOOR_STYLE_OVERLAP.get(door_style, 35))
    overlaps_cnt = overlaps_count(doors)
    total_overlap = overlaps_cnt * overlap_per_meeting

    height_stack_base = BOTTOM_LINER_THICKNESS + TRACKSET_HEIGHT
    door_system = normalized_door_system(row.get("Door_System", ""))

    # ========================================================
    # BLOOR: guidance-only (NO span/overlap calculations)
    # ========================================================
    if hb == "Bloor":
        # Still compute basic sides for visual + awareness (18/18 unless end panels imply 18 anyway)
        left_total = right_total = 18.0
        left_t = right_t = 0.0
        if end_panels == 0:
            left_total = right_total = 18.0
        elif end_panels == 1:
            left_total, right_total = 18.0, 18.0
        else:
            left_total, right_total = 18.0, 18.0

        net_width = width - left_total - right_total

        return pd.Series({
            "Door_System_Resolved": "Fixed 2223mm doors",
            "Door_Height_mm": FIXED_DOOR_HEIGHT,
            "Door_Width_mm": "",
            "Doors_Used": int(doors),
            "Dropdown_Height_mm": 108,
            "Side_Left_Total_mm": round(left_total, 1),
            "Side_Right_Total_mm": round(right_total, 1),
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

    # --------------------------
    # FIXED 2223mm DOORS (SOLVE BUILD-OUT)
    # --------------------------
    if door_system == "Fixed 2223mm doors":
        door_h = FIXED_DOOR_HEIGHT

        door_w = float(row.get("Fixed_Door_Width_mm", 762))
        if int(door_w) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_w = 762

        door_span = doors * door_w

        left_total, right_total, left_t, right_t, width_status, side_desc = compute_sides_for_fixed_doors(
            width_mm=width,
            door_span_mm=door_span,
            total_overlap_mm=total_overlap,
            end_panels=end_panels,
            locked_total_per_side=locked_total_per_side,
        )

        net_width = width - left_total - right_total

        # Dropdown is simply what's left (fixed door height)
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
            "Doors_Used": int(doors),
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Left_Total_mm": round(left_total, 1),
            "Side_Right_Total_mm": round(right_total, 1),
            "T_Liner_Left_mm": round(left_t, 1),
            "T_Liner_Right_mm": round(right_t, 1),
            "Side_Description": side_desc,
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
            "Overlaps_Count": int(overlaps_cnt),
            "Total_Overlap_mm": int(round(total_overlap)),
            "Door_Span_mm": int(round(door_span)),
            "Width_Status": width_status,
            "Height_Status": height_status,
            "Issue": issue,
        })

    # --------------------------
    # MADE TO MEASURE DOORS (LOCKED CLIENT RULES APPLY)
    # --------------------------
    dropdown_h = min(hb_dropdown_rule, MAX_DROPDOWN_LIMIT)

    # Side totals:
    if locked_total_per_side is not None and end_panels == 0:
        left_total = right_total = float(locked_total_per_side)
        left_t = right_t = max(left_total - 18.0, 0.0)
        side_desc = side_description(left_total, right_total, left_t, right_t, end_panels)
    else:
        # default MTM: 18mm each side unless end panels override
        if end_panels >= 2:
            left_total = right_total = 18.0
            left_t = right_t = 0.0
        elif end_panels == 1:
            left_total, right_total = 18.0, 18.0
            left_t = right_t = 0.0
        else:
            left_total, right_total = 18.0, 18.0
            left_t = right_t = 0.0
        side_desc = side_description(left_total, right_total, left_t, right_t, end_panels)

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
        "Doors_Used": int(doors),
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Left_Total_mm": round(left_total, 1),
        "Side_Right_Total_mm": round(right_total, 1),
        "T_Liner_Left_mm": round(left_t, 1),
        "T_Liner_Right_mm": round(right_t, 1),
        "Side_Description": side_desc,
        "Net_Width_mm": int(round(net_width)),
        "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
        "Overlaps_Count": int(overlaps_cnt),
        "Total_Overlap_mm": int(round(total_overlap)),
        "Door_Span_mm": int(round(net_width + total_overlap)),
        "Width_Status": width_status,
        "Height_Status": height_status,
        "Issue": issue,
    })


results = pd.concat([edited_df.reset_index(drop=True), edited_df.apply(calculate, axis=1)], axis=1)

# ============================================================
# 2. CALCULATED RESULTS (HIDDEN)
# ============================================================
st.subheader("2. Calculated results")
with st.expander("Show calculated table", expanded=False):
    st.dataframe(results, use_container_width=True)

if results.get("Issue", pd.Series(["—"])).iloc[0] not in ("—", None):
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "wardrobe_results.csv", "text/csv")

# ============================================================
# 3. VISUALISE OPENING
# ============================================================
st.subheader("3. Visualise opening")

row = results.iloc[0]
if pd.isna(row.get("Width_mm")) or pd.isna(row.get("Height_mm")):
    st.info("Enter width and height above to generate the diagram.")
    st.stop()

hb = row["Housebuilder"]
door_system = row.get("Door_System_Resolved", normalized_door_system(row.get("Door_System", "")))
door_style = row.get("Door_Style", "Classic")

dropdown = int(row.get("Dropdown_Height_mm", 0))
side_desc = row.get("Side_Description", "")
doors_used = int(row.get("Doors_Used", 2))

left_total = float(row.get("Side_Left_Total_mm", 18))
right_total = float(row.get("Side_Right_Total_mm", 18))

# Banner (plain English)
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
elif hb == "Non-client specific wardrobe":
    st.markdown(
        f"""
**Non-client specific wardrobe**

Enter the opening dimensions and use the outputs to build the wardrobe to suit the aperture.

- Default side liner: **18mm**
- If extra framing is required, a **T-liner** is added (minimum **50mm**)
- Bottom liner: **36mm**
- Trackset allowance: **54mm**
- Door system: **{door_system}**
- Door style: **{door_style}**
"""
    )
else:
    st.markdown(
        f"""
**Installer guidance**

- Dropdown applied: **{dropdown}mm**
- Side build-out: **{side_desc}**
- Door system: **{door_system}**
- Door style: **{door_style}**
"""
    )

# Diagram
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
    st.write(f"**Issue:** {row.get('Issue','—')}")
    st.write("---")
    st.write(f"**Doors:** {doors_used}")
    st.write(f"**Door height:** {int(row.get('Door_Height_mm', FIXED_DOOR_HEIGHT))} mm")
    if hb == "Bloor":
        st.write("**Door width (each):** Refer to floor plan")
    else:
        dw = row.get("Door_Width_mm", 0)
        st.write(f"**Door width (each):** {dw} mm")
    st.write("---")
    st.write(f"**Dropdown height:** {int(row.get('Dropdown_Height_mm', 0))} mm")
    st.write(f"**Side build-out totals:** {left_total}mm (left), {right_total}mm (right)")
    st.caption(f"Height stack includes bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm).")
