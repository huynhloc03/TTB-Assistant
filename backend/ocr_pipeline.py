import os
import shutil
import time

import cv2
import numpy as np
import pytesseract
from PIL import Image


if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
else:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def clean_text(text: str) -> str:
    if not text:
        return ""

    return " ".join(text.upper().replace("\n", " ").split())


def pil_to_cv2(image: Image.Image):
    image_np = np.array(image.convert("RGB"))
    return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)


def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=1.5,
        fy=1.5,
        interpolation=cv2.INTER_CUBIC,
    )

    thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]

    return [
        ("threshold", thresh),
    ]


def ocr_image(image, psm: int = 6) -> str:
    config = f"--oem 3 --psm {psm}"
    text = pytesseract.image_to_string(image, config=config)
    return clean_text(text)


def run_ocr_with_rotation(image: Image.Image):
    print("OCR PIPELINE FILE EXECUTED", flush=True)

    cv_image = pil_to_cv2(image)

    all_text = []
    psm = 6

    for name, processed in preprocess_image(cv_image):
        start = time.time()

        text = ocr_image(processed, psm=psm)

        print(
            f"OCR pass [{name}] took {time.time() - start:.2f}s",
            flush=True,
        )

        if text:
            all_text.append(text)

    merged_text = clean_text(" ".join(all_text))

    return {
        "text": merged_text,
        "confidence": 95 if merged_text else 0,
        "rotation": 0,
        "psm": psm,
    }