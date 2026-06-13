import os
import re
import shutil

import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps


if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
else:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def get_ocr_confidence(image: Image.Image) -> int:
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    confidences = []

    for conf in data.get("conf", []):
        try:
            value = float(conf)

            if value >= 0:
                confidences.append(value)

        except ValueError:
            continue

    if not confidences:
        return 0

    return round(sum(confidences) / len(confidences))


def detect_orientation_rotation(image: Image.Image) -> int:
    try:
        osd = pytesseract.image_to_osd(image)

        match = re.search(r"Rotate:\s+(\d+)", osd)

        if match:
            return int(match.group(1))

    except Exception:
        return 0

    return 0


def run_ocr_with_rotation(image: Image.Image):
    best_result = {
        "text": "",
        "confidence": 0,
        "rotation": 0,
        "psm": 3,
    }

    rotations = [0, 180]
    psm_modes = [3]

    for rotation in rotations:
        rotated = image.rotate(rotation, expand=True) if rotation else image

        rotated = rotated.convert("L")
        rotated = ImageOps.autocontrast(rotated)

        for psm in psm_modes:
            text = pytesseract.image_to_string(
                rotated,
                config=f"--psm {psm}",
            )

            confidence = get_ocr_confidence(rotated)

            score = confidence + min(len(text.strip()) / 10, 20)

            best_score = best_result["confidence"] + min(
                len(best_result["text"].strip()) / 10,
                20,
            )

            if score > best_score:
                best_result = {
                    "text": text,
                    "confidence": confidence,
                    "rotation": rotation,
                    "psm": psm,
                }

    return best_result