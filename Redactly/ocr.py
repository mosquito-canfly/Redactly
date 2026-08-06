"""OCR: extract words and bounding boxes from an image using Tesseract."""

import os
import shutil

from PIL import Image
import pytesseract

# pytesseract shells out to the tesseract binary; on Windows it's often
# installed but not added to PATH, so fall back to the default install path.
_DEFAULT_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if shutil.which("tesseract") is None and os.path.exists(_DEFAULT_WINDOWS_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = _DEFAULT_WINDOWS_TESSERACT


def extract_text_boxes(image_path: str) -> list[dict]:
    """Run OCR on an image and return each detected word with its bounding box.

    Each item in the returned list has keys: text, left, top, width, height, conf.
    Empty/whitespace text and non-text regions (conf < 0) are skipped.
    """
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    boxes = []
    for i in range(len(data["text"])):
        text = data["text"][i]
        conf = float(data["conf"][i])

        if not text.strip() or conf < 0:
            continue

        boxes.append({
            "text": text,
            "left": data["left"][i],
            "top": data["top"][i],
            "width": data["width"][i],
            "height": data["height"][i],
            "conf": conf,
        })

    return boxes
