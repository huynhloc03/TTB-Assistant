import cv2
import pytesseract
import numpy as np
import re
from rapidfuzz import fuzz


COMMON_LABEL_TERMS = [
    "GOVERNMENT WARNING",
    "ALC./VOL.",
    "ALC/VOL",
    "PROOF",
    "750 ML",
    "BOURBON WHISKEY",
    "BLENDED WHISKEY",
    "STRAIGHT BOURBON WHISKEY",
    "WHISKEY",
    "VODKA",
    "GIN",
    "RUM",
    "TEQUILA",
    "BRANDY",
    "DISTILLED",
    "BOTTLED",
    "BOTTLED BY",
    "DISTILLED BY",
    "PRODUCED BY",
    "CONTAINS SULFITES",
    "PRODUCT OF",
    "USA",
]


def clean_text(text: str) -> str:
    return " ".join(text.upper().replace("\n", " ").split())


def pil_to_cv2(image):
    image_np = np.array(image)

    if len(image_np.shape) == 2:
        return image_np

    return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)


def preprocess_versions(image):
    if len(image.shape) == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    versions = []

    versions.append(("gray", gray))

    upscaled = cv2.resize(
        gray,
        None,
        fx=1.5,
        fy=1.5,
        interpolation=cv2.INTER_CUBIC,
    )
    versions.append(("upscaled", upscaled))

    _, thresh = cv2.threshold(
        upscaled,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    versions.append(("threshold", thresh))

    return versions


def ocr_image(image, psm=6):
    config = f"--oem 3 --psm {psm}"
    text = pytesseract.image_to_string(image, config=config)
    return clean_text(text)


def rotate_image(image, angle):
    if angle == 0:
        return image

    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)

    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    return image


def dedupe_texts(texts):
    final = []

    for text in texts:
        if not text:
            continue

        duplicate = False

        for existing in final:
            if fuzz.ratio(text, existing) > 90:
                duplicate = True
                break

        if not duplicate:
            final.append(text)

    return final


def fuzzy_dictionary_match(all_text):
    matches = []

    for term in COMMON_LABEL_TERMS:
        score = fuzz.partial_ratio(term, all_text)

        if score >= 75:
            matches.append(
                {
                    "term": term,
                    "score": score,
                }
            )

    return matches


def detect_orientation_with_osd(cv_image):
    try:
        if len(cv_image.shape) == 2:
            gray = cv_image
        else:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        osd = pytesseract.image_to_osd(gray)

        rotate_match = re.search(r"Rotate:\s+(\d+)", osd)
        confidence_match = re.search(
            r"Orientation confidence:\s+([\d.]+)",
            osd,
        )

        rotation = int(rotate_match.group(1)) if rotate_match else 0
        confidence = float(confidence_match.group(1)) if confidence_match else 0

        if confidence >= 5:
            return rotation

    except Exception:
        pass

    return 0


def score_ocr_text(text, dictionary_matches):
    useful_terms_bonus = len(dictionary_matches) * 75
    text_length_score = len(text)
    return text_length_score + useful_terms_bonus


def run_single_ocr_pass(cv_image, rotation=0):
    print(f"OCR PASS: rotation={rotation}")

    rotated = rotate_image(cv_image, rotation)

    all_texts = []

    psm_modes = [6]

    for name, processed in preprocess_versions(rotated):
        print(f"OCR PASS: preprocessing={name}")

        for psm in psm_modes:
            print(f"OCR PASS: psm={psm}")

            text = ocr_image(processed, psm=psm)

            print("OCR PASS: text extraction done")

            if text:
                all_texts.append(text)

    deduped = dedupe_texts(all_texts)
    merged_text = clean_text(" ".join(deduped))
    dictionary_matches = fuzzy_dictionary_match(merged_text)

    avg_confidence = 90 if merged_text else 0

    return {
        "text": merged_text,
        "confidence": avg_confidence,
        "rotation": rotation,
        "psm": 6,
        "individual_results": deduped,
        "cluster_results": [],
        "dictionary_matches": dictionary_matches,
    }


def run_ocr_with_rotation(image):
    print("OCR: converting image")

    cv_image = pil_to_cv2(image)

    print("OCR: detecting orientation")

    detected_rotation = detect_orientation_with_osd(cv_image)

    print("OCR: detected rotation =", detected_rotation)

    print("OCR: starting initial OCR pass")

    result = run_single_ocr_pass(
        cv_image,
        rotation=detected_rotation,
    )

    print("OCR: initial OCR pass complete")

    score = score_ocr_text(
        result["text"],
        result["dictionary_matches"],
    )

    if result["confidence"] >= 60 and score >= 300:
        return result

    best_result = result
    best_score = score

    for rotation in [0]:
        if rotation == detected_rotation:
            continue

        print("OCR: trying fallback rotation", rotation)

        candidate = run_single_ocr_pass(
            cv_image,
            rotation=rotation,
        )

        candidate_score = score_ocr_text(
            candidate["text"],
            candidate["dictionary_matches"],
        )

        if candidate_score > best_score:
            best_result = candidate
            best_score = candidate_score

    return best_result