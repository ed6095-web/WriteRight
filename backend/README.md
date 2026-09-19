# WriteRight Backend: Handwriting Digit Recognition API

WriteRight is a high-performance Python Flask backend serving a trained Convolutional Neural Network (CNN) for handwritten digit recognition (0–9) and active learning feedback collection.

---

## 1. Project Structure

```
backend/
├── app.py                          # Flask API entry point (endpoints: /health, /predict, /feedback)
├── requirements.txt                # Python dependencies
├── model/
│   └── handwriting_model.keras     # Trained Keras CNN model file (28x28x1 input, 10 classes)
├── preprocessing/
│   ├── __init__.py
│   └── image_processor.py          # Bounding box detection, 20x20 scaling, 28x28 centering & normalization
├── services/
│   ├── __init__.py
│   └── prediction_service.py       # Singleton model manager and inference service
├── data/
│   └── user_samples/               # Collected user feedback drawings (0 through 9)
│       ├── 0/
│       ├── 1/
│       └── ... [0-9]
└── scripts/
    ├── test_api.py                 # Automated API test suite
    └── generate_reference_model.py # Reference CNN trainer on MNIST (~99% accuracy)
```

---

## 2. Preprocessing Pipeline

The model expects standard MNIST tensor format: `(1, 28, 28, 1)` with pixel intensities normalized to `[0.0, 1.0]`, white strokes on black background.

When an image is submitted from the drawing canvas:
1. **Grayscale Conversion**: Image converted to single-channel `'L'` mode.
2. **Stroke Inversion**: Inverts canvas (white background with dark strokes) so strokes are high-intensity (foreground) and background is black (0).
3. **Foreground Thresholding**: Thresholds stroke pixels (`img > 30`). If canvas is blank, raises an `EmptyDrawingError` with friendly HTTP 400 response.
4. **Bounding Box Extraction**: Crops tightly around the non-background stroke pixels.
5. **Aspect-Ratio Preserved Resizing**: Resizes the bounding box so its longest side is exactly 20 pixels.
6. **28×28 Centering**: Pastes the 20×20 resized digit into the center of a 28×28 black canvas.
7. **Center-of-Mass Alignment**: Fine-tunes horizontal/vertical alignment according to MNIST center-of-mass standards.
8. **Normalization**: Divides pixel intensities by 255.0 to yield values between `0.0` and `1.0`.
9. **Tensor Reshaping**: Formatted as `(1, 28, 28, 1)` `np.float32`.

---

## 3. API Endpoints

### `GET /health`
Inspects server status and checks whether the Keras model is loaded in memory.

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

### `POST /predict`
Uploads a drawing canvas image and performs digit recognition.

- **Content-Type**: `multipart/form-data`
- **Field**: `image` (binary file)

**Response:**
```json
{
  "prediction": 7,
  "confidence": 0.9517,
  "probabilities": {
    "0": 0.0000,
    "1": 0.0003,
    "2": 0.0479,
    "3": 0.0001,
    "4": 0.0000,
    "5": 0.0000,
    "6": 0.0000,
    "7": 0.9517,
    "8": 0.0000,
    "9": 0.0000
  }
}
```

---

### `POST /feedback`
Stores confirmed or user-corrected samples into dataset directories for future model fine-tuning.

- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image`: The original canvas image file.
  - `correct_label`: The true digit label (`0`–`9`).

**Response:**
```json
{
  "success": true,
  "message": "Sample stored successfully",
  "saved_file": "sample_1789841548449_aa86ab39.png"
}
```
Saved file path: `backend/data/user_samples/<correct_label>/sample_<timestamp>_<id>.png`

---

## 4. Setup & Running Instructions

### Step 1: Install Dependencies
```powershell
pip install -r backend/requirements.txt
```

### Step 2: Start Flask Server
```powershell
python backend/app.py
```
The server listens on `0.0.0.0:5000` to accept connections from local network devices (physical Android phones, emulators, and desktop clients).

### Step 3: Run Automated Test Suite
In a separate terminal:
```powershell
python backend/scripts/test_api.py
```
This validates `/health`, `/predict` (both valid digit and empty canvas rejection), and `/feedback`.
