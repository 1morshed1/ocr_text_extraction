# Claude Implementation Guide: OCR Text Extraction API

## Project Overview

**Goal**: Build a production-ready OCR API that accepts JPG image uploads and returns extracted text in JSON format, deployed to Google Cloud Run.

**Status**: Documentation complete, code implementation needed.

**Important**: Always use Context7 MCP when library/API documentation, code generation, setup or configuration steps are needed without explicit request.

## FastAPI Rules Compliance (MANDATORY)

**CRITICAL**: All code MUST follow the FastAPI rules defined in `.cursor/rules/fastapi.mdc`. Key requirements:

- ✅ **Functional Programming**: No classes, only pure functions
- ✅ **Type Hints**: Required for ALL function signatures
- ✅ **Pydantic Models**: Use BaseModel for request/response validation (NOT raw dicts)
- ✅ **Guard Clauses**: Handle errors early, happy path last
- ✅ **Early Returns**: Use early returns for error conditions
- ✅ **Lifespan Context Managers**: Use `lifespan` instead of `@app.on_event()`
- ✅ **Async Functions**: Use `async def` for I/O-bound, `def` for pure functions
- ✅ **HTTPException**: Use for expected errors with appropriate status codes
- ✅ **Descriptive Names**: Use auxiliary verbs (is_valid, has_text, can_process)

## Core Requirements

### Functional Requirements
- ✅ Accept JPG/JPEG image uploads via POST `/extract-text`
- ✅ Extract text using Google Cloud Vision API
- ✅ Return JSON response with extracted text
- ✅ Handle cases where no text is found
- ✅ Support max 10MB file size
- ✅ Comprehensive error handling
- ✅ Health check endpoint (`/health`)
- ✅ API info endpoint (`/`)

### Technical Requirements
- **Framework**: FastAPI 0.109.0
- **OCR Engine**: Google Cloud Vision API 3.7.0
- **Deployment**: Google Cloud Run
- **Python Version**: 3.11+
- **File Format**: JPG/JPEG only
- **Max File Size**: 10MB

## File Structure to Create

```
ocr-api/
├── main.py                 # FastAPI application (PRIMARY FILE)
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container definition
├── deploy.sh              # Deployment automation
├── test_api.sh            # Integration tests
├── test_main.py           # Unit tests
├── .dockerignore          # Docker exclusions
├── .gitignore             # Git exclusions
└── test_images/           # Test images (optional)
```

## FastAPI Coding Standards (MUST FOLLOW)

### Key Principles
- **Functional Programming**: Avoid classes, prefer pure functions
- **Type Hints**: Use type hints for ALL function signatures
- **Pydantic Models**: Use Pydantic BaseModel for request/response validation (not raw dicts)
- **Error Handling**: Handle errors at the beginning, use early returns and guard clauses
- **Happy Path Last**: Place the happy path last in functions
- **Guard Clauses**: Use guard clauses for preconditions and invalid states
- **Async Operations**: Use `async def` for I/O-bound tasks, `def` for pure functions
- **HTTPException**: Use HTTPException for expected errors with specific HTTP status codes
- **Lifespan Context Managers**: Prefer lifespan context managers over `@app.on_event()`
- **Descriptive Names**: Use auxiliary verbs (e.g., `is_valid`, `has_text`, `can_process`)

### Error Handling Pattern
```python
# ✅ GOOD: Early returns, guard clauses, happy path last
def process_image(file: UploadFile) -> dict:
    if not is_valid_format(file):
        raise HTTPException(400, "Invalid format")
    
    if not is_valid_size(file):
        raise HTTPException(413, "File too large")
    
    # Happy path last
    return process_successfully(file)

# ❌ BAD: Nested if statements, happy path first
def process_image(file: UploadFile) -> dict:
    if is_valid_format(file):
        if is_valid_size(file):
            return process_successfully(file)
        else:
            raise HTTPException(413, "File too large")
    else:
        raise HTTPException(400, "Invalid format")
```

## Implementation Guide: main.py

### Application Structure

```python
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import vision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/jpg"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg"]

# Global Vision API client (initialized in lifespan)
vision_client: Optional[vision.ImageAnnotatorClient] = None


# Lifespan context manager (preferred over @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global vision_client
    
    # Startup: Initialize Vision API client
    try:
        vision_client = vision.ImageAnnotatorClient()
        logger.info("Vision API client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Vision API client: {e}")
        vision_client = None
    
    yield
    
    # Shutdown: Cleanup (if needed)
    logger.info("Application shutting down")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="OCR Text Extraction API",
    description="Extract text from JPG images using Google Cloud Vision API",
    version="1.0.0",
    lifespan=lifespan
)
```

### Pydantic Models for Request/Response

```python
# Response Models (use Pydantic, not raw dicts)
class MetadataModel(BaseModel):
    """File metadata"""
    filename: Optional[str]
    file_size_bytes: int
    content_type: Optional[str]


class SuccessResponseModel(BaseModel):
    """Success response model"""
    success: bool = True
    text: str
    confidence: float
    processing_time_ms: int
    metadata: MetadataModel


class ErrorResponseModel(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: str
    processing_time_ms: int = 0
```

### Required Endpoints

#### 1. Root Endpoint (`GET /`)
```python
class ApiInfoModel(BaseModel):
    """API information response"""
    service: str
    status: str
    version: str
    endpoints: dict[str, str]


@app.get("/", response_model=ApiInfoModel)
async def root() -> ApiInfoModel:
    """API information endpoint"""
    return ApiInfoModel(
        service="OCR Text Extraction API",
        status="running",
        version="1.0.0",
        endpoints={
            "extract_text": "/extract-text (POST)",
            "health": "/health (GET)"
        }
    )
```

#### 2. Health Check (`GET /health`)
```python
class HealthResponseModel(BaseModel):
    """Health check response"""
    status: str
    vision_api: str
    timestamp: float


@app.get("/health", response_model=HealthResponseModel)
async def health() -> HealthResponseModel:
    """Health check endpoint"""
    vision_status = "healthy" if vision_client is not None else "unavailable"
    return HealthResponseModel(
        status="healthy",
        vision_api=vision_status,
        timestamp=time.time()
    )
```

#### 3. Main OCR Endpoint (`POST /extract-text`)
```python
@app.post("/extract-text", response_model=SuccessResponseModel)
async def extract_text(image: UploadFile = File(...)) -> SuccessResponseModel:
    """
    Extract text from uploaded JPG image
    
    Args:
        image: JPG/JPEG image file (max 10MB)
    
    Returns:
        SuccessResponseModel with extracted text and metadata
    """
    start_time = time.time()
    
    # Guard clauses: Handle errors early, happy path last
    # Step 1: Validate file format and extension
    validate_image(image)
    
    # Step 2: Read file content asynchronously
    image_content = await image.read()
    
    # Step 3: Check file size (guard clause)
    file_size = len(image_content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )
    
    # Step 4: Extract text using Vision API
    extracted_text, confidence = extract_text_from_image(image_content)
    
    # Step 5: Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    # Step 6: Return Pydantic model (happy path last)
    logger.info(f"Successfully processed {image.filename}")
    return SuccessResponseModel(
        success=True,
        text=extracted_text,
        confidence=confidence,
        processing_time_ms=processing_time_ms,
        metadata=MetadataModel(
            filename=image.filename,
            file_size_bytes=file_size,
            content_type=image.content_type
        )
    )
```

### Required Helper Functions

#### Validation Function (Guard Clauses Pattern)
```python
def validate_image(file: UploadFile) -> None:
    """
    Validate uploaded image file using guard clauses.
    
    Raises HTTPException if validation fails.
    """
    # Guard clause 1: Content-Type header validation
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Only JPG/JPEG images are supported. "
                   f"Received: {file.content_type}"
        )
    
    # Guard clause 2: File extension validation
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )
    
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Only .jpg and .jpeg are supported. "
                   f"Received: {extension}"
        )
```

#### OCR Processing Function (Guard Clauses + Error Handling)
```python
def extract_text_from_image(image_content: bytes) -> tuple[str, float]:
    """
    Extract text from image using Google Cloud Vision API.
    
    Pure function (no side effects except logging).
    
    Args:
        image_content: Image file content as bytes
    
    Returns:
        tuple: (extracted_text, confidence_score)
    
    Raises:
        HTTPException: If Vision API is unavailable or processing fails
    """
    # Guard clause: Check Vision API client availability
    if vision_client is None:
        logger.error("Vision API client not initialized")
        raise HTTPException(
            status_code=503,
            detail="Vision API service unavailable"
        )
    
    # Guard clause: Validate input
    if not image_content:
        raise HTTPException(
            status_code=400,
            detail="Empty image content"
        )
    
    # Create Vision API image object
    image = vision.Image(content=image_content)
    
    # Perform text detection
    response = vision_client.text_detection(image=image)
    
    # Guard clause: Check for API errors
    if response.error.message:
        logger.error(f"Vision API error: {response.error.message}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process image with Vision API"
        )
    
    # Extract text from annotations
    texts = response.text_annotations
    
    # Guard clause: Handle no text found
    if not texts:
        return "", 0.0
    
    # Happy path: Extract text and calculate confidence
    extracted_text = texts[0].description
    confidence = 0.95 if extracted_text else 0.0
    
    return extracted_text, confidence
```

### Error Handlers (Using Pydantic Models)
```python
@app.exception_handler(413)
async def payload_too_large_handler(request, exc) -> JSONResponse:
    """Handle payload too large errors"""
    error_response = ErrorResponseModel(
        success=False,
        error="Payload too large",
        detail="File size exceeds 10MB limit",
        processing_time_ms=0
    )
    return JSONResponse(
        status_code=413,
        content=error_response.model_dump()
    )
```

## Implementation Guide: requirements.txt

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
google-cloud-vision==3.7.0
python-multipart==0.0.6
gunicorn==21.2.0
pydantic>=2.0.0
```

## Implementation Guide: Dockerfile

```dockerfile
# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 0 \
    main:app
```

## Implementation Guide: deploy.sh

```bash
#!/bin/bash
set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
SERVICE_NAME="ocr-text-extraction"
REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Prompt for project ID
read -p "Enter project ID: " input_project_id
if [ ! -z "$input_project_id" ]; then
    PROJECT_ID=$input_project_id
fi

# Set the project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build container image
echo "Building container image..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo "Deployment Complete!"
echo "Service URL: ${SERVICE_URL}"
```

## Implementation Guide: .dockerignore

```
__pycache__/
*.pyc
*.pyo
.Python
env/
venv/
.env
*.log
.git/
README.md
test_images/
*.jpg
*.jpeg
.pytest_cache
memory-bank/
*.md
```

## Implementation Guide: .gitignore

```
__pycache__/
*.pyc
*.pyo
.Python
env/
venv/
.env
*.log
.pytest_cache
.coverage
htmlcov/
dist/
build/
*.egg-info/
key.json
*.jpg
*.jpeg
*.png
.DS_Store
```

## Key Implementation Notes (Following FastAPI Rules)

### 1. Vision API Client Initialization
- ✅ Use lifespan context manager (NOT `@app.on_event`)
- ✅ Initialize once at startup, cleanup at shutdown
- ✅ Handle initialization failures gracefully
- ✅ Use guard clauses to check for None before using

### 2. Validation Strategy (Guard Clauses Pattern)
- ✅ Multiple validation layers (Content-Type + extension)
- ✅ Validate before reading file content (fail-fast)
- ✅ Use early returns/guard clauses for invalid states
- ✅ Check file size after reading (guard clause)

### 3. Error Handling (Early Returns Pattern)
- ✅ Handle errors at the beginning of functions
- ✅ Use guard clauses for preconditions
- ✅ Happy path comes last
- ✅ Use appropriate HTTP status codes:
  - `400`: Invalid input
  - `413`: Payload too large
  - `500`: Internal server error
  - `503`: Service unavailable
- ✅ Log errors internally, return generic messages to clients

### 4. Response Format (Pydantic Models)
- ✅ Use Pydantic BaseModel for ALL responses (not raw dicts)
- ✅ Define response models with type hints
- ✅ Use `response_model` parameter in route decorators
- ✅ Include `success` flag, metadata, processing time, confidence score

### 5. Function Definitions (Type Hints Required)
- ✅ Use `async def` for I/O-bound operations (file reading)
- ✅ Use `def` for pure functions (validation, processing)
- ✅ Add type hints to ALL function signatures
- ✅ Vision API calls are synchronous (use `def`)

### 6. Functional Programming
- ✅ Avoid classes, prefer pure functions
- ✅ Functions should have no side effects (except logging)
- ✅ Use descriptive variable names with auxiliary verbs
- ✅ Modularize code to avoid duplication

### 7. Logging
- ✅ Use Python `logging` module
- ✅ Log at INFO level for successful operations
- ✅ Log at ERROR level for failures
- ✅ Include relevant context (filename, error details)

## Testing Checklist

### Unit Tests (test_main.py)
- [ ] Health endpoint returns 200
- [ ] Root endpoint returns API info
- [ ] Valid JPG upload returns 200 with text
- [ ] Invalid format (PNG) returns 400
- [ ] Invalid extension returns 400
- [ ] Empty file returns 400
- [ ] File > 10MB returns 413
- [ ] No text found returns 200 with empty text

### Integration Tests (test_api.sh)
- [ ] Health check works
- [ ] Valid image upload works
- [ ] Invalid format rejected
- [ ] Error responses formatted correctly

## Deployment Checklist

- [ ] Google Cloud project created
- [ ] Billing enabled
- [ ] gcloud CLI authenticated
- [ ] APIs enabled (Cloud Build, Cloud Run, Vision API)
- [ ] Container builds successfully
- [ ] Service deploys to Cloud Run
- [ ] Public URL accessible
- [ ] Health endpoint responds
- [ ] OCR endpoint works with test image

## Response Format Examples

### Success Response
```json
{
  "success": true,
  "text": "Hello World!",
  "confidence": 0.95,
  "processing_time_ms": 1234,
  "metadata": {
    "filename": "test.jpg",
    "file_size_bytes": 524288,
    "content_type": "image/jpeg"
  }
}
```

### Error Response (400)
```json
{
  "detail": "Invalid file format. Only JPG/JPEG images are supported. Received: image/png"
}
```

### Error Response (413)
```json
{
  "success": false,
  "error": "Payload too large",
  "detail": "File size exceeds 10MB limit",
  "processing_time_ms": 0
}
```

## Quick Reference

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up credentials
gcloud auth application-default login

# Run locally
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Test Locally
```bash
# Health check
curl http://localhost:8080/health

# OCR test
curl -X POST -F "image=@test_image1.jpeg" http://localhost:8080/extract-text
```

### Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

## Important Reminders (FastAPI Rules)

1. **File Format**: Only JPG/JPEG supported (not PNG, PDF, etc.)
2. **File Size**: Maximum 10MB
3. **Error Messages**: Generic to clients, detailed in logs
4. **Vision API**: Use lifespan context manager for initialization
5. **Type Hints**: REQUIRED for all function signatures
6. **Pydantic Models**: Use BaseModel for responses (NOT raw dicts)
7. **Guard Clauses**: Handle errors early, happy path last
8. **Functional Style**: Avoid classes, prefer pure functions
9. **Async**: Use `async def` for I/O-bound, `def` for pure functions
10. **Logging**: Log all important operations and errors
11. **Response Models**: Use `response_model` parameter in decorators

## Documentation References

- **Full Implementation Guide**: `COMPLETE_IMPLEMENTATION_GUIDE.md`
- **Setup Guide**: `SETUP_GUIDE.md`
- **Memory Bank**: `memory-bank/` directory

## Next Steps After Implementation

1. Test locally with `test_image1.jpeg`
2. Run unit tests: `pytest test_main.py -v`
3. Build Docker image: `docker build -t ocr-api .`
4. Test Docker locally: `docker run -p 8080:8080 ocr-api`
5. Deploy to Cloud Run: `./deploy.sh`
6. Test deployed service
7. Update documentation if needed

---

**Ready to implement!** Follow the code structure above and refer to the detailed documentation for additional context.
