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


def clean_text(text):
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

    upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    versions.append(("upscaled", upscaled))

    _, thresh = cv2.threshold(
        upscaled,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    versions.append(("threshold", thresh))

    inverted_thresh = cv2.bitwise_not(thresh)
    versions.append(("inverted_threshold", inverted_thresh))

    return versions


def ocr_image(image, psm=6):
    config = f"--oem 3 --psm {psm}"
    text = pytesseract.image_to_string(image, config=config)
    return clean_text(text)


def get_ocr_confidence(image, psm=6):
    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    confidences = []

    for conf in data.get("conf", []):
        try:
            conf = float(conf)
            if conf >= 0:
                confidences.append(conf)
        except ValueError:
            continue

    if not confidences:
        return 0

    return round(sum(confidences) / len(confidences), 2)


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


def find_text_clusters(image):
    if len(image.shape) == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    all_boxes = []

    for working in [gray, cv2.bitwise_not(gray)]:
        _, thresh = cv2.threshold(
            working,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            if w < 40 or h < 15:
                continue

            if w * h < 1000:
                continue

            all_boxes.append((x, y, w, h))

    return all_boxes, gray


def ocr_text_clusters(image):
    clusters, scaled_gray = find_text_clusters(image)

    results = []

    for x, y, w, h in clusters:
        padding = 14

        x1 = max(x - padding, 0)
        y1 = max(y - padding, 0)
        x2 = min(x + w + padding, scaled_gray.shape[1])
        y2 = min(y + h + padding, scaled_gray.shape[0])

        crop = scaled_gray[y1:y2, x1:x2]

        crop_versions = [
            crop,
            cv2.bitwise_not(crop),
        ]

        _, crop_thresh = cv2.threshold(
            crop,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        crop_versions.append(crop_thresh)
        crop_versions.append(cv2.bitwise_not(crop_thresh))

        for crop_version in crop_versions:
            text = ocr_image(crop_version, psm=7)

            if len(text) >= 3:
                results.append({
                    "text": text,
                    "box": [x1, y1, x2, y2],
                })

    return results


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
            matches.append({
                "term": term,
                "score": score,
            })

    return matches


def detect_orientation_with_osd(cv_image):
    try:
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        osd = pytesseract.image_to_osd(gray)

        rotate_match = re.search(r"Rotate:\s+(\d+)", osd)
        confidence_match = re.search(r"Orientation confidence:\s+([\d.]+)", osd)

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
    rotated = rotate_image(cv_image, rotation)

    all_texts = []
    confidence_scores = []

    psm_modes = [6,11]

    for name, processed in preprocess_versions(rotated):
        for psm in psm_modes:
            text = ocr_image(processed, psm=psm)
            confidence = get_ocr_confidence(processed, psm=psm)

            if text:
                all_texts.append(text)
                confidence_scores.append(confidence)

    cluster_results = ocr_text_clusters(rotated)

    for item in cluster_results:
        all_texts.append(item["text"])

    deduped = dedupe_texts(all_texts)
    merged_text = clean_text(" ".join(deduped))
    dictionary_matches = fuzzy_dictionary_match(merged_text)

    avg_confidence = (
        round(sum(confidence_scores) / len(confidence_scores), 2)
        if confidence_scores
        else 0
    )

    return {
        "text": merged_text,
        "confidence": avg_confidence,
        "rotation": rotation,
        "psm": 11,
        "individual_results": deduped,
        "cluster_results": cluster_results,
        "dictionary_matches": dictionary_matches,
    }


def run_ocr_with_rotation(image):
    cv_image = pil_to_cv2(image)

    detected_rotation = detect_orientation_with_osd(cv_image)

    result = run_single_ocr_pass(
        cv_image,
        rotation=detected_rotation,
    )

    score = score_ocr_text(
        result["text"],
        result["dictionary_matches"],
    )

    
    if result["confidence"] >= 60 and score >= 500:
        return result

    best_result = result
    best_score = score

    for rotation in [0, 90, 180, 270]:
        if rotation == detected_rotation:
            continue

        candidate = run_single_ocr_pass(cv_image, rotation=rotation)

        candidate_score = score_ocr_text(
            candidate["text"],
            candidate["dictionary_matches"],
        )

        if candidate_score > best_score:
            best_result = candidate
            best_score = candidate_score

    return best_result