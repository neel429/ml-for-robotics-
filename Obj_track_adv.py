import cv2
import numpy as np
import time
import socket
import threading
import requests
from ultralytics import YOLO


# ──────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Network
ESP_IP         = "192.168.137.228"
UDP_CMD_PORT   = 5001
UDP_TELEM_PORT = 5002

# Vision
TARGET_OBJECT = "ball"
TARGET_AREA   = 143_000

# Turn PID
BODY_TURN_KP = 10
BODY_TURN_KI = 0
BODY_TURN_KD = 3

# Distance PID
DIST_KP = 10
DIST_KI = 0
DIST_KD = 5
MAX_DIST_INTEGRAL = 0.8

# Motion limits
MAX_SPEED = 30
MIN_SPEED = 3
MAX_TURN  = 30
MAX_ACCEL = 2

# Dead zones (normalised)
ANGLE_DEAD_ZONE = 0.00
AREA_DEAD_ZONE  = 0.08

# Smoothing / state-machine
SMOOTH_RATE    = 0.04
ACQUIRE_FRAMES = 5
LOST_TIMEOUT   = 1.0


# ──────────────────────────────────────────────────────────────────────────────
#  CONTROLLERS
# ──────────────────────────────────────────────────────────────────────────────

class PID:
    """Proportional-Integral-Derivative controller with optional output clamping."""

    def __init__(self, kp, ki, kd, max_integral=100.0, output_limits=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_integral  = max_integral
        self.output_limits = output_limits
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None

    def update(self, error):
        now = time.time()
        dt  = 0.02 if self._prev_time is None else max(now - self._prev_time, 1e-4)
        self._prev_time = now

        self._integral   = np.clip(self._integral + error * dt,
                                   -self.max_integral, self.max_integral)
        derivative       = (error - self._prev_error) / dt
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        if self.output_limits:
            output = np.clip(output, *self.output_limits)
        return output

    def reset(self):
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None


# ──────────────────────────────────────────────────────────────────────────────
#  NETWORKING
# ──────────────────────────────────────────────────────────────────────────────

class MobileVideoStream:
    """Continuously pulls MJPEG frames from a phone camera in a background thread."""

    def __init__(self, url):
        self.url       = url
        self.frame     = None
        self.fid       = 0
        self.connected = False
        self.running   = True
        self._lock     = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        backoff = 1.0
        while self.running:
            try:
                response = requests.get(self.url, stream=True, timeout=10)
                if response.status_code != 200:
                    raise ConnectionError("Non-200 status")

                self.connected = True
                backoff = 1.0
                buf = b""

                for chunk in response.iter_content(1024):
                    buf += chunk
                    start = buf.find(b"\xff\xd8")
                    end   = buf.find(b"\xff\xd9")

                    if start != -1 and end != -1:
                        jpg = buf[start : end + 2]
                        buf = buf[end + 2 :]
                        img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                        if img is not None:
                            with self._lock:
                                self.frame = img
                                self.fid  += 1

                    if not self.running:
                        break

            except Exception:
                self.connected = False
                time.sleep(backoff)
                backoff = min(backoff * 2, 8.0)

    def read(self):
        with self._lock:
            return self.frame, self.fid

    def stop(self):
        self.running = False


class Commander:
    """Sends UDP motor commands to the ESP."""

    def __init__(self, ip, port):
        self.ip    = ip
        self.port  = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def motors(self, left, right, light="off"):
        msg = f"MOTOR,{int(left)},{int(right)},{light.upper()}"
        self._sock.sendto(msg.encode(), (self.ip, self.port))

    def stop(self):
        self._sock.sendto(b"STOP,OFF", (self.ip, self.port))


class Telemetry:
    """Receives encoder telemetry from the ESP over UDP."""

    def __init__(self, port):
        self.left_ticks  = 0
        self.right_ticks = 0
        self.cmd_left    = 0
        self.cmd_right   = 0
        self.running     = True
        self._lock       = threading.Lock()
        self._sock       = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", port))
        self._sock.settimeout(1.0)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            try:
                data, _ = self._sock.recvfrom(128)
                parts   = data.decode().strip().split(",")
                if parts[0] == "ENC" and len(parts) == 5:
                    with self._lock:
                        self.left_ticks  = int(parts[1])
                        self.right_ticks = int(parts[2])
                        self.cmd_left    = int(parts[3])
                        self.cmd_right   = int(parts[4])
            except Exception:
                pass

    def read(self):
        with self._lock:
            return {
                "left_ticks":  self.left_ticks,
                "right_ticks": self.right_ticks,
                "cmd_left":    self.cmd_left,
                "cmd_right":   self.cmd_right,
            }

    def stop(self):
        self.running = False
        self._sock.close()


# ──────────────────────────────────────────────────────────────────────────────
#  STATE MACHINE
# ──────────────────────────────────────────────────────────────────────────────

class RobotState:
    STOPPED   = "STOPPED"
    SEARCHING = "SEARCHING"
    ACQUIRING = "ACQUIRING"
    TRACKING  = "TRACKING"


# ──────────────────────────────────────────────────────────────────────────────
#  TRACKER
# ──────────────────────────────────────────────────────────────────────────────

def ramp(current, target, max_step):
    """Limit how fast a value can change per step."""
    diff = target - current
    if abs(diff) <= max_step:
        return target
    return current + max_step * np.sign(diff)


class Tracker:
    """YOLO-based ball tracker with PID control and a 4-state state machine."""

    STATE_COLORS = {
        RobotState.STOPPED:   (100, 100, 100),
        RobotState.SEARCHING: (255, 165,   0),
        RobotState.ACQUIRING: (255, 255,   0),
        RobotState.TRACKING:  (  0, 255,   0),
    }

    def __init__(self, model_path, target):
        print("Loading YOLO model...")
        self.model  = YOLO(model_path)
        self.target = target

        try:
            self.model.to("cuda")
            print("Using CUDA")
        except Exception:
            print("Using CPU")
        self.model.fuse()

        self.pid_turn = PID(BODY_TURN_KP, BODY_TURN_KI, BODY_TURN_KD,
                            output_limits=(-MAX_TURN, MAX_TURN))
        self.pid_dist = PID(DIST_KP, DIST_KI, DIST_KD,
                            max_integral=MAX_DIST_INTEGRAL,
                            output_limits=(-MAX_SPEED, MAX_SPEED))

        self.state          = RobotState.STOPPED
        self.acquire_count  = 0
        self.last_seen_t    = 0.0
        self.last_turn_dir  = 1.0
        self.smoothed_angle = 0.0
        self.speed_limit    = 1.0
        self.cur_left       = 0.0
        self.cur_right      = 0.0

    # ── Detection ────────────────────────────────────────────────────────────

    def _detect(self, frame):
        """Return the bounding box of the largest detected target, or None."""
        results   = self.model(frame, imgsz=320, verbose=False, conf=0.60)
        best      = None
        best_area = 0

        for r in results:
            for box in r.boxes:
                if self.model.names[int(box.cls[0])] != self.target:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                area = (x2 - x1) * (y2 - y1)
                if area > best_area:
                    best_area = area
                    best      = (x1, y1, x2, y2)

        return best

    # ── State machine ─────────────────────────────────────────────────────────

    def _update_state(self, bbox_found):
        if bbox_found:
            self.last_seen_t = time.time()

            if self.state in (RobotState.STOPPED, RobotState.SEARCHING):
                self.state         = RobotState.ACQUIRING
                self.acquire_count = 0
                self.speed_limit   = 0.4

            elif self.state == RobotState.ACQUIRING:
                self.acquire_count += 1
                self.speed_limit    = 0.4 + 0.6 * self.acquire_count / ACQUIRE_FRAMES
                if self.acquire_count >= ACQUIRE_FRAMES:
                    self.state       = RobotState.TRACKING
                    self.speed_limit = 1.0

            elif self.state == RobotState.TRACKING:
                self.speed_limit = 1.0

        else:
            elapsed = time.time() - self.last_seen_t
            if elapsed < LOST_TIMEOUT:
                self.state       = RobotState.SEARCHING
                self.speed_limit = 0.3
            else:
                self.state          = RobotState.STOPPED
                self.speed_limit    = 0.0
                self.smoothed_angle = 0.0
                self.pid_turn.reset()
                self.pid_dist.reset()

    # ── Control ──────────────────────────────────────────────────────────────

    def _motor_outputs_for_ball(self, cx, area, frame_width):
        """Compute raw left/right targets when the ball is visible."""
        raw_angle_error = (cx - frame_width / 2) / frame_width

        if abs(raw_angle_error) < ANGLE_DEAD_ZONE:
            raw_angle_error = 0.0
        if raw_angle_error != 0.0:
            self.last_turn_dir = np.sign(raw_angle_error)

        self.smoothed_angle = raw_angle_error
        turn_cmd = self.pid_turn.update(self.smoothed_angle)

        dist_error = (area - TARGET_AREA) / TARGET_AREA
        if abs(dist_error) < AREA_DEAD_ZONE:
            dist_error = 0.0
        self.pid_dist.update(dist_error)

        base_speed = 10
        tgt_left   = base_speed + turn_cmd
        tgt_right  = base_speed - turn_cmd

        # Scale to MAX_SPEED without clipping
        max_raw = max(abs(tgt_left), abs(tgt_right))
        if max_raw > MAX_SPEED:
            scale     = MAX_SPEED / max_raw
            tgt_left  *= scale
            tgt_right *= scale

        return tgt_left, tgt_right, dist_error, turn_cmd, base_speed

    def control(self, frame):
        """Run one control cycle; returns (left_speed, right_speed, debug_dict)."""
        h, w = frame.shape[:2]
        bbox = self._detect(frame)
        self._update_state(bbox is not None)

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            cx   = (x1 + x2) / 2
            area = (x2 - x1) * (y2 - y1)
            tgt_left, tgt_right, dist_error, turn_cmd, base_speed = \
                self._motor_outputs_for_ball(cx, area, w)

        elif self.state == RobotState.SEARCHING:
            tgt_left   =  10 * self.last_turn_dir * self.speed_limit
            tgt_right  = -10 * self.last_turn_dir * self.speed_limit
            dist_error = turn_cmd = base_speed = 0.0
            area = 0
            cx   = w / 2

        else:  # STOPPED
            tgt_left = tgt_right = 0
            dist_error = turn_cmd = base_speed = 0.0
            area = 0
            cx   = w / 2

        self.cur_left  = ramp(self.cur_left,  tgt_left,  MAX_ACCEL)
        self.cur_right = ramp(self.cur_right, tgt_right, MAX_ACCEL)

        debug = {
            "state":          self.state,
            "bbox":           bbox,
            "smoothed_angle": self.smoothed_angle,
            "turn_cmd":       turn_cmd,
            "dist_error":     dist_error,
            "base_speed":     base_speed,
            "area":           area,
            "cx":             int(cx) if bbox is None else int((bbox[0] + bbox[2]) / 2),
            "speed_limit":    self.speed_limit,
        }
        return round(self.cur_left), round(self.cur_right), debug

    def reset(self):
        self.pid_turn.reset()
        self.pid_dist.reset()
        self.smoothed_angle = 0.0


# ──────────────────────────────────────────────────────────────────────────────
#  VISUALISATION HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def draw_overlay(frame, debug, left_speed, right_speed, telem, scale_x, scale_y):
    h, w = frame.shape[:2]
    state_color = Tracker.STATE_COLORS.get(debug["state"], (255, 255, 255))

    # Centre line
    cv2.line(frame, (w // 2, 0), (w // 2, h), (0, 255, 0), 1)

    # Smoothed-angle indicator
    smooth_x = int(w / 2 + debug["smoothed_angle"] * w)
    cv2.line(frame, (smooth_x, 0), (smooth_x, h), (0, 255, 255), 2)
    cv2.putText(frame, "SMOOTH", (smooth_x + 5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Bounding box
    if debug["bbox"] is not None:
        x1, y1, x2, y2 = debug["bbox"]
        x1, y1, x2, y2 = (int(x1 * scale_x), int(y1 * scale_y),
                           int(x2 * scale_x), int(y2 * scale_y))

        if abs(debug["dist_error"]) < AREA_DEAD_ZONE:
            box_color = (0, 255, 0)     # green  — correct distance
        elif debug["dist_error"] > 0:
            box_color = (0, 0, 255)     # red    — too close
        else:
            box_color = (255, 100, 0)   # blue   — too far

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        cy = (y1 + y2) // 2
        cv2.circle(frame, (int(debug["cx"] * scale_x), cy), 6, (0, 0, 255), -1)

    # Text HUD
    lines = [
        (f"STATE:  {debug['state']}",                                   state_color),
        (f"SMOOTH: {debug['smoothed_angle']:+.3f}",                     (0, 255, 255)),
        (f"AREA:   {int(debug['area'])} / {TARGET_AREA}",               (255, 255, 255)),
        (f"SPD LIM:{debug['speed_limit']:.0%}",                         (255, 255, 255)),
        (f"L:{int(left_speed):+4d} R:{int(right_speed):+4d}",           (0, 255, 0)),
        (f"ENC L:{telem['left_ticks']:+4d} R:{telem['right_ticks']:+4d}", (255, 165, 0)),
    ]
    for i, (text, color) in enumerate(lines):
        thickness = 2 if i in (0, 4) else 1
        cv2.putText(frame, text, (10, 25 + i * 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65 if i in (0, 4) else 0.55,
                    color, thickness)


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    mobile_ip  = "10.18.204.215"
    stream_url = f"http://{mobile_ip}:8080/video"
    print(f"Stream: {stream_url}")

    video     = MobileVideoStream(stream_url)
    commander = Commander(ESP_IP, UDP_CMD_PORT)
    telemetry = Telemetry(UDP_TELEM_PORT)

    print("Waiting for camera", end="", flush=True)
    for _ in range(30):
        if video.connected:
            break
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()

    if not video.connected:
        print("Could not connect to camera")
        return

    tracker = Tracker("best.pt", TARGET_OBJECT)
    commander.stop()
    time.sleep(0.5)

    print(f"\nTracking: {TARGET_OBJECT}  |  Target area: {TARGET_AREA}")
    print("Q=Quit  R=Reset  F=Smooth faster  S=Smooth slower")
    print("=" * 60)

    last_fid      = -1
    last_cmd_time = 0.0
    CMD_INTERVAL  = 0.03
    fps_count     = 0
    fps_timer     = time.time()

    while True:
        frame, fid = video.read()
        if frame is None or fid == last_fid:
            time.sleep(0.005)
            continue

        last_fid   = fid
        fps_count += 1
        if fps_count >= 30:
            fps = fps_count / (time.time() - fps_timer)
            print(f"FPS: {fps:.1f}  SMOOTH_RATE: {SMOOTH_RATE:.2f}")
            fps_count = 0
            fps_timer = time.time()

        left_speed, right_speed, debug = tracker.control(frame)
        print(left_speed, right_speed)

        orig_h, orig_w = frame.shape[:2]
        frame = cv2.resize(frame, (640, 480))
        h, w  = frame.shape[:2]

        # Send motor command at a fixed interval
        now = time.time()
        if now - last_cmd_time >= CMD_INTERVAL:
            commander.motors(-left_speed, right_speed)
            last_cmd_time = now

        draw_overlay(frame, debug, left_speed, right_speed,
                     telemetry.read(), w / orig_w, h / orig_h)

        cv2.imshow(f"Object Tracker — {TARGET_OBJECT}", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            tracker.reset()
            print("Reset")
        elif key == ord("f"):
            SMOOTH_RATE = min(SMOOTH_RATE + 0.02, 0.5)
            print(f"SMOOTH_RATE → {SMOOTH_RATE:.2f}")
        elif key == ord("s"):
            SMOOTH_RATE = max(SMOOTH_RATE - 0.02, 0.02)
            print(f"SMOOTH_RATE → {SMOOTH_RATE:.2f}")

    print("\nShutting down...")
    commander.stop()
    time.sleep(0.2)
    video.stop()
    telemetry.stop()
    cv2.destroyAllWindows()
    print("Done")


if __name__ == "__main__":
    main()