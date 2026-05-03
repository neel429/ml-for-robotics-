import time

import cv2
import mediapipe as mp
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


MODEL_PATH = "hand_landmarker.task"


def draw_hand_landmarks(frame, hand_landmarks_list):
    for hand_landmarks in hand_landmarks_list:
        proto = landmark_pb2.NormalizedLandmarkList()
        proto.landmark.extend(
            landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z)
            for lm in hand_landmarks
        )
        solutions.drawing_utils.draw_landmarks(
            frame,
            proto,
            solutions.hands.HAND_CONNECTIONS,
            solutions.drawing_styles.get_default_hand_landmarks_style(),
            solutions.drawing_styles.get_default_hand_connections_style(),
        )


def is_hand_open(hand_landmarks):
    pts = hand_landmarks
    count = 0

    if pts[4].x > pts[2].x:
        count += 1

    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        if pts[tip].y < pts[pip].y:
            count += 1

    return count >= 3


def classify_gesture(hands_dict):
    if "Left" not in hands_dict or "Right" not in hands_dict:
        return "stop"

    left_open = hands_dict["Left"]["open"]
    right_open = hands_dict["Right"]["open"]

    if left_open and right_open:
        return "forward"
    if not left_open and not right_open:
        return "backward"
    if right_open and not left_open:
        return "right"
    if left_open and not right_open:
        return "left"
    return "stop"


def create_landmarker(model_path=MODEL_PATH):
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.6,
    )
    return mp_vision.HandLandmarker.create_from_options(options)


def main():
    landmarker = create_landmarker()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Could not open webcam.")
        landmarker.close()
        return

    cmd_colors = {
        "forward": (0, 255, 0),
        "backward": (0, 0, 255),
        "left": (255, 255, 0),
        "right": (255, 0, 255),
        "stop": (100, 100, 100),
    }

    print("Gesture test ready. Press Q to quit.")
    last_timestamp_ms = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = int(time.time() * 1000)
        if timestamp_ms <= last_timestamp_ms:
            timestamp_ms = last_timestamp_ms + 1
        last_timestamp_ms = timestamp_ms

        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.hand_landmarks:
            draw_hand_landmarks(frame, result.hand_landmarks)

        hands_dict = {}
        for i, handedness_list in enumerate(result.handedness):
            label = handedness_list[0].category_name
            open_state = is_hand_open(result.hand_landmarks[i])
            hands_dict[label] = {"open": open_state}

        command = classify_gesture(hands_dict)

        h, w = frame.shape[:2]
        color = cmd_colors.get(command, (200, 200, 200))
        cv2.rectangle(frame, (w - 140, 8), (w - 8, 52), color, -1)
        cv2.putText(
            frame,
            command.upper(),
            (w - 135, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 0),
            2,
        )

        for i, (label, data) in enumerate(hands_dict.items()):
            state = "OPEN" if data["open"] else "CLOSED"
            cv2.putText(
                frame,
                f"{label}: {state}",
                (10, 30 + i * 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )

        cv2.imshow("Gesture Test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    landmarker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
