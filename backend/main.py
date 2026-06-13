from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from ocr_pipeline import run_ocr_with_rotation
from verifier import verify_label

import json
import io
import time


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
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        return image
    except UnidentifiedImageError:
        return None


@app.post("/verify")
def verify(
    file: UploadFile = File(...),
    applicationData: str = Form(...),
):
    start_time = time.time()

    try:
        print("========== VERIFY START ==========", flush=True)
        print("Filename:", file.filename, flush=True)

        application = json.loads(applicationData)
        print("Application:", application, flush=True)

        if not is_allowed_image(file):
            return unsupported_file_response(file)

        image_bytes = file.file.read()
        image = open_uploaded_image(image_bytes)

        if image is None:
            return unsupported_file_response(file)

        image.thumbnail((900, 900))

        ocr_result = run_ocr_with_rotation(image)

        print("OCR SUCCESS", flush=True)
        print("OCR Confidence:", ocr_result.get("confidence"), flush=True)
        print("Rotation:", ocr_result.get("rotation"), flush=True)
        print("PSM:", ocr_result.get("psm"), flush=True)

        extracted_text = ocr_result.get("text", "")

        print("OCR Preview:", flush=True)
        print(extracted_text[:500], flush=True)

        verification = verify_label(application, extracted_text)

        verification["processingTimeSeconds"] = round(time.time() - start_time, 2)
        verification["filename"] = file.filename
        verification["ocrConfidence"] = ocr_result.get("confidence", 0)
        verification["rotationApplied"] = ocr_result.get("rotation", 0)
        verification["psmUsed"] = ocr_result.get("psm", 6)

        print("VERIFY SUCCESS", flush=True)
        print("Processing Time:", verification["processingTimeSeconds"], flush=True)
        print("=========== VERIFY END ===========", flush=True)

        return verification

    except json.JSONDecodeError:
        return {
            "overallStatus": "ERROR",
            "results": [],
            "complianceChecks": [],
            "extractedText": "",
            "error": "Invalid applicationData JSON",
            "received": applicationData,
        }

    except Exception as e:
        import traceback

        print("========== VERIFY ERROR ==========", flush=True)
        print("Error:", str(e), flush=True)
        traceback.print_exc()
        print("==================================", flush=True)

        raise