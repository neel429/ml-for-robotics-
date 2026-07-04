"""
pan_and_tilt.py

YOLO ball tracker for a fixed pan-tilt camera rig.

Architecture:
  - A phone streams camera frames over WiFi.
  - YOLO detects the target object in each frame.
  - One PID controls pan from horizontal image error.
  - One PID controls tilt from vertical image error.
  - Each PID outputs degrees per frame, which are added to the current angle.
  - Python sends UDP packets as SERVO,<pan>,<tilt> to the Arduino.
  - The Arduino replies with SERVO_ACK,<pan>,<tilt> for the HUD.

Place this file in the same folder as shared.py and best.pt.
"""

import socket
import threading
import time

import cv2
import numpy as np

from shared import PID, MobileVideoStream, RobotState


# -----------------------------------------------------------------------------
# CONFIGURATION - fill these in for your setup
# -----------------------------------------------------------------------------

# Network
ESP_IP = "192.168.x.x"       # Arduino IP from Serial Monitor
MOBILE_IP = "192.168.x.x"    # Phone IP from IP Webcam or Simple IP Camera
UDP_CMD_PORT = 5001
UDP_TELEM_PORT = 5002

# Vision
TARGET_OBJECT = "ball"

# Servo physical limits in degrees
PAN_MIN, PAN_MAX = 10, 170
TILT_MIN, TILT_MAX = 30, 150
PAN_HOME = 90
TILT_HOME = 40

# Flip these if the camera moves the wrong direction on that axis.
PAN_INVERT = False
TILT_INVERT = False

# Ignore tiny image errors near center to prevent buzzing.
ANGLE_DEAD_ZONE_H = 0.03
ANGLE_DEAD_ZONE_V = 0.01

# PID gains for velocity-mode output in degrees per frame.
PAN_KP = 8.0
PAN_KI = 0.0
PAN_KD = 2.0
MAX_PAN_SPEED = 3.0
MAX_PAN_INTEGRAL = 0.3

TILT_KP = 6.0
TILT_KI = 0.0
TILT_KD = 1.5
MAX_TILT_SPEED = 3.0
MAX_TILT_INTEGRAL = 0.3

# State machine
ACQUIRE_FRAMES = 5
LOST_TIMEOUT = 1.2
SEARCH_PAN_SPEED = 1.5
SEARCH_TILT_SPEED = 0.0
CMD_INTERVAL = 0.03


# -----------------------------------------------------------------------------
# COMMANDER - sends SERVO commands to the Arduino
# -----------------------------------------------------------------------------

class ServoCommander:
    """Sends UDP servo commands to the Arduino."""

    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send(self, message):
        self._sock.sendto(message.encode("utf-8"), (self._ip, self._port))

    def servos(self, pan, tilt):
        """Send absolute servo angles in integer degrees."""
        self._send(f"SERVO,{int(pan)},{int(tilt)}")

    def home(self):
        """Ask the Arduino to return both servos to their home angles."""
        self._send("HOME")

    def stop(self):
        """Ask the Arduino to home the rig before the Python script exits."""
        self._send("STOP")
        self._sock.close()


# -----------------------------------------------------------------------------
# TELEMETRY - receives optional SERVO_ACK packets from the Arduino
# -----------------------------------------------------------------------------

class ServoTelemetry:
    """
    Receives SERVO_ACK,pan,tilt packets from the Arduino.

    Servos do not provide encoder feedback in this project. The ACK contains the
    Arduino's current commanded angle after its smoothing step.
    """

    def __init__(self, port):
        self.pan = PAN_HOME
        self.tilt = TILT_HOME
        self.running = True
        self._lock = threading.Lock()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", port))
        self._sock.settimeout(1.0)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            try:
                data, _ = self._sock.recvfrom(64)
                parts = data.decode("utf-8").strip().split(",")
                if parts[0] == "SERVO_ACK" and len(parts) == 3:
                    with self._lock:
                        self.pan = int(parts[1])
                        self.tilt = int(parts[2])
            except (OSError, socket.timeout, UnicodeDecodeError, ValueError):
                pass

    def read(self):
        with self._lock:
            return {"pan": self.pan, "tilt": self.tilt}

    def stop(self):
        self.running = False
        self._sock.close()


# -----------------------------------------------------------------------------
# PAN-TILT TRACKER
# -----------------------------------------------------------------------------

class PanTiltTracker:
    """YOLO-based target tracker that drives two independent servo axes."""

    STATE_COLORS = {
        RobotState.STOPPED: (100, 100, 100),
        RobotState.SEARCHING: (255, 165, 0),
        RobotState.ACQUIRING: (255, 255, 0),
        RobotState.TRACKING: (0, 255, 0),
    }

    def __init__(self, model_path, target):
        print("Loading YOLO model...")
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.target = target

        try:
            self.model.to("cuda")
            print("  Using CUDA")
        except Exception:
            print("  Using CPU")
        self.model.fuse()

        self.pid_pan = PID(
            PAN_KP,
            PAN_KI,
            PAN_KD,
            max_integral=MAX_PAN_INTEGRAL,
            output_limits=(-MAX_PAN_SPEED, MAX_PAN_SPEED),
        )
        self.pid_tilt = PID(
            TILT_KP,
            TILT_KI,
            TILT_KD,
            max_integral=MAX_TILT_INTEGRAL,
            output_limits=(-MAX_TILT_SPEED, MAX_TILT_SPEED),
        )

        self.pan_angle = float(PAN_HOME)
        self.tilt_angle = float(TILT_HOME)

        self.state = RobotState.STOPPED
        self.acquire_count = 0
        self.last_seen_t = 0.0
        self.last_turn_dir = 1.0
        self.speed_limit = 1.0

    def _detect(self, frame):
        """Return the largest target bounding box as (x1, y1, x2, y2), or None."""
        results = self.model(frame, imgsz=320, verbose=False, conf=0.60)
        best = None
        best_area = 0

        for result in results:
            for box in result.boxes:
                class_name = self.model.names[int(box.cls[0])]
                if class_name != self.target:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                area = (x2 - x1) * (y2 - y1)
                if area > best_area:
                    best_area = area
                    best = (x1, y1, x2, y2)

        return best

    def _update_state(self, found):
        if found:
            self.last_seen_t = time.time()
            if self.state in (RobotState.STOPPED, RobotState.SEARCHING):
                self.state = RobotState.ACQUIRING
                self.acquire_count = 0
                self.speed_limit = 0.4
            elif self.state == RobotState.ACQUIRING:
                self.acquire_count += 1
                self.speed_limit = 0.4 + 0.6 * self.acquire_count / ACQUIRE_FRAMES
                if self.acquire_count >= ACQUIRE_FRAMES:
                    self.state = RobotState.TRACKING
                    self.speed_limit = 1.0
            else:
                self.speed_limit = 1.0
            return

        elapsed = time.time() - self.last_seen_t
        if elapsed < LOST_TIMEOUT:
            self.state = RobotState.SEARCHING
            self.speed_limit = 0.4
        else:
            self.state = RobotState.STOPPED
            self.speed_limit = 0.0
            self.pid_pan.reset()
            self.pid_tilt.reset()

    def control(self, frame):
        """
        Run one detection and control cycle.

        Returns:
            pan_angle, tilt_angle, debug_dict
        """
        h, w = frame.shape[:2]
        bbox = self._detect(frame)
        self._update_state(bbox is not None)

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            err_pan = (cx - w / 2) / w
            err_tilt = (cy - h / 2) / h

            if abs(err_pan) < ANGLE_DEAD_ZONE_H:
                err_pan = 0.0
            if abs(err_tilt) < ANGLE_DEAD_ZONE_V:
                err_tilt = 0.0

            if err_pan != 0.0:
                self.last_turn_dir = float(np.sign(err_pan))

            pan_sign = -1.0 if PAN_INVERT else 1.0
            tilt_sign = -1.0 if TILT_INVERT else 1.0

            # PID outputs angular velocity in degrees per frame.
            delta_pan = self.pid_pan.update(err_pan) * self.speed_limit * pan_sign
            delta_tilt = self.pid_tilt.update(err_tilt) * self.speed_limit * tilt_sign
            debug_cx, debug_cy = int(cx), int(cy)

        elif self.state == RobotState.SEARCHING:
            if self.pan_angle <= PAN_MIN + 1:
                self.last_turn_dir = 1.0
            elif self.pan_angle >= PAN_MAX - 1:
                self.last_turn_dir = -1.0

            delta_pan = SEARCH_PAN_SPEED * self.last_turn_dir * self.speed_limit
            delta_tilt = SEARCH_TILT_SPEED
            err_pan = 0.0
            err_tilt = 0.0
            debug_cx, debug_cy = w // 2, h // 2

        else:
            delta_pan = 0.0
            delta_tilt = 0.0
            err_pan = 0.0
            err_tilt = 0.0
            debug_cx, debug_cy = w // 2, h // 2

        self.pan_angle = float(np.clip(self.pan_angle + delta_pan, PAN_MIN, PAN_MAX))
        self.tilt_angle = float(np.clip(self.tilt_angle + delta_tilt, TILT_MIN, TILT_MAX))

        debug = {
            "state": self.state,
            "bbox": bbox,
            "err_pan": err_pan,
            "err_tilt": err_tilt,
            "delta_pan": delta_pan,
            "delta_tilt": delta_tilt,
            "pan_angle": self.pan_angle,
            "tilt_angle": self.tilt_angle,
            "speed_limit": self.speed_limit,
            "cx": debug_cx,
            "cy": debug_cy,
        }
        return round(self.pan_angle), round(self.tilt_angle), debug

    def home(self):
        self.pan_angle = float(PAN_HOME)
        self.tilt_angle = float(TILT_HOME)
        self.pid_pan.reset()
        self.pid_tilt.reset()


# -----------------------------------------------------------------------------
# VISUALIZATION
# -----------------------------------------------------------------------------

def draw_overlay(frame, debug, pan, tilt, telem, scale_x=1.0, scale_y=1.0):
    h, w = frame.shape[:2]
    state_color = PanTiltTracker.STATE_COLORS.get(debug["state"], (255, 255, 255))

    cx_frame, cy_frame = w // 2, h // 2
    cv2.line(frame, (cx_frame, 0), (cx_frame, h), (0, 255, 0), 1)
    cv2.line(frame, (0, cy_frame), (w, cy_frame), (0, 255, 0), 1)

    if debug["bbox"] is not None:
        x1, y1, x2, y2 = debug["bbox"]
        x1 = int(x1 * scale_x)
        y1 = int(y1 * scale_y)
        x2 = int(x2 * scale_x)
        y2 = int(y2 * scale_y)
        cx_scaled = int(debug["cx"] * scale_x)
        cy_scaled = int(debug["cy"] * scale_y)

        centered = (
            abs(debug["err_pan"]) < ANGLE_DEAD_ZONE_H
            and abs(debug["err_tilt"]) < ANGLE_DEAD_ZONE_V
        )
        box_color = (0, 255, 0) if centered else (0, 165, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        cv2.circle(frame, (cx_scaled, cy_scaled), 6, (0, 0, 255), -1)
        cv2.line(frame, (cx_frame, cy_frame), (cx_scaled, cy_scaled), (0, 200, 255), 1)

    lines = [
        (f"STATE:  {debug['state']}", state_color),
        (f"PAN:    {pan:3d} deg  err:{debug['err_pan']:+.3f}", (0, 255, 255)),
        (f"TILT:   {tilt:3d} deg  err:{debug['err_tilt']:+.3f}", (255, 200, 0)),
        (
            f"dPAN:  {debug['delta_pan']:+.2f} deg/f  "
            f"dTILT:{debug['delta_tilt']:+.2f} deg/f",
            (200, 200, 200),
        ),
        (f"SPD LIM: {debug['speed_limit']:.0%}", (255, 255, 255)),
        (f"TELEM pan:{telem['pan']} deg  tilt:{telem['tilt']} deg", (255, 165, 0)),
    ]

    for i, (text, color) in enumerate(lines):
        bold = i in (0, 1, 2)
        cv2.putText(
            frame,
            text,
            (10, 25 + i * 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60 if bold else 0.50,
            color,
            2 if bold else 1,
        )


# -----------------------------------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------------------------------

def main():
    stream_url = f"http://{MOBILE_IP}:8080/video"
    print(f"Video stream : {stream_url}")
    print(f"ESP target   : {ESP_IP}:{UDP_CMD_PORT}")

    video = MobileVideoStream(stream_url)
    commander = ServoCommander(ESP_IP, UDP_CMD_PORT)
    telemetry = ServoTelemetry(UDP_TELEM_PORT)

    print("Waiting for camera", end="", flush=True)
    for _ in range(30):
        if video.connected:
            break
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()

    if not video.connected:
        print("Could not connect to camera. Check MOBILE_IP and the camera app.")
        video.stop()
        telemetry.stop()
        return

    tracker = PanTiltTracker("best.pt", TARGET_OBJECT)
    commander.home()
    time.sleep(0.5)

    print(f"\nTracking: {TARGET_OBJECT}")
    print("Q = quit   H = home servos   R = reset PIDs")
    print("=" * 60)

    last_fid = -1
    last_cmd_time = 0.0
    fps_count = 0
    fps_timer = time.time()

    try:
        while True:
            frame, fid = video.read()
            if frame is None or fid == last_fid:
                time.sleep(0.005)
                continue

            last_fid = fid
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            fps_count += 1
            if fps_count >= 30:
                elapsed = time.time() - fps_timer
                fps = fps_count / elapsed
                print(
                    f"FPS:{fps:.1f}  pan:{tracker.pan_angle:.1f}  "
                    f"tilt:{tracker.tilt_angle:.1f}  state:{tracker.state}"
                )
                fps_count = 0
                fps_timer = time.time()

            pan_cmd, tilt_cmd, debug = tracker.control(frame)

            now = time.time()
            if now - last_cmd_time >= CMD_INTERVAL:
                commander.servos(pan_cmd, tilt_cmd)
                last_cmd_time = now

            orig_h, orig_w = frame.shape[:2]
            disp = cv2.resize(frame, (640, 480))
            draw_overlay(
                disp,
                debug,
                pan_cmd,
                tilt_cmd,
                telemetry.read(),
                640 / orig_w,
                480 / orig_h,
            )

            cv2.imshow(f"Pan-Tilt Tracker - {TARGET_OBJECT}", disp)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("h"):
                tracker.home()
                commander.home()
                print(f"Servos homed to {PAN_HOME}/{TILT_HOME}")
            elif key == ord("r"):
                tracker.pid_pan.reset()
                tracker.pid_tilt.reset()
                print("PIDs reset")

    finally:
        print("\nShutting down...")
        try:
            commander.stop()
        finally:
            video.stop()
            telemetry.stop()
            cv2.destroyAllWindows()
        print("Done.")


if __name__ == "__main__":
    main()
