# shared.py
# Reusable infrastructure used by both obj_track_adv.py
# and lane_follower_adv.py.
# Contains: PID, MobileVideoStream, Commander, Telemetry,
# RobotState, ramp()

import cv2
import numpy as np
import time
import socket
import threading
import requests


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

class RobotState:
    STOPPED   = "STOPPED"
    SEARCHING = "SEARCHING"
    ACQUIRING = "ACQUIRING"
    TRACKING  = "TRACKING"

def ramp(current, target, max_step):
    """Limit how fast a value can change per step."""
    diff = target - current
    if abs(diff) <= max_step:
        return target
    return current + max_step * np.sign(diff)
