import sys
import os
import time
import uuid
import json
import logging
import threading
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
from services.personalization_service import PersonalizationService
from training.personalize import train_personalized_model

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
        - mode: 'digit' | 'letter' | 'word' (REQUIRED)
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided in request. Expected field 'image'."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename provided."}), 400

    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded image file is empty."}), 400

    # Explicit mode requirement (no silent fallback)
    raw_mode = request.form.get("mode") or request.args.get("mode")
    if not raw_mode:
        return jsonify({"error": "Missing required field 'mode'. Must be 'digit', 'letter', or 'word'."}), 400

    mode = raw_mode.strip().lower()
    if mode in ("digit", "digits"):
        mode = "digit"
    elif mode in ("letter", "letters"):
        mode = "letter"
    elif mode in ("word", "words"):
        mode = "word"
    else:
        return jsonify({"error": f"Invalid recognition mode '{raw_mode}'. Expected 'digit', 'letter', or 'word'."}), 400

    # Required debug logging
    print("Recognition mode:", mode, flush=True)
    print("MODE:", mode, flush=True)

    try:
        if mode == "digit":
            print("MODEL: digit", flush=True)
            input_tensor, debug_img, debug_b64 = preprocess_digit_image(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            result = prediction_service.predict_digit(input_tensor)
            result["debug_image_base64"] = debug_b64
            logger.info(f"[DIGIT] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%)")
            return jsonify(result), 200

        elif mode == "letter":
            print("MODEL: controlled letter", flush=True)
            input_tensor, debug_img, debug_b64 = preprocess_single_letter_image(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            result = prediction_service.predict_letter(input_tensor)
            result["debug_image_base64"] = debug_b64
            logger.info(f"[LETTER] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%)")
            return jsonify(result), 200

        elif mode == "word":
            print("MODEL: controlled letter + segmentation", flush=True)
            batch_tensors, char_previews_b64, combined_debug_b64, segments = segment_and_preprocess_word(
                image_bytes,
                debug_output_path=DEBUG_IMG_PATH
            )
            print("SEGMENTS:", len(segments), flush=True)
            print("LETTER INPUT SHAPE:", batch_tensors.shape, flush=True)

            result = prediction_service.predict_word(batch_tensors, char_previews_b64)
            result["debug_image_base64"] = combined_debug_b64
            result["character_previews_base64"] = char_previews_b64
            logger.info(f"[WORD] Predicted: {result['prediction']} ({result['confidence']*100:.2f}%) [{len(result['characters'])} chars]")
            return jsonify(result), 200

        else:
            return jsonify({"error": f"Unsupported recognition mode: '{mode}'"}), 400

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
        - mode: 'digit' | 'letter' | 'word' (REQUIRED)
        - correct_label / correct_word: user-entered correct answer
    """
    if "image" not in request.files:
        return jsonify({"error": "Missing 'image' file in feedback request."}), 400

    raw_mode = request.form.get("mode") or request.args.get("mode")
    if not raw_mode:
        return jsonify({"error": "Missing required field 'mode'. Must be 'digit', 'letter', or 'word'."}), 400

    mode = raw_mode.strip().lower()
    if mode in ("digit", "digits"):
        mode = "digit"
    elif mode in ("letter", "letters"):
        mode = "letter"
    elif mode in ("word", "words"):
        mode = "word"
    else:
        return jsonify({"error": f"Invalid feedback mode '{raw_mode}'. Expected 'digit', 'letter', or 'word'."}), 400

    correct_label_raw = (
        request.form.get("correct_label") or
        request.form.get("correct_word") or
        request.args.get("correct_label") or
        request.args.get("correct_word") or ""
    ).strip()

    if not correct_label_raw:
        return jsonify({"error": "Missing 'correct_label' or 'correct_word' form field."}), 400

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Missing 'image' file in request."}), 400
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded feedback image is empty."}), 400

    # Extract optional metadata
    source = request.form.get("source") or request.args.get("source") or "explicit_correction"
    predicted_label = request.form.get("predicted_label") or request.args.get("predicted_label")
    confidence_val = None
    try:
        raw_conf = request.form.get("confidence") or request.args.get("confidence")
        if raw_conf is not None:
            confidence_val = float(raw_conf)
    except Exception:
        pass

    try:
        pers_service = PersonalizationService.get_instance()
        result = pers_service.record_feedback(
            image_bytes=image_bytes,
            mode=mode,
            correct_label=correct_label_raw,
            predicted_label=predicted_label,
            confidence=confidence_val,
            source=source,
        )

        # Check if threshold reached to trigger background fine-tuning
        if result.get("ready_for_training") and not pers_service.is_training_in_progress:
            def _async_train():
                try:
                    logger.info(f"Threshold reached ({result.get('pending_samples')} samples). Starting background training...")
                    train_personalized_model(mode=mode)
                    prediction_service.reload_active_models()
                except Exception as e:
                    logger.error(f"Automatic background training failed: {e}")

            threading.Thread(target=_async_train, daemon=True).start()

        logger.info(f"Feedback stored successfully for mode='{mode}', label='{correct_label_raw}', source='{source}'")
        return jsonify({
            "success": True,
            "message": "Feedback sample recorded successfully into personalized learning dataset.",
            **result,
        }), 200

    except EmptyDrawingError as e:
        return jsonify({"error": f"Invalid drawing: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing feedback: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error: {e}"}), 500


@app.route("/personalization/status", methods=["GET"])
def personalization_status():
    """Returns real-time personalization metrics and pending sample counts."""
    service = PersonalizationService.get_instance()
    return jsonify(service.get_status()), 200


@app.route("/personalization/train", methods=["POST"])
def personalization_train():
    """
    Triggers an asynchronous model fine-tuning job in a background thread.
    Does NOT block recognition or predict requests.
    """
    data = request.get_json(silent=True) or {}
    mode = data.get("mode") or request.args.get("mode") or "digits"
    force = bool(data.get("force") or request.args.get("force"))

    service = PersonalizationService.get_instance()
    if service.is_training_in_progress:
        return jsonify({
            "success": False,
            "message": "Training is already in progress in the background.",
        }), 409

    def _run_train():
        try:
            train_personalized_model(mode=mode, force=force)
            prediction_service.reload_active_models()
        except Exception as e:
            logger.error(f"Manual training job failed: {e}")

    threading.Thread(target=_run_train, daemon=True).start()

    return jsonify({
        "success": True,
        "message": f"Personalized training job launched for mode '{mode}'. Inference remains active.",
    }), 202


@app.route("/personalization/model", methods=["GET"])
def personalization_model():
    """Returns active model version information."""
    service = PersonalizationService.get_instance()
    active = service.get_active_versions()
    return jsonify({
        "active_models": active,
        "status": service.get_status(),
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting WriteRight Multimodal server on 0.0.0.0:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
