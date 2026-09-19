# WriteRight ✍️
### Intelligent Mobile Handwriting Digit Recognition System

WriteRight is a complete handwriting digit recognition application built with **Flutter (Material 3)**, **Python Flask**, and **TensorFlow/Keras CNN**.

---

## 📱 System Overview

- **Flutter Mobile App (`writeright_app`)**:
  - Touch-based handwriting drawing canvas with smooth quadratic bezier curves.
  - High-resolution canvas capture to lossless PNG byte buffers.
  - Material 3 professional blue & white UI theme.
  - Real-time prediction display with confidence indicator and 10-class probability breakdown.
  - Feedback system ("Was this correct?" -> `[Yes]` / `[Correct it]`) allowing users to submit corrections.
  - Configurable backend URL with in-app settings (works with Render HTTPS, local Wi-Fi LAN IP, or Android emulator).

- **Python Flask Machine Learning API (`backend`)**:
  - Preprocessing pipeline: Grayscale conversion, inversion, stroke thresholding, bounding box crop, 20x20 scaling, and 28x28 centering.
  - Keras CNN trained on MNIST (**99.03% test accuracy**).
  - Active learning storage: stores confirmed and corrected samples under `data/user_samples/<label>/` for future retraining.
  - Ready for cloud deployment on **Render.com**, **Railway**, or **Hugging Face Spaces**.

---

## 🚀 Cloud Deployment to Render (Free Tier)

This repository includes a `render.yaml` blueprint for automated deployment:

### Option A: 1-Click / Blueprint Deployment
1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository: `https://github.com/ed6095-web/WriteRight`.
4. Render will automatically detect `render.yaml` and configure:
   - **Service Name**: `writeright-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt`
   - **Start Command**: `gunicorn --workers 1 --threads 2 --bind 0.0.0.0:$PORT app:app`
5. Click **Apply**. Once built, Render will assign your public URL:
   `https://writeright-backend.onrender.com`

### Option B: Manual Web Service Deployment on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) -> **New +** -> **Web Service**.
2. Connect your GitHub repository: `https://github.com/ed6095-web/WriteRight`.
3. Fill in the service details:
   - **Name**: `writeright-backend`
   - **Region**: Oregon (US West) or closest region
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt`
   - **Start Command**: `gunicorn --workers 1 --threads 2 --bind 0.0.0.0:$PORT app:app`
   - **Instance Type**: `Free`
4. Add Environment Variables under **Advanced**:
   - `PYTHON_VERSION`: `3.11.9`
   - `KERAS_BACKEND`: `torch`
5. Click **Create Web Service**.

---

## 📲 Connecting Flutter to Your Render URL

Once your backend is live on Render:
1. Open the WriteRight app.
2. Tap the **Server Settings** icon in the app bar.
3. Enter your Render backend URL (e.g., `https://writeright-backend.onrender.com`).
4. Tap **Save**.
5. All digit recognition and feedback requests will now seamlessly flow through your cloud backend!

---

## 🛠️ Local Development

### Running the Backend Locally
```bash
cd backend
pip install -r requirements.txt
python app.py
```
*(Server listens on `0.0.0.0:5000`)*

### Testing the API
```bash
python backend/scripts/test_api.py
```

### Running the Flutter App
```bash
cd writeright_app
flutter pub get
flutter run -d windows   # For Windows desktop
flutter run -d chrome    # For Web preview
flutter run              # For connected Android device
```

### Building Release APK
```bash
cd writeright_app
flutter build apk --release
```
The compiled APK will be generated at:
`writeright_app/build/app/outputs/flutter-apk/app-release.apk`
