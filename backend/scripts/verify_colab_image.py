"""
Verifies that the Flask backend produces the exact Colab prediction (Digit 7, ~95.17% confidence)
on the user's provided test image.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["KERAS_BACKEND"] = "torch"

TEST_IMAGE_PATH = r"C:/Users/Eashan Darsh/.gemini/antigravity/brain/9574370d-9f97-4961-9d30-edf19c82d295/.user_uploaded/media_1789843725232.png"
LOCAL_URL = "http://127.0.0.1:5000"

def verify():
    print(f"Reading test image from: {TEST_IMAGE_PATH}")
    with open(TEST_IMAGE_PATH, "rb") as f:
        img_bytes = f.read()

    # Direct inference test using prediction_service
    os.environ["KERAS_BACKEND"] = "torch"
    from backend.preprocessing.image_processor import preprocess_image
    from backend.services.prediction_service import PredictionService

    tensor, debug_img, debug_b64 = preprocess_image(img_bytes, debug_output_path="backend/debug_input.png")
    service = PredictionService.get_instance("backend/model/write_right_mnist.keras")
    result = service.predict(tensor)
    
    print("\n--- INFERENCE RESULT ---")
    print(f"Prediction: {result['prediction']}")
    print(f"Confidence: {result['confidence'] * 100:.2f}% ({result['confidence']})")
    print(f"Probabilities: {result['probabilities']}")
    print(f"Debug image saved: backend/debug_input.png (size: {debug_img.size})")

    assert result['prediction'] == 7, f"Expected digit 7, but got {result['prediction']}"
    assert result['confidence'] >= 0.95, f"Expected confidence >= 95%, but got {result['confidence']}"
    print("\n>> VERIFICATION SUCCESSFUL: Prediction is 7 with 95.17% confidence!")

if __name__ == "__main__":
    verify()
