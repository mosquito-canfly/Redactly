"""OCR: extract words and bounding boxes from an image using Tesseract."""

import os
import shutil

from PIL import Image
import pytesseract

from redactly.preprocess import preprocess_for_ocr

# pytesseract shells out to the tesseract binary; on Windows it's often
# installed but not added to PATH, so fall back to the default install path.
_DEFAULT_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if shutil.which("tesseract") is None and os.path.exists(_DEFAULT_WINDOWS_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = _DEFAULT_WINDOWS_TESSERACT


def extract_text_boxes(image_path: str, preprocess: bool = True) -> list[dict]:
    """Run OCR on an image and return each detected word with its bounding box.

    By default OCR runs on a preprocessed (possibly upscaled) version of the
    image for better accuracy, with box coordinates scaled back to match the
    original. Pass preprocess=False to OCR the raw image instead — sometimes
    preprocessing garbles text (e.g. drops a dot) that the raw image reads fine.

    Each item in the returned list has keys: text, left, top, width, height, conf.
    Empty/whitespace text and non-text regions (conf < 0) are skipped.
    """
    if preprocess:
        original_width = Image.open(image_path).width
        image = preprocess_for_ocr(image_path)
        scale = image.width / original_width
    else:
        image = Image.open(image_path)
        scale = 1

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    boxes = []
    for i in range(len(data["text"])):
        text = data["text"][i]
        conf = float(data["conf"][i])

        if not text.strip() or conf < 0:
            continue

        boxes.append({
            "text": text,
            "left": round(data["left"][i] / scale),
            "top": round(data["top"][i] / scale),
            "width": round(data["width"][i] / scale),
            "height": round(data["height"][i] / scale),
            "conf": conf,
        })

    return boxes
