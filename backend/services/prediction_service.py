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
    def get_instance(cls, model_path: str = "backend/model/write_right_mnist.keras"):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize(model_path)
        return cls._instance

    def initialize(self, model_path: str):
        self._model_path = model_path
        if not os.path.exists(model_path):
            # Check relative to module directory
            candidates = [
                os.path.join(os.path.dirname(__file__), "..", "model", "write_right_mnist.keras"),
                os.path.join(os.path.dirname(__file__), "..", "model", "handwriting_model.keras"),
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    model_path = cand
                    self._model_path = cand
                    break

        if os.path.exists(model_path):
            try:
                logger.info(f"Loading user-trained Keras model from: {model_path}")
                self._model = keras.models.load_model(model_path)
                self._model_loaded = True
                logger.info("write_right_mnist.keras model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Keras model: {e}")
                self._model = None
                self._model_loaded = False
        else:
            logger.warning(f"Model file not found at {model_path}.")
            self._model = None
            self._model_loaded = False

    @property
    def is_model_loaded(self) -> bool:
        return self._model_loaded and self._model is not None

    def predict(self, input_tensor: np.ndarray) -> dict:
        """
        Runs inference on the preprocessed (1, 28, 28, 1) tensor.
        Returns exact softmax output according to specification contract.
        """
        if not self.is_model_loaded:
            raise RuntimeError(
                f"Model is not loaded. Ensure 'write_right_mnist.keras' is located at {self._model_path}."
            )

        # Softmax predictions for (1, 28, 28, 1) input
        raw_output = self._model.predict(input_tensor, verbose=0)
        probabilities = np.squeeze(raw_output)

        predicted_class = int(np.argmax(probabilities))
        confidence = float(np.max(probabilities))

        # Return list of 10 float probabilities rounded to 4 decimals
        prob_list = [round(float(p), 4) for p in probabilities]

        return {
            "prediction": predicted_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_list,
        }
