import io
import os
import base64
import numpy as np
from PIL import Image, ImageOps

class EmptyDrawingError(ValueError):
    """Raised when an uploaded canvas image contains no detectable handwriting."""
    pass

def preprocess_image(image_bytes: bytes, debug_output_path: str = None) -> tuple[np.ndarray, Image.Image, str]:
    """
    Preprocess an uploaded handwriting canvas image into a normalized 28x28x1 tensor
    conforming strictly to MNIST CNN specifications:
    
    1. Receive the actual drawing canvas image.
    2. Convert RGBA/RGB to grayscale, compositing any alpha on pure white.
    3. Convert the image to MNIST polarity:
       background = 0, handwriting = 255 (invert polarity).
    4. Detect handwriting pixels using a threshold.
    5. Find bounding box around handwriting.
    6. Crop ONLY the handwriting.
    7. Preserve aspect ratio.
    8. Resize the cropped handwriting so its largest dimension is approximately 20 pixels.
    9. Create a new 28x28 black image.
    10. Center the resized handwriting inside the 28x28 image.
    11. Convert to float32.
    12. Divide by 255.0.
    13. Reshape: (1, 28, 28, 1).
    14. Save debug_input.png and return base64 preview.

    Returns:
        (input_tensor, debug_image, debug_image_base64)
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Invalid image format: {e}")

    # Handle transparent background by compositing onto pure white
    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        if pil_img.mode == "RGBA":
            bg.paste(pil_img, mask=pil_img.split()[-1])
        else:
            bg.paste(pil_img.convert("RGBA"), mask=pil_img.convert("RGBA").split()[-1])
        pil_img = bg

    # 2. Convert to grayscale
    gray_img = pil_img.convert("L")
    img_array = np.array(gray_img)

    # 3. Convert image to MNIST polarity: background = 0, handwriting = 255
    if np.mean(img_array) > 127:
        # Light canvas background -> invert polarity so strokes become white on black
        inverted_img = ImageOps.invert(gray_img)
        inv_array = np.array(inverted_img)
    else:
        # Already dark background (e.g. Colab preprocessed test image)
        inverted_img = gray_img
        inv_array = img_array

    # Boost stroke intensity to MNIST brightness (stroke maximum should reach 255)
    max_val = float(np.max(inv_array))
    if max_val > 40:
        inv_array = np.clip(inv_array * (255.0 / max_val), 0, 255).astype(np.uint8)
        inverted_img = Image.fromarray(inv_array)

    # 4. Detect handwriting pixels using threshold
    foreground_mask = inv_array > 35
    if not np.any(foreground_mask):
        raise EmptyDrawingError("No handwriting detected. The drawing canvas is empty.")

    # 5. Find bounding box around handwriting
    rows = np.any(foreground_mask, axis=1)
    cols = np.any(foreground_mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # 6. Crop ONLY the handwriting
    cropped = inverted_img.crop((cmin, rmin, cmax + 1, rmax + 1))
    crop_w, crop_h = cropped.size

    # 7. Preserve aspect ratio
    # 8. Resize the cropped handwriting so its largest dimension is approximately 20 pixels
    scale = 20.0 / max(crop_w, crop_h)
    new_w = max(1, int(round(crop_w * scale)))
    new_h = max(1, int(round(crop_h * scale)))

    resized_digit = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 9. Create a new 28x28 black image
    canvas_28 = Image.new("L", (28, 28), color=0)

    # 10. Center the resized handwriting inside the 28x28 image
    offset_x = (28 - new_w) // 2
    offset_y = (28 - new_h) // 2
    canvas_28.paste(resized_digit, (offset_x, offset_y))

    # Save debug_input.png for inspection
    if debug_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(debug_output_path)), exist_ok=True)
        canvas_28.save(debug_output_path)

    # Convert to base64 PNG string for visual UI preview
    buf = io.BytesIO()
    canvas_28.save(buf, format="PNG")
    debug_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # 11. Convert to float32
    # 12. Divide by 255.0
    # 13. Reshape to (1, 28, 28, 1)
    tensor = (np.array(canvas_28, dtype=np.float32) / 255.0).reshape(1, 28, 28, 1)

    return tensor, canvas_28, debug_base64
