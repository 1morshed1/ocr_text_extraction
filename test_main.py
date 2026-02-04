import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _create_jpeg_bytes() -> bytes:
    """Create minimal valid JPEG bytes for testing."""
    try:
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        # Minimal JPEG header if Pillow is not installed
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01"
            b"\x00\x01\x00\x00" + b"\x00" * 100 + b"\xff\xd9"
        )


SAMPLE_JPEG = _create_jpeg_bytes()


# Patch Vision client before importing app so lifespan doesn't fail
@pytest.fixture(autouse=True)
def _patch_vision(monkeypatch):
    mock_client = MagicMock()

    # Default: return text annotations
    annotation = MagicMock()
    annotation.description = "Hello World"
    mock_response = MagicMock()
    mock_response.error.message = ""
    mock_response.text_annotations = [annotation]
    mock_client.text_detection.return_value = mock_response

    with patch("main.vision_client", mock_client):
        yield mock_client


@pytest.fixture()
def client():
    from main import app

    return TestClient(app)


# --- Root Endpoint ---


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "OCR Text Extraction API"
    assert data["status"] == "running"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data


# --- Health Endpoint ---


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "vision_api" in data
    assert "timestamp" in data


# --- Extract Text: Valid Requests ---


def test_extract_text_valid_jpg(client):
    files = {"image": ("test.jpg", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "text" in data
    assert "confidence" in data
    assert "processing_time_ms" in data
    assert data["metadata"]["filename"] == "test.jpg"


def test_extract_text_jpeg_extension(client):
    files = {"image": ("photo.jpeg", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 200
    assert response.json()["success"] is True


# --- Extract Text: Invalid Format ---


def test_extract_text_invalid_content_type(client):
    files = {"image": ("test.png", b"fakepng", "image/png")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]


def test_extract_text_invalid_extension(client):
    files = {"image": ("test.png", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


def test_extract_text_no_filename(client):
    files = {"image": ("", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    # Empty filename is rejected (422 by FastAPI or 400 by our validation)
    assert response.status_code in (400, 422)


# --- Extract Text: Size Validation ---


def test_extract_text_empty_file(client):
    files = {"image": ("test.jpg", b"", "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


def test_extract_text_file_too_large(client):
    large_content = b"\xff" * (10 * 1024 * 1024 + 1)
    files = {"image": ("test.jpg", large_content, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 413


# --- Extract Text: No Text Found ---


def test_extract_text_no_text_found(client, _patch_vision):
    mock_response = MagicMock()
    mock_response.error.message = ""
    mock_response.text_annotations = []
    _patch_vision.text_detection.return_value = mock_response

    files = {"image": ("test.jpg", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["text"] == ""
    assert data["confidence"] == 0.0


# --- Extract Text: Vision API Errors ---


def test_extract_text_vision_api_error(client, _patch_vision):
    mock_response = MagicMock()
    mock_response.error.message = "Some API error"
    _patch_vision.text_detection.return_value = mock_response

    files = {"image": ("test.jpg", SAMPLE_JPEG, "image/jpeg")}
    response = client.post("/extract-text", files=files)
    assert response.status_code == 500


def test_extract_text_vision_client_none(client):
    with patch("main.vision_client", None):
        files = {"image": ("test.jpg", SAMPLE_JPEG, "image/jpeg")}
        response = client.post("/extract-text", files=files)
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


# --- Missing Parameter ---


def test_extract_text_missing_file(client):
    response = client.post("/extract-text")
    assert response.status_code == 422
