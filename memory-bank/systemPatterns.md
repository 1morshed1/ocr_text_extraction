# System Patterns: OCR Text Extraction API

## Architecture Overview

### High-Level Architecture

```
┌─────────────┐
│   Client    │ (Browser, cURL, Mobile App)
└──────┬──────┘
       │ HTTPS POST /extract-text
       │ multipart/form-data
       ▼
┌─────────────────────────────────────┐
│      Google Cloud Run                │
│  ┌───────────────────────────────┐   │
│  │   FastAPI Application        │   │
│  │   (main.py)                  │   │
│  │                               │   │
│  │   1. Request Handler          │   │
│  │   2. Validation Layer         │   │
│  │   3. OCR Processing           │   │
│  │   4. Response Generator       │   │
│  └───────────────────────────────┘   │
└───────────────┬───────────────────────┘
                │
                │ Vision API Call
                │ (Service Account Auth)
                ▼
┌─────────────────────────────────────┐
│   Google Cloud Vision API            │
│   • Text Detection                   │
│   • Language Recognition              │
│   • Character Recognition             │
└─────────────────────────────────────┘
```

## Design Patterns

### 1. Layered Architecture

**Pattern**: Separation of concerns across layers

```
Request Layer (FastAPI endpoints)
    ↓
Validation Layer (Input validation)
    ↓
Business Logic Layer (OCR processing)
    ↓
External Service Layer (Vision API)
    ↓
Response Layer (JSON formatting)
```

**Benefits**:
- Clear separation of responsibilities
- Easy to test each layer independently
- Maintainable and extensible

### 2. Fail-Fast Validation

**Pattern**: Validate inputs early, reject invalid requests quickly

**Implementation**:
```python
# Multiple validation layers:
1. Content-Type header check
2. File extension validation
3. File size check (before reading)
4. Empty file detection
```

**Benefits**:
- Saves resources on invalid requests
- Clear error messages for users
- Security through defense-in-depth

### 3. Stateless Design

**Pattern**: No server-side state, each request is independent

**Characteristics**:
- No session storage
- No in-memory caching (initially)
- Each request is self-contained
- Vision API client reused but stateless

**Benefits**:
- Horizontal scalability
- No state synchronization needed
- Works well with Cloud Run's auto-scaling

### 4. Async I/O Pattern

**Pattern**: Non-blocking file operations

**Implementation**:
```python
async def extract_text(image: UploadFile):
    image_content = await image.read()  # Non-blocking
    # Process...
```

**Benefits**:
- Better resource utilization
- Handles concurrent requests efficiently
- Aligns with FastAPI's async capabilities

### 5. Error Handling Pattern

**Pattern**: Centralized exception handling with appropriate HTTP status codes

**Error Mapping**:
- `400`: Invalid input (format, extension, empty file)
- `413`: Payload too large (>10MB)
- `500`: Internal server error (Vision API errors, unexpected exceptions)
- `503`: Service unavailable (Vision API not initialized)

**Benefits**:
- Consistent error responses
- Proper HTTP semantics
- Better debugging with structured errors

### 6. Client Reuse Pattern

**Pattern**: Initialize Vision API client once, reuse for all requests

**Implementation**:
```python
# Module-level initialization
vision_client = vision.ImageAnnotatorClient()

# Reused in all requests
def extract_text_from_image(image_content):
    response = vision_client.text_detection(...)
```

**Benefits**:
- Connection pooling
- Reduced initialization overhead
- Better performance

## Component Relationships

### Core Components

#### 1. FastAPI Application (`main.py`)

**Responsibilities**:
- HTTP endpoint definitions
- Request/response handling
- Application lifecycle management

**Dependencies**:
- FastAPI framework
- Google Cloud Vision client
- Python standard library

**Exports**:
- `/` - API information endpoint
- `/health` - Health check endpoint
- `/extract-text` - Main OCR endpoint

#### 2. Validation Module

**Responsibilities**:
- File format validation
- File size validation
- Content-Type verification

**Dependencies**:
- FastAPI UploadFile type
- Application constants

**Exports**:
- `validate_image()` function

#### 3. OCR Processing Module

**Responsibilities**:
- Vision API integration
- Text extraction logic
- Confidence calculation

**Dependencies**:
- Google Cloud Vision client
- Image bytes

**Exports**:
- `extract_text_from_image()` function

#### 4. Response Formatter

**Responsibilities**:
- JSON response construction
- Metadata inclusion
- Error response formatting

**Dependencies**:
- FastAPI JSONResponse
- Request metadata

**Exports**:
- Response dictionaries

## Data Flow Patterns

### Request Flow

```
1. Client → POST /extract-text
   └─ multipart/form-data with image file

2. FastAPI → Receives UploadFile
   └─ Parses multipart form data

3. Validation → validate_image()
   ├─ Check Content-Type
   ├─ Check file extension
   └─ Validate file size

4. Processing → extract_text_from_image()
   ├─ Read file content (async)
   ├─ Create Vision API Image object
   ├─ Call text_detection()
   └─ Extract text from response

5. Response → JSONResponse
   ├─ Format success response
   ├─ Include metadata
   └─ Return to client
```

### Error Flow

```
1. Validation Error → HTTPException(400)
   └─ Return error JSON immediately

2. Size Error → HTTPException(413)
   └─ Return payload too large error

3. Vision API Error → HTTPException(500)
   └─ Log error, return generic message

4. Unexpected Error → HTTPException(500)
   └─ Log details, return safe error message
```

## Key Technical Decisions

### 1. FastAPI Framework

**Decision**: Use FastAPI instead of Flask/Django

**Rationale**:
- Native async support
- Automatic OpenAPI documentation
- Type safety with Pydantic
- High performance (Starlette/Uvicorn)

### 2. Google Cloud Vision API

**Decision**: Use Cloud Vision instead of Tesseract/AWS Textract

**Rationale**:
- Industry-leading accuracy
- Fully managed (no infrastructure)
- Native GCP integration
- Free tier available
- 50+ language support

### 3. Cloud Run Deployment

**Decision**: Deploy to Cloud Run instead of App Engine/Compute Engine

**Rationale**:
- Serverless (no infrastructure management)
- Auto-scaling (0 to N instances)
- Pay-per-use pricing
- Container-based (flexible)
- Fast deployment

### 4. Single Worker Gunicorn

**Decision**: Use 1 worker with Uvicorn worker class

**Rationale**:
- Cloud Run manages concurrency
- Multiple workers unnecessary
- Simpler configuration
- Better resource utilization

### 5. Python 3.11

**Decision**: Use Python 3.11 instead of 3.10 or 3.12

**Rationale**:
- Performance improvements (10-25% faster)
- Stable and well-supported
- Good library compatibility
- Modern language features

## Security Patterns

### 1. Input Validation

**Pattern**: Multiple validation layers

**Implementation**:
- Content-Type header validation
- File extension validation
- File size limits
- Empty file detection

**Security Benefits**:
- Prevents malicious file uploads
- Blocks non-image files
- Protects against file type spoofing

### 2. Error Message Sanitization

**Pattern**: Generic errors to clients, detailed logging internally

**Implementation**:
- Client receives: "Internal server error"
- Logs contain: Full stack traces and details

**Security Benefits**:
- No information leakage
- Prevents reconnaissance attacks
- Maintains security posture

### 3. HTTPS Only

**Pattern**: Enforce secure connections

**Implementation**:
- Cloud Run provides automatic SSL/TLS
- No HTTP endpoints exposed

**Security Benefits**:
- Encrypted data in transit
- Prevents man-in-the-middle attacks

## Performance Patterns

### 1. Connection Reuse

**Pattern**: Reuse Vision API client across requests

**Benefits**:
- Reduced connection overhead
- Better performance
- Lower latency

### 2. Async File Reading

**Pattern**: Non-blocking file I/O

**Benefits**:
- Better concurrency
- Efficient resource usage
- Handles multiple requests

### 3. Early Validation

**Pattern**: Validate before expensive operations

**Benefits**:
- Saves Vision API calls
- Reduces costs
- Faster error responses

## Deployment Patterns

### 1. Container-Based Deployment

**Pattern**: Docker container with all dependencies

**Benefits**:
- Consistent environments
- Easy deployment
- Portable across environments

### 2. Infrastructure as Code

**Pattern**: Deployment scripts and configuration files

**Benefits**:
- Reproducible deployments
- Version controlled
- Easy to update

### 3. Health Checks

**Pattern**: `/health` endpoint for monitoring

**Benefits**:
- Cloud Run can verify service health
- Monitoring integration
- Debugging support

## Future Pattern Considerations

### 1. Caching Pattern
- Cache results for duplicate images
- Reduce Vision API calls
- Improve response times

### 2. Rate Limiting Pattern
- Prevent abuse
- Fair resource usage
- Cost control

### 3. Authentication Pattern
- API keys or OAuth
- User-specific rate limits
- Usage tracking

### 4. Batch Processing Pattern
- Process multiple images
- Better throughput
- Reduced overhead
