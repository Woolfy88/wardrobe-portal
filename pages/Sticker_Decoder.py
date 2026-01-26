import re
import difflib
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Sticker Decoder", layout="wide")

st.title("Sticker Decoder")
st.caption("Take/upload a sticker photo, rotate if needed, and the portal will decode the code using your reference table.")

# ============================================================
# SETTINGS
# ============================================================
CSV_PATH = "data/sticker_decode.csv"

FUZZY_AUTO_ACCEPT = 0.86
FUZZY_SUGGEST = 0.65

ALLOWED_CHARS_REGEX = r"[^A-Z0-9\-\_\/\.]"
DEFAULT_OCR_MODE = "Balanced"

# ============================================================
# SESSION STATE
# ============================================================
if "sticker_rotation" not in st.session_state:
    st.session_state.sticker_rotation = 0

def rot_left():
    st.session_state.sticker_rotation = (st.session_state.sticker_rotation - 90) % 360

def rot_right():
    st.session_state.sticker_rotation = (st.session_state.sticker_rotation + 90) % 360

def rot_reset():
    st.session_state.sticker_rotation = 0

# ============================================================
# LOAD DECODE TABLE
# ============================================================
@st.cache_data
def load_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    if "code" not in df.columns:
        raise ValueError("CSV must include a 'code' column.")
    if "meaning" not in df.columns:
        df["meaning"] = ""
    df["code_norm"] = (
        df["code"].astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", "", regex=True)
    )
    return df

df = load_table(CSV_PATH)
KNOWN_CODES = df["code_norm"].tolist()

# ============================================================
# OCR HELPERS
# ============================================================
def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    gray = ImageOps.grayscale(img)

    w, h = gray.size
    if max(w, h) < 1200:
        gray = gray.resize((w * 2, h * 2))

    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)
    return ImageEnhance.Contrast(gray).enhance(2.2)

def ocr_read_text(pil_img: Image.Image) -> str:
    import pytesseract
    config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/."
    return pytesseract.image_to_string(pil_img, config=config) or ""

def extract_candidates(txt: str) -> list[str]:
    txt = txt.upper().replace("\n", " ")
    tokens = re.split(r"\s+", txt)

    candidates = []
    for t in tokens:
        t = re.sub(ALLOWED_CHARS_REGEX, "", t).strip(" -_/.")
        if len(t) >= 4 and (re.search(r"\d", t) or "-" in t):
            candidates.append(t)

    collapsed = re.sub(ALLOWED_CHARS_REGEX, "", txt.replace(" ", ""))
    if len(collapsed) >= 4:
        candidates.append(collapsed)

    return list(dict.fromkeys(candidates))

def best_code_match(candidate: str):
    if candidate in KNOWN_CODES:
        return candidate, 1.0

    best, score = None, 0.0
    for kc in KNOWN_CODES:
        s = difflib.SequenceMatcher(None, candidate, kc).ratio()
        if s > score:
            best, score = kc, s
    return best, score

def lookup_row(code_norm: str):
    hit = df[df["code_norm"] == code_norm]
    return None if hit.empty else hit.iloc[0]

def rotate_image(img: Image.Image, deg: int) -> Image.Image:
    return img if deg == 0 else img.rotate(deg, expand=True)

# ============================================================
# ROTATE BAR
# ============================================================
st.markdown("### Rotate (tap until text is horizontal)")

r1, r2, r3, r4 = st.columns([1.2, 1.2, 1, 1.2])
r1.button("⟲ ROTATE LEFT", on_click=rot_left, use_container_width=True)
r2.button("ROTATE RIGHT ⟳", on_click=rot_right, use_container_width=True)
r3.button("RESET", on_click=rot_reset, use_container_width=True)

r4.markdown(
    f"""
    <div style="text-align:center;border:1px solid #e5e5e5;border-radius:14px;padding:10px;">
      <div style="font-size:14px;color:#666;">Rotation</div>
      <div style="font-size:32px;font-weight:800;">{st.session_state.sticker_rotation}°</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# ============================================================
# MAIN LAYOUT
# ============================================================
left, right = st.columns([1.15, 1])

with left:
    st.subheader("Photo")
    cam = st.camera_input("Use camera (mobile)")
    up = st.file_uploader("Or upload photo", type=["jpg", "jpeg", "png", "webp"])

    with st.expander("Advanced (crop)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        crop_x = c1.number_input("x", min_value=0, value=0, step=10)
        crop_y = c2.number_input("y", min_value=0, value=0, step=10)
        crop_w = c3.number_input("w", min_value=0, value=0, step=10)
        crop_h = c4.number_input("h", min_value=0, value=0, step=10)
else:
    crop_x = crop_y = crop_w = crop_h = 0

with right:
    st.subheader("Result")
    st.caption("Rotate until the preview looks horizontal. Manual override is below if needed.")

# ============================================================
# IMAGE PIPELINE
# ============================================================
img = None
if cam is not None:
    img = Image.open(cam)
elif up is not None:
    img = Image.open(up)

ocr_raw = ""
candidates = []
best_code = None
best_score = 0.0
rotated_img = None

if img is not None:
    if crop_w > 0 and crop_h > 0:
        img = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

    rotated_img = rotate_image(img, st.session_state.sticker_rotation)
    prepped = preprocess_for_ocr(rotated_img)
    ocr_raw = ocr_read_text(prepped)
    candidates = extract_candidates(ocr_raw)

    for c in candidates:
        m, s = best_code_match(c)
        if s > best_score:
            best_code, best_score = m, s

# ============================================================
# RESULT + MANUAL ENTRY (RIGHT)
# ============================================================
with right:
    manual = st.text_input(
        "Manual entry (override if OCR struggles)",
        placeholder="e.g. SSP-2400-NK"
    )

    final_code = ""
    source = ""

    if manual.strip():
        final_code = manual.strip().upper()
        source = "Manual"
    elif best_code and best_score >= FUZZY_AUTO_ACCEPT:
        final_code = best_code
        source = f"OCR ({best_score:.2f})"
    else:
        source = "OCR (needs confirmation)"

    st.markdown(f"**Source:** {source}")

    if final_code:
        st.markdown(
            f"""
            <div style="border:1px solid #e5e5e5;border-radius:16px;padding:14px;margin-top:10px;">
              <div style="font-size:14px;color:#666;">Detected code</div>
              <div style="font-size:34px;font-weight:900;">{final_code}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        row = lookup_row(final_code)
        if row is not None:
            st.markdown(
                f"""
                <div style="border:1px solid #e5e5e5;border-radius:16px;padding:14px;margin-top:12px;">
                  <div style="font-size:14px;color:#666;">Meaning</div>
                  <div style="font-size:22px;font-weight:700;">{row['meaning']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.warning("Code not found in decode table.")
    else:
        if best_code and best_score >= FUZZY_SUGGEST:
            st.warning("Likely match found – please confirm.")
            st.markdown(f"Suggested: `{best_code}` ({best_score:.2f})")
        else:
            st.info("Rotate, take a closer photo, or use manual entry.")

# ============================================================
# PREVIEW
# ============================================================
if rotated_img is not None:
    st.divider()
    st.subheader("Preview (after rotate)")
    st.image(rotated_img, use_container_width=True)
