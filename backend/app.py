import sys
import os
import time
import uuid
import json
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing.image_processor import (
    preprocess_digit_image,
    preprocess_single_letter_image,
    segment_and_preprocess_word,
    EmptyDrawingError,
    WordSegmentationError,
)
from services.prediction_service import PredictionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WriteRightAPI")

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_IMG_PATH = os.path.join(BASE_DIR, "debug_input.png")
DATA_DIR = os.path.join(BASE_DIR, "data")
FEEDBACK_DIR = os.path.join(DATA_DIR, "feedback")

# Ensure feedback directories exist
for d in range(10):
    os.makedirs(os.path.join(FEEDBACK_DIR, "digits", str(d)), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "user_samples", str(d)), exist_ok=True)

for letter_code in range(26):
    letter_char = chr(ord('A') + letter_code)
    os.makedirs(os.path.join(FEEDBACK_DIR, "letters", letter_char), exist_ok=True)

os.makedirs(os.path.join(FEEDBACK_DIR, "words"), exist_ok=True)

# Load models once at startup
prediction_service = PredictionService.get_instance()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to inspect server status and loaded models."""
    return jsonify({
        "status": "ok",
        "model_loaded": prediction_service.is_model_loaded,
        "digit_model_loaded": prediction_service.is_digit_model_loaded,
        "letter_model_loaded": prediction_service.is_letter_model_loaded,
    }), 200


@app.route("/debug_input.png", methods=["GET"])
def get_debug_input_image():
    """Returns the latest preprocessed 28x28 image sent to the CNN."""
    if os.path.exists(DEBUG_IMG_PATH):
        return send_file(DEBUG_IMG_PATH, mimetype="image/png")
    return jsonify({"error": "No debug image generated yet. Run /predict first."}), 404


@app.route("/predict", methods=["POST"])
def predict():
    """
    Multimodal recognition endpoint for digits, single letters, and words.
    Accepts:
        - image: multipart PNG file
        - mode: 'digit' | 'letter' | 'word' (defaults to 'digit')
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided in request. Expected field 'image'."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename provided."}), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded image file is empty."}), 400

    mode = request.form.get("mode", "digit").strip().lower()
    if mode not in ("digit", "digits", "letter", "letters", "word", "words"):
        mode = "digit"

    # Normalize mode string
    if mode in ("digit", "digits"):
        normalized_mode = "digit"
    elif mode in ("letter", "letters"):
        normalized_mode = "letter"
    else:
        normalized_mode = "word"

    try:
        if normalized_mode == "digit":
            input_tensor, debug_img, debug_b64 = preprocess_digit_image(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            result = prediction_service.predict_digit(input_tensor)
            result["debug_image_base64"] = debug_b64
            logger.info(f"[DIGIT] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%)")
            return jsonify(result), 200

        elif normalized_mode == "letter":
            input_tensor, debug_img, debug_b64 = preprocess_single_letter_image(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            result = prediction_service.predict_letter(input_tensor)
            result["debug_image_base64"] = debug_b64
            logger.info(f"[LETTER] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%)")
            return jsonify(result), 200

        else: # word
            batch_tensors, char_previews_b64, combined_debug_b64 = segment_and_preprocess_word(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            result = prediction_service.predict_word(batch_tensors, char_previews_b64)
            result["debug_image_base64"] = combined_debug_b64
            result["character_previews_base64"] = char_previews_b64
            logger.info(f"[WORD] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%) [{len(result['characters'])} chars]")
            return jsonify(result), 200

    except EmptyDrawingError as e:
        return jsonify({"error": str(e)}), 400
    except WordSegmentationError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        logger.error(f"Runtime error during inference: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected inference failure: {e}", exc_info=True)
        return jsonify({"error": f"Recognition failed: {str(e)}"}), 500


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Feedback submission endpoint supporting Digits, Letters, and Words.
    Accepts:
        - image: multipart PNG file
        - mode: 'digit' | 'letter' | 'word'
        - correct_label: string value of correct answer
    """
    if "image" not in request.files:
        return jsonify({"error": "Missing 'image' file in feedback request."}), 400

    mode = request.form.get("mode", "digit").strip().lower()
    correct_label_raw = request.form.get("correct_label", "").strip()

    if not correct_label_raw:
        return jsonify({"error": "Missing 'correct_label' form field."}), 400

    file = request.files["image"]
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded feedback image is empty."}), 400

    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:8]
    filename = f"sample_{timestamp}_{unique_id}.png"

    # Validation and routing per mode
    if mode in ("digit", "digits"):
        try:
            val = int(correct_label_raw)
            if not (0 <= val <= 9):
                raise ValueError()
            label_str = str(val)
        except ValueError:
            return jsonify({"error": f"Invalid digit label '{correct_label_raw}'. Must be 0-9."}), 400

        target_dir = os.path.join(FEEDBACK_DIR, "digits", label_str)
        # Also copy to legacy user_samples
        legacy_dir = os.path.join(DATA_DIR, "user_samples", label_str)
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(legacy_dir, exist_ok=True)

        with open(os.path.join(target_dir, filename), "wb") as f:
            f.write(image_bytes)
        with open(os.path.join(legacy_dir, filename), "wb") as f:
            f.write(image_bytes)

    elif mode in ("letter", "letters"):
        char = correct_label_raw.upper()
        if len(char) != 1 or not ('A' <= char <= 'Z'):
            return jsonify({"error": f"Invalid letter label '{correct_label_raw}'. Must be single character A-Z."}), 400

        target_dir = os.path.join(FEEDBACK_DIR, "letters", char)
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, filename), "wb") as f:
            f.write(image_bytes)

    elif mode in ("word", "words"):
        word_clean = "".join(c for c in correct_label_raw.upper() if c.isalpha())
        if not word_clean:
            return jsonify({"error": "Word label must contain valid letters A-Z."}), 400

        target_dir = os.path.join(FEEDBACK_DIR, "words")
        os.makedirs(target_dir, exist_ok=True)
        img_path = os.path.join(target_dir, filename)
        with open(img_path, "wb") as f:
            f.write(image_bytes)

        # Append to metadata.jsonl
        meta_record = {
            "timestamp": timestamp,
            "correct_word": word_clean,
            "filename": filename,
        }
        meta_path = os.path.join(target_dir, "metadata.jsonl")
        with open(meta_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta_record) + "\n")

    logger.info(f"Feedback stored successfully for mode='{mode}', label='{correct_label_raw}'")
    return jsonify({
        "success": True,
        "message": "Feedback sample stored successfully",
        "saved_file": filename,
        "mode": mode,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting WriteRight Multimodal server on 0.0.0.0:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
