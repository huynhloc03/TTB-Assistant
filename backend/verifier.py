import re
from rapidfuzz import fuzz, process
from compliance import run_compliance_checks

try:
    from ocr_pipeline import run_ocr_pipeline
except ImportError:
    run_ocr_pipeline = None


KNOWN_CLASSES = [
    "blended whiskey",
    "bourbon whiskey",
    "straight bourbon whiskey",
    "rye whiskey",
    "whiskey",
    "vodka",
    "gin",
    "rum",
    "tequila",
    "tequila blanco",
    "brandy",
    "lager",
    "classic lager",
    "ale",
    "ipa",
    "stout",
    "porter",
    "wine",
    "chardonnay",
    "merlot",
    "cabernet",
    "pinot",
    "straight bourbon",
    "bourbon",
]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clean_ocr_line(text: str) -> str:
    if not text:
        return ""

    text = text.replace("=", " ")
    text = text.replace("—", " ")
    text = text.replace("-", " ")
    text = text.replace("•", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_found_value(field: str, value: str) -> str:
    if not value:
        return ""

    value = clean_ocr_line(value)

    if field == "Alcohol Content":
        match = re.search(r"\d+(?:\.\d+)?", value)
        return f"{match.group(0)}%" if match else ""

    if field == "Net Contents":
        match = re.search(r"\d+(?:\.\d+)?", value)
        return match.group(0) if match else ""

    if field in ["Brand Name", "Class/Type"]:
        value = re.sub(r"[^A-Za-z\s/&]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    return value.strip()


def split_lines(extracted_text: str) -> list[str]:
    cleaned_lines = []

    for line in extracted_text.splitlines():
        cleaned = clean_ocr_line(line)
        if cleaned:
            cleaned_lines.append(cleaned)

    return cleaned_lines


def get_threshold(field: str) -> int:
    thresholds = {
        "Brand Name": 85,
        "Class/Type": 85,
        "Alcohol Content": 85,
        "Net Contents": 85,
        "Government Warning": 75,
    }
    return thresholds.get(field, 85)


def is_known_class(text: str) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(item) == normalized for item in KNOWN_CLASSES)


def find_known_class(lines: list[str]) -> str:
    if not lines:
        return ""

    candidates = lines[:]

    for i in range(len(lines) - 1):
        candidates.append(f"{lines[i]} {lines[i + 1]}")

    joined_text = " ".join(lines)
    candidates.append(joined_text)

    best_match = None
    best_score = 0

    for candidate in candidates:
        match = process.extractOne(
            candidate,
            KNOWN_CLASSES,
            scorer=fuzz.partial_ratio,
        )

        if match and int(match[1]) > best_score:
            best_match = match[0]
            best_score = int(match[1])

    if best_match and best_score >= 80:
        return best_match.title()

    return ""


def detect_brand_and_class(lines: list[str]) -> tuple[str, str]:
    if not lines:
        return "", ""

    class_type = find_known_class(lines)
    first_line = lines[0]

    if len(lines) >= 2:
        combined_first_two = f"{lines[0]} {lines[1]}"

        if class_type and normalize_text(combined_first_two) == normalize_text(class_type):
            return "", class_type

    if is_known_class(first_line):
        return "", first_line.title()

    if class_type and normalize_text(first_line) in normalize_text(class_type):
        return "", class_type

    return first_line, class_type


def extract_net_contents(extracted_text: str) -> str:
    matches = re.findall(
        r"\b(\d{2,4}(?:\.\d+)?)\s*(ML|M\s*L|L|FL\.?\s*OZ\.?|OZ|M1|MI)\b",
        extracted_text,
        re.IGNORECASE,
    )

    for amount, unit in matches:
        normalized_unit = unit.upper().replace(" ", "")

        if normalized_unit in ["M1", "MI"]:
            normalized_unit = "ML"

        if normalized_unit in ["ML", "L", "FLOZ", "OZ"]:
            return f"{amount} {normalized_unit}"

    return ""


def extract_alcohol_content(extracted_text: str) -> str:
    abv_match = re.search(
        r"\b([1-9]\d?(?:\.\d+)?)\s*%\s*(?:ALC|ALC\.|ALC\./VOL\.|ALC/VOL|BY VOL\.?)?",
        extracted_text,
        re.IGNORECASE,
    )

    if not abv_match:
        abv_match = re.search(
            r"\b(\d{1,2}(?:\.\d+)?)\s*ALC",
            extracted_text,
            re.IGNORECASE,
        )

    if abv_match:
        return f"{abv_match.group(1)}%"

    return ""


def extract_label_fields(extracted_text: str) -> dict:
    lines = split_lines(extracted_text)

    useful_lines = [
        line
        for line in lines
        if "warning" not in line.lower()
        and "according" not in line.lower()
        and "surgeon" not in line.lower()
        and "pregnancy" not in line.lower()
        and "health" not in line.lower()
        and "alc" not in line.lower()
        and "%" not in line
        and "proof" not in line.lower()
        and "ml" not in line.lower()
        and "bottled" not in line.lower()
        and "distilled" not in line.lower()
        and "small batch" not in line.lower()
        and "handcrafted" not in line.lower()
        and len(line.strip()) > 1
    ]

    brand_name, class_type = detect_brand_and_class(useful_lines)

    bad_brand_values = [
        "blended",
        "whiskey",
        "bourbon",
        "blended whiskey",
        "straight bourbon",
        "straight bourbon whiskey",
        "vodka",
        "gin",
        "rum",
        "tequila",
    ]

    if normalize_text(brand_name) in [normalize_text(item) for item in bad_brand_values]:
        brand_name = ""

    alcohol_content = extract_alcohol_content(extracted_text)
    net_contents = extract_net_contents(extracted_text)

    return {
        "brandName": brand_name,
        "classType": class_type,
        "alcoholContent": alcohol_content,
        "netContents": net_contents,
    }


def find_best_match(expected: str, extracted_text: str, field: str) -> tuple[bool, str, int]:
    if not expected:
        return False, "", 0

    lines = split_lines(extracted_text)

    if not lines:
        return False, "", 0

    expected_normalized = normalize_text(expected)
    full_text_normalized = normalize_text(extracted_text)

    if field in ["Alcohol Content", "Net Contents"]:
        expected_number_match = re.search(r"\d+(?:\.\d+)?", expected)

        if not expected_number_match:
            return False, "", 0

        expected_number = expected_number_match.group(0)

        if field == "Alcohol Content":
            candidates = re.findall(
                r"\b([1-9]\d?(?:\.\d+)?)\s*%|\b([1-9]\d?(?:\.\d+)?)\s*ALC",
                extracted_text,
                re.IGNORECASE,
            )

            found_numbers = [
                first or second
                for first, second in candidates
                if first or second
            ]

        else:
            candidates = re.findall(
                r"\b(\d{2,4}(?:\.\d+)?)\s*(ML|M\s*L|L|FL\.?\s*OZ\.?|OZ|M1|MI)\b",
                extracted_text,
                re.IGNORECASE,
            )

            found_numbers = [amount for amount, _unit in candidates]

        for number in found_numbers:
            if number == expected_number:
                return True, number, 100

        if found_numbers:
            return False, found_numbers[0], 0

        return False, "", 0

    if expected_normalized in full_text_normalized:
        return True, expected, 100

    candidates = lines[:]

    for i in range(len(lines) - 1):
        candidates.append(f"{lines[i]} {lines[i + 1]}")

    for i in range(len(lines) - 2):
        candidates.append(f"{lines[i]} {lines[i + 1]} {lines[i + 2]}")

    best_line = ""
    best_score = 0

    for candidate in candidates:
        candidate_normalized = normalize_text(candidate)

        if not candidate_normalized:
            continue

        score = fuzz.ratio(expected_normalized, candidate_normalized)

        if score > best_score:
            best_score = int(score)
            best_line = candidate

    matched = best_score >= get_threshold(field)

    return matched, best_line, best_score


def get_status(expected: str, found_text: str, matched: bool, similarity: int) -> str:
    if not expected and found_text:
        return "Extracted"

    if not expected and not found_text:
        return "Missing"

    if matched:
        return "Match"

    if similarity >= 70:
        return "Review"

    return "Needs Review"


def build_result(
    field: str,
    expected: str,
    found_text: str,
    matched: bool,
    similarity: int,
    details: str,
    raw_found_text: str = "",
) -> dict:
    return {
        "field": field,
        "expected": expected,
        "foundText": found_text,
        "rawFoundText": raw_found_text,
        "found": matched,
        "similarity": similarity,
        "status": get_status(expected, found_text, matched, similarity),
        "details": details,
    }


def get_parsed_field_confidence(parsed_fields: dict) -> dict:
    return {
        "brandName": 95 if parsed_fields.get("brandName") else 0,
        "classType": 90 if parsed_fields.get("classType") else 0,
        "alcoholContent": 98 if parsed_fields.get("alcoholContent") else 0,
        "netContents": 98 if parsed_fields.get("netContents") else 0,
    }


def verify_label(application: dict, extracted_text: str) -> dict:
    parsed_fields = extract_label_fields(extracted_text)

    results = []

    fields = [
        ("Brand Name", "brandName"),
        ("Class/Type", "classType"),
        ("Alcohol Content", "alcoholContent"),
        ("Net Contents", "netContents"),
    ]

    for label, key in fields:
        expected = application.get(key, "").strip()

        if not expected:
            found_text = parsed_fields.get(key, "")

            results.append(
                build_result(
                    field=label,
                    expected="",
                    found_text=found_text,
                    matched=False,
                    similarity=0,
                    raw_found_text=found_text,
                    details="Extracted from OCR. No application value provided for comparison.",
                )
            )
            continue

        parsed_value = parsed_fields.get(key, "").strip()

        if parsed_value:
            found_text = parsed_value

            similarity = int(
                fuzz.ratio(
                    normalize_text(expected),
                    normalize_text(parsed_value),
                )
            )

            matched = similarity >= get_threshold(label)

        else:
            matched, found_text, similarity = find_best_match(
                expected,
                extracted_text,
                label,
            )
        raw_found_text = found_text
        found_text = clean_found_value(label, found_text)
        expected_clean = clean_found_value(label, expected)
        found_clean = clean_found_value(label, found_text)

        if label in ["Alcohol Content", "Net Contents"]:
            if expected_clean and found_clean and expected_clean == found_clean:
                matched = True
                similarity = 100
                found_text = found_clean

        if not matched:
            found_text = "Unable to Identify"

        elif label in ["Alcohol Content", "Net Contents"]:
            if not found_text:
                found_text = "Unable to Identify"

        else:
            if not found_text or similarity < 20:
                found_text = "Unable to Identify"

        if matched and found_text != "Unable to Identify":
            parsed_fields[key] = found_text

        results.append(
            build_result(
                field=label,
                expected=expected,
                found_text=found_text,
                matched=matched,
                similarity=similarity,
                raw_found_text=raw_found_text,
                details=(
                    "Unable to extract a reliable value from OCR."
                    if similarity < 50
                    else f"Similarity {similarity}%. Required threshold: {get_threshold(label)}%."
                ),
            )
        )

    warning_expected = "GOVERNMENT WARNING:"
    normalized_ocr = normalize_text(extracted_text)

    warning_present = (
        "warning" in normalized_ocr
        and (
            "government" in normalized_ocr
            or "goveriment" in normalized_ocr
            or "goverment" in normalized_ocr
            or "governnent" in normalized_ocr
        )
    )

    if warning_present:
        warning_matched = True
        warning_found_text = "GOVERNMENT WARNING:"
        warning_similarity = 100
    else:
        warning_matched, warning_found_text, warning_similarity = find_best_match(
            warning_expected,
            extracted_text,
            "Government Warning",
        )

    if not warning_matched:
        warning_found_text = "Not Detected"
        warning_similarity = 0

    results.append(
        build_result(
            field="Government Warning",
            expected=warning_expected,
            found_text=warning_found_text,
            matched=warning_matched,
            similarity=warning_similarity,
            details=(
                "Government warning detected."
                if warning_matched
                else "Required government warning statement was not detected on the label."
            ),
        )
    )

    compliance_checks = run_compliance_checks(extracted_text, parsed_fields, results)

    has_application_data = any(application.get(key, "").strip() for _, key in fields)

    field_pass = all(result["found"] for result in results)
    compliance_pass = all(check["passed"] for check in compliance_checks)

    if not has_application_data:
        overall_status = "OCR EXTRACTION ONLY"
    else:
        overall_status = "PASS" if field_pass and compliance_pass else "NEEDS REVIEW"

    parsed_field_confidence = get_parsed_field_confidence(parsed_fields)

    return {
        "overallStatus": overall_status,
        "parsedFields": parsed_fields,
        "parsedFieldConfidence": parsed_field_confidence,
        "results": results,
        "complianceChecks": compliance_checks,
        "extractedText": extracted_text,
    }


def verify_label_from_image(application: dict, image_path: str) -> dict:
    if run_ocr_pipeline is None:
        raise ImportError("ocr_pipeline.py was not found. Make sure it exists in the backend folder.")

    ocr_result = run_ocr_pipeline(image_path)
    extracted_text = ocr_result.get("merged_text", "")

    verification_result = verify_label(application, extracted_text)

    verification_result["ocrPipeline"] = {
        "individualResults": ocr_result.get("individual_results", []),
        "clusterResults": ocr_result.get("cluster_results", []),
        "dictionaryMatches": ocr_result.get("dictionary_matches", []),
    }

    return verification_result