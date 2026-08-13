"""Local, free face detection via OpenCV — YuNet (ONNX), falling back to Haar cascade.

No Gemini, no per-image network calls. The only network access is a one-time
download of the YuNet model file on first use; if that fails (e.g. offline),
detection falls back to OpenCV's bundled Haar cascade.
"""

import os
import urllib.request

import cv2

_MODEL_DIR = "models"
_MODEL_PATH = os.path.join(_MODEL_DIR, "face_detection_yunet.onnx")
_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
# YuNet's own default (0.9) misses smaller/blurrier faces (e.g. ID photos). For
# redaction, a missed face is worse than an extra blurred region.
DEFAULT_CONF_THRESHOLD = 0.5
# Expand each face box outward by this fraction of its own size before returning.
_FACE_PADDING_FACTOR = 0.15


def _ensure_yunet_model() -> str | None:
    """Return a local path to the YuNet ONNX model, downloading it once if missing."""
    if os.path.exists(_MODEL_PATH):
        return _MODEL_PATH
    try:
        os.makedirs(_MODEL_DIR, exist_ok=True)
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        return _MODEL_PATH
    except Exception as e:
        print(f"NOTE: couldn't download YuNet face model ({e}); falling back to Haar cascade.")
        return None


def _clamp_box(left: int, top: int, width: int, height: int, img_width: int, img_height: int) -> dict:
    """Clamp a box to image bounds and shape it like the other detectors' output."""
    left = max(0, min(left, img_width))
    top = max(0, min(top, img_height))
    right = max(0, min(left + width, img_width))
    bottom = max(0, min(top + height, img_height))
    return {"left": left, "top": top, "width": right - left, "height": bottom - top, "label": "face"}


def _pad_box(box: dict, factor: float, img_width: int, img_height: int) -> dict:
    """Expand a box outward by `factor` of its own size, clamped to image bounds."""
    pad_x = int(box["width"] * factor)
    pad_y = int(box["height"] * factor)
    left = max(0, box["left"] - pad_x)
    top = max(0, box["top"] - pad_y)
    right = min(img_width, box["left"] + box["width"] + pad_x)
    bottom = min(img_height, box["top"] + box["height"] + pad_y)
    return {**box, "left": left, "top": top, "width": right - left, "height": bottom - top}


def _detect_yunet(image, width: int, height: int, conf_threshold: float) -> list[tuple[dict, float]] | None:
    """Try YuNet detection. Returns None (not []) if the model isn't available/usable, so the caller falls back.

    Each result is (box, confidence) — confidence is YuNet's own detection score.
    """
    model_path = _ensure_yunet_model()
    if not model_path:
        return None
    try:
        detector = cv2.FaceDetectorYN.create(model_path, "", (width, height), score_threshold=conf_threshold)
        _, faces = detector.detect(image)
    except Exception as e:
        print(f"NOTE: YuNet model failed to load/run ({e}); falling back to Haar cascade.")
        return None
    if faces is None:
        return []
    return [
        (_clamp_box(int(f[0]), int(f[1]), int(f[2]), int(f[3]), width, height), float(f[14]))
        for f in faces
    ]


def _detect_haar(image, width: int, height: int) -> list[tuple[dict, None]]:
    """Fallback face detection using OpenCV's bundled Haar cascade. Returns [] if unavailable in this OpenCV build.

    Haar's detectMultiScale doesn't give a comparable confidence score, so confidence is always None here.
    """
    try:
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        cascade = cv2.CascadeClassifier(cascade_path)
    except AttributeError:
        print("NOTE: Haar cascade (cv2.CascadeClassifier) isn't available in this OpenCV build; no face detection possible.")
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detections = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return [(_clamp_box(int(x), int(y), int(w), int(h), width, height), None) for x, y, w, h in detections]


def detect_faces(image_path: str, conf_threshold: float = DEFAULT_CONF_THRESHOLD) -> list[dict]:
    """Detect faces in an image using local OpenCV models (YuNet, or Haar cascade as fallback).

    conf_threshold sets YuNet's minimum detection confidence (0-1); lower catches
    fainter/low-contrast faces at the cost of more false positives. Doesn't apply
    to the Haar fallback, which has no comparable score.

    Returns a list of box dicts: {left, top, width, height, label}, label always
    "face", each padded outward by _FACE_PADDING_FACTOR of its own size and
    clamped to image bounds. Prints each detection's confidence for inspection.
    Returns [] and prints a readable warning on any error; never raises.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"WARNING: could not read image for face detection: {image_path}")
            return []
        height, width = image.shape[:2]

        results = _detect_yunet(image, width, height, conf_threshold)
        if results is None:
            results = _detect_haar(image, width, height)

        boxes = []
        for box, conf in results:
            padded = _pad_box(box, _FACE_PADDING_FACTOR, width, height)
            conf_str = f"{conf:.2f}" if conf is not None else "n/a (Haar)"
            print(f"face detected (confidence: {conf_str}): {padded}")
            boxes.append(padded)
        return boxes
    except Exception as e:
        print(f"WARNING: face detection failed: {e}")
        return []


if __name__ == "__main__":
    import sys
    result = detect_faces(sys.argv[1] if len(sys.argv) > 1 else "samples/images.jpeg")
    print(f"detect_faces found {len(result)} face(s) total.")
