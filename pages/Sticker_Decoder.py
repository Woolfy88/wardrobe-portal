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
st.caption("Take a photo of the sticker code. We'll try to read it and show the plain-English meaning from your reference table.")

# ============================================================
# SETTINGS
# ============================================================
CSV_PATH = "data/sticker_decode.csv"

# If you want to be stricter/looser with fuzzy matches:
FUZZY_AUTO_ACCEPT = 0.86   # if best fuzzy match >= this, we auto-select it
FUZZY_SUGGEST = 0.65       # if best fuzzy match >= this, we suggest it

# Characters we consider plausible for codes (keeps OCR noise down)
ALLOWED_CHARS_REGEX = r"[^A-Z0-9\-\_\/\.]"  # keep A-Z, 0-9, - _ / .

# ============================================================
# LOAD DECODE TABLE
# ============================================================
@st.cache_data
def load_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    # Expected minimum columns
    if "code" not in df.columns:
        raise ValueError("CSV must include a 'code' column (the sticker code).")
    if "meaning" not in df.columns:
        df["meaning"] = ""

    # Normalised key for lookup
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
    """
    Returns a preprocessed image for OCR.
    mode: 'Balanced', 'High contrast', 'Inverted'
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    gray = ImageOps.grayscale(img)

    # Upscale slightly (helps small text)
    w, h = gray.size
    if max(w, h) < 1200:
        scale = 2
        gray = gray.resize((w * scale, h * scale))

    # Denoise + sharpen
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)

    if mode == "High contrast":
        gray = ImageEnhance.Contrast(gray).enhance(2.6)
        arr = np.array(gray)
        t = np.percentile(arr, 55)
        bw = Image.fromarray((arr > t).astype(np.uint8) * 255)
        return bw

    if mode == "Inverted":
        gray = ImageEnhance.Contrast(gray).enhance(2.2)
        inv = ImageOps.invert(gray)
        arr = np.array(inv)
        t = np.percentile(arr, 55)
        bw = Image.fromarray((arr > t).astype(np.uint8) * 255)
        return bw

    # Balanced
    gray = ImageEnhance.Contrast(gray).enhance(2.1)
    return gray


def ocr_read_text(pil_img: Image.Image) -> str:
    """
    OCR using pytesseract.
    """
    try:
        import pytesseract
    except Exception:
        st.error("Missing dependency: pytesseract. Add it to requirements.txt (see below).")
        return ""

    # PSM 6 = assume a block of text; better when no strict rules
    # Whitelist reduces garbage but still allows typical separators
    config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/."

    txt = pytesseract.image_to_string(pil_img, config=config)
    return txt or ""


def normalise_text(txt: str) -> str:
    t = (txt or "").upper()
    t = t.replace("\n", " ").replace("\r", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_candidates(ocr_text: str) -> list[str]:
    """
    From OCR output, extract plausible code-like candidates.
    No hard rules — we extract tokens containing at least one digit or separator,
    and at least 4 characters after cleaning.
    """
    txt = normalise_text(ocr_text)

    # Split into tokens on spaces
    raw_tokens = re.split(r"\s+", txt)

    candidates = []
    for tok in raw_tokens:
        tok = tok.strip().upper()
        # keep only allowed chars
        tok = re.sub(ALLOWED_CHARS_REGEX, "", tok)
        tok = tok.strip(" -_/.")
        if len(tok) < 4:
            continue
        # must contain at least one digit OR a separator (helps avoid plain words)
        if not (re.search(r"\d", tok) or re.search(r"[-_/\.]", tok)):
            continue
        candidates.append(tok)

    # Also try a "collapsed" version removing spaces (sometimes OCR inserts spaces inside a code)
    collapsed = re.sub(r"\s+", "", normalise_text(ocr_text))
    collapsed = re.sub(ALLOWED_CHARS_REGEX, "", collapsed)
    if len(collapsed) >= 4 and (re.search(r"\d", collapsed) or re.search(r"[-_/\.]", collapsed)):
        candidates.append(collapsed.strip(" -_/."))
    # de-dupe preserving order
    seen = set()
    out = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def best_code_match(candidate: str, known_codes: list[str]) -> tuple[str | None, float]:
    """
    Exact match first; then fuzzy match.
    """
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
            best_score = score
            best = kc
    return best, float(best_score)


def lookup_row(code_norm: str) -> pd.Series | None:
    hit = df[df["code_norm"] == code_norm]
    if hit.empty:
        return None
    return hit.iloc[0]


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

    manual = st.text_input("Manual entry (fallback)", placeholder="Type the sticker code if OCR struggles (e.g. SSP-2400-NK)")

with right:
    st.subheader("2) Result")
    st.write("Tips: get close, keep it square-on, tap to focus, avoid glare/reflections.")

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

# OCR pipeline
ocr_raw = ""
candidates = []
best_overall_code = None
best_overall_score = 0.0
best_overall_from = None

if img is not None:
    prepped = preprocess_for_ocr(img, ocr_mode)
    ocr_raw = ocr_read_text(prepped)
    candidates = extract_candidates(ocr_raw)

    # Try each candidate; pick best match against known codes
    for cand in candidates:
        m, s = best_code_match(cand, KNOWN_CODES)
        if s > best_overall_score:
            best_overall_code = m
            best_overall_score = s
            best_overall_from = cand

# Determine final code to use
final_code_norm = ""
source = ""

manual_norm = manual.strip().upper().replace(" ", "")

if manual_norm:
    # If user typed something, prefer it
    final_code_norm = manual_norm
    source = "Manual"
else:
    if best_overall_code and best_overall_score >= FUZZY_AUTO_ACCEPT:
        final_code_norm = best_overall_code
        source = f"OCR (matched {best_overall_score:.2f})"
    else:
        # Don't auto-pick weak matches; show candidates and suggestions instead
        final_code_norm = ""
        source = "OCR (needs confirmation)"

# Present results
with right:
    st.markdown(f"**Source:** {source}")

    if img is not None:
        with st.expander("Show OCR details"):
            st.markdown(f"**OCR raw:** `{normalise_text(ocr_raw)}`")
            st.markdown("**Extracted candidates:**")
            if candidates:
                for c in candidates[:12]:
                    st.code(c)
            else:
                st.write("No candidates extracted — try a tighter crop or different OCR mode.")

            if best_overall_code:
                st.markdown(f"**Best match suggestion:** `{best_overall_code}` (score {best_overall_score:.2f}) from `{best_overall_from}`")

    # If we have a final code (manual or strong OCR)
    if final_code_norm:
        st.markdown(f"**Code:** `{final_code_norm}`")
        row = lookup_row(final_code_norm)
        if row is None:
            st.warning("No exact match found in decode table.")
            # Offer closest suggestion if available
            if best_overall_code and best_overall_score >= FUZZY_SUGGEST:
                st.info(f"Closest known code: `{best_overall_code}` (score {best_overall_score:.2f})")
        else:
            st.markdown(f"**Meaning:** {row.get('meaning','')}")
            # Optional extras (only show if columns exist + non-empty)
            for field in ["product", "colour", "notes"]:
                if field in row.index and str(row[field]).strip():
                    st.markdown(f"**{field.title()}:** {row[field]}")
    else:
        # No final code auto-selected — show suggestions + manual nudge
        if best_overall_code and best_overall_score >= FUZZY_SUGGEST:
            st.warning("We found a likely match, but it needs confirmation.")
            st.markdown(f"Suggested: `{best_overall_code}` (score {best_overall_score:.2f})")
            st.caption("Copy/paste it into Manual entry if it looks right, or retake the photo closer.")
        else:
            st.warning("Couldn’t confidently match a code. Try a tighter crop, another OCR mode, or manual entry.")

# Previews
if img is not None:
    st.divider()
    p1, p2 = st.columns(2)
    with p1:
        st.subheader("Photo (cropped if set)")
        st.image(img, use_container_width=True)
    with p2:
        st.subheader(f"Pre-processed ({ocr_mode})")
        st.image(preprocess_for_ocr(img, ocr_mode), use_container_width=True)
