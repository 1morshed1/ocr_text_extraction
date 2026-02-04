# OCR Text Extraction API

A FastAPI service that extracts text from JPG images using Google Cloud Vision API, designed for deployment on Google Cloud Run.

## Endpoints

| Method | Path            | Description                      |
|--------|-----------------|----------------------------------|
| GET    | `/`             | API info and available endpoints |
| GET    | `/health`       | Health check with Vision API status |
| POST   | `/extract-text` | Extract text from a JPG image    |

### POST /extract-text

Upload a JPG/JPEG image (max 10MB) as multipart form data with the field name `image`.

```bash
curl -X POST -F "image=@photo.jpg" https://YOUR_SERVICE_URL/extract-text
```

Response:

```json
{
  "success": true,
  "text": "Extracted text here",
  "confidence": 0.95,
  "processing_time_ms": 342,
  "metadata": {
    "filename": "photo.jpg",
    "file_size_bytes": 102400,
    "content_type": "image/jpeg"
  }
}
```

## Prerequisites

- Python 3.11+
- A GCP project with the [Cloud Vision API](https://cloud.google.com/vision) enabled
- Authentication configured (e.g. `GOOGLE_APPLICATION_CREDENTIALS` env var or default credentials)

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

The server starts on `http://localhost:8080`.

## Testing

Unit tests (mocks the Vision API client):

```bash
pip install pytest pillow
pytest test_main.py
```

Integration tests against a running server:

```bash
./test_api.sh                        # tests against localhost:8080
./test_api.sh https://YOUR_SERVICE_URL  # tests against a deployed URL
```

## Deploy to Cloud Run

Set your GCP project ID and run the deploy script:

```bash
export GCP_PROJECT_ID=my-project
export GCP_REGION=us-central1  # optional, defaults to us-central1
./deploy.sh
```

The script enables the required APIs, builds the container with Cloud Build, and deploys it to Cloud Run.

## Project Structure

```
main.py           - FastAPI application
Dockerfile        - Container image definition
deploy.sh         - Cloud Run deployment script
requirements.txt  - Python dependencies
test_main.py      - Unit tests
test_api.sh       - Integration test script
```
