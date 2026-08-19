"""Redactly CLI entry point."""

import argparse
import os
import sys
import time

from redactly.ocr import extract_text_boxes
from redactly.redact import redact_boxes, filter_boxes_by_targets, DEFAULT_BLUR_RADIUS
from redactly.classify import filter_sensitive_boxes
from redactly.llm import detect_sensitive_regions
from redactly.faces import detect_faces
from redactly.agent import run_agent

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VISION_CALL_DELAY = 1.5  # seconds between Gemini calls in batch mode, avoids free-tier per-minute quota


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Redact sensitive information from a screenshot or a folder of them.")
    parser.add_argument("input", help="path to an input image, or a directory of images")
    parser.add_argument("-o", "--output", help="output path (file mode) or output directory (folder mode); default: output/")
    parser.add_argument("--blur", type=int, default=DEFAULT_BLUR_RADIUS, help="blur strength / Gaussian radius (default: %(default)s)")
    parser.add_argument("--no-vision", action="store_true", help="text only: OCR + regex, skip face detection and Gemini")
    parser.add_argument("--smart", action="store_true", help="also call Gemini vision (catches passwords, names, hard-to-read IDs). Uses quota.")
    parser.add_argument("--targets", choices=["all", "faces", "text"], default="all", help="which detected boxes to blur (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be redacted, but don't blur or save")
    parser.add_argument("--agent", action="store_true", help="let Gemini drive redaction via tool calls instead of the fixed pipeline (single image only)")
    return parser.parse_args(argv)


def print_no_vision_warning() -> None:
    print("=" * 60)
    print("⚠  --no-vision mode: using OCR + regex ONLY (text only).")
    print("   Faces, ID photos, and text that OCR cannot read (e.g. numbers")
    print("   over holograms, stylized fonts) will NOT be detected or redacted.")
    print("   Use the default mode (or --smart) for fuller redaction. Review before sharing.")
    print("=" * 60)


def print_free_mode_note() -> None:
    print("Free mode: catches emails, cards, IPs, and faces. May MISS passwords, "
          "names, and hard-to-read IDs. Use --smart for full coverage (uses Gemini quota).")


def detect_regex_boxes(image_path: str) -> list[dict]:
    """OCR the image and return only the boxes flagged as sensitive by regex."""
    return filter_sensitive_boxes(extract_text_boxes(image_path))


def detect_face_boxes(image_path: str, skip: bool) -> list[dict]:
    """Run local face detection, unless skipped. Never raises."""
    if skip:
        return []
    try:
        return detect_faces(image_path)
    except Exception as e:
        print(f"WARNING: face detection crashed unexpectedly: {e}")
        return []


def detect_vision_boxes(image_path: str, skip: bool) -> list[dict]:
    """Ask Gemini for sensitive regions, unless skipped. Never raises."""
    if skip:
        return []
    try:
        return detect_sensitive_regions(image_path)
    except Exception as e:
        print(f"WARNING: vision detection crashed unexpectedly: {e}")
        return []


def print_summary(
    regex_boxes: list[dict],
    face_boxes: list[dict],
    gemini_boxes: list[dict],
    use_faces: bool,
    use_gemini: bool,
) -> None:
    print("Flagged by regex (OCR text):")
    if not regex_boxes:
        print("  (none)")
    for box in regex_boxes:
        print(f"  {box['text']!r}")

    if use_faces:
        print("Flagged by face detection:")
        if not face_boxes:
            print("  (none)")
        for box in face_boxes:
            print(f"  {box}")
    else:
        print("Face detection: skipped (--no-vision)")

    if use_gemini:
        print("Flagged by Gemini (vision):")
        for box in gemini_boxes:
            print(f"  {box['label']}")
        if not gemini_boxes:
            print("=" * 60)
            print("WARNING: Gemini detection found nothing (or failed).")
            print("Passwords, names, and hard-to-read text may NOT be redacted.")
            print("Output may be INCOMPLETE — review before sharing.")
            print("=" * 60)
    else:
        print("Gemini detection: skipped (use --smart to enable)")


def process_image(
    image_path: str,
    output_path: str,
    blur: int,
    use_faces: bool,
    use_gemini: bool,
    dry_run: bool,
    targets: str = "all",
) -> bool:
    """Run the full detect+redact pipeline on one image. Returns True on success."""
    try:
        regex_boxes = detect_regex_boxes(image_path)
        face_boxes = detect_face_boxes(image_path, skip=not use_faces)
        gemini_boxes = detect_vision_boxes(image_path, skip=not use_gemini)
        print_summary(regex_boxes, face_boxes, gemini_boxes, use_faces, use_gemini)

        all_boxes = filter_boxes_by_targets(regex_boxes + face_boxes + gemini_boxes, targets)

        if dry_run:
            print(f"Dry run: {len(all_boxes)} region(s) would be redacted (targets={targets}). No file written.")
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


def run_batch(input_dir: str, output_dir: str, blur: int, use_faces: bool, use_gemini: bool, dry_run: bool, targets: str = "all") -> None:
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

        if process_image(image_path, output_path, blur, use_faces, use_gemini, dry_run, targets):
            succeeded += 1
            status = "done"
        else:
            failed += 1
            status = "FAILED"
        print(f"[{i}/{total}] {name} ... {status}")

        # face detection is free/local, no delay needed; only Gemini is rate-limited
        if use_gemini and i < total:
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

    if args.agent:
        if os.path.isdir(args.input):
            print("Error: --agent only supports a single image, not a folder.")
            sys.exit(1)
        output_path = args.output or os.path.join("output", f"redacted_{os.path.basename(args.input)}")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        run_agent(args.input, output_path)
        return

    # --no-vision = text only; default = text + faces; --smart = text + faces + Gemini.
    # --no-vision always wins over --smart (it's the explicit "opt out of everything but text" flag).
    use_faces = not args.no_vision
    use_gemini = args.smart and not args.no_vision

    if args.no_vision:
        print_no_vision_warning()
    elif not args.smart:
        print_free_mode_note()

    if os.path.isdir(args.input):
        output_dir = args.output or "output"
        run_batch(args.input, output_dir, args.blur, use_faces, use_gemini, args.dry_run, args.targets)
        return

    output_path = args.output or os.path.join("output", f"redacted_{os.path.basename(args.input)}")
    if not process_image(args.input, output_path, args.blur, use_faces, use_gemini, args.dry_run, args.targets):
        sys.exit(1)


if __name__ == "__main__":
    main()
