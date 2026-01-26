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
st.caption("Take a photo of the sticker code. Rotate if needed, then OCR will read it and show the meaning from your decode table.")

# ============================================================
# SETTINGS
# ============================================================
CSV_PATH = "data/sticker_decode.csv"

FUZZY_AUTO_ACCEPT = 0.86   # auto-select if best match >= this
FUZZY_SUGGEST = 0.65       # show suggestion if best match >= this

ALLOWED_CHARS_REGEX = r"[^A-Z0-9\-\_\/\.]"  # keep A-Z, 0-9, - _ / .

# ============================================================
# SESSION STATE (rotation)
# ============================================================
if "sticker_rotation" not in st.session_state:
    st.session_state.sticker_rotation = 0  # degrees: 0, 90, 180, 270

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
        df["code"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", "", regex=True)
    )
    return df

try:
    df = load_table(CSV_PATH)
except Exception as e:
    st.error(f"Couldn't load `{CSV_PATH}`. Error: {e}")
    st.stop()

KNOWN_CODES = df["code_norm"].tolist()

# ============================================================
# OCR + PREPROCESSING
# ============================================================
def preprocess_for_ocr(img: Image.Image, mode: str) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    gray = ImageOps.grayscale(img)

    # Upscale small images (helps small text)
    w, h = gray.size
    if max(w, h) < 1200:
        gray = gray.resize((w * 2, h * 2))

    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)

    if mode == "High contrast":
        gray = ImageEnhance.Contrast(gray).enhance(2.8)
        arr = np.array(gray)
        t = np.percentile(arr, 55)
        return Image.fromarray((arr > t).astype(np.uint8) * 255)

    if mode == "Inverted":
        gray = ImageEnhance.Contrast(gray).enhance(2.4)
        inv = ImageOps.invert(gray)
        arr = np.array(inv)
        t = np.percentile(arr, 55)
        return Image.fromarray((arr > t).astype(np.uint8) * 255)

    return ImageEnhance.Contrast(gray).enhance(2.2)

def ocr_read_text(pil_img: Image.Image) -> str:
    try:
        import pytesseract
    except Exception:
        st.error("Missing dependency: pytesseract. Add it to requirements.txt (and packages.txt with tesseract-ocr if using Streamlit Cloud).")
        return ""

    # PSM 6 = general layout; good when sticker codes vary / might be multi-line
    config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/."
    return pytesseract.image_to_string(pil_img, config=config) or ""

def normalise_text(txt: str) -> str:
    t = (txt or "").upper()
    t = t.replace("\n", " ").replace("\r", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_candidates(ocr_text: str) -> list[str]:
    txt = normalise_text(ocr_text)
    raw_tokens = re.split(r"\s+", txt)

    candidates = []
    for tok in raw_tokens:
        tok = tok.strip().upper()
        tok = re.sub(ALLOWED_CHARS_REGEX, "", tok)
        tok = tok.strip(" -_/.")
        if len(tok) < 4:
            continue
        if not (re.search(r"\d", tok) or re.search(r"[-_/\.]", tok)):
            continue
        candidates.append(tok)

    collapsed = re.sub(r"\s+", "", normalise_text(ocr_text))
    collapsed = re.sub(ALLOWED_CHARS_REGEX, "", collapsed).strip(" -_/.")
    if len(collapsed) >= 4 and (re.search(r"\d", collapsed) or re.search(r"[-_/\.]", collapsed)):
        candidates.append(collapsed)

    # de-dupe preserving order
    seen = set()
    out = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out

def best_code_match(candidate: str, known_codes: list[str]) -> tuple[str | None, float]:
    if not candidate:
        return None, 0.0
    cand = candidate.strip().upper().replace(" ", "")
    if cand in known_codes:
        return cand, 1.0

    best = None
    best_score = 0.0
    for kc in known_codes:
        score = difflib.SequenceMatcher(None, cand, kc).ratio()
        if score > best_score:
            best_score, best = score, kc
    return best, float(best_score)

def lookup_row(code_norm: str) -> pd.Series | None:
    hit = df[df["code_norm"] == code_norm]
    return None if hit.empty else hit.iloc[0]

def rotate_image(img: Image.Image, degrees: int) -> Image.Image:
    if degrees % 360 == 0:
        return img
    return img.rotate(degrees, expand=True)

# ============================================================
# UI
# ============================================================
left, right = st.columns([1.15, 1])

with left:
    st.subheader("1) Take / upload sticker photo")
    cam = st.camera_input("Use camera (mobile)")
    up = st.file_uploader("Or upload photo", type=["jpg", "jpeg", "png", "webp"])

    st.markdown("**Optional crop (recommended):** crop tightly around the sticker text.")
    c1, c2, c3, c4 = st.columns(4)
    crop_x = c1.number_input("x", min_value=0, value=0, step=10)
    crop_y = c2.number_input("y", min_value=0, value=0, step=10)
    crop_w = c3.number_input("w", min_value=0, value=0, step=10, help="0 = no crop")
    crop_h = c4.number_input("h", min_value=0, value=0, step=10, help="0 = no crop")

    ocr_mode = st.selectbox("OCR mode", ["Balanced", "High contrast", "Inverted"], index=0)

    st.markdown("**Rotate (for vertical stickers):**")
    r1, r2, r3, r4 = st.columns([1, 1, 1, 1.2])
    r1.button("⟲ Rotate Left", on_click=rot_left, use_container_width=True)
    r2.button("Rotate Right ⟳", on_click=rot_right, use_container_width=True)
    r3.button("Reset", on_click=rot_reset, use_container_width=True)
    r4.markdown(f"<div style='padding-top:8px;font-weight:600;'>Now: {st.session_state.sticker_rotation}°</div>", unsafe_allow_html=True)

    manual = st.text_input("Manual entry (fallback)", placeholder="Type the sticker code (e.g. SSP-2400-NK)")

with right:
    st.subheader("2) Result")
    st.write("Tip: get close, square-on, tap to focus, avoid glare. If it reads rubbish, rotate until the text looks horizontal.")

# Pick image source
img = None
if cam is not None:
    img = Image.open(cam)
elif up is not None:
    img = Image.open(up)

if img is None and not manual.strip():
    st.info("Take/upload a sticker photo, or type the code manually.")
    st.stop()

# Apply crop
if img is not None and crop_w > 0 and crop_h > 0:
    W, H = img.size
    x1 = min(max(0, int(crop_x)), W)
    y1 = min(max(0, int(crop_y)), H)
    x2 = min(W, int(crop_x + crop_w))
    y2 = min(H, int(crop_y + crop_h))
    if x2 > x1 and y2 > y1:
        img = img.crop((x1, y1, x2, y2))

# Rotate per button state
ocr_raw = ""
candidates = []
best_suggest_code = None
best_suggest_score = 0.0
best_suggest_from = None
prepped_img = None
rotated_img = None

if img is not None:
    rotated_img = rotate_image(img, int(st.session_state.sticker_rotation))
    prepped_img = preprocess_for_ocr(rotated_img, ocr_mode)
    ocr_raw = ocr_read_text(prepped_img)
    candidates = extract_candidates(ocr_raw)

    for cand in candidates:
        m, s = best_code_match(cand, KNOWN_CODES)
        if s > best_suggest_score:
            best_suggest_code, best_suggest_score, best_suggest_from = m, s, cand

# Decide final code
manual_norm = manual.strip().upper().replace(" ", "")
final_code_norm = ""
source = ""

if manual_norm:
    final_code_norm = manual_norm
    source = "Manual"
else:
    if best_suggest_code and best_suggest_score >= FUZZY_AUTO_ACCEPT:
        final_code_norm = best_suggest_code
        source = f"OCR (rotation {st.session_state.sticker_rotation}°, match {best_suggest_score:.2f})"
    else:
        source = f"OCR (rotation {st.session_state.sticker_rotation}°) needs confirmation"

# Display results
with right:
    st.markdown(f"**Source:** {source}")

    with st.expander("Show OCR details"):
        st.markdown(f"**Rotation used:** {st.session_state.sticker_rotation}°")
        st.markdown(f"**OCR raw:** `{normalise_text(ocr_raw)}`")
        st.markdown("**Extracted candidates:**")
        if candidates:
            for c in candidates[:15]:
                st.code(c)
        else:
            st.write("No candidates extracted — try a tighter crop, different OCR mode, or rotate again.")

        if best_suggest_code:
            st.markdown(f"**Best suggestion:** `{best_suggest_code}` (score {best_suggest_score:.2f}) from `{best_suggest_from}`")

    if final_code_norm:
        st.markdown(f"**Code:** `{final_code_norm}`")
        row = lookup_row(final_code_norm)
        if row is None:
            st.warning("No exact match found in decode table.")
            if best_suggest_code and best_suggest_score >= FUZZY_SUGGEST:
                st.info(f"Closest known code: `{best_suggest_code}` (score {best_suggest_score:.2f})")
        else:
            st.markdown(f"**Meaning:** {row.get('meaning','')}")
            for field in ["product", "colour", "notes"]:
                if field in row.index and str(row[field]).strip():
                    st.markdown(f"**{field.title()}:** {row[field]}")
    else:
        if best_suggest_code and best_suggest_score >= FUZZY_SUGGEST:
            st.warning("Likely match found, but needs confirmation.")
            st.markdown(f"Suggested: `{best_suggest_code}` (score {best_suggest_score:.2f})")
            st.caption("If it looks right, type/paste it into Manual entry, or rotate/crop and retake.")
        else:
            st.warning("Couldn’t confidently match a code. Rotate until text looks horizontal, crop tighter, try another OCR mode, or use manual entry.")

# Previews
if rotated_img is not None and prepped_img is not None:
    st.divider()
    p1, p2 = st.columns(2)
    with p1:
        st.subheader("Photo preview (after rotate)")
        st.image(rotated_img, use_container_width=True)
    with p2:
        st.subheader(f"Pre-processed for OCR ({ocr_mode})")
        st.image(prepped_img, use_container_width=True)
