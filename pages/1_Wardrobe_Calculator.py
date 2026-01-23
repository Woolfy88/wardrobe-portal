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
MAX_DROPDOWN_LIMIT = 400

FIXED_DOOR_HEIGHT = 2223
FIXED_DOOR_WIDTH_OPTIONS = [610, 762, 914]

# Door system dropdown shows blank by default; blank resolves to Fixed doors
DOOR_SYSTEM_OPTIONS = ["", "Fixed 2223mm doors", "Made to measure doors"]

# ============================================================
# HOUSEBUILDER RULES
# ============================================================
# Non-client specific:
# - 18mm side liners each side (default)
# - dropdown = 0 (no forced dropdown rule)
HOUSEBUILDER_RULES = {
    "Non-client specific wardrobe": {"dropdown": 0, "side_each": BASE_SIDE_LINER_THICKNESS},
    "Avant": {"dropdown": 90, "side_each": BASE_SIDE_LINER_THICKNESS},
    "Homes By Honey": {"dropdown": 90, "side_each": BASE_SIDE_LINER_THICKNESS},
    "Bloor": {"dropdown": 108, "side_each": BASE_SIDE_LINER_THICKNESS},
    "Story": {"dropdown": 50, "side_each": 68},
    "Strata": {"dropdown": 50, "side_each": 68},
    "Jones Homes": {"dropdown": 50, "side_each": 68},
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
    """Overlap-count rules:
       2 doors -> 1 overlap
       3 doors -> 2 overlaps
       4 doors -> 2 overlaps
       5 doors -> 4 overlaps
       fallback: doors - 1
    """
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


def get_side_thicknesses(housebuilder: str, end_panels_count: int):
    """
    End panels are ALWAYS 18mm each (count: 0/1/2).

    Base (no end panels):
      - Non-client specific: 18mm each side (default side liners)
      - Most client builders: 18mm each side
      - Story/Strata/Jones: 68mm each side (50mm T-liner + 18mm side liner)

    End panels override the side build-out:
      - 1 end panel: one side 18mm end panel + other side builder rule
      - 2 end panels: both sides 18mm end panels
    """
    rule = HOUSEBUILDER_RULES.get(
        housebuilder, {"dropdown": 0, "side_each": BASE_SIDE_LINER_THICKNESS}
    )
    each = float(rule["side_each"])
    c = int(end_panels_count or 0)

    # End panels always 18mm
    if c >= 2:
        left = right = 18.0
        desc = "2x end panels (18mm each side)"
        return left, right, desc

    if c == 1:
        left = 18.0
        right = each
        if each == 18.0:
            desc = "1x end panel (18mm) + 1x 18mm side liner"
        else:
            desc = "1x end panel (18mm) + 1x 68mm build-out (50mm T-liner + 18mm side liner)"
        return left, right, desc

    left = right = each
    if each == 18.0:
        desc = "2x 18mm side liners"
    else:
        desc = "68mm build-out each side (50mm T-liner + 18mm side liner)"
    return left, right, desc


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
    "Housebuilder": "Non-client specific wardrobe",  # default choice
    "Door_System": "",  # blank default => Fixed doors
    "Door_Style": DOOR_STYLE_OPTIONS[0],
    "Fixed_Door_Width_mm": 762,
    "End_Panels": 0,
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
    rule = HOUSEBUILDER_RULES.get(hb, {"dropdown": 0, "side_each": BASE_SIDE_LINER_THICKNESS})
    hb_dropdown = int(rule["dropdown"])

    end_panels = int(row.get("End_Panels", 0) or 0)
    side_left, side_right, side_desc = get_side_thicknesses(hb, end_panels)
    net_width = width - side_left - side_right

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
        return pd.Series({
            "Door_System_Resolved": "Fixed 2223mm doors",
            "Door_Height_mm": FIXED_DOOR_HEIGHT,
            "Door_Width_mm": "",
            "Doors_Used": int(doors),
            "Dropdown_Height_mm": 108,
            "Side_Left_mm": round(side_left, 1),
            "Side_Right_mm": round(side_right, 1),
            "Side_Description": side_desc,
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": "",
            "Overlaps_Count": "",
            "Total_Overlap_mm": "",
            "Door_Span_mm": "",
            "Issue": "ℹ️ Refer to floor plan",
        })

    # --------------------------
    # FIXED 2223mm DOORS
    # --------------------------
    if door_system == "Fixed 2223mm doors":
        door_h = FIXED_DOOR_HEIGHT

        door_w = float(row.get("Fixed_Door_Width_mm", 762))
        if int(door_w) not in FIXED_DOOR_WIDTH_OPTIONS:
            door_w = 762

        # Dropdown required is "what's left"
        dropdown_raw = height - height_stack_base - door_h
        dropdown_h = max(dropdown_raw, 0)
        if dropdown_raw > MAX_DROPDOWN_LIMIT:
            dropdown_h = MAX_DROPDOWN_LIMIT

        door_span = doors * door_w
        effective_span_available = net_width + total_overlap

        width_ok = (net_width > 0) and (effective_span_available >= door_span)
        height_ok = (height - height_stack_base) >= door_h

        issue = "✅ OK" if (width_ok and height_ok) else "🔴 Check"

        return pd.Series({
            "Door_System_Resolved": door_system,
            "Door_Height_mm": int(round(door_h)),
            "Door_Width_mm": int(round(door_w)),
            "Doors_Used": int(doors),
            "Dropdown_Height_mm": int(round(dropdown_h)),
            "Side_Left_mm": round(side_left, 1),
            "Side_Right_mm": round(side_right, 1),
            "Side_Description": side_desc,
            "Net_Width_mm": int(round(net_width)),
            "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
            "Overlaps_Count": int(overlaps_cnt),
            "Total_Overlap_mm": int(round(total_overlap)),
            "Door_Span_mm": int(round(door_span)),
            "Issue": issue,
        })

    # --------------------------
    # MADE TO MEASURE DOORS
    # --------------------------
    # For non-client specific, hb_dropdown will be 0 (no forced dropdown)
    dropdown_h = min(hb_dropdown, MAX_DROPDOWN_LIMIT)

    raw_door_h = height - height_stack_base - dropdown_h
    door_h = max(min(raw_door_h, MAX_DOOR_HEIGHT), 0)

    door_w = (net_width + total_overlap) / doors if doors else 0
    issue = "✅ OK" if (net_width > 0 and door_h > 0) else "🔴 Check"

    return pd.Series({
        "Door_System_Resolved": door_system,
        "Door_Height_mm": int(round(door_h)),
        "Door_Width_mm": int(round(door_w)),
        "Doors_Used": int(doors),
        "Dropdown_Height_mm": int(round(dropdown_h)),
        "Side_Left_mm": round(side_left, 1),
        "Side_Right_mm": round(side_right, 1),
        "Side_Description": side_desc,
        "Net_Width_mm": int(round(net_width)),
        "Overlap_Per_Meeting_mm": int(overlap_per_meeting),
        "Overlaps_Count": int(overlaps_cnt),
        "Total_Overlap_mm": int(round(total_overlap)),
        "Door_Span_mm": int(round(net_width + total_overlap)),
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
side_left = float(row.get("Side_Left_mm", 0))
side_right = float(row.get("Side_Right_mm", 0))
side_desc = row.get("Side_Description", "")
doors_used = int(row.get("Doors_Used", 2))

# Banner (plain English)
if hb == "Bloor":
    st.markdown(
        """
**Bloor specification – follow Field Aware floor plan**

This job is **Bloor**. The final opening width/height and any build-out needed must be taken from the
**client floor plan in Field Aware** to make the wardrobe product work with the aperture.

- **Door height is fixed at 2223mm**
- **Dropdown is fixed at 108mm**
- Side build-out shown here is **indicative only**
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

Enter the opening dimensions and use the calculated outputs to build your wardrobe to suit the aperture.

- Default side liners: **18mm each side**
- Bottom liner: **36mm**
- Trackset allowance: **54mm**
- Door system: **{door_system}**
- Door style: **{door_style}**
"""
    )
else:
    if door_system == "Made to measure doors":
        if hb in ["Story", "Strata", "Jones Homes"]:
            st.markdown(
                f"""
**Installer guidance**

- Dropdown is fixed at **50mm**
- Side build-out is locked by the client rule: **{side_desc}**
- Doors are made-to-measure to suit what remains after dropdown and build-out

**Do not alter the dropdown or the build-out on site.**
"""
            )
        else:
            st.markdown(
                f"""
**Installer guidance**

- Dropdown applied: **{dropdown}mm**
- Side build-out: **{side_desc}**
- Doors are made-to-measure to suit the net opening

**Do not change the dropdown height.**
"""
            )
    else:
        st.markdown(
            f"""
**Installer guidance**

- Doors are fixed at **2223mm high**
- Dropdown is calculated from remaining height (currently **{dropdown}mm**)
- Side build-out applied: **{side_desc}**

**Confirm dropdown and build-out before ordering.**
"""
        )

# Diagram
fig = draw_wardrobe_diagram(
    opening_width_mm=row["Width_mm"],
    opening_height_mm=row["Height_mm"],
    bottom_thk_mm=BOTTOM_LINER_THICKNESS,
    side_left_mm=side_left,
    side_right_mm=side_right,
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
    st.write(f"**Build-out applied:** {side_desc}")
    st.write(f"**Issue:** {row.get('Issue','—')}")
    st.write("---")
    st.write(f"**Doors:** {doors_used}")
    st.write(f"**Door height:** {int(row.get('Door_Height_mm', FIXED_DOOR_HEIGHT))} mm")
    if hb == "Bloor":
        st.write("**Door width (each):** Refer to floor plan")
    else:
        st.write(f"**Door width (each):** {int(row.get('Door_Width_mm', 0))} mm")
    st.write("---")
    st.write(f"**Dropdown height:** {int(row.get('Dropdown_Height_mm', 0))} mm")
    st.write(f"**Side build-out:** {side_left}mm (left), {side_right}mm (right)")
    st.write(f"**Net width:** {int(row.get('Net_Width_mm', 0))} mm")
    st.caption(
        f"Height stack includes bottom liner ({BOTTOM_LINER_THICKNESS}mm) + trackset ({TRACKSET_HEIGHT}mm)."
    )
