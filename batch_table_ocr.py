#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Table OCR for Taiwanese financial forms with red stamps removed.

Usage:
  python batch_table_ocr.py --input ./scans --output ./csv_out

Dependencies (pip):
  pip install opencv-python pillow pytesseract numpy pandas pdf2image
System deps:
  - Tesseract OCR installed (https://tesseract-ocr.github.io/)
  - For PDF support, poppler may be required by pdf2image (macOS: brew install poppler)
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytesseract
import pandas as pd

try:
    from pdf2image import convert_from_path
    HAS_PDF = True
except Exception:
    HAS_PDF = False


def remove_red_stamp(bgr):
    """Inpaint red-ish regions (two hue ranges) to suppress stamps/seals."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # broader red mask
    lower1 = np.array([0, 30, 30])
    upper1 = np.array([20, 255, 255])
    lower2 = np.array([160, 30, 30])
    upper2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
    # optional dilation to cover edges of stamp strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    mask = cv2.dilate(mask, kernel, iterations=1)
    inpainted = cv2.inpaint(bgr, mask, 5, cv2.INPAINT_TELEA)
    return inpainted


def deskew(gray):
    """Deskew using minAreaRect of detected text edges."""
    edges = cv2.Canny(gray, 50, 150)
    coords = np.column_stack(np.where(edges > 0))
    if coords.shape[0] < 50:
        return gray
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated


def detect_table_lines(bin_img):
    """Detect vertical and horizontal table lines via morphology."""
    h, w = bin_img.shape
    # vertical
    v_kernel_len = max(10, w // 150)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))
    v_temp = cv2.erode(bin_img, v_kernel, iterations=1)
    v_lines = cv2.dilate(v_temp, v_kernel, iterations=2)

    # horizontal
    h_kernel_len = max(10, h // 150)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
    h_temp = cv2.erode(bin_img, h_kernel, iterations=1)
    h_lines = cv2.dilate(h_temp, h_kernel, iterations=2)

    grid = cv2.addWeighted(v_lines, 0.5, h_lines, 0.5, 0.0)
    return v_lines, h_lines, grid


def extract_cells_from_grid(grid):
    """Find cell boxes by intersecting grid lines and contouring rectangles."""
    # make thin grid
    grid_bin = cv2.threshold(grid, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    contours, _ = cv2.findContours(grid_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 40 or h < 20:  # filter tiny noise
            continue
        aspect = w / float(h)
        if aspect < 0.6 or aspect > 40:  # heuristic
            continue
        boxes.append((x, y, w, h))

    # Remove duplicates by IoU merge
    def iou(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        xa1, ya1, xa2, ya2 = ax, ay, ax+aw, ay+ah
        xb1, yb1, xb2, yb2 = bx, by, bx+bw, by+bh
        inter_w = max(0, min(xa2, xb2) - max(xa1, xb1))
        inter_h = max(0, min(ya2, yb2) - max(ya1, yb1))
        inter = inter_w * inter_h
        if inter == 0: return 0.0
        union = aw*ah + bw*bh - inter
        return inter / union

    merged = []
    for b in sorted(boxes, key=lambda t: (t[1], t[0])):
        if not merged:
            merged.append(b)
            continue
        if iou(merged[-1], b) > 0.5:
            # expand last
            x1, y1, w1, h1 = merged[-1]
            x2, y2, w2, h2 = b
            nx1, ny1 = min(x1, x2), min(y1, y2)
            nx2, ny2 = max(x1+w1, x2+w2), max(y1+h1, y2+h2)
            merged[-1] = (nx1, ny1, nx2-nx1, ny2-ny1)
        else:
            merged.append(b)

    # cluster rows by y
    merged = sorted(merged, key=lambda t: (t[1], t[0]))
    rows = []
    for b in merged:
        placed = False
        for row in rows:
            if abs(row[0][1] - b[1]) < 15:  # row tolerance
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])

    # sort each row by x
    for row in rows:
        row.sort(key=lambda t: t[0])

    # keep only rows with multiple cells (actual table rows)
    rows = [row for row in rows if len(row) >= 5]
    return rows


def ocr_cell(img_gray, box, lang):
    x,y,w,h = box
    pad = 4
    x0 = max(x+1, x - pad)
    y0 = max(y+1, y - pad)
    x1 = min(img_gray.shape[1]-1, x + w + pad)
    y1 = min(img_gray.shape[0]-1, y + h + pad)
    roi = img_gray[y0:y1, x0:x1]
    roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    cfg = '--psm 6'
    try:
        text = pytesseract.image_to_string(roi, lang=lang, config=cfg)
    except pytesseract.TesseractError:
        text = pytesseract.image_to_string(roi, lang='eng', config=cfg)
    # cleanup
    text = text.replace('\n', ' ').replace('\r', ' ').strip()
    return text


def process_image(path, out_csv, lang_preference=('chi_tra+eng','chi_sim+eng','eng')):
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise RuntimeError(f"Cannot read image: {path}")
    bgr = remove_red_stamp(bgr)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = deskew(gray)

    # binarize
    bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 25, 15)

    v_lines, h_lines, grid = detect_table_lines(bin_img)
    rows = extract_cells_from_grid(grid)

    # pick language installed
    langs = []
    try:
        avail = pytesseract.get_languages(config='')
    except Exception:
        avail = ['eng']
    for cand in lang_preference:
        sub = [t for t in cand.split('+') if t in avail]
        if sub:
            langs.append('+'.join(sub))
    lang = langs[0] if langs else 'eng'

    data = []
    for row in rows:
        texts = [ocr_cell(gray, box, lang) for box in row]
        # drop very short header rows by heuristic (optional)
        data.append(texts)

    # best-effort: keep first 7 columns (可依需求調整)
    max_cols = max((len(r) for r in data), default=0)
    # If the sheet looks like: 項次,科目,名稱,預算,決算,差額,說明
    headers = ['項次','科目','名稱','112年度決算','112年度預算','差額','說明']
    if max_cols > len(headers):
        headers += [f'欄位{idx}' for idx in range(len(headers)+1, max_cols+1)]

    # normalize row lengths
    norm = []
    for r in data:
        row = r + ['']*(max_cols - len(r))
        norm.append(row[:max_cols])

    df = pd.DataFrame(norm, columns=headers[:max_cols])
    # drop empty lines
    df = df[~(df.astype(str).apply(lambda s: ''.join(s), axis=1).str.strip()=='')]

    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    return df


def convert_pdf(pdf_path, tempdir):
    if not HAS_PDF:
        raise RuntimeError("pdf2image not available. Install pdf2image & poppler to handle PDFs.")
    images = convert_from_path(str(pdf_path), dpi=300)
    out_paths = []
    for i, img in enumerate(images):
        outp = Path(tempdir) / f"{Path(pdf_path).stem}_p{i+1}.png"
        img.save(outp)
        out_paths.append(outp)
    return out_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='Folder containing scans (PNG/JPG/PDF)')
    ap.add_argument('--output', required=True, help='Folder to write CSVs')
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for ext in ('*.png','*.jpg','*.jpeg','*.tif','*.tiff','*.pdf'):
        files += list(in_dir.glob(ext))
    if not files:
        print("No files found in", in_dir)
        sys.exit(0)

    with tempfile.TemporaryDirectory() as td:
        for f in sorted(files):
            try:
                if f.suffix.lower()=='.pdf':
                    pages = convert_pdf(f, td)
                    for p in pages:
                        out_csv = out_dir / (Path(p).stem + '.csv')
                        print("Processing", p)
                        process_image(p, out_csv)
                else:
                    out_csv = out_dir / (f.stem + '.csv')
                    print("Processing", f)
                    process_image(f, out_csv)
            except Exception as e:
                print("ERROR processing", f, ":", e)

if __name__ == '__main__':
    main()
