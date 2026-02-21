"""
PDF Syllabus OCR Pipeline (No Poppler Required)
------------------------------------------------
Steps:
  1. Convert each PDF page to image using PyMuPDF (no poppler needed!)
  2. Enhance the image step-by-step, stopping when quality threshold is reached
  3. Run EasyOCR on each enhanced image
  4. Save extracted text to a .txt file

Requirements:
    pip install pymupdf easyocr opencv-python Pillow numpy

Usage:
    python pdf_ocr_pipeline.py                         # uses default INPUT_PDF below
    python pdf_ocr_pipeline.py "F:\\AAI syllabus.pdf"  # pass PDF as argument
"""

import os
import sys
import cv2
import numpy as np
import easyocr
import fitz  # pymupdf
from PIL import Image, ImageEnhance

# ─────────────────────────────────────────────
# CONFIG  (edit these as needed)
# ─────────────────────────────────────────────
INPUT_PDF          = r"F:\AAI syllabus.pdf"    # default PDF path
OUTPUT_DIR         = r"F:\output_images"       # folder to save enhanced images
OUTPUT_TXT         = r"F:\extracted_text.txt"  # output text file
ZOOM               = 2                         # PDF to image zoom level
MAX_WIDTH          = 2000                      # max image width (memory safety)
LANGUAGES          = ['en']                    # EasyOCR languages
GPU                = False                     # set True if CUDA GPU available
SAVE_IMAGES        = True                      # save enhanced images

# ── Enhancement threshold settings ──────────
# Laplacian variance measures image sharpness.
# Higher score = sharper image.
# Typical ranges:
#   < 100  → blurry / low quality
#   100–500 → decent quality
#   500–1000 → good quality
#   > 1000  → very sharp (usually max needed for OCR)
QUALITY_THRESHOLD  = 800   # stop enhancing once this score is reached
MAX_ENHANCE_PASSES = 5     # hard limit on enhancement passes (safety cap)


# ─────────────────────────────────────────────
# QUALITY SCORE – Laplacian Variance
# ─────────────────────────────────────────────
def get_sharpness_score(gray_img: np.ndarray) -> float:
    """
    Measures image sharpness using Laplacian variance.
    Higher = sharper/clearer image.
    """
    return cv2.Laplacian(gray_img, cv2.CV_64F).var()


# ─────────────────────────────────────────────
# STEP 1 – Convert PDF pages to PIL images
# ─────────────────────────────────────────────
def pdf_to_images(pdf_path: str, zoom: int) -> list:
    print(f"[1] Converting PDF → images (zoom={zoom}x) using PyMuPDF ...")
    doc = fitz.open(pdf_path)
    images = []
    matrix = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
        print(f"    Page {i+1}: {pix.width}x{pix.height} px")

    doc.close()
    print(f"    Total pages found: {len(images)}")
    return images


# ─────────────────────────────────────────────
# STEP 2 – Smart enhancement with threshold
# ─────────────────────────────────────────────
def enhance_image(pil_img: Image.Image, page_num: int, max_width: int) -> np.ndarray:
    """
    Smart enhancement pipeline with quality threshold:
      - Measures sharpness score after each enhancement pass
      - Stops as soon as QUALITY_THRESHOLD is reached (no over-processing)
      - Applies up to MAX_ENHANCE_PASSES if threshold not yet reached
      - Each pass increases contrast, sharpness, and applies CLAHE
    """
    print(f"    [2] Enhancing page {page_num} ...")

    # ── Resize to safe size ──────────────────
    w, h = pil_img.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        pil_img = pil_img.resize((max_width, new_h), Image.LANCZOS)
        print(f"       Resized: {w}x{h} → {max_width}x{new_h} px")

    # ── Convert to grayscale OpenCV image ───
    img_cv = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # ── Check initial quality ────────────────
    initial_score = get_sharpness_score(gray)
    print(f"       Initial sharpness score: {initial_score:.1f} (threshold: {QUALITY_THRESHOLD})")

    if initial_score >= QUALITY_THRESHOLD:
        print(f"       ✅ Already meets threshold! Skipping enhancement passes.")
        # Still apply binarisation for clean OCR
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    # ── Enhancement passes ───────────────────
    current = gray.copy()
    clahe   = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    for pass_num in range(1, MAX_ENHANCE_PASSES + 1):

        # Pass 1: CLAHE + denoise
        enhanced = clahe.apply(current)
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # Pass 2+: Also apply unsharp mask (progressive sharpening)
        if pass_num >= 2:
            blurred  = cv2.GaussianBlur(enhanced, (0, 0), 3)
            enhanced = cv2.addWeighted(enhanced, 1.8, blurred, -0.8, 0)

        # Pass 3+: Also boost PIL contrast/sharpness on top
        if pass_num >= 3:
            pil_temp = Image.fromarray(enhanced)
            pil_temp = ImageEnhance.Contrast(pil_temp).enhance(1.5)
            pil_temp = ImageEnhance.Sharpness(pil_temp).enhance(2.0)
            enhanced = np.array(pil_temp)

        score = get_sharpness_score(enhanced)
        print(f"       Pass {pass_num}: sharpness score = {score:.1f}")

        current = enhanced  # update current with enhanced version

        if score >= QUALITY_THRESHOLD:
            print(f"       ✅ Threshold reached at pass {pass_num}! Stopping enhancement.")
            break
        elif pass_num == MAX_ENHANCE_PASSES:
            print(f"       ⚠️  Max passes reached ({MAX_ENHANCE_PASSES}). Using best result.")

    # ── Final Otsu binarisation ──────────────
    _, binary = cv2.threshold(current, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    final_score = get_sharpness_score(binary)
    print(f"       Final sharpness score: {final_score:.1f} | Size: {binary.shape[1]}x{binary.shape[0]} px")

    return binary


# ─────────────────────────────────────────────
# STEP 3 – OCR with EasyOCR
# ─────────────────────────────────────────────
def run_ocr(reader: easyocr.Reader, img: np.ndarray) -> str:
    print(f"    [3] Running EasyOCR ...")
    try:
        results = reader.readtext(img, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception as e:
        print(f"       WARNING: OCR failed on this page → {e}")
        return "[OCR FAILED FOR THIS PAGE]"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else INPUT_PDF

    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found -> {pdf_path}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[Init] Loading EasyOCR for languages: {LANGUAGES} ...")
    reader = easyocr.Reader(LANGUAGES, gpu=GPU)

    pages = pdf_to_images(pdf_path, ZOOM)
    all_text = []

    for i, page_img in enumerate(pages, start=1):
        print(f"\n-- Page {i}/{len(pages)} ------------------------------------------")

        enhanced = enhance_image(page_img, i, MAX_WIDTH)

        if SAVE_IMAGES:
            img_path = os.path.join(OUTPUT_DIR, f"page_{i:03d}_enhanced.png")
            cv2.imwrite(img_path, enhanced)
            print(f"       Saved -> {img_path}")

        text = run_ocr(reader, enhanced)
        all_text.append(
            f"{'='*60}\n  PAGE {i}\n{'='*60}\n{text}\n"
        )
        print(f"       Extracted {len(text)} characters.")

    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(all_text))

    print(f"\n✅ All done!")
    print(f"   Text file    -> {OUTPUT_TXT}")
    print(f"   Images saved -> {OUTPUT_DIR}\\")


if __name__ == "__main__":
    main()
