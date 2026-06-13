import os
import shutil
import time

import pytesseract
from PIL import Image, ImageOps


if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
else:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def looks_readable(text: str) -> bool:
    if not text:
        return False

    upper_text = text.upper()

    strong_terms = [
        "GOVERNMENT WARNING",
        "ALC",
        "VOL",
        "PROOF",
        "ML",
        "DISTILLED",
        "BOTTLED",
        "WHISKEY",
        "VODKA",
        "GIN",
        "RUM",
        "TEQUILA",
        "BRANDY",
        "BOURBON",
    ]

    if any(term in upper_text for term in strong_terms):
        return True

    words = upper_text.split()
    readable_words = [
        word for word in words
        if len(word) >= 3 and word.isalpha()
    ]

    return len(readable_words) >= 8


def clean_text(text: str) -> str:
    if not text:
        return ""

    return " ".join(text.upper().replace("\n", " ").split())


def run_single_ocr(image: Image.Image, rotation: int, psm: int = 6):
    start = time.time()

    rotated = image.rotate(rotation, expand=True) if rotation else image
    gray = rotated.convert("L")
    gray = ImageOps.autocontrast(gray)

    text = pytesseract.image_to_string(
        gray,
        config=f"--oem 3 --psm {psm}",
    )

    cleaned_text = clean_text(text)

    print(
        f"OCR rotation [{rotation}] psm [{psm}] took {time.time() - start:.2f}s",
        flush=True,
    )

    return {
        "text": cleaned_text,
        "confidence": 95 if cleaned_text else 0,
        "rotation": rotation,
        "psm": psm,
        "score": score_text(cleaned_text),
    }


def score_text(text: str) -> int:
    if not text:
        return 0

    upper_text = text.upper()

    strong_terms = [
        "GOVERNMENT WARNING",
        "ALC",
        "VOL",
        "PROOF",
        "ML",
        "DISTILLED",
        "BOTTLED",
        "WHISKEY",
        "VODKA",
        "GIN",
        "RUM",
        "TEQUILA",
        "BRANDY",
        "BOURBON",
    ]

    score = len(upper_text)

    for term in strong_terms:
        if term in upper_text:
            score += 100

    return score


def run_ocr_with_rotation(image: Image.Image):
    print("FAST ROTATION OCR PIPELINE EXECUTED", flush=True)

    result = run_single_ocr(image, rotation=0, psm=6)

    if looks_readable(result["text"]):
        return result

    best_result = result
    best_score = score_text(result["text"])

    for rotation in [90, 180, 270]:
        candidate = run_single_ocr(image, rotation=rotation, psm=6)
        candidate_score = score_text(candidate["text"])

        if candidate_score > best_score:
            best_result = candidate
            best_score = candidate_score

        if looks_readable(candidate["text"]):
            return candidate

    return best_result