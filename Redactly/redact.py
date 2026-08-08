"""Redaction: pad/merge/blur given boxes on an image."""

from PIL import Image, ImageFilter

_DEFAULT_PADDING = 10
DEFAULT_BLUR_RADIUS = 15


def pad_box(box: dict, padding: int, img_width: int, img_height: int) -> dict:
    """Return a copy of box expanded by padding pixels, clamped to the image bounds."""
    left = max(0, box["left"] - padding)
    top = max(0, box["top"] - padding)
    right = min(img_width, box["left"] + box["width"] + padding)
    bottom = min(img_height, box["top"] + box["height"] + padding)
    return {**box, "left": left, "top": top, "width": right - left, "height": bottom - top}


def _overlaps(a: dict, b: dict) -> bool:
    """True if two boxes overlap or touch (shared edge)."""
    a_right, a_bottom = a["left"] + a["width"], a["top"] + a["height"]
    b_right, b_bottom = b["left"] + b["width"], b["top"] + b["height"]
    return not (a_right < b["left"] or b_right < a["left"] or a_bottom < b["top"] or b_bottom < a["top"])


def _merge_two(a: dict, b: dict) -> dict:
    """Combine two boxes into their bounding rectangle, joining labels if present."""
    left = min(a["left"], b["left"])
    top = min(a["top"], b["top"])
    right = max(a["left"] + a["width"], b["left"] + b["width"])
    bottom = max(a["top"] + a["height"], b["top"] + b["height"])
    merged = {"left": left, "top": top, "width": right - left, "height": bottom - top}

    labels = [box["label"] for box in (a, b) if "label" in box]
    if labels:
        merged["label"] = "+".join(dict.fromkeys(labels))  # dedupe, keep order
    return merged


def merge_overlapping_boxes(boxes: list[dict]) -> list[dict]:
    """Repeatedly merge overlapping/touching boxes until none remain."""
    # ponytail: O(n^3) worst case, fine for the handful of boxes per screenshot;
    # switch to a sweep-line merge if box counts ever get into the hundreds.
    boxes = list(boxes)
    merged_any = True
    while merged_any:
        merged_any = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if _overlaps(boxes[i], boxes[j]):
                    combined = _merge_two(boxes[i], boxes[j])
                    boxes = [b for k, b in enumerate(boxes) if k not in (i, j)] + [combined]
                    merged_any = True
                    break
            if merged_any:
                break
    return boxes


def redact_boxes(
    image_path: str,
    boxes: list[dict],
    output_path: str,
    padding: int = _DEFAULT_PADDING,
    blur_radius: int = DEFAULT_BLUR_RADIUS,
) -> None:
    """Pad, merge, and blur each box region on the image; save the result to output_path."""
    image = Image.open(image_path)

    padded = [pad_box(box, padding, image.width, image.height) for box in boxes]
    merged = merge_overlapping_boxes(padded)

    for box in merged:
        left, top = box["left"], box["top"]
        right, bottom = left + box["width"], top + box["height"]
        region = image.crop((left, top, right, bottom))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        image.paste(blurred, (left, top))

    image.save(output_path)


if __name__ == "__main__":
    # ponytail: smallest possible self-check, not a test suite
    assert pad_box({"left": 5, "top": 5, "width": 10, "height": 10}, 10, 100, 100) == \
        {"left": 0, "top": 0, "width": 25, "height": 25}
    assert pad_box({"left": 90, "top": 90, "width": 5, "height": 5}, 10, 100, 100) == \
        {"left": 80, "top": 80, "width": 20, "height": 20}

    overlapping = [{"left": 0, "top": 0, "width": 10, "height": 10}, {"left": 5, "top": 5, "width": 10, "height": 10}]
    assert merge_overlapping_boxes(overlapping) == [{"left": 0, "top": 0, "width": 15, "height": 15}]

    separate = [{"left": 0, "top": 0, "width": 5, "height": 5}, {"left": 50, "top": 50, "width": 5, "height": 5}]
    assert len(merge_overlapping_boxes(separate)) == 2

    img = Image.new("RGB", (100, 100), "white")
    img.save("_selftest.png")
    redact_boxes("_selftest.png", [{"left": 10, "top": 10, "width": 30, "height": 30}], "_selftest_out.png")
    assert Image.open("_selftest_out.png").size == (100, 100)
    import os
    os.remove("_selftest.png")
    os.remove("_selftest_out.png")
    print("redact.py self-check passed")
