import cv2
import os
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

DATASET_DIR = "dataset"
IMAGES_PER_CLASS = 300  # More images = better accuracy for gestures

CLASSES = [
    "hello", "goodbye", "good morning", "good night",
    "yes", "no", "maybe", "okay",
    "please", "thanks", "sorry", "welcome",
    "help", "stop", "wait", "more",
    "good", "bad", "happy", "sad"

]

os.makedirs(DATASET_DIR, exist_ok=True)
cap = cv2.VideoCapture(0)

with mp_hands.Hands(static_image_mode=False, max_num_hands=1) as hands:
    for label in CLASSES:
        # Use underscore for folder name (no spaces)
        folder_name = label.replace(" ", "_")
        class_dir = os.path.join(DATASET_DIR, folder_name)
        os.makedirs(class_dir, exist_ok=True)

        print(f"\n>> GET READY FOR: '{label.upper()}'")
        print(f"   Make the gesture for '{label}' and press S to start")

        # Wait for user to press S
        while True:
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)
            cv2.putText(frame, f"Gesture: {label}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(frame, "Press S to start collecting", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.imshow("Data Collection", frame)
            if cv2.waitKey(1) & 0xFF == ord('s'):
                break

        # Collect images
        count = 0
        while count < IMAGES_PER_CLASS:
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)

            img_path = os.path.join(class_dir, f"{count}.jpg")
            cv2.imwrite(img_path, frame)

            # Progress bar
            progress = int((count / IMAGES_PER_CLASS) * 40)
            bar = "[" + "=" * progress + " " * (40 - progress) + "]"

            cv2.putText(frame, f"{label}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)
            cv2.putText(frame, f"{count}/{IMAGES_PER_CLASS} images", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("Data Collection", frame)
            print(f"\r  {bar} {count}/{IMAGES_PER_CLASS}", end="")

            count += 1
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        print(f"\n  ✅ Done: {label}")

cap.release()
cv2.destroyAllWindows()
print("\n🎉 All gestures collected!")