"""Redactly CLI entry point."""

import os
import sys

from redactly.ocr import extract_text_boxes
from redactly.redact import redact_boxes
from redactly.classify import filter_sensitive_boxes


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_image>")
        return

    image_path = sys.argv[1]
    boxes = extract_text_boxes(image_path)
    sensitive_boxes = filter_sensitive_boxes(boxes)

    print("Flagged as sensitive:")
    for box in sensitive_boxes:
        print(f"  {box['text']!r}")

    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", f"redacted_{os.path.basename(image_path)}")
    redact_boxes(image_path, sensitive_boxes, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
