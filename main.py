"""Redactly CLI entry point."""

import os
import sys

from redactly.ocr import extract_text_boxes
from redactly.redact import redact_boxes
from redactly.classify import filter_sensitive_boxes
from redactly.llm import detect_sensitive_regions


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_image>")
        return

    image_path = sys.argv[1]

    # regex brain: OCR words, then flag the sensitive-looking ones
    ocr_boxes = extract_text_boxes(image_path)
    regex_boxes = filter_sensitive_boxes(ocr_boxes)

    # vision brain: Gemini looks at the whole image directly. It already
    # catches its own errors and returns [] rather than raising, but we
    # wrap defensively anyway and treat "no boxes" as a reason to warn,
    # since we can't otherwise tell "found nothing" apart from "failed".
    try:
        vision_boxes = detect_sensitive_regions(image_path)
    except Exception as e:
        vision_boxes = []
        print(f"WARNING: vision detection crashed unexpectedly: {e}")

    print("Flagged by regex (OCR text):")
    for box in regex_boxes:
        print(f"  {box['text']!r}")

    print("Flagged by Gemini (vision):")
    for box in vision_boxes:
        print(f"  {box['label']}")

    if not vision_boxes:
        print("=" * 60)
        print("WARNING: Vision-based detection found nothing (or failed).")
        print("Faces and other image-based sensitive data may NOT be redacted.")
        print("Output is INCOMPLETE — review before sharing.")
        print("=" * 60)

    all_boxes = regex_boxes + vision_boxes

    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", f"redacted_{os.path.basename(image_path)}")
    redact_boxes(image_path, all_boxes, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
