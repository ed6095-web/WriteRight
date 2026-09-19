"""
Automated test suite for WriteRight Flask API.
Tests /health, /predict (with Colab ground truth and drawings), /debug_input.png, and /feedback.
"""
import io
import sys
import os
import requests
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:5000"
COLAB_TEST_IMG = r"C:/Users/Eashan Darsh/.gemini/antigravity/brain/9574370d-9f97-4961-9d30-edf19c82d295/.user_uploaded/media_1789843725232.png"

def create_synthetic_digit_8():
    """Create a white canvas with a blue handwritten-style 8."""
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw figure-8 using smooth ellipses
    draw.ellipse([100, 50, 200, 150], outline=(13, 71, 161), width=18)
    draw.ellipse([90, 140, 210, 260], outline=(13, 71, 161), width=18)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_empty_canvas():
    """Create an empty white canvas."""
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def run_tests():
    print(f"Connecting to WriteRight backend at {BASE_URL}...")
    
    # 1. Test /health
    print("\n[TEST 1] GET /health")
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert res.json().get("status") == "ok"
        assert res.json().get("model_loaded") is True
        print(">> [TEST 1 PASSED]: /health is healthy and user model is loaded.")
    except Exception as e:
        print(f">> [TEST 1 FAILED]: {e}")
        return False

    # 2. Test /predict with Colab Ground Truth Image
    print("\n[TEST 2] POST /predict (Colab Test Image -> Must predict 7 with ~95.17%)")
    try:
        if os.path.exists(COLAB_TEST_IMG):
            with open(COLAB_TEST_IMG, "rb") as f:
                colab_bytes = f.read()
            files = {"image": ("colab_7.png", colab_bytes, "image/png")}
            res = requests.post(f"{BASE_URL}/predict", files=files, timeout=10)
            print(f"Status code: {res.status_code}")
            data = res.json()
            print(f"Prediction: {data.get('prediction')}, Confidence: {data.get('confidence')}")
            assert res.status_code == 200
            assert data["prediction"] == 7, f"Expected 7, got {data['prediction']}"
            assert data["confidence"] >= 0.95, f"Expected >=0.95, got {data['confidence']}"
            assert "debug_image_base64" in data
            print(f">> [TEST 2 PASSED]: Correctly predicted 7 with {data['confidence']*100:.2f}% confidence!")
        else:
            print(">> [TEST 2 SKIPPED]: Colab test image path not found.")
    except Exception as e:
        print(f">> [TEST 2 FAILED]: {e}")
        return False

    # 3. Test /predict with Handwritten Blue 8
    print("\n[TEST 3] POST /predict (Synthetic Blue 8 on White Canvas)")
    try:
        digit_bytes = create_synthetic_digit_8()
        files = {"image": ("test_8.png", digit_bytes, "image/png")}
        res = requests.post(f"{BASE_URL}/predict", files=files, timeout=10)
        print(f"Status code: {res.status_code}")
        data = res.json()
        print(f"Prediction: {data.get('prediction')}, Confidence: {data.get('confidence')}")
        assert res.status_code == 200
        assert data["prediction"] == 8, f"Expected 8, got {data['prediction']}"
        assert data["confidence"] >= 0.90, f"Expected >= 90%, got {data['confidence']}"
        print(f">> [TEST 3 PASSED]: Correctly recognized blue digit 8 with {data['confidence']*100:.2f}% confidence.")
    except Exception as e:
        print(f">> [TEST 3 FAILED]: {e}")
        return False

    # 4. Test /debug_input.png endpoint
    print("\n[TEST 4] GET /debug_input.png")
    try:
        res = requests.get(f"{BASE_URL}/debug_input.png", timeout=5)
        print(f"Status code: {res.status_code}, Content-Type: {res.headers.get('Content-Type')}")
        assert res.status_code == 200
        assert "image/png" in res.headers.get("Content-Type", "")
        # Verify it is a valid 28x28 image
        img = Image.open(io.BytesIO(res.content))
        assert img.size == (28, 28), f"Expected (28, 28), got {img.size}"
        print(">> [TEST 4 PASSED]: /debug_input.png returned valid 28x28 PNG!")
    except Exception as e:
        print(f">> [TEST 4 FAILED]: {e}")
        return False

    # 5. Test /predict with empty canvas
    print("\n[TEST 5] POST /predict (Empty Canvas -> should return 400)")
    try:
        empty_bytes = create_empty_canvas()
        files = {"image": ("empty.png", empty_bytes, "image/png")}
        res = requests.post(f"{BASE_URL}/predict", files=files, timeout=10)
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "No handwriting detected" in res.json().get("error", "")
        print(">> [TEST 5 PASSED]: Correctly rejected empty canvas with friendly error.")
    except Exception as e:
        print(f">> [TEST 5 FAILED]: {e}")
        return False

    # 6. Test /feedback
    print("\n[TEST 6] POST /feedback (Store corrected sample for label 8)")
    try:
        digit_bytes = create_synthetic_digit_8()
        files = {"image": ("feedback_8.png", digit_bytes, "image/png")}
        payload = {"correct_label": "8"}
        res = requests.post(f"{BASE_URL}/feedback", files=files, data=payload, timeout=10)
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert res.json().get("success") is True
        print(">> [TEST 6 PASSED]: Successfully recorded feedback sample.")
    except Exception as e:
        print(f">> [TEST 6 FAILED]: {e}")
        return False

    print("\n==========================================")
    print("ALL API ENDPOINTS VALIDATED 100%!")
    print("==========================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
