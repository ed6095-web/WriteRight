import io
import numpy as np
from PIL import Image, ImageOps

class EmptyDrawingError(ValueError):
    """Raised when an uploaded canvas image contains no detectable handwriting."""
    pass

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Preprocess an uploaded handwriting canvas image into a normalized 28x28x1 tensor
    conforming to MNIST CNN standards:
    
    1. Read input image bytes.
    2. Convert to grayscale.
    3. Ensure white strokes on black background (invert if canvas has light background).
    4. Detect non-background pixels and bounding box.
    5. Crop handwriting tightly to bounding box.
    6. Resize while preserving aspect ratio so the longest dimension is 20 pixels.
    7. Center the 20x20 digit inside a 28x28 black canvas.
    8. Normalize pixel values to range [0.0, 1.0].
    9. Reshape to (1, 28, 28, 1).
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Invalid image format: {e}")

    # Convert to grayscale
    gray_img = pil_img.convert("L")
    img_array = np.array(gray_img)

    # Determine background: if average corners/borders or mean > 128, canvas is light background
    # MNIST digits must have bright strokes (255) on a dark background (0)
    if np.mean(img_array) > 127:
        gray_img = ImageOps.invert(gray_img)
        img_array = np.array(gray_img)

    # Threshold foreground pixels (strokes)
    # Consider pixels above 25 as stroke content to ignore minor noise
    foreground_mask = img_array > 30

    if not np.any(foreground_mask):
        raise EmptyDrawingError("No handwriting detected. The drawing canvas is empty.")

    # Find bounding box coordinates
    rows = np.any(foreground_mask, axis=1)
    cols = np.any(foreground_mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Crop tightly to the handwriting bounding box
    # PIL crop box: (left, upper, right, lower)
    cropped = gray_img.crop((cmin, rmin, cmax + 1, rmax + 1))
    crop_w, crop_h = cropped.size

    # Scale so that the longer side is 20 pixels, preserving aspect ratio
    scale = 20.0 / max(crop_w, crop_h)
    new_w = max(1, int(round(crop_w * scale)))
    new_h = max(1, int(round(crop_h * scale)))

    # Use LANCZOS / Resampling.LANCZOS for smooth downsampling
    resized_digit = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Create a 28x28 black canvas (value 0)
    canvas_28 = Image.new("L", (28, 28), color=0)

    # Place the resized digit in the center of the 28x28 canvas
    offset_x = (28 - new_w) // 2
    offset_y = (28 - new_h) // 2
    canvas_28.paste(resized_digit, (offset_x, offset_y))

    # Center-of-mass adjustment (optional MNIST fine-tuning)
    # If the center of mass deviates significantly from (14, 14), shift slightly
    canvas_array = np.array(canvas_28, dtype=np.float32)
    total_mass = np.sum(canvas_array)
    if total_mass > 0:
        y_indices, x_indices = np.indices((28, 28))
        cy = np.sum(y_indices * canvas_array) / total_mass
        cx = np.sum(x_indices * canvas_array) / total_mass
        shift_x = int(round(14.0 - cx))
        shift_y = int(round(14.0 - cy))
        
        # Only apply small shifts (-3 to +3) to avoid pushing digit out of frame
        if abs(shift_x) <= 3 and abs(shift_y) <= 3 and (shift_x != 0 or shift_y != 0):
            shifted = Image.new("L", (28, 28), color=0)
            shifted.paste(canvas_28, (shift_x, shift_y))
            canvas_28 = shifted
            canvas_array = np.array(canvas_28, dtype=np.float32)

    # Normalize pixel values to 0.0 - 1.0
    normalized = canvas_array / 255.0

    # Reshape to (1, 28, 28, 1)
    tensor = normalized.reshape(1, 28, 28, 1)
    return tensor
