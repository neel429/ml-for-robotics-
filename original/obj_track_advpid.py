import cv2
import socket
import numpy as np
import requests
import time
from ultralytics import YOLO

# -- CONFIGURATION ----------------------------------------------------
# Paste your phone stream URL here
# Android (IP Webcam):      "http://192.168.x.x:8080/video"
# iPhone (Simple IP Camera): "http://192.168.x.x:8080/live"
STREAM_URL = "http://192.168.1.137:8080/video"
# STREAM_URL = "http://192.168.1.20:8080/live"
ARDUINO_IP = "192.168.1.19"
CMD_PORT = 5001
# Path to your trained model from Exercise A
MODEL_PATH = "best.pt"
# MODEL_PATH = "yolo26x-obb.pt"

# Only show detections above this confidence level (0.0 to 1.0)
CONFIDENCE = 0.1
SPEED = 100
TURN = 255
# --------------------------------------------------------------------


cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class PID:
    """Proportional-Integral-Derivative controller with optional output clamping."""

    def __init__(self, kp, ki, kd, max_integral=100.0, output_limit=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_integral = max_integral
        self.output_limit = output_limit
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def update(self, error):
        now = time.time()
        dt = 0.02 if self._prev_time is None else max(now - self._prev_time, 1e-4)
        self._prev_time = now
        # print(dt)
        if dt > 2:
            self._integral = 0

        self._integral = np.clip(
            self._integral + error * dt, -self.max_integral, self.max_integral
        )
        derivative = (error - self._prev_error) / dt
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        if self.output_limit:
            output = np.clip(output, -self.output_limit, self.output_limit)
        return output

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None


def send_command(left, right):
    msg = f"MOTOR,{int(left)},{int(right)}"
    cmd_sock.sendto(msg.encode(), (ARDUINO_IP, CMD_PORT))


def send_stop():
    cmd_sock.sendto(b"STOP", (ARDUINO_IP, CMD_PORT))


def open_stream(url):
    print(f"Connecting to stream: {url}")
    response = requests.get(url, stream=True, timeout=10)
    if response.status_code != 200:
        raise ConnectionError(f"Could not connect. Status: {response.status_code}")
    print("Stream connected.")
    return response


def read_frame(stream_response):
    buf = b""
    for chunk in stream_response.iter_content(4096):
        if not chunk:
            continue

        buf += chunk
        start = buf.find(b"\xff\xd8")
        if start == -1:
            # Keep one byte in case the JPEG marker is split across chunks.
            buf = buf[-1:]
            continue

        end = buf.find(b"\xff\xd9", start + 2)
        if end == -1:
            # Keep the partial JPEG and wait for more bytes.
            buf = buf[start:]
            continue

        jpg = buf[start : end + 2]
        buf = buf[end + 2 :]

        if len(jpg) <= 2:
            continue

        frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            return frame
    return None


def findbest(results):
    """Return the bounding box of the largest detected target, or None."""
    best = None
    best_area = 0

    for r in results:
        for box in r.boxes:
            # if self.model.names[int(box.cls[0])] != self.target:
            #     continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best = (x1, y1, x2, y2)

    return best


def main():
    # Load the trained model
    print("Loading model...")
    model = YOLO(MODEL_PATH)
    print("Model loaded.")

    # Connect to the phone stream
    stream = open_stream(STREAM_URL)

    print("Press Q to quit.")
    fps_timer = time.time()
    frame_count = 0
    fps = 0

    pid = PID(0.7, 0.1, 0.05, output_limit=1)

    while True:
        frame = read_frame(stream)
        if frame is None:
            continue

        # Run detection on the frame
        now = time.time()
        results = model(frame, imgsz=416, conf=CONFIDENCE, verbose=False)
        fin = time.time()
        print(fin - now)

        best = findbest(results)
        if best is not None:
            wid = len(frame[0])
            x = (best[0] + best[2]) / 2
            # print(best,x)
            x = (x - wid / 2) / (wid / 2)
            power = pid.update(x) * TURN
            # if power != 0:
            # power = (x / abs(x)) * min(abs(x * TURN), 255)
            # print(f"{round(x,2)}\t{round(power,2)}")
            send_command(-power - SPEED, power - SPEED)
        else:
            pass
            # send_command(0, 0)
            # pid.reset()
        # send_command(255,255)
        # Draw boxes on the frame
        annotated = results[0].plot()

        # Calculate and display FPS
        frame_count += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            frame_count = 0
            fps_timer = time.time()
        cv2.putText(
            annotated,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        cv2.imshow("Phone Stream - YOLO26n Detection", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.close()
    cv2.destroyAllWindows()
    print("Stopped.")


if __name__ == "__main__":
    main()
