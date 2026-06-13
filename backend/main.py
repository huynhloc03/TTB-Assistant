from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError, ImageOps
from ocr_pipeline import run_ocr_with_rotation
from verifier import verify_label
import pytesseract
from pytesseract import Output
import json
import io
import os
import time
import shutil
import uuid
from typing import List

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
else:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


app = FastAPI(title="TTB AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "TTB AI API running"}


@app.get("/test-verify")
def test_verify():
    sample_application = {
        "brandName": "OLD TOM DISTILLERY",
        "classType": "Kentucky Straight Bourbon Whiskey",
        "alcoholContent": "45%",
        "netContents": "750 mL",
    }

    sample_extracted_text = """
    OLD TOM DISTILLERY
    Kentucky Straight Bourbon Whiskey
    45% Alc./Vol. (90 Proof)
    750 mL
    GOVERNMENT WARNING:
    """

    return verify_label(sample_application, sample_extracted_text)


def is_allowed_image(file: UploadFile) -> bool:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()

    return (
        content_type in ALLOWED_IMAGE_TYPES
        or filename.endswith(".png")
        or filename.endswith(".jpg")
        or filename.endswith(".jpeg")
    )


def unsupported_file_response(file: UploadFile):
    return {
        "overallStatus": "ERROR",
        "results": [],
        "complianceChecks": [],
        "extractedText": "",
        "error": "Unsupported file type",
        "message": "Please upload a PNG or JPG label image. PDF support is planned for a future version.",
        "filename": file.filename,
        "contentType": file.content_type,
    }


def open_uploaded_image(image_bytes: bytes):
    try:
        return Image.open(io.BytesIO(image_bytes))
    except UnidentifiedImageError:
        return None

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

    rotations = [0, 90, 180, 270]
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

@app.post("/verify")
def verify(
    file: UploadFile = File(...),
    applicationData: str = Form(...),
):
    start_time = time.time()

    try:
        print("========== VERIFY START ==========")
        print("Filename:", file.filename)

        application = json.loads(applicationData)
        print("Application:", application)

        if not is_allowed_image(file):
            return unsupported_file_response(file)

        image_bytes = file.file.read()
        image = open_uploaded_image(image_bytes)

        if image is None:
            return unsupported_file_response(file)

        ocr_result = run_ocr_with_rotation(image)

        print("OCR SUCCESS")
        print("OCR Confidence:", ocr_result["confidence"])
        print("Rotation:", ocr_result["rotation"])
        print("PSM:", ocr_result["psm"])

        extracted_text = ocr_result["text"]

        print("OCR Preview:")
        print(extracted_text[:500])

        verification = verify_label(application, extracted_text)

        print("VERIFY SUCCESS")

        verification["processingTimeSeconds"] = round(time.time() - start_time, 2)
        verification["filename"] = file.filename
        verification["ocrConfidence"] = ocr_result["confidence"]
        verification["rotationApplied"] = ocr_result["rotation"]
        verification["psmUsed"] = ocr_result["psm"]

        return verification

    except json.JSONDecodeError:
        return {
            "error": "Invalid applicationData JSON",
            "received": applicationData,
        }

    except Exception as e:
        import traceback

        print("========== VERIFY ERROR ==========")
        print("Error:", str(e))
        traceback.print_exc()
        print("==================================")

        raise


@app.post("/analyze-label")
async def analyze_label(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    image_path = f"uploads/{file_id}_{file.filename}"

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = run_ocr_pipeline(image_path)

    return result