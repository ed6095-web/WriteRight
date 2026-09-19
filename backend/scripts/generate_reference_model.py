"""
Utility script to generate and save the reference handwriting_model.keras CNN.
Trained on MNIST achieving ~99% test accuracy.
"""
import os
os.environ["KERAS_BACKEND"] = "torch"
import numpy as np
import keras
from keras import layers

def build_and_train():
    output_path = os.path.join(os.path.dirname(__file__), "..", "model", "handwriting_model.keras")
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("Loading MNIST dataset...")
    (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

    # Normalize pixel values to [0, 1]
    x_train = x_train.astype("float32") / 255.0
    x_test = x_test.astype("float32") / 255.0

    # Ensure shape is (28, 28, 1)
    x_train = np.expand_dims(x_train, -1)
    x_test = np.expand_dims(x_test, -1)

    # One-hot encode targets
    num_classes = 10
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)

    print(f"Training data shape: {x_train.shape}")
    print(f"Test data shape: {x_test.shape}")

    # Build CNN architecture
    model = keras.Sequential([
        keras.Input(shape=(28, 28, 1)),
        layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation="softmax"),
    ])

    model.summary()

    model.compile(
        loss="categorical_crossentropy",
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        metrics=["accuracy"],
    )

    print("Training CNN for 5 epochs...")
    model.fit(
        x_train,
        y_train,
        batch_size=128,
        epochs=5,
        validation_split=0.1,
        verbose=1,
    )

    score = model.evaluate(x_test, y_test, verbose=0)
    print(f"Test loss: {score[0]:.4f}")
    print(f"Test accuracy: {score[1] * 100:.2f}%")

    print(f"Saving model to {output_path}...")
    model.save(output_path)
    print("Model saved successfully!")

if __name__ == "__main__":
    build_and_train()
