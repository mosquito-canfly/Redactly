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
# YuNet's default score_threshold (0.9) misses smaller/blurrier faces (e.g. ID
# photos). For redaction, a missed face is worse than an extra blurred region.
_SCORE_THRESHOLD = 0.4


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


def _detect_yunet(image, width: int, height: int) -> list[dict] | None:
    """Try YuNet detection. Returns None (not []) if the model isn't available/usable, so the caller falls back."""
    model_path = _ensure_yunet_model()
    if not model_path:
        return None
    try:
        detector = cv2.FaceDetectorYN.create(model_path, "", (width, height), score_threshold=_SCORE_THRESHOLD)
        _, faces = detector.detect(image)
    except Exception as e:
        print(f"NOTE: YuNet model failed to load/run ({e}); falling back to Haar cascade.")
        return None
    if faces is None:
        return []
    return [_clamp_box(int(f[0]), int(f[1]), int(f[2]), int(f[3]), width, height) for f in faces]


def _detect_haar(image, width: int, height: int) -> list[dict]:
    """Fallback face detection using OpenCV's bundled Haar cascade. Returns [] if unavailable in this OpenCV build."""
    try:
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        cascade = cv2.CascadeClassifier(cascade_path)
    except AttributeError:
        print("NOTE: Haar cascade (cv2.CascadeClassifier) isn't available in this OpenCV build; no face detection possible.")
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detections = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return [_clamp_box(int(x), int(y), int(w), int(h), width, height) for x, y, w, h in detections]


def detect_faces(image_path: str) -> list[dict]:
    """Detect faces in an image using local OpenCV models (YuNet, or Haar cascade as fallback).

    Returns a list of box dicts: {left, top, width, height, label}, label always "face".
    Coordinates are ints, clamped to the image bounds. Returns [] and prints a
    readable warning on any error; never raises.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"WARNING: could not read image for face detection: {image_path}")
            return []
        height, width = image.shape[:2]

        boxes = _detect_yunet(image, width, height)
        if boxes is None:
            boxes = _detect_haar(image, width, height)
        return boxes
    except Exception as e:
        print(f"WARNING: face detection failed: {e}")
        return []


if __name__ == "__main__":
    import sys
    result = detect_faces(sys.argv[1] if len(sys.argv) > 1 else "samples/images.jpeg")
    print(f"detect_faces found {len(result)} face(s):")
    for box in result:
        print(f"  {box}")
