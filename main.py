"""Redactly CLI entry point."""

import argparse
import os
import sys

from redactly.ocr import extract_text_boxes
from redactly.redact import redact_boxes, DEFAULT_BLUR_RADIUS
from redactly.classify import filter_sensitive_boxes
from redactly.llm import detect_sensitive_regions


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Redact sensitive information from a screenshot.")
    parser.add_argument("input", help="path to the input image")
    parser.add_argument("-o", "--output", help="output path (default: output/redacted_<filename>)")
    parser.add_argument("--blur", type=int, default=DEFAULT_BLUR_RADIUS, help="blur strength / Gaussian radius (default: %(default)s)")
    parser.add_argument("--no-vision", action="store_true", help="skip the Gemini vision step; use only OCR + regex")
    parser.add_argument("--dry-run", action="store_true", help="print what would be redacted, but don't blur or save")
    return parser.parse_args(argv)


def detect_regex_boxes(image_path: str) -> list[dict]:
    """OCR the image and return only the boxes flagged as sensitive by regex."""
    return filter_sensitive_boxes(extract_text_boxes(image_path))


def detect_vision_boxes(image_path: str, skip: bool) -> list[dict]:
    """Ask Gemini for sensitive regions, unless skipped. Never raises."""
    if skip:
        return []
    try:
        return detect_sensitive_regions(image_path)
    except Exception as e:
        print(f"WARNING: vision detection crashed unexpectedly: {e}")
        return []


def print_summary(regex_boxes: list[dict], vision_boxes: list[dict], vision_skipped: bool) -> None:
    print("Flagged by regex (OCR text):")
    if not regex_boxes:
        print("  (none)")
    for box in regex_boxes:
        print(f"  {box['text']!r}")

    if vision_skipped:
        print("Vision detection: skipped (--no-vision)")
    else:
        print("Flagged by Gemini (vision):")
        for box in vision_boxes:
            print(f"  {box['label']}")

    if not vision_skipped and not vision_boxes:
        print("=" * 60)
        print("WARNING: Vision-based detection found nothing (or failed).")
        print("Faces and other image-based sensitive data may NOT be redacted.")
        print("Output is INCOMPLETE — review before sharing.")
        print("=" * 60)


def main():
    args = parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}")
        sys.exit(1)

    regex_boxes = detect_regex_boxes(args.input)
    vision_boxes = detect_vision_boxes(args.input, skip=args.no_vision)
    print_summary(regex_boxes, vision_boxes, vision_skipped=args.no_vision)

    all_boxes = regex_boxes + vision_boxes

    if args.dry_run:
        print(f"Dry run: {len(all_boxes)} region(s) would be redacted. No file written.")
        return

    output_path = args.output or os.path.join("output", f"redacted_{os.path.basename(args.input)}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    redact_boxes(args.input, all_boxes, output_path, blur_radius=args.blur)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
