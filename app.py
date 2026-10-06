import os
import re
import shutil

import cv2
import numpy as np
import pandas as pd
import pytesseract
import streamlit as st
from PIL import Image
from pytesseract import Output

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ReceiptOCR AI",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 ReceiptOCR AI")
st.subheader("AI-Powered Receipt & Bill Analyzer")

st.write(
    "Upload a receipt or bill to extract the date, invoice number, "
    "GSTIN, line items, tax and total, then verify the maths."
)

# ============================================================
# TESSERACT SETUP
# ============================================================

tesseract_path = shutil.which("tesseract")

# Common Windows install locations if Tesseract is not on PATH
WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

if not tesseract_path:
    for candidate in WINDOWS_PATHS:
        if os.path.exists(candidate):
            tesseract_path = candidate
            break

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

try:
    pytesseract.get_tesseract_version()
except Exception:
    st.error(
        "❌ Tesseract OCR is not installed or not found. "
        "Install it from https://github.com/UB-Mannheim/tesseract/wiki "
        "(default folder: C:\\Program Files\\Tesseract-OCR), "
        "then restart the app."
    )
    st.stop()

# ============================================================
# REGEX PATTERNS
# ============================================================

PRICE = r"(\d{1,3}(?:,\d{3})+[.,]\d{2}|\d+[.,]\d{2})(?!\d)"

DATE_PATTERNS = [
    r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}\s?(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
    r"[A-Z]*\.?,?\s?\d{2,4}\b",
]

TIME_PATTERN = r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?\b"

GSTIN_PATTERN = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"

INVOICE_PATTERN = (
    r"(?:INVOICE|INV|BILL|RECEIPT|ORDER)[ \t]*"
    r"(?:NO|NUMBER|NUM|#)\.?[ \t]*[:#\-]*[ \t]*([A-Z0-9][A-Z0-9\-/]{2,})"
)

SKIP_WORDS = (
    "TOTAL", "SUBTOTAL", "SUB TOTAL", "GST", "CGST", "SGST", "IGST",
    "TAX", "VAT", "CASH", "CARD", "CHANGE", "ROUND", "DISCOUNT",
    "TENDER", "PAID", "BALANCE", "AMOUNT", "UPI", "SAVINGS",
)

TAX_WORDS = ("GST", "CGST", "SGST", "IGST", "TAX", "VAT")

# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def prepare_ocr_images(image):

    img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    enlarged = cv2.resize(
        gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
    )

    denoised = cv2.fastNlMeansDenoising(enlarged, None, 15, 7, 21)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    otsu = cv2.threshold(
        enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )

    return [enhanced, otsu, adaptive]

# ============================================================
# OCR (LINE-BASED)
# ============================================================

def ocr_lines(img, psm):
    """Run Tesseract and group words into text lines."""

    data = pytesseract.image_to_data(
        img,
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT
    )

    grouped = {}

    for i in range(len(data["text"])):

        word = data["text"][i].strip()

        if not word:
            continue

        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = 0

        if conf < 30:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        grouped.setdefault(key, []).append(
            (data["left"][i], word, conf)
        )

    lines = []

    for words in grouped.values():
        words.sort(key=lambda w: w[0])
        text = " ".join(w[1] for w in words)
        conf = sum(w[2] for w in words) / len(words)
        lines.append({"text": text, "confidence": conf})

    return lines


def perform_ocr(images):
    """Try each preprocessed image and keep the best result."""

    best_lines = []
    best_score = -1

    for img in images:

        for psm in (6, 4):

            try:
                lines = ocr_lines(img, psm)
            except Exception:
                continue

            score = sum(
                len(line["text"]) * line["confidence"]
                for line in lines
            )

            if score > best_score:
                best_score = score
                best_lines = lines

    return best_lines

# ============================================================
# HELPERS
# ============================================================

def normalize(text):
    return re.sub(r"\s+", " ", str(text).upper()).strip()


def to_amount(value):
    """Convert '1,234.50' or '12,50' to a float."""

    value = str(value).replace(" ", "")

    if re.search(r",\d{2}$", value) and "." not in value:
        value = value[:-3] + "." + value[-2:]

    value = value.replace(",", "")

    try:
        return float(value)
    except ValueError:
        return None


def last_amount(line):
    matches = re.findall(PRICE, line)
    return to_amount(matches[-1]) if matches else None

# ============================================================
# FIELD EXTRACTION
# ============================================================

def extract_header_fields(lines):

    full_text = "\n".join(normalize(l["text"]) for l in lines)

    date = None
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, full_text)
        if m:
            date = m.group()
            break

    time_match = re.search(TIME_PATTERN, full_text)
    gstin_match = re.search(GSTIN_PATTERN, full_text)
    invoice_match = re.search(INVOICE_PATTERN, full_text)

    # Merchant name: first reasonably confident line with letters
    merchant = None
    for line in lines[:6]:
        text = line["text"].strip()
        if (
            len(re.findall(r"[A-Za-z]", text)) >= 3
            and line["confidence"] >= 50
            and not re.search(r"\d{5,}", text)
        ):
            merchant = text
            break

    return {
        "Merchant": merchant,
        "Date": date,
        "Time": time_match.group().strip() if time_match else None,
        "Invoice No": invoice_match.group(1) if invoice_match else None,
        "GSTIN": gstin_match.group() if gstin_match else None,
    }


def extract_items(lines):

    items = []

    for line in lines:

        text = line["text"].strip()
        upper = normalize(text)

        if any(word in upper for word in SKIP_WORDS):
            continue

        amount = last_amount(text)

        if amount is None:
            continue

        # Name = everything before the first price-like token
        name = re.split(PRICE, text)[0]
        name = re.sub(r"[^A-Za-z0-9 .&/\-]", " ", name).strip()

        if len(re.findall(r"[A-Za-z]", name)) < 2:
            continue

        qty = 1
        qty_pattern = r"\b(\d{1,3})\s*[xX*]\b|\b[xX*]\s*(\d{1,3})\b"
        qty_match = re.search(qty_pattern, name)
        if qty_match:
            qty = int(qty_match.group(1) or qty_match.group(2))
            name = re.sub(qty_pattern, "", name).strip()

        items.append({
            "Item": name,
            "Qty": qty,
            "Amount": amount,
        })

    return items


def extract_totals(lines):

    subtotal = None
    tax_total = 0.0
    tax_lines = []
    total = None
    grand_total = None

    for line in lines:

        upper = normalize(line["text"])
        amount = last_amount(line["text"])

        if amount is None:
            continue

        if "SUB" in upper and "TOTAL" in upper:
            subtotal = amount

        elif any(w in upper for w in ("GRAND TOTAL", "NET AMOUNT",
                                      "AMOUNT DUE", "NET PAYABLE",
                                      "TOTAL PAYABLE")):
            grand_total = amount

        elif "TOTAL" in upper and not any(w in upper for w in TAX_WORDS):
            total = amount

        elif any(w in upper for w in TAX_WORDS):
            tax_total += amount
            tax_lines.append((line["text"].strip(), amount))

    final_total = grand_total if grand_total is not None else total

    return subtotal, tax_total, tax_lines, final_total

# ============================================================
# COMPUTER VISION ANALYSIS
# ============================================================

def analyze_layout(image):

    img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # --- Blur / sharpness ---
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    # --- Brightness / contrast ---
    brightness = float(gray.mean())
    contrast = float(gray.std())

    # --- Skew estimate from text pixels ---
    binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(np.where(binary > 0))
    skew = 0.0

    if len(coords) > 100:
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        skew = -(90 + angle) if angle < -45 else -angle
        if abs(skew) > 45:
            skew = 0.0

    # --- Horizontal separator lines (----, ====) ---
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 50, 150)

    min_len = max(60, img.shape[1] // 4)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=60, minLineLength=min_len, maxLineGap=15
    )

    separators = 0

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = map(int, np.asarray(line).reshape(-1))
            if abs(x2 - x1) > min_len and abs(y2 - y1) < 6:
                separators += 1

    # --- Barcode / QR hint: dense vertical-stripe regions ---
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=-1)
    diff = cv2.convertScaleAbs(cv2.subtract(grad_x, grad_y))
    blurred = cv2.blur(diff, (9, 9))
    thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)[1]
    closed = cv2.morphologyEx(
        thresh, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    )
    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    barcode_like = sum(
        1 for c in contours
        if cv2.contourArea(c) > 2000
        and cv2.boundingRect(c)[2] > cv2.boundingRect(c)[3] * 1.5
    )

    return {
        "sharpness": sharpness,
        "brightness": brightness,
        "contrast": contrast,
        "skew": skew,
        "separators": separators,
        "barcode_like": barcode_like,
    }

# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📤 Upload Receipt / Bill Image",
    type=["png", "jpg", "jpeg"]
)

# ============================================================
# MAIN PROGRAM
# ============================================================

if uploaded_file:

    try:
        image = Image.open(uploaded_file).convert("RGB")
    except Exception as error:
        st.error(f"Could not open the image: {error}")
        st.stop()

    st.divider()
    st.header("📷 Uploaded Receipt")

    left, right = st.columns([1, 2])

    with left:
        st.image(image, use_container_width=True)

    # --------------------------------------------------------
    # OCR + VISION
    # --------------------------------------------------------

    with st.spinner("🤖 Reading receipt text..."):
        ocr_images = prepare_ocr_images(image)
        lines = perform_ocr(ocr_images)

    with st.spinner("👁️ Analysing image quality and layout..."):
        layout = analyze_layout(image)

    with right:

        st.header("📄 OCR Result")

        if lines:
            st.success(f"{len(lines)} text lines detected!")
            st.text("\n".join(l["text"] for l in lines))
        else:
            st.warning(
                "No readable text detected. Try a sharper, "
                "well-lit, flat photo of the receipt."
            )

    if not lines:
        st.stop()

    # --------------------------------------------------------
    # RECEIPT DETAILS
    # --------------------------------------------------------

    st.divider()
    st.header("🏪 Receipt Details")

    header = extract_header_fields(lines)

    cols = st.columns(len(header))

    for col, (label, value) in zip(cols, header.items()):
        col.metric(label, value if value else "—")

    # --------------------------------------------------------
    # LINE ITEMS
    # --------------------------------------------------------

    st.divider()
    st.header("🛒 Line Items")

    items = extract_items(lines)

    if items:
        df = pd.DataFrame(items)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download items as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="receipt_items.csv",
            mime="text/csv"
        )
    else:
        df = pd.DataFrame(columns=["Item", "Qty", "Amount"])
        st.info("No reliable line items detected.")

    # --------------------------------------------------------
    # TOTALS
    # --------------------------------------------------------

    st.divider()
    st.header("💰 Totals & Tax")

    subtotal, tax_total, tax_lines, final_total = extract_totals(lines)

    t1, t2, t3 = st.columns(3)

    t1.metric("Subtotal", f"{subtotal:,.2f}" if subtotal is not None else "—")
    t2.metric("Tax", f"{tax_total:,.2f}" if tax_lines else "—")
    t3.metric("Total", f"{final_total:,.2f}" if final_total is not None else "—")

    for text, amount in tax_lines:
        st.write(f"🏛️ {text} → {amount:,.2f}")

    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    st.divider()
    st.header("🧮 Math Verification")

    if items and final_total is not None:

        items_sum = float(df["Amount"].sum())

        base = subtotal if subtotal is not None else items_sum
        expected = base + tax_total

        st.write(f"Sum of detected items: **{items_sum:,.2f}**")
        st.write(f"Subtotal + tax: **{expected:,.2f}**")
        st.write(f"Printed total: **{final_total:,.2f}**")

        gap = abs(expected - final_total)

        if gap <= 1.0:
            st.success("✅ The numbers add up (within rounding).")
        elif abs(items_sum - final_total) <= 1.0:
            st.success("✅ Items add up to the printed total.")
        else:
            st.warning(
                f"⚠️ Mismatch of {gap:,.2f}. Either OCR missed an item "
                "or misread a digit — check the receipt manually."
            )

    else:
        st.info(
            "Both line items and a printed total are needed "
            "for verification."
        )

    # --------------------------------------------------------
    # IMAGE QUALITY
    # --------------------------------------------------------

    st.divider()
    st.header("👁️ Image Quality & Layout")

    q1, q2, q3, q4 = st.columns(4)

    q1.metric("Sharpness", f"{layout['sharpness']:.0f}")
    q2.metric("Brightness", f"{layout['brightness']:.0f}")
    q3.metric("Skew", f"{layout['skew']:.1f}°")
    q4.metric("Separator lines", layout["separators"])

    if layout["sharpness"] < 100:
        st.warning("📉 Image looks blurry — OCR accuracy may suffer.")

    if layout["brightness"] < 70:
        st.warning("🌑 Image is quite dark — try better lighting.")
    elif layout["brightness"] > 220:
        st.warning("☀️ Image is overexposed — reduce glare.")

    if abs(layout["skew"]) > 5:
        st.warning(
            f"📐 Receipt is tilted by about {layout['skew']:.1f}° — "
            "straighten it for better results."
        )

    if layout["barcode_like"]:
        st.info("▮▯▮ A barcode / QR-like region was detected.")

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    st.divider()
    st.header("💡 Observations")

    if header["GSTIN"]:
        st.success("🧾 GSTIN found — this looks like a GST invoice.")
    else:
        st.info("No GSTIN detected (not all receipts carry one).")

    if items:
        priciest = df.loc[df["Amount"].idxmax()]
        st.write(
            f"💸 Most expensive item: **{priciest['Item']}** "
            f"({priciest['Amount']:,.2f})"
        )

    st.divider()

    st.success("🎯 ReceiptOCR AI analysis completed!")

    st.caption(
        "ReceiptOCR AI combines Tesseract OCR with OpenCV image "
        "analysis. OCR reads the text and amounts, while OpenCV "
        "checks sharpness, lighting, skew and layout. Always verify "
        "important figures against the original receipt."
    )
