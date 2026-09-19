"""
Automated test suite for WriteRight Flask API.
Tests /health, /predict, and /feedback endpoints.
"""
import io
import sys
import requests
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:5000"

def create_synthetic_digit_7():
    """Create a white canvas with a bold dark digit 7, simulating Flutter drawing canvas."""
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw digit 7
    # Top horizontal bar
    draw.line([(60, 50), (240, 50)], fill=(13, 71, 161), width=24)
    # Diagonal down to bottom
    draw.line([(240, 50), (120, 260)], fill=(13, 71, 161), width=24)
    
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
        print(f"Status code: {res.statusCode if hasattr(res, 'statusCode') else res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert res.json().get("status") == "ok"
        assert res.json().get("model_loaded") is True
        print(">> [TEST 1 PASSED]: /health is healthy and model is loaded.")
    except Exception as e:
        print(f">> [TEST 1 FAILED]: {e}")
        return False

    # 2. Test /predict with synthetic digit 7
    print("\n[TEST 2] POST /predict (Synthetic Digit 7)")
    try:
        digit_bytes = create_synthetic_digit_7()
        files = {"image": ("test_7.png", digit_bytes, "image/png")}
        res = requests.post(f"{BASE_URL}/predict", files=files, timeout=10)
        print(f"Status code: {res.status_code}")
        data = res.json()
        print(f"Response: {data}")
        assert res.status_code == 200
        assert "prediction" in data
        assert "confidence" in data
        assert "probabilities" in data
        print(f">> [TEST 2 PASSED]: Predicted digit {data['prediction']} with {data['confidence']*100:.2f}% confidence.")
    except Exception as e:
        print(f">> [TEST 2 FAILED]: {e}")
        return False

    # 3. Test /predict with empty canvas
    print("\n[TEST 3] POST /predict (Empty Canvas -> should return 400 with helpful message)")
    try:
        empty_bytes = create_empty_canvas()
        files = {"image": ("empty.png", empty_bytes, "image/png")}
        res = requests.post(f"{BASE_URL}/predict", files=files, timeout=10)
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "No handwriting detected" in res.json().get("error", "")
        print(">> [TEST 3 PASSED]: Correctly rejected empty canvas with friendly error.")
    except Exception as e:
        print(f">> [TEST 3 FAILED]: {e}")
        return False

    # 4. Test /feedback
    print("\n[TEST 4] POST /feedback (Store corrected sample for label 7)")
    try:
        digit_bytes = create_synthetic_digit_7()
        files = {"image": ("feedback_7.png", digit_bytes, "image/png")}
        payload = {"correct_label": "7"}
        res = requests.post(f"{BASE_URL}/feedback", files=files, data=payload, timeout=10)
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert res.json().get("success") is True
        print(">> [TEST 4 PASSED]: Successfully recorded feedback sample.")
    except Exception as e:
        print(f">> [TEST 4 FAILED]: {e}")
        return False

    print("\n==========================================")
    print("ALL API ENDPOINTS TESTED AND VALIDATED 100%!")
    print("==========================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
