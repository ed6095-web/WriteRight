import sys
import os
import time
import uuid
import logging

# Ensure backend directory is in python module search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

from preprocessing.image_processor import preprocess_image, EmptyDrawingError
from services.prediction_service import PredictionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WriteRightAPI")

app = Flask(__name__)
# Enable CORS for all routes to allow Flutter web or mobile access
CORS(app)

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "handwriting_model.keras")
DATA_DIR = os.path.join(BASE_DIR, "data", "user_samples")

# Ensure user sample directories (0-9) exist
for digit in range(10):
    os.makedirs(os.path.join(DATA_DIR, str(digit)), exist_ok=True)

# Load model once at startup
prediction_service = PredictionService.get_instance(MODEL_PATH)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to inspect server status and model loading."""
    return jsonify({
        "status": "ok",
        "model_loaded": prediction_service.is_model_loaded
    }), 200


@app.route("/predict", methods=["POST"])
def predict():
    """
    Accepts multipart/form-data with 'image' file.
    Preprocesses the image, feeds it to the CNN, and returns prediction.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided in request. Expected field 'image'."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename provided."}), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded image file is empty."}), 400

    try:
        # Preprocessing pipeline
        input_tensor = preprocess_image(image_bytes)
    except EmptyDrawingError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Image preprocessing error: {e}")
        return jsonify({"error": f"Invalid or unreadable image: {str(e)}"}), 400

    try:
        # Inference pipeline
        result = prediction_service.predict(input_tensor)
        logger.info(f"Prediction: {result['prediction']} (confidence: {result['confidence']:.4f})")
        return jsonify(result), 200
    except RuntimeError as e:
        logger.error(f"Prediction runtime error: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected prediction error: {e}")
        return jsonify({"error": f"Inference failed: {str(e)}"}), 500


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Accepts user-corrected or confirmed samples.
    Stores the handwriting image in backend/data/user_samples/<correct_label>/
    """
    if "image" not in request.files:
        return jsonify({"error": "Missing 'image' file in feedback request."}), 400

    correct_label_raw = request.form.get("correct_label")
    if correct_label_raw is None:
        return jsonify({"error": "Missing 'correct_label' form field."}), 400

    try:
        correct_label = int(correct_label_raw)
        if not (0 <= correct_label <= 9):
            raise ValueError()
    except ValueError:
        return jsonify({"error": f"Invalid correct_label: '{correct_label_raw}'. Must be an integer 0–9."}), 400

    file = request.files["image"]
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded feedback image is empty."}), 400

    # Store sample in destination directory
    target_dir = os.path.join(DATA_DIR, str(correct_label))
    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:8]
    filename = f"sample_{timestamp}_{unique_id}.png"
    filepath = os.path.join(target_dir, filename)

    try:
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Saved feedback sample for label {correct_label}: {filepath}")
        return jsonify({
            "success": True,
            "message": "Sample stored successfully",
            "saved_file": filename
        }), 200
    except Exception as e:
        logger.error(f"Failed to save feedback sample: {e}")
        return jsonify({"error": f"Failed to save sample: {str(e)}"}), 500


if __name__ == "__main__":
    # Host 0.0.0.0 allows connections from local network devices and cloud hosts
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting WriteRight Flask server on 0.0.0.0:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
