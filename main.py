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

    # vision brain: Gemini looks at the whole image directly
    vision_boxes = detect_sensitive_regions(image_path)

    print("Flagged by regex (OCR text):")
    for box in regex_boxes:
        print(f"  {box['text']!r}")

    print("Flagged by Gemini (vision):")
    for box in vision_boxes:
        print(f"  {box['label']}")

    all_boxes = regex_boxes + vision_boxes

    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", f"redacted_{os.path.basename(image_path)}")
    redact_boxes(image_path, all_boxes, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
