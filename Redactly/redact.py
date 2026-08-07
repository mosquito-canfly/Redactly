"""Redaction: blur given boxes on an image."""

from PIL import Image, ImageFilter


def redact_boxes(image_path: str, boxes: list[dict], output_path: str) -> None:
    """Blur each box region on the image and save the result to output_path."""
    image = Image.open(image_path)

    for box in boxes:
        left, top = box["left"], box["top"]
        right, bottom = left + box["width"], top + box["height"]
        region = image.crop((left, top, right, bottom))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=15))
        image.paste(blurred, (left, top))

    image.save(output_path)


if __name__ == "__main__":
    # ponytail: smallest possible self-check, not a test suite
    img = Image.new("RGB", (100, 100), "white")
    img.save("_selftest.png")
    redact_boxes("_selftest.png", [{"left": 10, "top": 10, "width": 30, "height": 30}], "_selftest_out.png")
    assert Image.open("_selftest_out.png").size == (100, 100)
    import os
    os.remove("_selftest.png")
    os.remove("_selftest_out.png")
    print("redact.py self-check passed")
