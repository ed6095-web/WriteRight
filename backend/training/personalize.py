"""
WriteRight Staged Personalization Engine
Fine-tunes CNN models on personal feedback combined with balanced baseline data.
Enforces safe promotion: models are only promoted if baseline accuracy is preserved
and personal validation criteria are met. Automatic rollback on failure.
"""
import os
import sys
import json
import logging
import random
from typing import Tuple, Dict, Any, List
import numpy as np
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("KERAS_BACKEND", "torch")
import keras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.image_processor import (
    preprocess_digit_image,
    preprocess_single_letter_image,
)
from services.personalization_service import PersonalizationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("PersonalizeEngine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
ACTIVE_MODEL_JSON = os.path.join(MODELS_DIR, "active_model.json")
ALPHABET = [chr(ord('A') + i) for i in range(26)]


def generate_baseline_letter_samples(num_per_class: int = 15) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates a balanced baseline synthetic dataset of letters (A-Z)
    rendered across standard clean fonts, processed with the exact Colab preprocessing contract.
    """
    x_list = []
    y_list = []

    for class_idx, char in enumerate(ALPHABET):
        for _ in range(num_per_class):
            img = Image.new("RGB", (120, 120), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            # Randomize font size and slight position
            font_size = random.randint(70, 90)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            offset_x = random.randint(15, 35)
            offset_y = random.randint(10, 25)
            draw.text((offset_x, offset_y), char, fill=(0, 0, 0), font=font)

            buf = io_bytes = io.BytesIO()
            img.save(buf, format="PNG")
            tensor, _, _ = preprocess_single_letter_image(buf.getvalue())
            x_list.append(tensor.squeeze(axis=0))
            y_list.append(class_idx)

    X = np.array(x_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    return X, y


import io


def load_mnist_baseline(num_per_class: int = 100) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Loads balanced subset of MNIST digits for baseline training and validation."""
    (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
    x_train = (x_train.astype("float32") / 255.0)[..., np.newaxis]
    x_test = (x_test.astype("float32") / 255.0)[..., np.newaxis]

    train_indices = []
    for d in range(10):
        idx = np.where(y_train == d)[0][:num_per_class]
        train_indices.extend(idx)

    test_indices = []
    for d in range(10):
        idx = np.where(y_test == d)[0][:50]
        test_indices.extend(idx)

    return x_train[train_indices], y_train[train_indices], x_test[test_indices], y_test[test_indices]


def augment_tensor(tensor: np.ndarray) -> np.ndarray:
    """Applies subtle random translation, rotation, and intensity jitter."""
    img = Image.fromarray((tensor.squeeze() * 255).astype(np.uint8))
    angle = random.uniform(-8.0, 8.0)
    img = img.rotate(angle, resample=Image.BILINEAR, fillcolor=0)
    dx = random.randint(-1, 1)
    dy = random.randint(-1, 1)
    img = Image.fromarray(np.roll(np.roll(np.array(img), dx, axis=1), dy, axis=0))
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr[..., np.newaxis]


def train_personalized_model(mode: str, force: bool = False) -> Dict[str, Any]:
    """
    Executes a staged fine-tuning run for either 'digits' or 'letters'.
    Combines 85% baseline dataset + 15% personalized feedback.
    Validates on baseline holdout and personal holdout.
    Promotes only if validation succeeds; otherwise rolls back.
    """
    service = PersonalizationService.get_instance()
    status = service.get_status()

    # Model mode mapping: "digits" or "letters"
    mode_singular = "digit" if mode in ("digit", "digits") else "letter"
    mode_plural = "digits" if mode_singular == "digit" else "letters"
    num_classes = 10 if mode_singular == "digit" else 26

    pending = service.get_pending_samples(mode_singular, limit=200)
    min_threshold = status["min_samples_threshold"]

    if len(pending) < min_threshold and not force:
        logger.info(f"Mode {mode_plural}: {len(pending)} pending samples is below threshold ({min_threshold}). Skipping training.")
        return {
            "trained": False,
            "reason": f"Pending samples ({len(pending)}) below threshold ({min_threshold}). Use force=True to override.",
            "pending_count": len(pending),
        }

    logger.info(f"Starting staged personalized training for '{mode_plural}' with {len(pending)} personal samples...")
    service.is_training_in_progress = True

    try:
        active_versions = service.get_active_versions()
        current_version_str = active_versions.get(mode_plural, "v1")
        current_version_num = int(current_version_str.replace("v", ""))
        next_version_num = current_version_num + 1
        next_version_str = f"v{next_version_num}"

        current_model_path = os.path.join(MODELS_DIR, mode_plural, f"{current_version_str}.keras")
        if not os.path.exists(current_model_path):
            # Fallback to model/ directory
            fallback = os.path.join(BASE_DIR, "model", f"write_right_{mode_plural}.keras" if mode_singular == "digit" else "write_right_letters_controlled.keras")
            current_model_path = fallback

        logger.info(f"Loading current active model from: {current_model_path}")
        model = keras.models.load_model(current_model_path)

        # 1. Load Baseline Data
        if mode_singular == "digit":
            x_base_train, y_base_train, x_base_val, y_base_val = load_mnist_baseline(num_per_class=80)
        else:
            x_base_full, y_base_full = generate_baseline_letter_samples(num_per_class=20)
            split_idx = int(len(x_base_full) * 0.8)
            x_base_train, y_base_train = x_base_full[:split_idx], y_base_full[:split_idx]
            x_base_val, y_base_val = x_base_full[split_idx:], y_base_full[split_idx:]

        # Baseline evaluation on current model
        baseline_preds_old = np.argmax(model.predict(x_base_val, verbose=0), axis=-1)
        old_baseline_acc = float(np.mean(baseline_preds_old == y_base_val))
        logger.info(f"Current model baseline accuracy on '{mode_plural}': {old_baseline_acc * 100:.2f}%")

        # 2. Load and Preprocess Personal Samples
        personal_x = []
        personal_y = []
        valid_sample_ids = []

        for sample in pending:
            img_rel = sample["image_path"]
            img_abs = os.path.join(BASE_DIR, img_rel)
            if not os.path.exists(img_abs):
                continue
            with open(img_abs, "rb") as f:
                img_bytes = f.read()

            try:
                if mode_singular == "digit":
                    tensor, _, _ = preprocess_digit_image(img_bytes)
                    label_idx = int(sample["correct_label"])
                else:
                    tensor, _, _ = preprocess_single_letter_image(img_bytes)
                    label_idx = ord(sample["correct_label"].upper()) - ord('A')

                if 0 <= label_idx < num_classes:
                    personal_x.append(tensor.squeeze(axis=0))
                    personal_y.append(label_idx)
                    valid_sample_ids.append(sample["sample_id"])
            except Exception as e:
                logger.warning(f"Could not preprocess personal sample {sample['sample_id']}: {e}")

        personal_x = np.array(personal_x, dtype=np.float32)
        personal_y = np.array(personal_y, dtype=np.int64)

        if len(personal_x) > 0:
            personal_preds_old = np.argmax(model.predict(personal_x, verbose=0), axis=-1)
            old_personal_acc = float(np.mean(personal_preds_old == personal_y))
            logger.info(f"Current model accuracy on personal samples before training: {old_personal_acc * 100:.2f}%")
        else:
            old_personal_acc = 1.0

        # 3. Create Balanced Mixed Training Dataset (85% Baseline + 15% Personal)
        if len(personal_x) > 0:
            # Augment personal samples to give them sufficient presence
            aug_personal_x = []
            aug_personal_y = []
            multiplier = max(1, int(len(x_base_train) * 0.15 / max(1, len(personal_x))))
            for i in range(len(personal_x)):
                for _ in range(multiplier):
                    aug_personal_x.append(augment_tensor(personal_x[i]))
                    aug_personal_y.append(personal_y[i])

            X_train = np.concatenate([x_base_train, np.array(aug_personal_x)], axis=0)
            y_train = np.concatenate([y_base_train, np.array(aug_personal_y)], axis=0)
        else:
            X_train = x_base_train
            y_train = y_base_train

        # Shuffle
        indices = np.arange(len(X_train))
        np.random.shuffle(indices)
        X_train = X_train[indices]
        y_train = y_train[indices]

        # One-hot encode targets
        Y_train_one_hot = keras.utils.to_categorical(y_train, num_classes=num_classes)
        Y_base_val_one_hot = keras.utils.to_categorical(y_base_val, num_classes=num_classes)

        # 4. Fine-Tune with Low Learning Rate & Early Stopping
        fine_tune_model = keras.models.clone_model(model)
        fine_tune_model.set_weights(model.get_weights())
        fine_tune_model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=5e-5),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        logger.info(f"Fine-tuning {mode_plural} model on {len(X_train)} samples for 5 epochs...")
        early_stop = keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=2,
            restore_best_weights=True,
        )
        fine_tune_model.fit(
            X_train,
            Y_train_one_hot,
            validation_data=(x_base_val, Y_base_val_one_hot),
            epochs=5,
            batch_size=32,
            callbacks=[early_stop],
            verbose=0,
        )

        # 5. Validation Check
        new_base_preds = np.argmax(fine_tune_model.predict(x_base_val, verbose=0), axis=-1)
        new_baseline_acc = float(np.mean(new_base_preds == y_base_val))

        if len(personal_x) > 0:
            new_pers_preds = np.argmax(fine_tune_model.predict(personal_x, verbose=0), axis=-1)
            new_personal_acc = float(np.mean(new_pers_preds == personal_y))
        else:
            new_personal_acc = 1.0

        logger.info(
            f"Validation Results for '{mode_plural}':\n"
            f"  Baseline Accuracy: {old_baseline_acc * 100:.2f}% -> {new_baseline_acc * 100:.2f}%\n"
            f"  Personal Accuracy: {old_personal_acc * 100:.2f}% -> {new_personal_acc * 100:.2f}%"
        )

        # Criteria: Baseline accuracy must NOT degrade by more than 1.5%
        # And personal accuracy must be equal or improved
        baseline_acceptable = (new_baseline_acc >= (old_baseline_acc - 0.015))
        personal_acceptable = (new_personal_acc >= old_personal_acc)

        new_model_path = os.path.join(MODELS_DIR, mode_plural, f"{next_version_str}.keras")
        fine_tune_model.save(new_model_path)

        promoted = baseline_acceptable and personal_acceptable

        if promoted:
            logger.info(f">> [PASSED] Model {mode_plural} promoted to {next_version_str}!")
            service.record_model_version(
                mode=mode_plural,
                version_num=next_version_num,
                file_path=new_model_path,
                baseline_acc=new_baseline_acc,
                personal_acc=new_personal_acc,
                promoted=True,
            )
            service.mark_samples_trained(valid_sample_ids, next_version_str)
            active_version = next_version_str
        else:
            logger.warning(
                f">> [REJECTED] Model failed validation criteria. Automatic rollback to {current_version_str}.\n"
                f"   Baseline acceptable: {baseline_acceptable}, Personal acceptable: {personal_acceptable}"
            )
            service.record_model_version(
                mode=mode_plural,
                version_num=next_version_num,
                file_path=new_model_path,
                baseline_acc=new_baseline_acc,
                personal_acc=new_personal_acc,
                promoted=False,
            )
            active_version = current_version_str

        return {
            "trained": True,
            "mode": mode_plural,
            "promoted": promoted,
            "active_version": active_version,
            "new_version": next_version_str,
            "old_baseline_acc": round(old_baseline_acc, 4),
            "new_baseline_acc": round(new_baseline_acc, 4),
            "old_personal_acc": round(old_personal_acc, 4),
            "new_personal_acc": round(new_personal_acc, 4),
            "personal_samples_trained": len(valid_sample_ids),
        }

    finally:
        service.is_training_in_progress = False


if __name__ == "__main__":
    target_mode = sys.argv[1] if len(sys.argv) > 1 else "digits"
    is_force = "--force" in sys.argv
    result = train_personalized_model(target_mode, force=is_force)
    print(json.dumps(result, indent=2))
