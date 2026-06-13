import re
from rapidfuzz import fuzz


REQUIRED_HEALTH_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, "
    "women should not drink alcoholic beverages during pregnancy "
    "because of the risk of birth defects. (2) Consumption of "
    "alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)




def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def find_warning_text(extracted_text: str) -> str:
    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
    warning_lines = []
    found_warning_start = False

    for line in lines:
        lower = line.lower()

        if "warning" in lower or "gover" in lower:
            found_warning_start = True

        if found_warning_start:
            warning_lines.append(line)

    return " ".join(warning_lines)


def run_compliance_checks(
    extracted_text: str,
    parsed_fields: dict,
    results: list[dict] | None = None,
) -> list[dict]:
    parsed_fields = parsed_fields or {}
    results = results or []

    def field_passed(field_name: str) -> bool:
        result = next(
            (item for item in results if item.get("field") == field_name),
            None,
        )

        if result:
            return result.get("status") == "Match"

        return False

    text = extracted_text.upper()
    parsed_fields = parsed_fields or {}
    text = extracted_text.upper()
    label_warning_text = find_warning_text(extracted_text)

    warning_similarity = int(
        fuzz.partial_ratio(
            normalize_text(REQUIRED_HEALTH_WARNING),
            normalize_text(label_warning_text),
        )
    )
    brand_name = parsed_fields.get("brandName", "").strip()

    known_non_brand_terms = [
        "blended",
        "whiskey",
        "bourbon",
        "blended whiskey",
        "straight bourbon",
        "straight bourbon whiskey",
        "lager",
        "beer",
        "wine",
        "vodka",
        "gin",
        "rum",
        "tequila",
    ]

    brand_present = (
        bool(brand_name)
        and brand_name.lower() not in known_non_brand_terms
    )
    checks = [
        {
            "name": "Health Warning Statement",
            "category": "Part 16",
            "passed": warning_similarity >= 85,
            "expected": REQUIRED_HEALTH_WARNING,
            "found": label_warning_text,
            "similarity": warning_similarity,
            "details": (
                "Required health warning appears present."
                if warning_similarity >= 85
                else "Health warning appears missing, incomplete, or materially different."
            ),
        },
        {
            "name": "Brand Name Present",
            "category": "Basic Label Element",
            "passed": field_passed("Brand Name"),
            "expected": "Brand name must be present.",
            "found": brand_name if brand_present else "",
            "similarity": 100 if brand_present else 0,
            "details": "Brand name detected." if brand_present else "Brand name not detected or value appears to be a class/type term.",
        },
        {
            "name": "Class/Type Present",
            "category": "Basic Label Element",
            "passed": field_passed("Class/Type"),
            "expected": "Class/type designation must be present.",
            "found": parsed_fields.get("classType", ""),
            "similarity": 100 if parsed_fields.get("classType") else 0,
            "details": "Class/type detected." if parsed_fields.get("classType") else "Class/type not detected.",
        },
        {
            "name": "Alcohol Content Present",
            "category": "Basic Label Element",
            "passed": field_passed("Alcohol Content"),
            "expected": "Alcohol content percentage must be present.",
            "found": parsed_fields.get("alcoholContent", ""),
            "similarity": 100 if parsed_fields.get("alcoholContent") else 0,
            "details": "Alcohol content detected." if parsed_fields.get("alcoholContent") else "Alcohol content not detected.",
        },
        {
            "name": "Net Contents Present",
            "category": "Basic Label Element",
            "passed": field_passed("Net Contents"),
            "expected": "Net contents must be present.",
            "found": parsed_fields.get("netContents", ""),
            "similarity": 100 if parsed_fields.get("netContents") else 0,
            "details": "Net contents detected." if parsed_fields.get("netContents") else "Net contents not detected.",
        },
        {
            "name": "Readable Label Text",
            "category": "OCR Quality",
            "passed": len(text.strip()) > 20,
            "expected": "OCR should extract readable label text.",
            "found": f"{len(text.strip())} characters extracted",
            "similarity": 100 if len(text.strip()) > 20 else 0,
            "details": "OCR extracted readable text." if len(text.strip()) > 20 else "OCR text is too short.",
        },
    ]

    return checks