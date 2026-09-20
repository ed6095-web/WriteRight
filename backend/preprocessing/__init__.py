"""
Image preprocessing package for WriteRight.
Supports digits, letters, and word segmentation.
"""
from .image_processor import (
    preprocess_digit_image,
    preprocess_single_letter_image,
    segment_and_preprocess_word,
    preprocess_letter_crop,
    EmptyDrawingError,
    WordSegmentationError,
)

# Backwards compatibility alias
preprocess_image = preprocess_digit_image

__all__ = [
    "preprocess_digit_image",
    "preprocess_single_letter_image",
    "segment_and_preprocess_word",
    "preprocess_letter_crop",
    "preprocess_image",
    "EmptyDrawingError",
    "WordSegmentationError",
]
