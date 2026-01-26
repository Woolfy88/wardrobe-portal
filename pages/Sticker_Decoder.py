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
st.caption("Upload/take a sticker photo, rotate if needed, then decode the code using your reference table.")

# ============================================================
# SETTINGS
# ============================================================
CSV_PATH = "data/sticker_decode.csv"

FUZZY_AUTO_ACCEPT = 0.86   # auto-select if best match >= this
FUZZY_SUGGEST = 0.65       # show suggestion if best match >= this

ALLOWED_CHARS_REGEX = r"[^A-Z0-9\-\_\/\.]"  # keep A-Z, 0-9, - _ / .
DEFAULT_OCR_MODE = "Balanced"

# ============================================================
# SESSION STATE
# ============================================================
if "sticker_rotation" not in st.session_state:
    st.session_state.sticker_rotation = 0  # 0, 90, 180, 270

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
# OCR HELPERS
# ============================================================
def preprocess_for_ocr(img: Image.Image, mode: str) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    gray = ImageOps.grayscale(img)

    # upscale small images (helps small text)
    w, h = gray.size
    if max(w, h) < 1200:
        gray = gray.resize((w * 2, h * 2))

    # denoise + sharpen
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

    # Balanced
    return ImageEnhance.Contrast(gray).enhance(2.2)

def ocr_read_text(pil_img: Image.Image) -> str:
    try:
        import pytesseract
    except Exception:
        st.error("Missing dependency: pytesseract. Add `pytesseract` to requirements.txt (and `tesseract-ocr` to packages.txt on Streamlit Cloud).")
        return ""

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
        # keep tokens that look "code-ish"
        if not (re.search(r"\d", tok) or re.search(r"[-_/\.]", tok)):
            continue
        candidates.append(tok)

    # also try collapsed version (OCR sometimes inserts spaces)
    collapsed = re.sub(r"\s+", "", txt)
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

def best_code_match(candidate: str) -> tuple[str | None, float]:
    cand = (candidate or "").strip().upper().replace(" ", "")
    if not cand:
        return None, 0.0

    if cand in KNOWN_CODES:
        return cand, 1.0

    best = None
    best_score = 0.0
    for kc in KNOWN_CODES:
        s = difflib.SequenceMatcher(None, cand, kc).ratio()
        if s > best_score:
            best, best_score = kc, s
    return best, float(best_score)

def lookup_row(code_norm: str) -> pd.Series | None:
    hit = df[df["code_norm"] == code_norm]
    return None if hit.empty else hit.iloc[0]

def rotate_image(img: Image.Image, degrees: int) -> Image.Image:
    degrees = int(degrees) % 360
    return img if degrees == 0 else img.rotate(degrees, expand=True)

# ============================================================
# BIG ROTATE BAR (TOP)
# ============================================================
st.markdown("### Rotate (tap until the sticker text looks horizontal)")

rb1, rb2, rb3, rb4 = st.columns([1.3, 1.3, 1.0, 1.2])
rb1.button("⟲ ROTATE LEFT", on_click=rot_left, use_container_width=True)
rb2.button("ROTATE RIGHT ⟳", on_click=rot_right, use_container_width=True)
rb3.button("RESET", on_click=rot_reset, use_container_width=True)
rb4.markdown(
    f"""
    <div style="text-align:center;border:1px solid #e5e5e5;border-radius:14px;padding:10px;">
      <div style="font-size:14px;color:#666;">Rotation</div>
      <div style="font-size:34px;font-weight:900;line-height:1.0;">{st.session_state.sticker_rotation}°</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ============================================================
# MAIN LAYOUT
# ============================================================
# Defaults (keep page uncluttered)
crop_x = crop_y = crop_w = crop_h = 0
ocr_mode = DEFAULT_OCR_MODE
show_debug = False

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Photo")
    cam = st.camera_input("Use camera (mobile)")
    up = st.file_uploader("Or upload photo", type=["jpg", "jpeg", "png", "webp"])

    with st.expander("Advanced (crop / OCR mode)", expanded=False):
        st.markdown("**Crop (optional):** Use only if there’s lots of background.")
        c1, c2, c3, c4 = st.columns(4)
        crop_x = c1.number_input("x", min_value=0, value=0, step=10)
        crop_y = c2.number_input("y", min_value=0, value=0, step=10)
        crop_w = c3.number_input("w", min_value=0, value=0, step=10, help="0 = no crop")
        crop_h = c4.number_input("h", min_value=0, value=0, step=10, help="0 = no crop")

        ocr_mode = st.selectbox("OCR mode", ["Balanced", "High contrast", "Inverted"], index=0)
        show_debug = st.toggle("Show OCR debug panel", value=False)

with right:
    st.subheader("Result")
    st.caption("If OCR struggles: rotate, take a closer photo, or use manual override below.")

# ============================================================
# IMAGE PICK + PROCESS
# ============================================================
img = None
if cam is not None:
    img = Image.open(cam)
elif up is not None:
    img = Image.open(up)

# manual entry moved to RIGHT
with right:
    manual = st.text_input(
        "Manual entry (override)",
        placeholder="e.g. SSP-2400-NK"
    )

if img is None and not manual.strip():
    st.info("Upload/take a photo, or enter the code manually.")
    st.stop()

rotated_img = None
prepped_img = None
ocr_raw = ""
candidates = []
best_suggest_code = None
best_suggest_score = 0.0
best_suggest_from = None

if img is not None:
    # Optional crop
    if crop_w > 0 and crop_h > 0:
        W, H = img.size
        x1 = min(max(0, int(crop_x)), W)
        y1 = min(max(0, int(crop_y)), H)
        x2 = min(W, int(crop_x + crop_w))
        y2 = min(H, int(crop_y + crop_h))
        if x2 > x1 and y2 > y1:
            img = img.crop((x1, y1, x2, y2))

    rotated_img = rotate_image(img, st.session_state.sticker_rotation)
    prepped_img = preprocess_for_ocr(rotated_img, ocr_mode)
    ocr_raw = ocr_read_text(prepped_img)
    candidates = extract_candidates(ocr_raw)

    for cand in candidates:
        m, s = best_code_match(cand)
        if s > best_suggest_score:
            best_suggest_code, best_suggest_score, best_suggest_from = m, s, cand

# ============================================================
# FINAL DECISION + DISPLAY (BIG TEXT)
# ============================================================
manual_norm = manual.strip().upper().replace(" ", "")
final_code = ""
source = ""

if manual_norm:
    final_code = manual_norm
    source = "Manual"
else:
    if best_suggest_code and best_suggest_score >= FUZZY_AUTO_ACCEPT:
        final_code = best_suggest_code
        source = f"OCR (match {best_suggest_score:.2f})"
    else:
        source = "OCR (needs confirmation)"

with right:
    st.markdown(f"**Source:** {source}")

    if final_code:
        st.markdown(
            f"""
            <div style="border:1px solid #e5e5e5;border-radius:16px;padding:14px;margin-top:10px;">
              <div style="font-size:14px;color:#666;">Code</div>
              <div style="font-size:36px;font-weight:950;letter-spacing:0.5px;">{final_code}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        row = lookup_row(final_code)
        if row is None:
            st.warning("Code not found in decode table.")
            if best_suggest_code and best_suggest_score >= FUZZY_SUGGEST and not manual_norm:
                st.info(f"Closest known code: `{best_suggest_code}` (score {best_suggest_score:.2f})")
        else:
            meaning = str(row.get("meaning", "")).strip()
            st.markdown(
                f"""
                <div style="border:1px solid #e5e5e5;border-radius:16px;padding:14px;margin-top:12px;">
                  <div style="font-size:14px;color:#666;">Meaning</div>
                  <div style="font-size:24px;font-weight:800;line-height:1.25;">{meaning}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for field in ["product", "colour", "notes"]:
                if field in row.index and str(row[field]).strip():
                    st.markdown(f"**{field.title()}:** {row[field]}")
    else:
        if best_suggest_code and best_suggest_score >= FUZZY_SUGGEST:
            st.warning("Likely match found — please confirm.")
            st.markdown(f"Suggested: `{best_suggest_code}` (score {best_suggest_score:.2f})")
        else:
            st.info("Rotate, take a closer photo, or use manual entry.")

# ============================================================
# PREVIEW (helps rotation)
# ============================================================
if rotated_img is not None:
    st.divider()
    st.subheader("Preview (after rotate)")
    st.image(rotated_img, use_container_width=True)

    if show_debug and prepped_img is not None:
        st.subheader("OCR debug (pre-processed)")
        st.image(prepped_img, use_container_width=True)
        st.markdown("**OCR raw:**")
        st.code(normalise_text(ocr_raw)[:600])
        st.markdown("**Candidates:**")
        if candidates:
            for c in candidates[:15]:
                st.code(c)
        else:
            st.write("No candidates extracted.")
