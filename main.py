"""Redactly CLI entry point."""

import sys

from redactly.ocr import extract_text_boxes


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_image>")
        return

    image_path = sys.argv[1]
    boxes = extract_text_boxes(image_path)

    for box in boxes:
        print(f"{box['text']!r:20} left={box['left']:5} top={box['top']:5} "
              f"width={box['width']:5} height={box['height']:5} conf={box['conf']:.1f}")


if __name__ == "__main__":
    main()
