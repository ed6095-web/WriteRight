"""
Automated test suite for WriteRight Multimodal Backend.
Tests Digits, Letters, and Words pipelines across all endpoints.
"""
import io
import sys
import os
import requests
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:5000"

def create_digit_7():
    img = Image.new("RGB", (300, 300), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.line([(60, 50), (240, 50)], fill=(13, 71, 161), width=24)
    d.line([(240, 50), (120, 260)], fill=(13, 71, 161), width=24)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_letter_e():
    img = Image.new("RGB", (300, 300), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.line([(80, 50), (80, 250)], fill=(13, 71, 161), width=20)
    d.line([(80, 50), (200, 50)], fill=(13, 71, 161), width=20)
    d.line([(80, 150), (180, 150)], fill=(13, 71, 161), width=20)
    d.line([(80, 250), (200, 250)], fill=(13, 71, 161), width=20)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_word_hello():
    img = Image.new("RGB", (900, 300), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # H
    d.line([(50, 60), (50, 240)], fill=(13, 71, 161), width=18)
    d.line([(150, 60), (150, 240)], fill=(13, 71, 161), width=18)
    d.line([(50, 150), (150, 150)], fill=(13, 71, 161), width=18)
    # E
    d.line([(220, 60), (220, 240)], fill=(13, 71, 161), width=18)
    d.line([(220, 60), (310, 60)], fill=(13, 71, 161), width=18)
    d.line([(220, 150), (290, 150)], fill=(13, 71, 161), width=18)
    d.line([(220, 240), (310, 240)], fill=(13, 71, 161), width=18)
    # L
    d.line([(380, 60), (380, 240)], fill=(13, 71, 161), width=18)
    d.line([(380, 240), (470, 240)], fill=(13, 71, 161), width=18)
    # L
    d.line([(540, 60), (540, 240)], fill=(13, 71, 161), width=18)
    d.line([(540, 240), (630, 240)], fill=(13, 71, 161), width=18)
    # O
    d.ellipse([700, 60, 830, 240], outline=(13, 71, 161), width=18)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def run_all_tests():
    print(f"Connecting to WriteRight backend at {BASE_URL}...")

    # 1. Health check
    print("\n[TEST 1] GET /health")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(r.json())
    assert r.status_code == 200
    assert r.json().get("digit_model_loaded") is True
    assert r.json().get("letter_model_loaded") is True
    print(">> [PASSED] Models loaded successfully.")

    # 2. Digit Mode (Digit 7)
    print("\n[TEST 2] POST /predict (mode=digit, drawing 7)")
    r = requests.post(
        f"{BASE_URL}/predict",
        files={"image": ("digit_7.png", create_digit_7(), "image/png")},
        data={"mode": "digit"},
        timeout=10,
    )
    print("Response:", r.json())
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "digit"
    assert str(data["prediction"]) == "7"
    assert "debug_image_base64" in data
    print(f">> [PASSED] Digit recognized: {data['prediction']} ({data['confidence']*100:.2f}%)")

    # 3. Letter Mode (Letter E)
    print("\n[TEST 3] POST /predict (mode=letter, drawing E)")
    r = requests.post(
        f"{BASE_URL}/predict",
        files={"image": ("letter_e.png", create_letter_e(), "image/png")},
        data={"mode": "letter"},
        timeout=10,
    )
    print("Response:", r.json())
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "letter"
    assert data["prediction"] == "E"
    assert "debug_image_base64" in data
    print(f">> [PASSED] Letter recognized: {data['prediction']} ({data['confidence']*100:.2f}%)")

    # 4. Word Mode (Word HELLO)
    print("\n[TEST 4] POST /predict (mode=word, drawing HELLO)")
    r = requests.post(
        f"{BASE_URL}/predict",
        files={"image": ("word_hello.png", create_word_hello(), "image/png")},
        data={"mode": "word"},
        timeout=15,
    )
    print("Response:", r.json())
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "word"
    assert data["prediction"] == "HELLO"
    assert len(data["characters"]) == 5
    print(f">> [PASSED] Word recognized: {data['prediction']} ({data['confidence']*100:.2f}%)")

    # 5. Feedback Submissions
    print("\n[TEST 5] POST /feedback for all 3 modes")
    # Digit feedback
    r = requests.post(
        f"{BASE_URL}/feedback",
        files={"image": ("f_digit.png", create_digit_7(), "image/png")},
        data={"mode": "digit", "correct_label": "7"},
    )
    assert r.status_code == 200
    assert r.json().get("success") is True

    # Letter feedback
    r = requests.post(
        f"{BASE_URL}/feedback",
        files={"image": ("f_letter.png", create_letter_e(), "image/png")},
        data={"mode": "letter", "correct_label": "E"},
    )
    assert r.status_code == 200
    assert r.json().get("success") is True

    # Word feedback
    r = requests.post(
        f"{BASE_URL}/feedback",
        files={"image": ("f_word.png", create_word_hello(), "image/png")},
        data={"mode": "word", "correct_label": "HELLO"},
    )
    assert r.status_code == 200
    assert r.json().get("success") is True
    print(">> [PASSED] All feedback submissions stored successfully.")

    print("\n========================================================")
    print("ALL THREE MODES (DIGITS, LETTERS, WORDS) VERIFIED 100%!")
    print("========================================================")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
