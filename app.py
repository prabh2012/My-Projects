from flask import Flask, render_template, Response, jsonify
import cv2
import pickle
import numpy as np
import mediapipe as mp
from collections import deque
import os
import threading
import time

app = Flask(__name__)

# ── Gesture Classes (words only, no alphabets) ────────────────────────
CLASSES = [
    "hello", "goodbye", "good morning", "good night",
    "yes", "no", "maybe", "okay",
    "please", "thanks", "sorry", "welcome",
    "help", "stop", "wait", "more",
    "good", "bad", "happy", "sad",

]

# ── Load model ────────────────────────────────────────────────────────
model = None
model_path = "model/sign_model.pkl"
if os.path.exists(model_path):
    with open(model_path, "rb") as f:
        model = pickle.load(f)["model"]
    print("✅ Model loaded successfully")
else:
    print("⚠️  No model found. Run train_model.py first.")

# ── MediaPipe setup ───────────────────────────────────────────────────
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils
hands_detector = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)

# ── Shared app state ──────────────────────────────────────────────────
state = {
    "current_sign":  "",
    "sentence":      [],
    "confidence":    0,
    "hand_detected": False,
    "fps":           0,
    "total_detected": 0,
}
state_lock = threading.Lock()

prediction_buffer = deque(maxlen=20)
last_added   = ""
stable_count = 0
fps_counter  = 0
fps_timer    = time.time()

# ── Camera ────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


def normalize_landmarks(hand_landmarks):
    """Normalize landmarks relative to hand bounding box."""
    x_vals = [lm.x for lm in hand_landmarks.landmark]
    y_vals = [lm.y for lm in hand_landmarks.landmark]
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    landmarks = []
    for lm in hand_landmarks.landmark:
        norm_x = (lm.x - x_min) / (x_max - x_min + 1e-6)
        norm_y = (lm.y - y_min) / (y_max - y_min + 1e-6)
        landmarks.extend([norm_x, norm_y])
    return landmarks


def generate_frames():
    global last_added, stable_count, fps_counter, fps_timer

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame   = cv2.flip(frame, 1)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result  = hands_detector.process(img_rgb)

        # FPS
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            with state_lock:
                state["fps"] = fps_counter
            fps_counter = 0
            fps_timer   = time.time()

        with state_lock:
            state["hand_detected"] = False
            state["current_sign"]  = ""
            state["confidence"]    = 0

        if result.multi_hand_landmarks and model:
            for hand_landmarks in result.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame, hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(0, 255, 170), thickness=2, circle_radius=5),
                    mp_draw.DrawingSpec(color=(200, 200, 255), thickness=2)
                )

                landmarks  = normalize_landmarks(hand_landmarks)
                prediction = model.predict([np.array(landmarks)])[0]
                proba      = model.predict_proba([np.array(landmarks)])[0]
                confidence = int(max(proba) * 100)

                prediction_buffer.append(prediction)

                if len(prediction_buffer) == 20:
                    stable = max(set(prediction_buffer), key=prediction_buffer.count)

                    with state_lock:
                        state["current_sign"]  = stable
                        state["confidence"]    = confidence
                        state["hand_detected"] = True

                    if stable == last_added:
                        stable_count += 1
                    else:
                        stable_count = 0
                        last_added   = stable

                    # Hold ~1.5 sec → auto add
                    if stable_count == 25:
                        with state_lock:
                            state["sentence"].append(stable)
                            state["total_detected"] += 1
                        stable_count = 0

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# ── Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', classes=CLASSES)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_state')
def get_state():
    with state_lock:
        return jsonify({
            "current_sign":   state["current_sign"],
            "sentence":       " ".join(w if w != "|space|" else " " for w in state["sentence"]),
            "word_list":      state["sentence"],
            "confidence":     state["confidence"],
            "hand_detected":  state["hand_detected"],
            "fps":            state["fps"],
            "total_detected": state["total_detected"],
            "model_loaded":   model is not None,
        })


@app.route('/clear_sentence', methods=['POST'])
def clear_sentence():
    with state_lock:
        state["sentence"].clear()
    return jsonify({"status": "cleared"})


@app.route('/add_space', methods=['POST'])
def add_space():
    with state_lock:
        state["sentence"].append("|space|")
    return jsonify({"status": "space added"})


@app.route('/delete_last', methods=['POST'])
def delete_last():
    with state_lock:
        if state["sentence"]:
            state["sentence"].pop()
    return jsonify({"status": "deleted"})


if __name__ == '__main__':
    print("🚀 Starting Sign Language Converter...")
    print(f"📚 {len(CLASSES)} gesture classes loaded")
    print("🌐 Open http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
