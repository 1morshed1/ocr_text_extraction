import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from google.cloud import vision
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/jpg"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg"]

# Global Vision API client (initialized in lifespan)
vision_client: Optional[vision.ImageAnnotatorClient] = None


# --- Pydantic Response Models ---


class MetadataModel(BaseModel):
    filename: Optional[str]
    file_size_bytes: int
    content_type: Optional[str]


class SuccessResponseModel(BaseModel):
    success: bool = True
    text: str
    confidence: float
    processing_time_ms: int
    metadata: MetadataModel


class ErrorResponseModel(BaseModel):
    success: bool = False
    error: str
    detail: str
    processing_time_ms: int = 0


class ApiInfoModel(BaseModel):
    service: str
    status: str
    version: str
    endpoints: dict[str, str]


class HealthResponseModel(BaseModel):
    status: str
    vision_api: str
    timestamp: float


# --- Lifespan ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vision_client

    try:
        vision_client = vision.ImageAnnotatorClient()
        logger.info("Vision API client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Vision API client: {e}")
        vision_client = None

    yield

    logger.info("Application shutting down")


# --- App ---

app = FastAPI(
    title="OCR Text Extraction API",
    description="Extract text from JPG images using Google Cloud Vision API",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Helper Functions ---


def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file format. Only JPG/JPEG images are supported. "
                f"Received: {file.content_type}"
            ),
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file extension. Only .jpg and .jpeg are supported. "
                f"Received: {extension}"
            ),
        )


def extract_text_from_image(image_content: bytes) -> tuple[str, float]:
    if vision_client is None:
        logger.error("Vision API client not initialized")
        raise HTTPException(
            status_code=503,
            detail="Vision API service unavailable",
        )

    if not image_content:
        raise HTTPException(
            status_code=400,
            detail="Empty image content",
        )

    image = vision.Image(content=image_content)
    response = vision_client.text_detection(image=image)

    if response.error.message:
        logger.error(f"Vision API error: {response.error.message}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process image with Vision API",
        )

    texts = response.text_annotations

    if not texts:
        return "", 0.0

    extracted_text = texts[0].description
    confidence = 0.95 if extracted_text else 0.0

    return extracted_text, confidence


# --- Endpoints ---


@app.get("/", response_model=ApiInfoModel)
async def root() -> ApiInfoModel:
    return ApiInfoModel(
        service="OCR Text Extraction API",
        status="running",
        version="1.0.0",
        endpoints={
            "extract_text": "/extract-text (POST)",
            "health": "/health (GET)",
        },
    )


@app.get("/health", response_model=HealthResponseModel)
async def health() -> HealthResponseModel:
    vision_status = "healthy" if vision_client is not None else "unavailable"
    return HealthResponseModel(
        status="healthy",
        vision_api=vision_status,
        timestamp=time.time(),
    )


@app.post("/extract-text", response_model=SuccessResponseModel)
async def extract_text(
    image: UploadFile = File(...),
) -> SuccessResponseModel:
    start_time = time.time()

    # Guard clause: validate format and extension
    validate_image(image)

    # Read file content
    image_content = await image.read()

    # Guard clause: check file size
    file_size = len(image_content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded",
        )

    # Extract text via Vision API
    extracted_text, confidence = extract_text_from_image(image_content)

    processing_time_ms = int((time.time() - start_time) * 1000)

    logger.info(f"Successfully processed {image.filename}")
    return SuccessResponseModel(
        success=True,
        text=extracted_text,
        confidence=confidence,
        processing_time_ms=processing_time_ms,
        metadata=MetadataModel(
            filename=image.filename,
            file_size_bytes=file_size,
            content_type=image.content_type,
        ),
    )


# --- Error Handlers ---


@app.exception_handler(413)
async def payload_too_large_handler(request, exc) -> JSONResponse:
    error_response = ErrorResponseModel(
        success=False,
        error="Payload too large",
        detail="File size exceeds 10MB limit",
        processing_time_ms=0,
    )
    return JSONResponse(
        status_code=413,
        content=error_response.model_dump(),
    )


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
