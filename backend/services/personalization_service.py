import os
import sys
import time
import uuid
import json
import sqlite3
import hashlib
import logging
from typing import Optional, Dict, Any, List
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.image_processor import (
    _prepare_inverted_grayscale,
    segment_and_preprocess_word,
    EmptyDrawingError,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "personalization.db")
TRAINING_DATA_DIR = os.path.join(BASE_DIR, "training_data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
ACTIVE_MODEL_JSON = os.path.join(MODELS_DIR, "active_model.json")

PERSONALIZATION_MIN_SAMPLES = int(os.environ.get("PERSONALIZATION_MIN_SAMPLES", 20))


class PersonalizationService:
    """
    Manages persistent storage, metadata, duplicate rejection, character alignment,
    and lifecycle for real-time personalized handwriting learning.
    """
    _instance = None
    _training_in_progress = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(TRAINING_DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(TRAINING_DATA_DIR, "words"), exist_ok=True)
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(os.path.join(MODELS_DIR, "digits"), exist_ok=True)
        os.makedirs(os.path.join(MODELS_DIR, "letters"), exist_ok=True)

        for d in range(10):
            os.makedirs(os.path.join(TRAINING_DATA_DIR, "digits", str(d)), exist_ok=True)
        for i in range(26):
            char = chr(ord('A') + i)
            os.makedirs(os.path.join(TRAINING_DATA_DIR, "letters", char), exist_ok=True)

        # Initialize SQLite DB
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    sample_id TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    source TEXT NOT NULL,
                    predicted_label TEXT,
                    correct_label TEXT NOT NULL,
                    confidence REAL,
                    image_path TEXT NOT NULL,
                    image_hash TEXT UNIQUE NOT NULL,
                    used_for_training INTEGER DEFAULT 0,
                    training_version TEXT,
                    parent_word_id TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    version_num INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    baseline_accuracy REAL,
                    personal_accuracy REAL,
                    is_active INTEGER DEFAULT 0,
                    promoted INTEGER DEFAULT 0
                )
            """)
            conn.commit()

        self._ensure_active_model_json()
        logger.info("PersonalizationService initialized successfully.")

    def _get_connection(self):
        return sqlite3.connect(DB_PATH)

    def _ensure_active_model_json(self):
        if not os.path.exists(ACTIVE_MODEL_JSON):
            initial_data = {
                "digits": "v1",
                "letters": "v1",
                "updated_at": int(time.time() * 1000)
            }
            with open(ACTIVE_MODEL_JSON, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def get_active_versions(self) -> Dict[str, str]:
        self._ensure_active_model_json()
        try:
            with open(ACTIVE_MODEL_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading active_model.json: {e}")
            return {"digits": "v1", "letters": "v1"}

    @property
    def is_training_in_progress(self) -> bool:
        return self._training_in_progress

    @is_training_in_progress.setter
    def is_training_in_progress(self, val: bool):
        self._training_in_progress = val

    def record_feedback(
        self,
        image_bytes: bytes,
        mode: str,
        correct_label: str,
        predicted_label: Optional[str] = None,
        confidence: Optional[float] = None,
        source: str = "explicit_correction",
    ) -> Dict[str, Any]:
        """
        Validates, checks for duplicates, saves images into training_data/,
        and writes records to SQLite. Handles word character alignment.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Feedback image is empty.")

        # Validate handwriting presence
        inv = _prepare_inverted_grayscale(image_bytes)
        if np.max(inv) < 30:
            raise EmptyDrawingError("No detectable handwriting in image.")

        # Duplicate detection via SHA-256
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sample_id, correct_label FROM samples WHERE image_hash = ?", (image_hash,))
            existing = cursor.fetchone()
            if existing:
                logger.info(f"Duplicate feedback rejected (sample_id={existing[0]})")
                return {
                    "success": True,
                    "duplicate": True,
                    "sample_id": existing[0],
                    "message": "Duplicate sample ignored (already recorded).",
                }

        timestamp = int(time.time() * 1000)
        sample_id = f"s_{timestamp}_{uuid.uuid4().hex[:6]}"
        filename = f"{sample_id}.png"

        aligned_characters_count = 0

        if mode == "digit":
            val = int(correct_label)
            if not (0 <= val <= 9):
                raise ValueError(f"Invalid digit label '{correct_label}'. Must be 0-9.")
            label_str = str(val)
            dest_dir = os.path.join(TRAINING_DATA_DIR, "digits", label_str)
            os.makedirs(dest_dir, exist_ok=True)
            rel_path = os.path.join("training_data", "digits", label_str, filename)
            abs_path = os.path.join(BASE_DIR, rel_path)
            with open(abs_path, "wb") as f:
                f.write(image_bytes)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO samples (
                        sample_id, timestamp, mode, source, predicted_label,
                        correct_label, confidence, image_path, image_hash,
                        used_for_training
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    sample_id, timestamp, mode, source,
                    predicted_label, label_str, confidence,
                    rel_path, image_hash
                ))
                conn.commit()

        elif mode == "letter":
            char = correct_label.strip().upper()
            if len(char) != 1 or not ('A' <= char <= 'Z'):
                raise ValueError(f"Invalid letter label '{correct_label}'. Must be A-Z.")
            dest_dir = os.path.join(TRAINING_DATA_DIR, "letters", char)
            os.makedirs(dest_dir, exist_ok=True)
            rel_path = os.path.join("training_data", "letters", char, filename)
            abs_path = os.path.join(BASE_DIR, rel_path)
            with open(abs_path, "wb") as f:
                f.write(image_bytes)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO samples (
                        sample_id, timestamp, mode, source, predicted_label,
                        correct_label, confidence, image_path, image_hash,
                        used_for_training
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    sample_id, timestamp, mode, source,
                    predicted_label, char, confidence,
                    rel_path, image_hash
                ))
                conn.commit()

        elif mode == "word":
            word_clean = "".join(c for c in correct_label.strip().upper() if c.isalpha())
            if not word_clean:
                raise ValueError(f"Invalid word label '{correct_label}'. Must contain letters.")

            dest_dir = os.path.join(TRAINING_DATA_DIR, "words")
            os.makedirs(dest_dir, exist_ok=True)
            rel_path = os.path.join("training_data", "words", filename)
            abs_path = os.path.join(BASE_DIR, rel_path)
            with open(abs_path, "wb") as f:
                f.write(image_bytes)

            # Store the word entry
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO samples (
                        sample_id, timestamp, mode, source, predicted_label,
                        correct_label, confidence, image_path, image_hash,
                        used_for_training
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    sample_id, timestamp, mode, source,
                    predicted_label, word_clean, confidence,
                    rel_path, image_hash
                ))
                conn.commit()

            # Word Character Alignment: segment into character crops and attribute to letter model
            try:
                full_tensor, char_previews, _, valid_segments = segment_and_preprocess_word(image_bytes)
                num_segmented = full_tensor.shape[0] if (full_tensor is not None and full_tensor.ndim == 4) else 0
                if num_segmented == len(word_clean):
                    aligned_characters_count = len(word_clean)
                    with self._get_connection() as conn:
                        cursor = conn.cursor()
                        for idx in range(num_segmented):
                            c_label = word_clean[idx]
                            c_sub_id = f"{sample_id}_c{idx}"
                            c_filename = f"{c_sub_id}.png"
                            c_dir = os.path.join(TRAINING_DATA_DIR, "letters", c_label)
                            os.makedirs(c_dir, exist_ok=True)
                            c_rel_path = os.path.join("training_data", "letters", c_label, c_filename)
                            c_abs_path = os.path.join(BASE_DIR, c_rel_path)

                            # Save 28x28 normalized character image
                            char_pil = Image.fromarray((full_tensor[idx].squeeze() * 255.0).astype(np.uint8))
                            char_pil.save(c_abs_path, format="PNG")

                            with open(c_abs_path, "rb") as cf:
                                c_hash = hashlib.sha256(cf.read()).hexdigest()

                            cursor.execute("""
                                INSERT OR IGNORE INTO samples (
                                    sample_id, timestamp, mode, source, predicted_label,
                                    correct_label, confidence, image_path, image_hash,
                                    used_for_training, parent_word_id
                                ) VALUES (?, ?, 'letter', ?, ?, ?, ?, ?, ?, 0, ?)
                            """, (
                                c_sub_id, timestamp, source,
                                None, c_label, confidence,
                                c_rel_path, c_hash, sample_id
                            ))
                        conn.commit()
                    logger.info(f"Aligned {aligned_characters_count} character crops for word '{word_clean}' into letter training set.")
                else:
                    logger.info(
                        f"Word '{word_clean}' has length {len(word_clean)} but segmented {num_segmented} characters. "
                        "Safely stored whole word without character decomposition."
                    )
            except Exception as e:
                logger.warning(f"Character segmentation alignment skipped for word: {e}")

        else:
            raise ValueError(f"Unknown recognition mode: '{mode}'.")

        status = self.get_status()
        return {
            "success": True,
            "sample_id": sample_id,
            "mode": mode,
            "correct_label": correct_label,
            "aligned_characters": aligned_characters_count,
            "pending_samples": status["pending_samples"],
            "ready_for_training": status["pending_samples"] >= PERSONALIZATION_MIN_SAMPLES,
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive personalization metrics."""
        active = self.get_active_versions()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM samples")
            total_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE mode = 'digit'")
            digit_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE mode = 'letter'")
            letter_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE mode = 'word'")
            word_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE used_for_training = 0")
            pending_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE mode = 'digit' AND used_for_training = 0")
            pending_digit_samples = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM samples WHERE mode = 'letter' AND used_for_training = 0")
            pending_letter_samples = cursor.fetchone()[0]

        return {
            "enabled": True,
            "total_samples": total_samples,
            "digit_samples": digit_samples,
            "letter_samples": letter_samples,
            "word_samples": word_samples,
            "pending_samples": pending_samples,
            "pending_digit_samples": pending_digit_samples,
            "pending_letter_samples": pending_letter_samples,
            "active_digit_model": active.get("digits", "v1"),
            "active_letter_model": active.get("letters", "v1"),
            "min_samples_threshold": PERSONALIZATION_MIN_SAMPLES,
            "training_in_progress": self._training_in_progress,
        }

    def get_pending_samples(self, mode: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM samples
                WHERE mode = ? AND used_for_training = 0
                ORDER BY timestamp ASC LIMIT ?
            """, (mode, limit))
            return [dict(row) for row in cursor.fetchall()]

    def mark_samples_trained(self, sample_ids: List[str], version: str):
        if not sample_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in sample_ids)
            cursor.execute(f"""
                UPDATE samples
                SET used_for_training = 1, training_version = ?
                WHERE sample_id IN ({placeholders})
            """, [version] + sample_ids)
            conn.commit()

    def record_model_version(
        self,
        mode: str,
        version_num: int,
        file_path: str,
        baseline_acc: float,
        personal_acc: float,
        promoted: bool,
    ):
        version_id = f"{mode}_v{version_num}"
        created_at = int(time.time() * 1000)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO model_versions (
                    version_id, mode, version_num, file_path, created_at,
                    baseline_accuracy, personal_accuracy, is_active, promoted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, mode, version_num, file_path, created_at,
                baseline_acc, personal_acc, 1 if promoted else 0, 1 if promoted else 0
            ))
            if promoted:
                cursor.execute("""
                    UPDATE model_versions
                    SET is_active = 0
                    WHERE mode = ? AND version_id != ?
                """, (mode, version_id))
            conn.commit()

        if promoted:
            active = self.get_active_versions()
            active[mode] = f"v{version_num}"
            active["updated_at"] = created_at
            with open(ACTIVE_MODEL_JSON, "w", encoding="utf-8") as f:
                json.dump(active, f, indent=2)
            logger.info(f"Active model promoted: {mode} -> v{version_num}")
