import io
import os
import base64
import numpy as np
from PIL import Image, ImageOps

class EmptyDrawingError(ValueError):
    """Raised when an uploaded canvas image contains no detectable handwriting."""
    pass

class WordSegmentationError(ValueError):
    """Raised when handwritten word cannot be separated into characters."""
    pass


def _prepare_inverted_grayscale(image_bytes: bytes) -> np.ndarray:
    """
    Converts uploaded canvas image bytes to an inverted grayscale uint8 numpy array
    where background is 0 (black) and handwriting strokes are bright (up to 255).
    Handles transparency and dark/light stroke polarity.
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Invalid image format: {e}")

    # Composite alpha on pure white
    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        if pil_img.mode == "RGBA":
            bg.paste(pil_img, mask=pil_img.split()[-1])
        else:
            bg.paste(pil_img.convert("RGBA"), mask=pil_img.convert("RGBA").split()[-1])
        pil_img = bg

    gray = pil_img.convert("L")
    arr = np.array(gray, dtype=np.uint8)

    # Invert if light canvas background so strokes are bright on black background
    if np.mean(arr) > 127:
        inv_arr = 255 - arr
    else:
        inv_arr = arr

    # Normalize stroke peak intensity to 255 if strokes exist
    max_val = float(np.max(inv_arr))
    if max_val > 30:
        inv_arr = np.clip(inv_arr * (255.0 / max_val), 0, 255).astype(np.uint8)

    return inv_arr


def preprocess_digit_image(image_bytes: bytes, debug_output_path: str = None) -> tuple[np.ndarray, Image.Image, str]:
    """
    Digit Preprocessing Pipeline:
    1. Grayscale & invert to black background / bright strokes.
    2. Threshold foreground strokes (> 35).
    3. Crop tightly to bounding box.
    4. Preserve aspect ratio & scale largest dimension to 20 pixels.
    5. Center inside 28x28 black canvas.
    6. Normalize to [0.0, 1.0] and reshape to (1, 28, 28, 1).
    """
    inv_arr = _prepare_inverted_grayscale(image_bytes)

    foreground_mask = inv_arr > 35
    if not np.any(foreground_mask):
        raise EmptyDrawingError("No handwriting detected. The drawing canvas is empty.")

    rows = np.any(foreground_mask, axis=1)
    cols = np.any(foreground_mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    inv_img = Image.fromarray(inv_arr)
    cropped = inv_img.crop((cmin, rmin, cmax + 1, rmax + 1))
    crop_w, crop_h = cropped.size

    scale = 20.0 / max(crop_w, crop_h)
    new_w = max(1, int(round(crop_w * scale)))
    new_h = max(1, int(round(crop_h * scale)))

    resized_digit = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas_28 = Image.new("L", (28, 28), color=0)
    offset_x = (28 - new_w) // 2
    offset_y = (28 - new_h) // 2
    canvas_28.paste(resized_digit, (offset_x, offset_y))

    if debug_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(debug_output_path)), exist_ok=True)
        canvas_28.save(debug_output_path)

    buf = io.BytesIO()
    canvas_28.save(buf, format="PNG")
    debug_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    tensor = (np.array(canvas_28, dtype=np.float32) / 255.0).reshape(1, 28, 28, 1)
    return tensor, canvas_28, debug_base64


def preprocess_letter_crop(crop: np.ndarray) -> np.ndarray:
    """
    Exact Colab letter crop preprocessing function.
    Finds coords where crop > 30, crops tightly, scales max dimension to 20,
    centers in (28, 28), and divides by 255.0.
    Returns (28, 28) float32 array or None if empty.
    """
    coords = np.argwhere(crop > 30)
    if coords.size == 0:
        return None

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)

    cropped = crop[y_min:y_max + 1, x_min:x_max + 1]
    h, w = cropped.shape

    scale = 20.0 / max(h, w)
    new_h = max(1, int(round(h * scale)))
    new_w = max(1, int(round(w * scale)))

    # Use PIL bilinear resize matching Colab tf.image.resize
    pil_cropped = Image.fromarray(cropped)
    resized = np.array(
        pil_cropped.resize((new_w, new_h), Image.Resampling.BILINEAR),
        dtype=np.float32
    )

    final = np.zeros((28, 28), dtype=np.float32)
    y_offset = (28 - new_h) // 2
    x_offset = (28 - new_w) // 2

    final[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    final = final / 255.0
    return final


def preprocess_single_letter_image(image_bytes: bytes, debug_output_path: str = None) -> tuple[np.ndarray, Image.Image, str]:
    """
    Single Letter Preprocessing:
    Takes full canvas image, inverts, and passes to preprocess_letter_crop.
    """
    inv_arr = _prepare_inverted_grayscale(image_bytes)
    final_28 = preprocess_letter_crop(inv_arr)

    if final_28 is None:
        raise EmptyDrawingError("No handwriting detected. The drawing canvas is empty.")

    canvas_28 = Image.fromarray((final_28 * 255.0).astype(np.uint8))

    if debug_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(debug_output_path)), exist_ok=True)
        canvas_28.save(debug_output_path)

    buf = io.BytesIO()
    canvas_28.save(buf, format="PNG")
    debug_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    tensor = final_28.reshape(1, 28, 28, 1)
    return tensor, canvas_28, debug_base64


def segment_and_preprocess_word(image_bytes: bytes, debug_output_path: str = None) -> tuple[np.ndarray, list[str], str, list]:
    """
    Word Segmentation and Preprocessing:
    1. Invert canvas so handwriting is bright on black.
    2. Segment individual characters using vertical projection and gap detection.
    3. Run preprocess_letter_crop on each character crop.
    4. Return (N, 28, 28, 1) tensor, per-character base64 previews, combined debug base64, and segments list.
    """
    inv_arr = _prepare_inverted_grayscale(image_bytes)

    # Column projection
    col_sum = np.sum(inv_arr > 30, axis=0)
    active_cols = np.where(col_sum > 0)[0]

    if active_cols.size == 0:
        raise EmptyDrawingError("No handwriting detected. The drawing canvas is empty.")

    # Detect horizontal gaps between letters
    diffs = np.diff(active_cols)
    # Gap threshold: at least 6 pixels or 0.01 of image width
    gap_threshold = max(6, int(0.01 * inv_arr.shape[1]))
    split_points = np.where(diffs > gap_threshold)[0]

    start_indices = [active_cols[0]] + [active_cols[i + 1] for i in split_points]
    end_indices = [active_cols[i] for i in split_points] + [active_cols[-1]]

    raw_segments = list(zip(start_indices, end_indices))

    # Filter out tiny noise segments (< 4px wide)
    segments = []
    for s_start, s_end in raw_segments:
        if (s_end - s_start + 1) >= 4:
            segments.append((int(s_start), int(s_end)))

    if not segments:
        raise WordSegmentationError("Could not detect any characters. Please write clearly on the canvas.")

    char_tensors = []
    char_previews_b64 = []
    combined_images = []
    valid_segments = []

    for s_start, s_end in segments:
        margin_x1 = max(0, s_start - 3)
        margin_x2 = min(inv_arr.shape[1], s_end + 4)
        char_crop = inv_arr[:, margin_x1:margin_x2]

        p = preprocess_letter_crop(char_crop)
        if p is not None:
            char_tensors.append(p)
            valid_segments.append((s_start, s_end))
            c_img = Image.fromarray((p * 255.0).astype(np.uint8))
            combined_images.append(c_img)

            buf = io.BytesIO()
            c_img.save(buf, format="PNG")
            char_previews_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    if not char_tensors:
        raise WordSegmentationError("Could not detect any characters. Please write clearly on the canvas.")

    # Create combined horizontal debug preview showing all characters side-by-side
    total_w = 28 * len(combined_images)
    combined_debug = Image.new("L", (total_w, 28), color=0)
    for i, c_img in enumerate(combined_images):
        combined_debug.paste(c_img, (i * 28, 0))

    if debug_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(debug_output_path)), exist_ok=True)
        combined_debug.save(debug_output_path)

    buf = io.BytesIO()
    combined_debug.save(buf, format="PNG")
    combined_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    batch_tensor = np.array(char_tensors, dtype=np.float32).reshape(-1, 28, 28, 1)
    return batch_tensor, char_previews_b64, combined_b64, valid_segments
