import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from shared import Commander, MobileVideoStream


# ================= CONFIGURATION =================
ESP_IP = "192.168.137.35"
UDP_CMD_PORT = 5001

# Mobile phone camera stream
MOBILE_IP = "10.18.88.38"  # Change to your phone's IP
STREAM_URL = f"http://{MOBILE_IP}:8080/video"

# Speed settings. Tune these to your robot.
BASE_SPEED = 13
TURN_SPEED = 11

MODEL_PATH = "hand_landmarker.task"
HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
]


def draw_hand_landmarks(rgb_image, hand_landmarks_list):
    annotated = rgb_image.copy()
    h, w, _ = annotated.shape

    for hand_landmarks in hand_landmarks_list:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
        for start, end in HAND_CONNECTIONS:
            cv2.line(annotated, pts[start], pts[end], (0, 255, 0), 2)
        for pt in pts:
            cv2.circle(annotated, pt, 4, (0, 0, 255), -1)

    return annotated


# ================= HAND GESTURE DETECTOR =================
class HandGestureDetector:
    """
    Two-hand gesture -> direct motor speeds.

    Gesture map:
      Both open   -> FORWARD
      Both closed -> BACKWARD
      Right open, Left closed -> TURN RIGHT
      Left open, Right closed -> TURN LEFT
      Single / no hand        -> STOP
    """

    def __init__(self, model_path=MODEL_PATH):
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.6,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = 0

    def _next_timestamp_ms(self):
        timestamp_ms = int(time.time() * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _is_open(self, hand_landmarks):
        pts = hand_landmarks
        count = 0

        if pts[4].x > pts[2].x:
            count += 1

        for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
            if pts[tip].y < pts[pip].y:
                count += 1

        return count >= 3

    def _gesture_to_speeds(self, command):
        if command == "forward":
            return BASE_SPEED, BASE_SPEED
        if command == "backward":
            return -BASE_SPEED, -BASE_SPEED
        if command == "left":
            return 0, TURN_SPEED
        if command == "right":
            return TURN_SPEED, 0
        return 0, 0

    def detect(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, self._next_timestamp_ms())

        command = "stop"
        hands_dict = {}
        debug = {
            "left_hand": None,
            "right_hand": None,
            "left_open": False,
            "right_open": False,
        }

        for i, handedness_list in enumerate(result.handedness):
            label = handedness_list[0].category_name
            open_state = self._is_open(result.hand_landmarks[i])
            hands_dict[label] = {"open": open_state}

            if label == "Left":
                debug["left_hand"] = "detected"
                debug["left_open"] = open_state
            elif label == "Right":
                debug["right_hand"] = "detected"
                debug["right_open"] = open_state

        if "Left" in hands_dict and "Right" in hands_dict:
            left_open = hands_dict["Left"]["open"]
            right_open = hands_dict["Right"]["open"]
            if left_open and right_open:
                command = "forward"
            elif not left_open and not right_open:
                command = "backward"
            elif right_open and not left_open:
                command = "right"
            elif left_open and not right_open:
                command = "left"

        if result.hand_landmarks:
            rgb_annotated = draw_hand_landmarks(rgb, result.hand_landmarks)
            frame[:] = cv2.cvtColor(rgb_annotated, cv2.COLOR_RGB2BGR)

        left_speed, right_speed = self._gesture_to_speeds(command)
        return left_speed, right_speed, command, debug

    def close(self):
        self._landmarker.close()


# ================= MAIN =================
def main():
    print("\n" + "=" * 55)
    print("  Hand-Gesture Robot - Mobile Camera Edition")
    print(f"  BASE_SPEED={BASE_SPEED}  TURN_SPEED={TURN_SPEED}")
    print("=" * 55)
    print("  Both open        -> FORWARD")
    print("  Both closed      -> BACKWARD")
    print("  Right open only  -> TURN RIGHT")
    print("  Left open only   -> TURN LEFT")
    print("  One/no hand      -> STOP")
    print("  Q = quit")
    print("=" * 55 + "\n")

    print(f"Connecting to camera at {STREAM_URL} ...")
    video = MobileVideoStream(STREAM_URL)
    commander = Commander(ESP_IP, UDP_CMD_PORT)
    detector = HandGestureDetector()

    wait_start = time.time()
    while time.time() - wait_start < 15:
        if video.connected:
            break
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()

    if not video.connected:
        print("Could not connect to camera stream. Check MOBILE_IP.")
        detector.close()
        video.stop()
        return

    commander.stop()
    time.sleep(0.3)

    last_fid = -1
    last_left = 0
    last_right = 0
    last_cmd_time = 0.0
    cmd_interval = 0.08

    fps_count = 0
    fps_timer = time.time()

    cmd_colors = {
        "forward": (0, 255, 0),
        "backward": (0, 0, 255),
        "left": (255, 255, 0),
        "right": (255, 0, 255),
        "stop": (100, 100, 100),
    }

    while True:
        frame, fid = video.read()

        if frame is None or fid == last_fid:
            time.sleep(0.005)
            continue

        last_fid = fid
        fps_count += 1

        if fps_count >= 30:
            fps = fps_count / (time.time() - fps_timer)
            print(f"FPS: {fps:.1f}")
            fps_count = 0
            fps_timer = time.time()

        try:
            left_speed, right_speed, cmd_name, debug = detector.detect(frame)
        except Exception as error:
            print(f"Detection error: {error}")
            left_speed = right_speed = 0
            cmd_name = "stop"
            debug = {}

        now = time.time()
        speed_changed = (
            abs(left_speed - last_left) > 5
            or abs(right_speed - last_right) > 5
        )
        if speed_changed or (now - last_cmd_time) >= cmd_interval:
            commander.motors(left_speed, right_speed)
            last_left = left_speed
            last_right = right_speed
            last_cmd_time = now
            print(f"{cmd_name.upper():8s} | L:{left_speed:+4d}  R:{right_speed:+4d}")

        h, w = frame.shape[:2]

        color = cmd_colors.get(cmd_name, (200, 200, 200))
        cv2.rectangle(frame, (w - 130, 8), (w - 8, 50), color, -1)
        cv2.putText(
            frame,
            cmd_name.upper(),
            (w - 125, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 0, 0),
            2,
        )

        cv2.putText(
            frame,
            f"L:{left_speed:+4d}  R:{right_speed:+4d}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )

        left_state = (
            "OPEN" if debug.get("left_open") else "CLOSED"
        ) if debug.get("left_hand") else "---"
        right_state = (
            "OPEN" if debug.get("right_open") else "CLOSED"
        ) if debug.get("right_hand") else "---"

        cv2.putText(
            frame,
            f"LEFT:  {left_state}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"RIGHT: {right_state}",
            (10, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
        )

        cv2.imshow("Hand-Gesture Robot Control", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    print("\nShutting down...")
    commander.stop()
    time.sleep(0.2)
    video.stop()
    detector.close()
    cv2.destroyAllWindows()
    print("Done")


if __name__ == "__main__":
    main()
