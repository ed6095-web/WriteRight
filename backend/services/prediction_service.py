import os
import logging
import numpy as np

# Ensure Keras selects torch backend on this environment if TensorFlow is not installed
os.environ.setdefault("KERAS_BACKEND", "torch")
import keras

logger = logging.getLogger(__name__)

ALPHABET = [chr(ord('A') + i) for i in range(26)]

class PredictionService:
    """
    Singleton service managing both the Digit CNN and Letter CNN models.
    Models are loaded once at server startup.
    """
    _instance = None
    _digit_model = None
    _letter_model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(base_dir, "..", "model")
        user_downloads_dir = r"C:\Users\Eashan Darsh\Downloads\WriteRight_Models"

        # 1. Load Digits Model (Check user Downloads first, then workspace model dir)
        digit_paths = [
            os.path.join(user_downloads_dir, "write_right_digits.keras"),
            os.path.join(models_dir, "write_right_digits.keras"),
            os.path.join(models_dir, "write_right_mnist.keras"),
            os.path.join(models_dir, "handwriting_model.keras"),
        ]
        for path in digit_paths:
            if os.path.exists(path):
                try:
                    logger.info(f"Loading Digits model from: {path}")
                    self._digit_model = keras.models.load_model(path)
                    logger.info(f"Digits model loaded successfully from: {path}")
                    break
                except Exception as e:
                    logger.error(f"Failed to load digit model from {path}: {e}")

        # 2. Load Controlled Letters Model (used for Letters and Words recognition)
        # Priority: C:\Users\Eashan Darsh\Downloads\WriteRight_Models
        letter_paths = [
            os.path.join(user_downloads_dir, "write_right_letters_controlled.keras"),
            os.path.join(user_downloads_dir, "write_right_letters.keras"),
            os.path.join(models_dir, "write_right_letters_controlled.keras"),
            os.path.join(models_dir, "write_right_letters.keras"),
        ]
        for path in letter_paths:
            if os.path.exists(path):
                try:
                    logger.info(f"Loading Letters model from: {path}")
                    self._letter_model = keras.models.load_model(path)
                    logger.info(f"Letters model loaded successfully from: {path}")
                    break
                except Exception as e:
                    logger.error(f"Failed to load letter model from {path}: {e}")

    @property
    def is_digit_model_loaded(self) -> bool:
        return self._digit_model is not None

    @property
    def is_letter_model_loaded(self) -> bool:
        return self._letter_model is not None

    @property
    def is_model_loaded(self) -> bool:
        return self.is_digit_model_loaded or self.is_letter_model_loaded

    def predict_digit(self, input_tensor: np.ndarray) -> dict:
        """
        Runs inference on 28x28 digit tensor.
        Output: 10 classes (0-9).
        """
        if not self.is_digit_model_loaded:
            raise RuntimeError("Digit model is not loaded on the server.")

        raw_output = self._digit_model.predict(input_tensor, verbose=0)
        probabilities = np.squeeze(raw_output)

        predicted_class = int(np.argmax(probabilities))
        confidence = float(np.max(probabilities))
        prob_list = [round(float(p), 4) for p in probabilities]

        return {
            "mode": "digit",
            "prediction": predicted_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_list,
        }

    def predict_letter(self, input_tensor: np.ndarray) -> dict:
        """
        Runs inference on 28x28 letter tensor.
        Output: 26 classes (A-Z).
        """
        if not self.is_letter_model_loaded:
            raise RuntimeError("Letter model is not loaded on the server.")

        raw_output = self._letter_model.predict(input_tensor, verbose=0)
        probabilities = np.squeeze(raw_output)

        predicted_idx = int(np.argmax(probabilities))
        predicted_char = ALPHABET[predicted_idx]
        confidence = float(np.max(probabilities))
        prob_list = [round(float(p), 4) for p in probabilities]

        return {
            "mode": "letter",
            "prediction": predicted_char,
            "confidence": round(confidence, 4),
            "probabilities": prob_list,
        }

    def predict_word(self, batch_tensors: np.ndarray, char_previews_b64: list[str]) -> dict:
        """
        Runs batch inference on segmented characters.
        Output: combined word prediction and character breakdown.
        """
        if not self.is_letter_model_loaded:
            raise RuntimeError("Letter model is not loaded on the server.")

        raw_outputs = self._letter_model.predict(batch_tensors, verbose=0)
        characters = []
        word_chars = []
        confidences = []

        for i, probs in enumerate(raw_outputs):
            idx = int(np.argmax(probs))
            char = ALPHABET[idx]
            conf = float(np.max(probs))
            word_chars.append(char)
            confidences.append(conf)

            characters.append({
                "prediction": char,
                "confidence": round(conf, 4),
                "debug_image_base64": char_previews_b64[i] if i < len(char_previews_b64) else None,
            })

        predicted_word = "".join(word_chars)
        overall_confidence = float(np.mean(confidences)) if confidences else 0.0

        return {
            "mode": "word",
            "prediction": predicted_word,
            "confidence": round(overall_confidence, 4),
            "characters": characters,
        }
