# Technical Context: OCR Text Extraction API

## Technology Stack

### Backend Framework

**FastAPI 0.109.0**
- **Purpose**: Web framework for building the REST API
- **Why**: High performance, async support, automatic OpenAPI docs
- **Key Features**:
  - Built on Starlette/Uvicorn
  - Type hints with Pydantic validation
  - Automatic interactive API documentation
  - Async/await support

### OCR Engine

**Google Cloud Vision API 3.7.0**
- **Purpose**: Text extraction from images
- **Why**: Industry-leading accuracy, fully managed, free tier
- **Key Features**:
  - Text detection (used in this project)
  - Document text detection (for dense text)
  - Language recognition (50+ languages)
  - Handwriting support
- **Pricing**: 
  - Free: First 1,000 units/month
  - Paid: $1.50 per 1,000 units

### Deployment Platform

**Google Cloud Run**
- **Purpose**: Serverless container hosting
- **Why**: Auto-scaling, pay-per-use, no infrastructure management
- **Configuration**:
  - Memory: 512Mi
  - CPU: 1
  - Timeout: 300s (5 minutes)
  - Max Instances: 10
  - Concurrency: 80 requests per instance
- **Pricing**:
  - Free: 2M requests/month, 180k vCPU-sec, 360k GiB-sec
  - Paid: $0.40 per million requests

### Production Server

**Gunicorn 21.2.0 + Uvicorn 0.27.0**
- **Purpose**: WSGI/ASGI server for production
- **Configuration**:
  - Workers: 1 (Cloud Run manages concurrency)
  - Worker Class: UvicornWorker (for async support)
  - Timeout: 0 (let Cloud Run handle timeouts)

### Programming Language

**Python 3.11**
- **Why**: 
  - Official Google Cloud client libraries
  - FastAPI native support
  - Strong typing with type hints
  - Excellent async/await support
  - 10-25% faster than Python 3.10

### Container Technology

**Docker**
- **Base Image**: `python:3.11-slim`
- **Why slim**: Smaller image size (~120MB vs ~900MB)
- **Optimization**: Multi-stage builds, layer caching

## Development Setup

### Required Tools

1. **gcloud CLI**
   - Purpose: Google Cloud Platform command-line interface
   - Installation: `curl https://sdk.cloud.google.com | bash`
   - Required for: Deployment, authentication, API management

2. **Docker** (optional, for local testing)
   - Purpose: Container building and testing
   - Installation: Platform-specific installers

3. **Python 3.11+**
   - Purpose: Local development and testing
   - Installation: Platform-specific package managers

4. **Git**
   - Purpose: Version control
   - Installation: Platform-specific package managers

### Python Dependencies

**requirements.txt**:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
google-cloud-vision==3.7.0
python-multipart==0.0.6
gunicorn==21.2.0
```

**Dependency Purposes**:
- `fastapi`: Web framework
- `uvicorn`: ASGI server (development)
- `google-cloud-vision`: Vision API client library
- `python-multipart`: Multipart form data parsing
- `gunicorn`: Production WSGI server

### Development Environment Setup

**Local Development**:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up Google Cloud credentials
gcloud auth application-default login

# Run locally
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8080
```

**Docker Development**:
```bash
# Build image
docker build -t ocr-api-local .

# Run container
docker run -p 8080:8080 \
  -v ~/.config/gcloud:/root/.config/gcloud \
  ocr-api-local
```

## Technical Constraints

### File Format Constraints

- **Supported**: JPG/JPEG only
- **Not Supported**: PNG, GIF, PDF, TIFF (future enhancement)
- **Validation**: Content-Type header + file extension check

### File Size Constraints

- **Maximum**: 10MB (10 * 1024 * 1024 bytes)
- **Enforcement**: Checked after reading file content
- **Error**: HTTP 413 Payload Too Large

### API Constraints

- **Timeout**: 300 seconds (5 minutes) per request
- **Concurrency**: 80 requests per Cloud Run instance
- **Scaling**: 0 to 10 instances (configurable)

### Vision API Constraints

- **Rate Limits**: Based on quota (1,000/month free)
- **Image Size**: Up to 20MB (we limit to 10MB)
- **Supported Formats**: JPEG, PNG, GIF, BMP, WEBP, RAW, ICO
- **Languages**: 50+ languages supported

## Development Workflow

### Code Structure

```
ocr-api/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container definition
├── deploy.sh               # Deployment automation
├── test_api.sh             # Integration tests
├── test_main.py            # Unit tests
├── .dockerignore           # Docker exclusions
├── .gitignore              # Git exclusions
└── test_images/            # Test images directory
```

### Build Process

1. **Local Build**:
   ```bash
   docker build -t ocr-api .
   ```

2. **Cloud Build**:
   ```bash
   gcloud builds submit --tag gcr.io/${PROJECT_ID}/ocr-api
   ```

### Deployment Process

1. **Enable APIs**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable vision.googleapis.com
   ```

2. **Build Container**:
   ```bash
   gcloud builds submit --tag gcr.io/${PROJECT_ID}/ocr-api
   ```

3. **Deploy Service**:
   ```bash
   gcloud run deploy ocr-text-extraction \
     --image gcr.io/${PROJECT_ID}/ocr-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Testing Workflow

1. **Unit Tests**:
   ```bash
   pytest test_main.py -v
   ```

2. **Integration Tests**:
   ```bash
   ./test_api.sh ${SERVICE_URL}
   ```

3. **Manual Testing**:
   ```bash
   curl -X POST -F "image=@test.jpg" ${SERVICE_URL}/extract-text
   ```

## Environment Variables

### Application Variables

- `PORT`: Port number (default: 8080, set by Cloud Run)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `PYTHONUNBUFFERED`: Set to 1 for immediate log output

### Google Cloud Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key (local dev)
- `GCP_PROJECT_ID`: Google Cloud project ID
- `GCP_REGION`: Deployment region (default: us-central1)

## Authentication & Authorization

### Local Development

**Application Default Credentials**:
```bash
gcloud auth application-default login
```

**Service Account Key** (alternative):
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
```

### Cloud Run Deployment

**Service Account**:
- Uses Cloud Run default service account
- Requires `roles/cloudvision.user` permission
- Automatically authenticated

**Public Access**:
- Initially: `--allow-unauthenticated`
- Future: Can enable authentication with IAM

## Monitoring & Logging

### Logging

**Framework**: Python `logging` module
**Levels**: INFO, ERROR
**Destination**: Cloud Run logs (Cloud Logging)

**View Logs**:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Metrics

**Available Metrics** (via Cloud Console):
- Request count
- Request latency (p50, p95, p99)
- Error rate
- Instance count
- Memory utilization
- CPU utilization

## Performance Considerations

### Optimization Techniques

1. **Connection Reuse**: Vision API client initialized once
2. **Async I/O**: Non-blocking file operations
3. **Early Validation**: Reject invalid requests quickly
4. **Efficient Serialization**: Fast JSON encoding

### Resource Allocation

- **Memory**: 512Mi (sufficient for 10MB images)
- **CPU**: 1 (I/O-bound work, doesn't need more)
- **Timeout**: 300s (allows for large image processing)

### Cold Start Mitigation

- **Default**: Scale to zero (free, but ~2-3s cold start)
- **Option**: `--min-instances 1` (~$10/month, no cold starts)

## Security Considerations

### Input Validation

- Content-Type header validation
- File extension validation
- File size limits
- Empty file detection

### Error Handling

- Generic error messages to clients
- Detailed logging internally
- No stack traces exposed

### Network Security

- HTTPS only (automatic via Cloud Run)
- No open ports (managed ingress)
- IAM integration available

## Cost Optimization

### Free Tier Usage

- **Cloud Run**: 2M requests/month free
- **Vision API**: 1,000 OCR operations/month free
- **Container Registry**: 0.5 GB storage free

### Cost Control

- **Max Instances**: Limit to 10 (prevents runaway costs)
- **Scale to Zero**: Default (no cost when idle)
- **Budget Alerts**: Set up in GCP Console

### Estimated Costs

- **Low Usage** (1,000 requests/month): $0.00
- **Medium Usage** (10,000 requests/month): ~$13.75
- **High Usage** (100,000 requests/month): ~$150.90

## Future Technical Enhancements

### Planned Additions

1. **Multi-format Support**: PNG, PDF, TIFF
2. **Caching Layer**: Redis for duplicate images
3. **Rate Limiting**: slowapi or similar
4. **Authentication**: API keys or OAuth
5. **Batch Processing**: Multiple images per request
6. **Webhook Support**: Async processing with callbacks

### Technology Considerations

- **Redis**: For caching (Cloud Memorystore)
- **Cloud Tasks**: For async processing
- **Cloud Storage**: For temporary file storage
- **Cloud Monitoring**: For advanced metrics and alerts
