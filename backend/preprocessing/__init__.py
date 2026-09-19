"""
Image preprocessing package for WriteRight.
"""
from .image_processor import preprocess_image, EmptyDrawingError

__all__ = ["preprocess_image", "EmptyDrawingError"]
