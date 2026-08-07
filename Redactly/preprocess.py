"""Image preprocessing to improve OCR accuracy on small/low-contrast images."""

from PIL import Image, ImageEnhance

_MIN_LONG_SIDE = 1000  # below this, upscale before OCR


def preprocess_for_ocr(image_path: str) -> Image.Image:
    """Upscale small images, convert to grayscale, and boost contrast for OCR.

    Returns the processed PIL Image (not saved to disk). If the image is
    upscaled, its dimensions are proportionally larger than the original.
    """
    image = Image.open(image_path)

    long_side = max(image.size)
    if long_side < _MIN_LONG_SIDE:
        scale = 3 if long_side < _MIN_LONG_SIDE / 2 else 2
        new_size = (image.width * scale, image.height * scale)
        image = image.resize(new_size, Image.LANCZOS)

    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(1.3)

    return image


if __name__ == "__main__":
    # ponytail: smallest possible self-check, not a test suite
    small = Image.new("RGB", (400, 200), "white")
    small.save("_selftest.png")
    processed = preprocess_for_ocr("_selftest.png")
    assert processed.size == (1200, 600)  # upscaled 3x (400 < 500)
    assert processed.mode == "L"

    large = Image.new("RGB", (1200, 600), "white")
    large.save("_selftest.png")
    processed = preprocess_for_ocr("_selftest.png")
    assert processed.mode == "L"
    assert processed.size == (1200, 600)  # not upscaled

    import os
    os.remove("_selftest.png")
    print("preprocess.py self-check passed")
