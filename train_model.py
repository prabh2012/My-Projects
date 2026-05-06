import os
import cv2
import pickle
import numpy as np
import mediapipe as mp
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

mp_hands = mp.solutions.hands
DATASET_DIR = "dataset"

CLASSES = [
    "hello", "goodbye", "good morning", "good night",
    "yes", "no", "maybe", "okay",
    "please", "thanks", "sorry", "welcome",
    "help", "stop", "wait", "more",
    "good", "bad", "happy", "sad"
    
]

data, labels = [], []
skipped = 0

print("📂 Reading dataset...")

with mp_hands.Hands(static_image_mode=True, max_num_hands=1,
                    min_detection_confidence=0.5) as hands:

    for label in CLASSES:
        folder_name = label.replace(" ", "_")
        folder_path = os.path.join(DATASET_DIR, folder_name)

        if not os.path.exists(folder_path):
            print(f"  ⚠️  Skipping '{label}' — folder not found")
            continue

        count = 0
        for img_file in os.listdir(folder_path):
            img_path = os.path.join(folder_path, img_file)
            img = cv2.imread(img_path)
            if img is None:
                continue

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            result = hands.process(img_rgb)

            if result.multi_hand_landmarks:
                landmarks = []
                hand = result.multi_hand_landmarks[0]

                # Get min/max for normalization
                x_vals = [lm.x for lm in hand.landmark]
                y_vals = [lm.y for lm in hand.landmark]
                x_min, x_max = min(x_vals), max(x_vals)
                y_min, y_max = min(y_vals), max(y_vals)

                for lm in hand.landmark:
                    # Normalize landmarks relative to hand bounding box
                    norm_x = (lm.x - x_min) / (x_max - x_min + 1e-6)
                    norm_y = (lm.y - y_min) / (y_max - y_min + 1e-6)
                    landmarks.extend([norm_x, norm_y])

                data.append(landmarks)
                labels.append(label)
                count += 1
            else:
                skipped += 1

        print(f"  ✅ {label}: {count} samples loaded")

print(f"\n📊 Total: {len(data)} samples | Skipped (no hand): {skipped}")

if len(data) == 0:
    print("❌ No data found! Run data_collection.py first.")
    exit()

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    np.array(data), labels,
    test_size=0.2,
    random_state=42,
    stratify=labels  # Balanced split per class
)

print(f"\n🤖 Training model on {len(X_train)} samples...")

model = RandomForestClassifier(
    n_estimators=200,      # More trees = better accuracy
    max_depth=20,
    random_state=42,
    n_jobs=-1              # Use all CPU cores
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"\n✅ Accuracy: {acc * 100:.2f}%")
print("\n📋 Per-gesture report:")
print(classification_report(y_test, y_pred))

# Save model
os.makedirs("model", exist_ok=True)
with open("model/sign_model.pkl", "wb") as f:
    pickle.dump({"model": model, "classes": CLASSES}, f)

print("💾 Model saved to model/sign_model.pkl")