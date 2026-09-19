import os
import logging
import numpy as np

# Ensure Keras selects torch backend on this environment if TensorFlow is not installed
os.environ.setdefault("KERAS_BACKEND", "torch")
import keras

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Singleton service managing the trained Keras CNN model.
    The model is loaded once at server startup.
    """
    _instance = None
    _model = None
    _model_loaded = False
    _model_path = ""

    @classmethod
    def get_instance(cls, model_path: str = "backend/model/handwriting_model.keras"):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize(model_path)
        return cls._instance

    def initialize(self, model_path: str):
        self._model_path = model_path
        if not os.path.exists(model_path):
            # Also check relative to current working directory or file location
            alt_path = os.path.join(os.path.dirname(__file__), "..", "model", "handwriting_model.keras")
            if os.path.exists(alt_path):
                model_path = alt_path
                self._model_path = alt_path

        if os.path.exists(model_path):
            try:
                logger.info(f"Loading Keras model from: {model_path}")
                self._model = keras.models.load_model(model_path)
                self._model_loaded = True
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Keras model: {e}")
                self._model = None
                self._model_loaded = False
        else:
            logger.warning(
                f"Model file not found at {model_path}. "
                "Please place 'handwriting_model.keras' in backend/model/."
            )
            self._model = None
            self._model_loaded = False

    @property
    def is_model_loaded(self) -> bool:
        return self._model_loaded and self._model is not None

    def predict(self, input_tensor: np.ndarray) -> dict:
        """
        Runs inference on the preprocessed (1, 28, 28, 1) tensor.
        Returns:
            {
                "prediction": int,
                "confidence": float,
                "probabilities": { "0": 0.0000, ... "9": 0.0000 }
            }
        """
        if not self.is_model_loaded:
            raise RuntimeError(
                f"Model is not loaded. Please ensure 'handwriting_model.keras' is located at {self._model_path}."
            )

        # Predict softmax probabilities (shape: (1, 10))
        raw_output = self._model.predict(input_tensor, verbose=0)
        probabilities = np.squeeze(raw_output)

        predicted_class = int(np.argmax(probabilities))
        confidence = float(np.max(probabilities))

        prob_dict = {
            str(i): round(float(probabilities[i]), 4)
            for i in range(10)
        }

        return {
            "prediction": predicted_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_dict,
        }
