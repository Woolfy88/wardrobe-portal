import streamlit as st
import numpy as np
from PIL import Image, ImageOps

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Woodwork Colour Checker", layout="wide")

st.title("Woodwork Colour Checker")
st.caption(
    "Take a photo (or upload one). This tool estimates the dominant colour and "
    "matches it to your internal product colour names."
)

# ============================================================
# COLOUR PALETTE (YOUR INTERNAL NAMES + RGB)
# ============================================================
PALETTE = [
    {"name": "Onyx",        "rgb": (78, 84, 82)},
    {"name": "Pebble Grey", "rgb": (156, 156, 156)},
]

# ============================================================
# COLOUR SPACE HELPERS (RGB -> Lab for perceptual matching)
# ============================================================
def _srgb_to_linear(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def rgb_to_xyz(rgb):
    rgb = np.array(rgb, dtype=np.float32)
    r, g, b = _srgb_to_linear(rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return np.array([x, y, z], dtype=np.float32)

def xyz_to_lab(xyz):
    ref = np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)
    xyz = xyz / ref

    def f(t):
        delta = 6 / 29
        return np.where(t > delta**3, np.cbrt(t), (t / (3 * delta**2)) + (4 / 29))

    fx, fy, fz = f(xyz[0]), f(xyz[1]), f(xyz[2])
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return np.array([L, a, b], dtype=np.float32)

def rgb_to_lab(rgb):
    return xyz_to_lab(rgb_to_xyz(rgb))

# Precompute palette in Lab space
for p in PALETTE:
    p["lab"] = rgb_to_lab(p["rgb"])

# ============================================================
# DOMINANT COLOUR EXTRACTION (k-means)
# ============================================================
def kmeans_dominant_rgb(pixels_rgb, k=3, iters=12, seed=42):
    rng = np.random.default_rng(seed)
    X = pixels_rgb.astype(np.float32)

    idx = rng.choice(len(X), size=min(k, len(X)), replace=False)
    centers = X[idx].copy()

    for _ in range(iters):
        dists = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1)

        new_centers = []
        for ci in range(len(centers)):
            pts = X[labels == ci]
            new_centers.append(centers[ci] if len(pts) == 0 else pts.mean(axis=0))
        new_centers = np.vstack(new_centers)

        if np.allclose(centers, new_centers, atol=0.5):
            break
        centers = new_centers

    dists = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    labels = np.argmin(dists, axis=1)
    counts = np.bincount(labels, minlength=len(centers))
    dom = np.argmax(counts)

    return centers[dom], counts[dom] / counts.sum()

def clamp_rgb(rgb):
    return tuple(int(max(0, min(255, v))) for v in rgb)

# ============================================================
# IMAGE PIPELINE
# ============================================================
def prep_pixels(img: Image.Image, max_side=520, ignore_glare=True):
    img = ImageOps.exif_transpose(img).convert("RGB")

    w, h = img.size
    scale = max(w, h) / max_side if max(w, h) > max_side else 1.0
    if scale > 1.0:
        img = img.resize((int(w / scale), int(h / scale)))

    arr = np.asarray(img, dtype=np.uint8).reshape(-1, 3)

    if ignore_glare:
        brightness = arr.mean(axis=1)
        arr = arr[brightness < 245]

    return arr, img

def match_palette(dominant_rgb):
    dom_lab = rgb_to_lab(dominant_rgb)

    rows = []
    for p in PALETTE:
        dist = float(np.linalg.norm(dom_lab - p["lab"]))
        rows.append((p["name"], p["rgb"], dist))

    rows.sort(key=lambda x: x[2])

    def dist_to_score(d):
        return float(np.clip(1.0 - (d / 35.0), 0.0, 1.0))

    top = [
        {"name": n, "rgb": rgb, "dist": d, "score": dist_to_score(d)}
        for n, rgb, d in rows[:5]
    ]

    return top[0], top

def confidence_label(score):
    if score >= 0.80:
        return "High"
    if score >= 0.60:
        return "Medium"
    return "Low"

# ============================================================
# UI
# ============================================================
left, right = st.columns([1.15, 1])

with left:
    st.subheader("1) Take / upload photo")

    cam = st.camera_input(
        "Use camera (mobile)",
        help="Take a close-up of the product surface. Avoid glare if possible."
    )
    up = st.file_uploader(
        "Or upload a photo",
        type=["jpg", "jpeg", "png", "webp"]
    )

    ignore_glare = st.toggle(
        "Ignore bright reflections (recommended)",
        value=True
    )

with right:
    st.subheader("Colour reference")
    cols = st.columns(len(PALETTE))
    for i, p in enumerate(PALETTE):
        r, g, b = p["rgb"]
        cols[i].markdown(
            f"""
            <div style="border:1px solid #ddd;border-radius:14px;padding:12px;">
              <div style="height:32px;border-radius:10px;
                   background:rgb({r},{g},{b});
                   border:1px solid #eee;"></div>
              <div style="font-size:13px;margin-top:8px;text-align:center;">
                {p['name']}
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.divider()

# Pick image source
img = None
if cam is not None:
    img = Image.open(cam)
elif up is not None:
    img = Image.open(up)

if img is None:
    st.info("Take or upload a photo to identify the colour.")
    st.stop()

pixels, preview = prep_pixels(img, ignore_glare=ignore_glare)

if len(pixels) < 200:
    st.warning("Photo too dark/bright to analyse reliably. Try another photo.")
    st.stop()

dom_rgb, dom_share = kmeans_dominant_rgb(pixels)
dom_rgb = clamp_rgb(dom_rgb)

best, top = match_palette(dom_rgb)
conf = confidence_label(best["score"])

c1, c2 = st.columns([1.1, 1])

with c1:
    st.subheader("Photo preview")
    st.image(preview, use_container_width=True)

with c2:
    st.subheader("Result")
    st.markdown(
        f"""
        **Closest match:** {best['name']}  
        **Confidence:** {conf}  
        **Dominant colour share:** {dom_share:.0%}
        """
    )

    r, g, b = dom_rgb
    st.markdown(
        f"""
        <div style="display:flex;gap:14px;align-items:center;margin-top:14px;">
          <div style="width:60px;height:60px;border-radius:16px;
               border:1px solid #ddd;
               background:rgb({r},{g},{b});"></div>
          <div style="font-size:12px;color:#666;">
            Estimated dominant colour
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("#### Match ranking")
    for i, t in enumerate(top, start=1):
        rr, gg, bb = t["rgb"]
        st.markdown(
            f"{i}) **{t['name']}** — score {t['score']:.2f} "
            f"<span style='display:inline-block;width:14px;height:14px;"
            f"border-radius:4px;border:1px solid #ddd;"
            f"background:rgb({rr},{gg},{bb});'></span>",
            unsafe_allow_html=True
        )

    st.caption(
        "Tip: Best results come from a close-up photo in daylight, "
        "with minimal background and little reflection from packaging."
    )
