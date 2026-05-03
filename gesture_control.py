import cv2
import time
import mediapipe as mp

from shared import MobileVideoStream, Commander


# ================= CONFIGURATION =================
ESP_IP        = "192.168.137.35"
UDP_CMD_PORT  = 5001

# Mobile phone camera stream
MOBILE_IP     = "10.18.88.38"   # ← change to your phone's IP
STREAM_URL    = f"http://{MOBILE_IP}:8080/video"

# ⭐ Speed Settings — tune these to your robot
BASE_SPEED    = 9   # base wheel speed (0–255)
TURN_SPEED    = 7   # speed used for the spinning wheel during a turn

# ================= HAND GESTURE DETECTOR =================
class HandGestureDetector:
    """
    Two-hand gesture → direct motor speeds (no PID).

    Gesture map:
      Both open   → FORWARD
      Both closed → BACKWARD
      Right open, Left closed → TURN RIGHT  (left wheel drives)
      Left open, Right closed → TURN LEFT   (right wheel drives)
      Single / no hand        → STOP
    """

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )
        self.mp_draw  = mp.solutions.drawing_utils

    def _is_open(self, lm):
        """Return True when hand is mostly open (≥3 digits extended)."""
        pts = lm.landmark
        count = 0
        # Thumb (x-axis comparison)
        if pts[4].x > pts[2].x:
            count += 1
        # Four fingers (tip above PIP = extended)
        for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
            if pts[tip].y < pts[pip].y:
                count += 1
        return count >= 3

    def _gesture_to_speeds(self, command):
        """
        Map a command string to (left_speed, right_speed).
        Positive = forward, negative = backward.
        """
        if command == "forward":
            return  BASE_SPEED,  BASE_SPEED
        elif command == "backward":
            return -BASE_SPEED, -BASE_SPEED
        elif command == "left":
            # Only right wheel turns; left wheel still
            return  0,  TURN_SPEED
        elif command == "right":
            # Only left wheel turns; right wheel still
            return  TURN_SPEED,  0
        else:                          # "stop"
            return  0,  0

    def detect(self, frame):
        """
        Process a BGR frame, draw landmarks, return:
          (left_speed, right_speed, command_name, debug_dict)
        """
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        command = "stop"
        debug   = {
            'left_hand':  None,
            'right_hand': None,
            'left_open':  False,
            'right_open': False,
        }

        if results.multi_hand_landmarks and results.multi_handedness:
            hands = {}

            for lm, handedness in zip(results.multi_hand_landmarks,
                                      results.multi_handedness):
                label   = handedness.classification[0].label   # "Left" / "Right"
                is_open = self._is_open(lm)
                hands[label] = {'lm': lm, 'open': is_open}

                self.mp_draw.draw_landmarks(
                    frame, lm, self.mp_hands.HAND_CONNECTIONS
                )

            if 'Left' in hands:
                debug['left_hand'] = 'detected'
                debug['left_open'] = hands['Left']['open']
            if 'Right' in hands:
                debug['right_hand'] = 'detected'
                debug['right_open'] = hands['Right']['open']

            # Require BOTH hands for a movement command
            if 'Left' in hands and 'Right' in hands:
                lo = hands['Left']['open']
                ro = hands['Right']['open']
                if   lo and ro:     command = "forward"
                elif not lo and not ro: command = "backward"
                elif ro and not lo: command = "right"
                elif lo and not ro: command = "left"

        left_speed, right_speed = self._gesture_to_speeds(command)
        return left_speed, right_speed, command, debug

    def close(self):
        self.hands.close()


# ================= MAIN =================
def main():
    print("\n" + "=" * 55)
    print("  🤖 Hand-Gesture Robot — Mobile Camera Edition")
    print(f"  BASE_SPEED={BASE_SPEED}  TURN_SPEED={TURN_SPEED}")
    print("=" * 55)
    print("  🖐️🖐️  Both open    → FORWARD")
    print("  ✊✊   Both closed  → BACKWARD")
    print("  🖐️✊  Right open   → TURN RIGHT")
    print("  ✊🖐️  Left open    → TURN LEFT")
    print("  (one hand only)  → STOP")
    print("  Q = quit")
    print("=" * 55 + "\n")

    # --- Boot up subsystems ---
    print(f"Connecting to camera at {STREAM_URL} …")
    video     = MobileVideoStream(STREAM_URL)
    commander = Commander(ESP_IP, UDP_CMD_PORT)
    detector  = HandGestureDetector()

    # Wait for first frame
    wait_start = time.time()
    while time.time() - wait_start < 15:
        if video.connected:
            break
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()

    if not video.connected:
        print("❌ Could not connect to camera stream. Check MOBILE_IP.")
        exit(1)

    commander.stop()
    time.sleep(0.3)

    # --- Control loop variables ---
    last_fid       = -1
    last_left      = 0
    last_right     = 0
    last_cmd_name  = "stop"
    last_cmd_time  = 0.0
    CMD_INTERVAL   = 0.08    # re-send every 80 ms even if unchanged (keep-alive)

    fps_count = 0
    fps_timer = time.time()

    CMD_COLORS = {
        "forward":  (0,   255,   0),
        "backward": (0,     0, 255),
        "left":     (255, 255,   0),
        "right":    (255,   0, 255),
        "stop":     (100, 100, 100),
    }

    while True:
        frame, fid = video.read()

        if frame is None or fid == last_fid:
            time.sleep(0.005)
            continue

        last_fid   = fid
        fps_count += 1

        # FPS readout every 30 frames
        if fps_count >= 30:
            fps = fps_count / (time.time() - fps_timer)
            print(f"📊 FPS: {fps:.1f}")
            fps_count = 0
            fps_timer = time.time()

        # --- Gesture detection ---
        try:
            left_speed, right_speed, cmd_name, debug = detector.detect(frame)
        except Exception as e:
            print(f"❌ Detection error: {e}")
            left_speed = right_speed = 0
            cmd_name   = "stop"
            debug      = {}

        # --- Send command ---
        now = time.time()
        speed_changed = (abs(left_speed - last_left) > 5 or
                         abs(right_speed - last_right) > 5)
        if speed_changed or (now - last_cmd_time) >= CMD_INTERVAL:
            commander.motors(left_speed, right_speed)
            last_left     = left_speed
            last_right    = right_speed
            last_cmd_name = cmd_name
            last_cmd_time = now
            print(f"🤖 {cmd_name.upper():8s} | L:{left_speed:+4d}  R:{right_speed:+4d}")

        # --- HUD overlay ---
        h, w = frame.shape[:2]

        # Command badge (top-right)
        color = CMD_COLORS.get(cmd_name, (200, 200, 200))
        cv2.rectangle(frame, (w - 130, 8), (w - 8, 50), color, -1)
        cv2.putText(frame, cmd_name.upper(),
                    (w - 125, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (0, 0, 0), 2)

        # Speed readout
        cv2.putText(frame, f"L:{left_speed:+4d}  R:{right_speed:+4d}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 255, 0), 2)

        # Hand state indicators
        left_state  = ("OPEN" if debug.get('left_open')  else "CLOSED") \
                       if debug.get('left_hand')  else "---"
        right_state = ("OPEN" if debug.get('right_open') else "CLOSED") \
                       if debug.get('right_hand') else "---"

        cv2.putText(frame, f"LEFT:  {left_state}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 255, 255), 1)
        cv2.putText(frame, f"RIGHT: {right_state}",
                    (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 255, 255), 1)

        cv2.imshow("Hand-Gesture Robot Control", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # --- Shutdown ---
    print("\nShutting down…")
    commander.stop()
    time.sleep(0.2)
    video.stop()
    detector.close()
    cv2.destroyAllWindows()
    print("✅ Done")


if __name__ == "__main__":
    main()
