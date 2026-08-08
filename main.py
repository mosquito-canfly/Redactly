"""Redactly CLI entry point."""

import argparse
import os
import sys
import time

from redactly.ocr import extract_text_boxes
from redactly.redact import redact_boxes, DEFAULT_BLUR_RADIUS
from redactly.classify import filter_sensitive_boxes
from redactly.llm import detect_sensitive_regions

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VISION_CALL_DELAY = 1.5  # seconds between Gemini calls in batch mode, avoids free-tier per-minute quota


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Redact sensitive information from a screenshot or a folder of them.")
    parser.add_argument("input", help="path to an input image, or a directory of images")
    parser.add_argument("-o", "--output", help="output path (file mode) or output directory (folder mode); default: output/")
    parser.add_argument("--blur", type=int, default=DEFAULT_BLUR_RADIUS, help="blur strength / Gaussian radius (default: %(default)s)")
    parser.add_argument("--no-vision", action="store_true", help="skip the Gemini vision step; use only OCR + regex")
    parser.add_argument("--dry-run", action="store_true", help="print what would be redacted, but don't blur or save")
    return parser.parse_args(argv)


def print_no_vision_warning() -> None:
    print("=" * 60)
    print("⚠  --no-vision mode: using OCR + regex ONLY.")
    print("   Faces, ID photos, and text that OCR cannot read (e.g. numbers")
    print("   over holograms, stylized fonts) will NOT be detected or redacted.")
    print("   Use without --no-vision for full redaction. Review before sharing.")
    print("=" * 60)


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


def process_image(image_path: str, output_path: str, blur: int, skip_vision: bool, dry_run: bool) -> bool:
    """Run the full detect+redact pipeline on one image. Returns True on success."""
    try:
        regex_boxes = detect_regex_boxes(image_path)
        vision_boxes = detect_vision_boxes(image_path, skip=skip_vision)
        print_summary(regex_boxes, vision_boxes, vision_skipped=skip_vision)

        all_boxes = regex_boxes + vision_boxes

        if dry_run:
            print(f"Dry run: {len(all_boxes)} region(s) would be redacted. No file written.")
            return True

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        redact_boxes(image_path, all_boxes, output_path, blur_radius=blur)
        print(f"Saved: {output_path}")
        return True
    except Exception as e:
        print(f"WARNING: failed to process {image_path}: {e}")
        return False


def find_image_files(directory: str) -> list[str]:
    """Return top-level (non-recursive) image files in a directory, sorted by name."""
    files = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
            files.append(path)
    return files


def run_batch(input_dir: str, output_dir: str, blur: int, skip_vision: bool, dry_run: bool) -> None:
    image_files = find_image_files(input_dir)
    if not image_files:
        print(f"No image files found in {input_dir}")
        return

    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    succeeded = failed = 0
    total = len(image_files)
    for i, image_path in enumerate(image_files, start=1):
        name = os.path.basename(image_path)
        print(f"[{i}/{total}] processing {name}...")
        output_path = os.path.join(output_dir, f"redacted_{name}")

        if process_image(image_path, output_path, blur, skip_vision, dry_run):
            succeeded += 1
            status = "done"
        else:
            failed += 1
            status = "FAILED"
        print(f"[{i}/{total}] {name} ... {status}")

        if not skip_vision and i < total:
            time.sleep(VISION_CALL_DELAY)

    print("=" * 60)
    print(f"Batch complete: {succeeded} succeeded, {failed} failed.")
    if not dry_run:
        print(f"Outputs saved to: {output_dir}")
    print("=" * 60)


def main():
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input path not found: {args.input}")
        sys.exit(1)

    if args.no_vision:
        print_no_vision_warning()

    if os.path.isdir(args.input):
        output_dir = args.output or "output"
        run_batch(args.input, output_dir, args.blur, args.no_vision, args.dry_run)
        return

    output_path = args.output or os.path.join("output", f"redacted_{os.path.basename(args.input)}")
    if not process_image(args.input, output_path, args.blur, args.no_vision, args.dry_run):
        sys.exit(1)


if __name__ == "__main__":
    main()
