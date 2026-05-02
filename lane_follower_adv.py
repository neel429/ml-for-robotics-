import cv2
import numpy as np
import time
import socket
import threading
import requests

# ==================== CONFIGURATION ====================
ESP_IP         = "192.168.137.228"
UDP_CMD_PORT   = 5001
UDP_TELEM_PORT = 5002

BINARY_THRESHOLD   = 70
ROI_HEIGHT_PERCENT = 0.88
MORPH_KERNEL_SIZE  = 7
MIN_LINE_AREA      = 500
BASE_SPEED         = 100
TARGET_AREA        = 20000
MAX_SPEED          = 255
MAX_TURN           = 30
MAX_ACCEL          = 2
MOTOR_OUTPUT_SCALE = 10

SMOOTH_RATE = 0.04

BODY_TURN_KP = 100
BODY_TURN_KD = 4
BODY_TURN_KI = 0

DIST_KP = 0
DIST_KI = 0
DIST_KD = 0
MAX_DIST_INTEGRAL = 0.8

ANGLE_DEAD_ZONE = 0.00
AREA_DEAD_ZONE  = 0.2

ACQUIRE_FRAMES = 5
LOST_TIMEOUT   = 1.0

ROW_FRACS = [0.90, 0.75, 0.60, 0.45, 0.30]

STATE_COLORS = {
    "STOPPED":   (100, 100, 100),
    "SEARCHING": (255, 165,   0),
    "ACQUIRING": (255, 255,   0),
    "TRACKING":  (  0, 255,   0),
}


# ==================== CONTROLLERS ====================
class PD:
    def __init__(self, kp, kd, output_limits=None):
        self.kp = kp
        self.kd = kd
        self.output_limits = output_limits
        self._prev_error = 0.0
        self._prev_time  = None

    def update(self, error):
        now = time.time()
        dt  = 0.02 if self._prev_time is None else max(now - self._prev_time, 1e-4)
        self._prev_time  = now
        derivative       = (error - self._prev_error) / dt
        self._prev_error = error
        out = self.kp * error + self.kd * derivative
        if self.output_limits:
            out = np.clip(out, *self.output_limits)
        return out

    def reset(self):
        self._prev_error = 0.0
        self._prev_time  = None


class PID:
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
        self._integral  = np.clip(
            self._integral + error * dt, -self.max_integral, self.max_integral
        )
        derivative       = (error - self._prev_error) / dt
        self._prev_error = error
        out = self.kp * error + self.ki * self._integral + self.kd * derivative
        if self.output_limits:
            out = np.clip(out, *self.output_limits)
        print(f"error: {error:.3f} | derivative: {derivative:.3f} | out: {out:.3f}")
        return out

    def reset(self):
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None


# ==================== VIDEO STREAM ====================
class MobileVideoStream:
    def __init__(self, url):
        self.url       = url
        self.frame     = None
        self.fid       = 0
        self._lock     = threading.Lock()
        self.connected = False
        self.running   = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        backoff = 1.0
        while self.running:
            try:
                r = requests.get(self.url, stream=True, timeout=10)
                if r.status_code != 200:
                    raise ConnectionError()
                self.connected = True
                backoff = 1.0
                buf = b''
                for chunk in r.iter_content(1024):
                    if not self.running:
                        break
                    buf += chunk
                    a, b = buf.find(b'\xff\xd8'), buf.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        img = cv2.imdecode(np.frombuffer(buf[a:b+2], np.uint8), cv2.IMREAD_COLOR)
                        buf = buf[b+2:]
                        if img is not None:
                            with self._lock:
                                self.frame = img
                                self.fid  += 1
            except Exception:
                self.connected = False
                time.sleep(backoff)
                backoff = min(backoff * 2, 8.0)

    def read(self):
        with self._lock:
            return self.frame, self.fid

    def stop(self):
        self.running = False


# ==================== COMMANDER ====================
class Commander:
    def __init__(self, ip, port):
        self.ip    = ip
        self.port  = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def motors(self, left, right, light='off'):
        msg = f"MOTOR,{int(left)},{int(right)},{light.upper()}"
        self._sock.sendto(msg.encode(), (self.ip, self.port))

    def stop(self):
        self._sock.sendto(b"STOP,OFF", (self.ip, self.port))


# ==================== TELEMETRY ====================
class Telemetry:
    def __init__(self, port):
        self._lock   = threading.Lock()
        self.running = True
        self.data    = dict(left_ticks=0, right_ticks=0, cmd_left=0, cmd_right=0)
        self._sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(('', port))
        self._sock.settimeout(1.0)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            try:
                msg = self._sock.recvfrom(128)[0].decode().strip()
                if msg.startswith("ENC,"):
                    parts = msg.split(',')
                    if len(parts) == 5:
                        with self._lock:
                            self.data = dict(
                                left_ticks  = int(parts[1]),
                                right_ticks = int(parts[2]),
                                cmd_left    = int(parts[3]),
                                cmd_right   = int(parts[4]),
                            )
            except Exception:
                pass

    def read(self):
        with self._lock:
            return dict(self.data)

    def stop(self):
        self.running = False
        self._sock.close()


# ==================== HELPERS ====================
def ramp(current, target, max_step):
    diff = target - current
    if abs(diff) <= max_step:
        return target
    return current + max_step * np.sign(diff)


def scale_motors(left, right):
    """Scale motor commands so neither exceeds MAX_SPEED."""
    peak = max(abs(left), abs(right))
    if peak > MAX_SPEED:
        scale = MAX_SPEED / peak
        return left * scale, right * scale
    return left, right


# ==================== LANE DETECTION ====================
def detect_lane(frame):
    h, w  = frame.shape[:2]
    roi_y = int(h * (1 - ROI_HEIGHT_PERCENT))
    roi   = frame[roi_y:, :]

    blur = cv2.GaussianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (7, 7), 0)
    _, binary = cv2.threshold(blur, BINARY_THRESHOLD, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    points = []
    for frac in ROW_FRACS:
        ry  = int(binary.shape[0] * frac)
        xs  = np.where(binary[ry] > 0)[0]
        if len(xs) < 15:
            continue
        runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
        best = max(runs, key=len)
        if len(best) < 12:
            continue
        points.append((int((best[0] + best[-1]) / 2), ry + roi_y))

    area = int(np.count_nonzero(binary))

    if len(points) < 2:
        return None, None, None, area, roi_y, binary, points

    return points[0], points[-1], points, area, roi_y, binary, points


# ==================== STATE MACHINE ====================
class RobotState:
    STOPPED   = "STOPPED"
    SEARCHING = "SEARCHING"
    ACQUIRING = "ACQUIRING"
    TRACKING  = "TRACKING"


# ==================== LANE FOLLOWER ====================
class LaneFollower:
    def __init__(self):
        self.smoothed_angle = 0.0
        self.pid_turn = PID(BODY_TURN_KP, BODY_TURN_KI, BODY_TURN_KD,
                            output_limits=(-MAX_TURN, MAX_TURN))
        self.pid_dist = PID(DIST_KP, DIST_KI, DIST_KD,
                            max_integral=MAX_DIST_INTEGRAL,
                            output_limits=(-MAX_SPEED, MAX_SPEED))
        self.state         = RobotState.STOPPED
        self.acquire_count = 0
        self.last_seen_t   = 0.0
        self.last_turn_dir = 1.0
        self.cur_left      = 0.0
        self.cur_right     = 0.0
        self.speed_limit   = 1.0

    def _update_state(self, line_found):
        if line_found:
            self.last_seen_t = time.time()
            if self.state in (RobotState.STOPPED, RobotState.SEARCHING):
                self.state, self.acquire_count, self.speed_limit = RobotState.ACQUIRING, 0, 0.4
            elif self.state == RobotState.ACQUIRING:
                self.acquire_count += 1
                self.speed_limit = 0.4 + 0.6 * self.acquire_count / ACQUIRE_FRAMES
                if self.acquire_count >= ACQUIRE_FRAMES:
                    self.state, self.speed_limit = RobotState.TRACKING, 1.0
            # TRACKING → no change needed
        else:
            elapsed = time.time() - self.last_seen_t
            if elapsed < LOST_TIMEOUT:
                self.state, self.speed_limit = RobotState.SEARCHING, 0.3
            else:
                self.state, self.speed_limit = RobotState.STOPPED, 0.0
                self.smoothed_angle = 0.0
                self.pid_turn.reset()
                self.pid_dist.reset()

    def control(self, frame):
        h, w = frame.shape[:2]
        near_pt, far_pt, centers, area, roi_y, binary, points = detect_lane(frame)
        line_found = near_pt is not None and far_pt is not None

        self._update_state(line_found)

        if line_found:
            near_cx, near_cy = near_pt
            far_cx,  _       = far_pt

            position_error  = (near_cx - w / 2) / w
            direction_error = (far_cx  - near_cx) / w
            raw_angle_error = 0.25 * position_error + 0.75 * direction_error

            if abs(raw_angle_error) < ANGLE_DEAD_ZONE:
                raw_angle_error = 0.0
            if raw_angle_error != 0.0:
                self.last_turn_dir = np.sign(raw_angle_error)

            self.smoothed_angle = (
                SMOOTH_RATE * self.smoothed_angle
                + (1 - SMOOTH_RATE) * raw_angle_error
            )

            turn_cmd   = self.pid_turn.update(self.smoothed_angle)
            dist_error = (TARGET_AREA - area) / TARGET_AREA
            if abs(dist_error) < AREA_DEAD_ZONE:
                dist_error = 0.0
            dist_cmd = self.pid_dist.update(dist_error)

            tgt_left, tgt_right = scale_motors(
                (BASE_SPEED + turn_cmd) * self.speed_limit,
                (BASE_SPEED - turn_cmd) * self.speed_limit,
            )
            cx, cy = near_cx, near_cy

        elif self.state == RobotState.SEARCHING:
            search_turn = 8 * self.last_turn_dir * self.speed_limit
            forward     = 5 * self.speed_limit
            tgt_left, tgt_right = scale_motors(forward + search_turn, forward - search_turn)
            dist_error, turn_cmd, area, cx = 0.0, 0.0, 0, w // 2
            cy = h // 2

        else:  # STOPPED
            tgt_left = tgt_right = 0
            dist_error, turn_cmd, area, cx = 0.0, 0.0, 0, w // 2
            cy = h // 2

        self.cur_left  = ramp(self.cur_left,  tgt_left,  MAX_ACCEL)
        self.cur_right = ramp(self.cur_right, tgt_right, MAX_ACCEL)

        debug = {
            'state':          self.state,
            'line_found':     line_found,
            'cx':             cx,
            'cy':             cy,
            'area':           area,
            'roi_y':          roi_y,
            'binary':         binary,
            'smoothed_angle': self.smoothed_angle,
            'turn_cmd':       turn_cmd,
            'dist_error':     dist_error,
            'base_speed':     BASE_SPEED if line_found else 0,
            'speed_limit':    self.speed_limit,
            'points':         points if line_found else [],
        }
        return round(self.cur_left), round(self.cur_right), debug


# ==================== VISUALIZATION ====================
def draw_debug(frame, debug, left_speed, right_speed, telem):
    h, w = frame.shape[:2]

    # ROI line
    cv2.line(frame, (0, debug['roi_y']), (w, debug['roi_y']), (0, 165, 255), 1)
    cv2.putText(frame, "ROI", (5, debug['roi_y'] - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

    # Centre and smoothed-angle guide lines
    cv2.line(frame, (w // 2, 0), (w // 2, h), (0, 255, 0), 1)
    smooth_x = int(w / 2 + debug['smoothed_angle'] * w)
    cv2.line(frame, (smooth_x, 0), (smooth_x, h), (0, 255, 255), 2)
    cv2.putText(frame, "SMOOTH", (smooth_x + 5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Detected lane points and centroid
    if debug['line_found']:
        color = ((0, 255, 0) if abs(debug['dist_error']) < AREA_DEAD_ZONE
                 else (0, 0, 255) if debug['dist_error'] < 0
                 else (255, 100, 0))
        cv2.circle(frame, (debug['cx'], debug['cy']), 8, color, -1)
        cv2.line(frame, (w // 2, debug['cy']), (debug['cx'], debug['cy']), (0, 255, 255), 2)

        for px, py in debug['points']:
            cv2.circle(frame, (px, py), 5, (255, 0, 255), -1)
        if len(debug['points']) >= 2:
            cv2.line(frame, debug['points'][0], debug['points'][-1], (255, 0, 0), 2)

    # HUD text
    sc = STATE_COLORS.get(debug['state'], (255, 255, 255))
    lines = [
        (f"STATE:  {debug['state']}",                       sc,            25),
        (f"SMOOTH: {debug['smoothed_angle']:+.3f}",          (0, 255, 255), 50),
        (f"AREA:   {int(debug['area'])} / {TARGET_AREA}",   (255,255,255), 75),
        (f"SPD LIM:{debug['speed_limit']:.0%}",             (255,255,255), 100),
        (f"L:{int(left_speed):+4d} R:{int(right_speed):+4d}", (0,255,0),   125),
        (f"DIST:   {debug['dist_error']:+.3f}",             (255, 165, 0), 150),
        (f"ENC L:{telem['left_ticks']:+4d} R:{telem['right_ticks']:+4d}", (255,165,0), 175),
        (f"THRESH: {BINARY_THRESHOLD}",                     (200,200,200), 200),
    ]
    for text, color, y in lines:
        thickness = 2 if y in (25, 125) else 1
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55 if thickness == 1 else 0.65, color, thickness)

    # Binary window
    if debug['binary'] is not None:
        bin_disp = cv2.resize(cv2.cvtColor(debug['binary'], cv2.COLOR_GRAY2BGR), (640, 480))
        cv2.putText(bin_disp, f"THRESH={BINARY_THRESHOLD}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.imshow("Binary (lane detection)", bin_disp)


# ==================== MAIN ====================
def main():
    global BINARY_THRESHOLD

    mobile_ip = "10.18.204.215"
    stream_url = f"http://{mobile_ip}:8080/video"
    print(f"Stream: {stream_url}")

    video     = MobileVideoStream(stream_url)
    commander = Commander(ESP_IP, UDP_CMD_PORT)
    telemetry = Telemetry(UDP_TELEM_PORT)

    print("Waiting for camera...")
    for _ in range(30):
        if video.connected:
            break
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()

    if not video.connected:
        print("Could not connect to camera")
        exit(1)

    follower = LaneFollower()
    commander.stop()
    time.sleep(0.5)

    print("\nLane Following Active")
    print(
        f"BINARY_THRESHOLD: {BINARY_THRESHOLD}  "
        f"ROI: {ROI_HEIGHT_PERCENT:.0%}  "
        f"KERNEL: {MORPH_KERNEL_SIZE}x{MORPH_KERNEL_SIZE}  "
        f"TARGET_AREA: {TARGET_AREA}"
    )
    print("Q=Quit  R=Reset  T=Threshold up  Y=Threshold down")
    print("=" * 60 + "\n")

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
            print(f"FPS: {fps_count / (time.time() - fps_timer):.1f}")
            fps_count = 0
            fps_timer = time.time()

        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        left_speed, right_speed, debug = follower.control(frame)
        print(left_speed, right_speed)

        now = time.time()
        if now - last_cmd_time >= CMD_INTERVAL:
            commander.motors(0, 0) if (left_speed == right_speed == 0) \
                else commander.motors(
                    -left_speed / MOTOR_OUTPUT_SCALE,
                    right_speed / MOTOR_OUTPUT_SCALE,
                )
            last_cmd_time = now

        draw_debug(frame, debug, left_speed, right_speed, telemetry.read())
        cv2.imshow("Lane Follower", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            follower.pid_turn.reset()
            follower.pid_dist.reset()
            follower.smoothed_angle = 0.0
            print("Reset")
        elif key == ord('t'):
            BINARY_THRESHOLD = min(BINARY_THRESHOLD + 5, 255)
            print(f"BINARY_THRESHOLD -> {BINARY_THRESHOLD}")
        elif key == ord('y'):
            BINARY_THRESHOLD = max(BINARY_THRESHOLD - 5, 0)
            print(f"BINARY_THRESHOLD -> {BINARY_THRESHOLD}")

    print("\nShutting down...")
    commander.stop()
    time.sleep(0.2)
    video.stop()
    telemetry.stop()
    cv2.destroyAllWindows()
    print("Done")


if __name__ == "__main__":
    main()
