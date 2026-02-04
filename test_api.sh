#!/bin/bash

API_URL="${1:-http://localhost:8080}"
PASSED=0
FAILED=0

echo "========================================="
echo "OCR API Testing Script"
echo "========================================="
echo "API URL: ${API_URL}"
echo ""

run_test() {
    local name="$1"
    local expected_code="$2"
    local actual_code="$3"

    if [ "$actual_code" -eq "$expected_code" ]; then
        echo "  ✓ PASSED: ${name} (HTTP ${actual_code})"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ FAILED: ${name} (expected ${expected_code}, got ${actual_code})"
        FAILED=$((FAILED + 1))
    fi
}

# --- Test 1: Health endpoint ---
echo "========================================="
echo "1. Testing Health Endpoint"
echo "========================================="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health")
run_test "GET /health" 200 "$CODE"
echo "  Response:"
curl -s "${API_URL}/health" | python3 -m json.tool 2>/dev/null || curl -s "${API_URL}/health"
echo ""

# --- Test 2: Root endpoint ---
echo "========================================="
echo "2. Testing Root Endpoint"
echo "========================================="
CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/")
run_test "GET /" 200 "$CODE"
echo ""

# --- Test 3: Valid image upload ---
echo "========================================="
echo "3. Testing Valid Image Upload"
echo "========================================="
if [ -f "test_image1.jpeg" ]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -F "image=@test_image1.jpeg" "${API_URL}/extract-text")
    run_test "POST /extract-text (valid JPG)" 200 "$CODE"
    echo "  Response:"
    curl -s -X POST -F "image=@test_image1.jpeg" "${API_URL}/extract-text" | python3 -m json.tool 2>/dev/null
else
    echo "  SKIPPED: test_image1.jpeg not found"
fi
echo ""

# --- Test 4: Invalid format (PNG) ---
echo "========================================="
echo "4. Testing Invalid Format (PNG)"
echo "========================================="
echo "fake png data" > /tmp/test_invalid.png
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -F "image=@/tmp/test_invalid.png;type=image/png" "${API_URL}/extract-text")
run_test "POST /extract-text (PNG rejected)" 400 "$CODE"
rm -f /tmp/test_invalid.png
echo ""

# --- Test 5: Empty file ---
echo "========================================="
echo "5. Testing Empty File"
echo "========================================="
touch /tmp/test_empty.jpg
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -F "image=@/tmp/test_empty.jpg;type=image/jpeg" "${API_URL}/extract-text")
run_test "POST /extract-text (empty file)" 400 "$CODE"
rm -f /tmp/test_empty.jpg
echo ""

# --- Test 6: Missing file parameter ---
echo "========================================="
echo "6. Testing Missing File Parameter"
echo "========================================="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/extract-text")
run_test "POST /extract-text (no file)" 422 "$CODE"
echo ""

# --- Summary ---
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Tests Passed: ${PASSED}"
echo "Tests Failed: ${FAILED}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo "All tests passed! ✓"
    exit 0
else
    echo "Some tests failed. ✗"
    exit 1
fi
