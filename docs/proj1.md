#  Project 1: Object Tracker
<!-- TODO: Tell claude to insert this into old index.html -->
<!-- add links to old exercises -->

<!-- TODO: new things -->
<!-- add servos for tilt, -->
<!-- convert proj1 to old format, -->
<!-- convert proj2-4 to new code if possible -->

TODO: get from wei
shield
uno r4
better battery snaps


---

## What We Are Building

<video controls width="100%"><source src="../original/project_1.mp4" type="video/mp4"></video>

---

You have built four exercises. Each one taught one hard thing in isolation. Project 1 is where all four converge into one closed-loop robot: your model detects the target, the phone supplies video, and UDP carries commands between the laptop and Arduino.
Exercise A trained `best.pt` YOLO26n detection, class names, confidence, and bounding-box area. Exercise B phone stream MJPEG over WiFi, JPEG markers, OpenCV decoding, stream testing. Exercise C encoder motors Precise movement, ticks to distance, ramping, and calibration. Exercise D UDP WiFi Command packets to the robot. Project 1 YOLO detects ball -> PID computes steering -> UDP sends motor commands -> annotated display shows it live.
All four exercises converging: the robot detects, steers, and tracks autonomously.

### The Four Components

1. **Object Detection**  
   **What it does:** finds the ball in every camera frame and returns the largest bounding box.  
   **Where you learned it:** Exercise A, especially PA.8 and PA.9.  
   **New here:** none. It is the same YOLO call you used in `detect_stream.py`.

2. **Camera Stream**  
   **What it does:** pulls MJPEG frames from your phone camera.  
   **Where you learned it:** Exercise B, PB.5 and PB.6.  
   **New here:** none. Same `read_frame()` pattern from Exercise B.

3. **PID Controller**  
   **What it does:** converts horizontal error into a turn correction continuously.  
   **Where you learned the idea:** Exercise C's distance control in PC.8.  
   **New here:** continuous adjustment instead of a threshold stop.

4. **UDP Communication**  
   **What it does:** sends `MOTOR` commands to the robot.  
   **Where you learned it:** Exercise D, PD.2 and PD.3.  
   **New here:** none. Same socket and message format from Exercise D.

### Pre-flight Checklist
`best.pt` is in the project folder and detects your target above the confidence threshold. Phone stream opens in a browser without timing out. Robot drives 30 cm with less than 2 cm error. WASD keyboard control works over UDP. You know your robot's ARDUINO_IP from Exercise D Serial Monitor output. You know your phone stream URL from Exercise B.
!!! warning "Do not skip broken prerequisites"
    If any box is unchecked, finish that exercise before continuing. Project 1 is an integration project; it will not work if its detector, camera stream, motor base, or UDP link is already broken.

Download this file and place it in your `my-detector` project folder. You will not run it until the final lesson.

---

## Get the Code

[Download](original/obj_track_advpid.py)

---


### Full Code
This is the complete file for reference. Do not try to read it all now : it will not make sense yet. As you work through each lesson, come back here to find the exact section being explained. By the end of the project every line will be familiar.
Complete `obj_track_advpid.py`

```python
--8<-- "original/obj_track_advpid.py"
```


The code for this project is in the course GitHub repository. Download the file before continuing.

1. Download the file above. Save it to your my-detector project folder from Exercise A.
- Verify the file is there. Open VS Code and open the my-detector folder. You should see `obj_track_advpid.py` in the file explorer on the left.
- Open the project file and read the configuration block. The very top section after the import lines is the CONFIGURATION block. Every value in this section must be filled in before running. The next lesson walks through each one.

The complete Project 1 file: PID controller, YOLO detection, UDP commands, MJPEG stream reader, and the main loop. Everything is in one self-contained file with no extra dependencies beyond what you already installed.
!!! info "Do not run the file yet"
    It will not work with the default placeholder values. Complete every lesson in this project first, then run the project file in the final lesson.

---

## Setting Up


---

If you completed Exercise A, your VS Code setup is already done. Project 1 runs in the same folder and virtual environment you used for your detector.
Open your my-detector folder in VS Code. Activate the same virtual environment you used in Exercise A. On Windows use venv\Scripts\activate . On macOS or Linux use source venv/bin/activate . Copy `obj_track_advpid.py` into this folder if it is not already there. Copy your trained `best.pt` into the same folder as `obj_track_advpid.py`.
!!! tip "Reuse the Exercise A environment"
    In Exercise A you created `my-detector` and installed `ultralytics`, `opencv-python`, and `requests`. Those are the core packages Project 1 needs. You do not need a new folder or a new virtual environment.
!!! warning "Use the same terminal context"
    If `python obj_track_advpid.py` cannot find `ultralytics`, you are probably in the wrong folder or the virtual environment is not activated.

---

## Installing Dependencies


---

Project 1 only adds one dependency beyond what you already used in Exercises A and B.

### Already Installed From Earlier Projects
Package Where you used it What Project 1 uses it for ultralytics Exercise A Loads `best.pt` and runs YOLO detection. opencv-python Exercises A and B Decodes frames, draws detection boxes, and shows the video window. requests Exercise B Connects to the phone MJPEG stream.

### The Only New Package
`numpy` may already be installed because `ultralytics` depends on it. Verify first:
Check NumPy
```bash
python -c "import numpy; print(numpy.__version__)"
```
If that prints a version number, you are done. If it throws an import error, install NumPy:
Install NumPy only if needed
```bash
pip install numpy
```

### Full Dependency Check
Create `check_deps.py` in the same folder as `obj_track_advpid.py` and run it.
check_deps.py
```python
import cv2
import numpy as np
import requests
import socket
from ultralytics import YOLO

print("All dependencies present.")
```
Run the check
```bash
python check_deps.py
```
If `All dependencies present.` prints, move on.

---

## Configuration: Tuning Your Robot


---

Project 1 becomes your robot when you fill in the configuration block at the top of `obj_track_advpid.py`. Every value comes from a previous project or from one calibration step you perform now.

| Constant | Source | What to enter |
|:--|:--|:--|
| `STREAM_URL` | Exercise B, PB.3 | The full stream URL shown in IP Webcam or Simple IP Camera when the stream is active. Android: `http://<phone-ip>:8080/video`. iPhone: `http://<phone-ip>:8080/live`. |
| `ARDUINO_IP` | Exercise D, PD.2 | The IP printed by the Arduino Serial Monitor when robot_udp boots. If you lost it, re-upload Exercise D's sketch and read Serial Monitor again. |
| `CMD_PORT = 5001` | Exercise D, PD.0 | Leave as `5001`. It must match `CMD_PORT` in the Arduino sketch. |
| `MODEL_PATH` | Exercise A | The path to your trained model file. Leave as `"best.pt"` if it is in the same folder. |
| `CONFIDENCE` | Exercise A, PA.8 | Detection threshold. Start at `0.1` for testing; raise to `0.5` or higher once tracking works to reduce false detections. |
| `SPEED` | First-run safety | Forward base speed added to both motors. Start at `80` for a slow first test. |
| `TURN` | PID tuning | Maximum turn output. Leave at `255` and control aggressiveness through PID gains instead. |

### Fill-in Table
Value Your entry Source STREAM_URL "____________" Exercise B phone app ARDUINO_IP "____________" Exercise D Serial Monitor MODEL_PATH "____________" Exercise A trained file CONFIDENCE ____________ Start at 0.1, raise after first test SPEED ____________ Start at 80 for safety
!!! warning "Configuration errors look like code bugs"
    A wrong `STREAM_URL`, stale `ARDUINO_IP`, or inverted motor sign can make correct code behave incorrectly. Fill in this table before changing any PID values.

---

## The PID Controller


---

In Exercise C's `driveDistance()` function, the robot stopped when encoder ticks reached a target. That is closed-loop in the sense that it checks the measured result, but it only makes one decision: keep going or stop.
A PID controller makes a continuous adjustment. Every few milliseconds it measures the current error, computes a correction, applies it, and measures again. It never stops adjusting until the error is zero.

### Exercise C Code You Already Wrote
You have already written closed-loop control. In Exercise C, `driveDistance()` measured encoder ticks, compared them to a target, and changed motor behavior when the robot got close.
Exercise C driveDistance()Reference
```cpp
void driveDistance(float targetCm, int speed) {
  long targetTicks = abs(targetCm) / CM_PER_TICK;
  resetEncoders();
  setMotors(speed, speed);

  while (ticksLeft < targetTicks && ticksRight < targetTicks) {
    long remaining = targetTicks - max(ticksLeft, ticksRight);
    if (remaining < 50) {
      int slowSpeed = max(80, speed / 3);
      setMotors(slowSpeed, slowSpeed);
    }
  }

  stopMotors();
}
```
Line Control idea targetTicks The desired result, converted from centimeters into encoder ticks. ticksLeft , ticksRight The measured result from the hardware. remaining The error: how far the robot still needs to travel. if (remaining < 50) A threshold decision: when the error is small, slow down. stopMotors() The final action when the measured value reaches the target.
**Exercise C approach** — `if remaining < 50 ticks: slow down`
`if remaining == 0: stop`
**Project 1 PID approach** — `correction = Kp * error + Ki * integral + Kd * derivative`
`turn_output = correction * TURN`
The Exercise C version had two output levels: full speed or slow speed. The PID version produces a continuous output, so a large error creates a large correction and a small error creates a small correction.

### The Project 1 PID Class
This class is defined at the top of `obj_track_advpid.py`.
PID classobj_track_advpid.py
```python
class PID:
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
```
self.kp , self.ki , self.kd These are the three tuning knobs. Exercise C used one threshold, 50 ticks. Project 1 separates the response into current error, accumulated error, and rate of change. dt : time since the previous update The integral and derivative terms only make sense when time is measured. The first call assumes 0.02 seconds, about 50 Hz. The max(..., 1e-4) guard prevents division by zero if two updates happen almost instantly. if dt > 2: self._integral = 0 If more than two seconds pass between updates (for example during startup or a long pause), old accumulated error is discarded so it cannot cause a lurch when tracking resumes. self._integral + error * dt This accumulates error over time. np.clip() prevents windup: the PID version of a robot continuing to push harder after it has been blocked for too long. derivative = (error - self._prev_error) / dt This measures whether the error is shrinking or growing. Exercise C could slow down near the target, but it could not tell whether the robot was already correcting quickly enough. output = kp * error + ki * integral + kd * derivative This is the PID equation translated into code. The result is one continuous correction value, not a binary full-speed-or-slow-speed decision. output_limit The output is clamped to [-output_limit, output_limit]. The main loop creates the PID with output_limit=1, so the correction is always between -1 and +1 before being scaled by TURN. reset() Project 1 does not call reset() during tracking. It is available to call from your own code if you want to clear accumulated state between sessions.

### How the PID Is Used in main()
PID creation and usemain()
```python
pid = PID(0.7, 0.1, 0.05, output_limit=1)

# inside the loop:
x = (x - wid / 2) / (wid / 2)   # normalize: -1 (far left) to +1 (far right)
power = pid.update(x) * TURN     # correction scaled to motor range
send_command(-power - SPEED, power - SPEED)
```
`pid` controls steering. Its error is the normalized horizontal position of the ball: -1.0 when the ball is at the left edge, 0.0 when centered, and +1.0 at the right edge. Its output is multiplied by `TURN` to produce a motor correction value.

Concept Exercise C Project 1 PID What is measured encoder ticks bounding-box center x What is the target targetTicks frame center (x = 0) What is the error targetTicks - ticksLeft (cx - frame_center) / half_width What happens at zero error stop motors keep adjusting gently around center Response type binary: go or stop continuous: always adjusting
**P: Proportional**
Current error. Big error produces a big correction. Too much `Kp` creates oscillation.
**I: Integral**
Accumulated old error. It corrects persistent offset but can cause windup.
**D: Derivative**
Error slope. It dampens overshoot by reacting when error changes quickly.

### Integral Windup
In Exercise C, if the robot could not reach the target because of wheel slip, it could keep trying forever. The PID equivalent is integral windup: if the robot cannot center the ball, the integral term grows until the robot lunges when the obstruction clears.
`max_integral=100.0` clamps the accumulated error so old failure does not turn into a dangerous future command. The `if dt > 2` guard also resets the integral after a long pause.

### Tuning Procedure
Phase 1: Turn only. Set SPEED = 0 so the robot cannot drive forward. Set kp = 0.5 , ki = 0 , kd = 0 . Hold the ball in front. Increase kp until the robot oscillates left and right, then reduce by about 40 percent. Add kd starting near 0.3 * kp to dampen overshoot. Phase 2: Add forward speed. Restore SPEED = 80 . Confirm the robot drives toward the ball while centering it. Reduce SPEED if approach is too aggressive. Phase 3: Add integral if needed. If the robot never quite centers (persistent offset), increase ki from 0 toward 0.1.
!!! tip "Goal of tuning"
    A tuned tracker turns smoothly toward the ball and approaches without oscillating left and right.

---

## Reading the Camera Stream


---

The stream functions in `obj_track_advpid.py` are the same pattern from Exercise B, reorganized into two functions: `open_stream()` opens the HTTP connection once, and `read_frame()` reads one JPEG frame from the running response.

### Exercise B Code You Already Wrote
Exercise B `detect_stream.py` core loopReference
```python
response = requests.get(url, stream=True, timeout=10)

buf = b""
for chunk in response.iter_content(1024):
    buf += chunk
    start = buf.find(b"\xff\xd8")
    end = buf.find(b"\xff\xd9")
    if start != -1 and end != -1:
        jpg = buf[start:end + 2]
        buf = buf[end + 2:]
        frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            ...
```

### Project 1 Code: Two Functions
open_stream() and read_frame()`obj_track_advpid.py`
```python
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
            buf = buf[-1:]
            continue

        end = buf.find(b"\xff\xd9", start + 2)
        if end == -1:
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
```
Concept Exercise B `detect_stream.py` Project 1 open_stream / read_frame Open HTTP connection requests.get(url, stream=True) Same call, now returns the response object. Read bytes response.iter_content(1024) Same pattern, chunk size raised to 4096. Find JPEG start buf.find(b"\xff\xd8") Same bytes. Find JPEG end buf.find(b"\xff\xd9") Now searches after start + 2 to avoid false matches inside the header. Decode frame cv2.imdecode(...) Identical. Guard for empty chunk Not present if not chunk: continue Skips empty keep-alive chunks. Partial JPEG handling Not explicit buf = buf[-1:] and buf = buf[start:] handle split markers correctly.

### What Changed and Why
The chunk size increased from 1024 to 4096. Larger chunks reduce the number of Python loop iterations per frame, which matters when YOLO detection also runs in the same loop. The JPEG end search now starts at `start + 2` instead of 0 to avoid misidentifying the two-byte JPEG SOI marker itself as the EOI marker. The `if len(jpg) <= 2` guard discards accidentally empty captures.

!!! info "Exercise B is the reference"
    If read_frame() feels unfamiliar, go back to PB.6 and compare the JPEG parsing lines. The logic is the same; Project 1 only makes the byte handling slightly more robust.

---

## Sending Commands (UDP)


---

The UDP command functions in `obj_track_advpid.py` are the same socket code from Exercise D, split into two named functions.

### Exercise D Code You Already Wrote
Exercise D `robot_control.py` senderReference
```python
cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_command(left, right):
    msg = f"MOTOR,{int(left)},{int(right)}"
    cmd_sock.sendto(msg.encode(), (ARDUINO_IP, CMD_PORT))

def send_stop():
    cmd_sock.sendto(b"STOP", (ARDUINO_IP, CMD_PORT))
```

### Project 1 Code: Identical Pattern
send_command() and send_stop()`obj_track_advpid.py`
```python
cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_command(left, right):
    msg = f"MOTOR,{int(left)},{int(right)}"
    cmd_sock.sendto(msg.encode(), (ARDUINO_IP, CMD_PORT))

def send_stop():
    cmd_sock.sendto(b"STOP", (ARDUINO_IP, CMD_PORT))
```
These are the same functions from Exercise D. Nothing changed. `cmd_sock` is a module-level UDP socket. `send_command` formats and sends a `MOTOR,left,right` packet. `send_stop` sends the stop packet.

### How Motor Values Are Computed
The main loop computes motor values like this:
Motor command computationmain()
```python
x = (best[0] + best[2]) / 2          # pixel center of bounding box
x = (x - wid / 2) / (wid / 2)        # normalize to -1 ... +1
power = pid.update(x) * TURN          # PID output scaled to turn range
send_command(-power - SPEED, power - SPEED)
```
`power` is positive when the ball is to the right. Subtracting `power` from the left motor and adding it to the right motor steers the robot toward the ball. `SPEED` is subtracted from both sides to produce forward motion. The negative sign on the left motor (`-power - SPEED`) reflects the physical wiring of one motor being mounted in reverse on the chassis.
!!! warning "Motor sign is chassis-specific"
    If your robot spins instead of moving forward on `send_command(100, 100)`, one motor is wired in reverse relative to the code. Adjust by removing or adding the negative sign on the left side: `send_command(power - SPEED, power - SPEED)` or `send_command(-power - SPEED, -power - SPEED)`. Test with Exercise D's keyboard script first.

---

## Finding the Target: findbest()


---

`findbest()` replaces the class-based detection from earlier in the project with one short function. The job is identical to what you wrote in Exercise A: run YOLO, look at every bounding box, and return the one with the largest area.

### The Function
findbest()`obj_track_advpid.py`
```python
def findbest(results):
    """Return the bounding box of the largest detected target, or None."""
    best = None
    best_area = 0

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best = (x1, y1, x2, y2)

    return best
```
box.xyxy[0] Gives the bounding box in pixel coordinates: top-left x, top-left y, bottom-right x, bottom-right y. This is the same format you used in Exercise A. area = (x2 - x1) * (y2 - y1) Width times height. A larger area means the object is physically closer to the camera. Selecting by largest area picks the most prominent detection and ignores smaller false positives in the background. Returns None when no boxes pass the confidence threshold so the main loop can decide to do nothing.

### Connection to Exercise A
In Exercise A you iterated over `results[0].boxes` to inspect detections. `findbest()` does the same iteration and applies the same `.xyxy` attribute you used then. The only addition is the area comparison to find the single best box.

Note that `findbest()` does not filter by class name. All detections that pass the `CONFIDENCE` threshold are candidates. If your scene has multiple objects and you only want to track one class, you can add a class-name check:
Optional class filterfindbest()
```python
if model.names[int(box.cls[0])] != "ball":
    continue
```

---

## The Main Loop


---

The `main()` function is the integration point. Every line traces back to a project you already completed.

### The Complete `main()` Function
main()`obj_track_advpid.py`
```python
def main():
    print("Loading model...")
    model = YOLO(MODEL_PATH)
    print("Model loaded.")

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

        results = model(frame, imgsz=416, conf=CONFIDENCE, verbose=False)

        best = findbest(results)
        if best is not None:
            wid = len(frame[0])
            x = (best[0] + best[2]) / 2
            x = (x - wid / 2) / (wid / 2)
            power = pid.update(x) * TURN
            send_command(-power - SPEED, power - SPEED)

        annotated = results[0].plot()

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

        cv2.imshow("Phone Stream - YOLO Detection", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.close()
    cv2.destroyAllWindows()
    print("Stopped.")
```
Line in main() Origin model = YOLO(MODEL_PATH) Exercise A YOLO model loading. stream = open_stream(STREAM_URL) Exercise B HTTP stream connection. pid = PID(...) Project 1 PID class. frame = read_frame(stream) Exercise B frame parsing. results = model(frame, ...) Exercise A detection call. best = findbest(results) Project 1 largest-box selection. send_command(-power - SPEED, power - SPEED) Exercise D UDP send. annotated = results[0].plot() Exercise A annotated display. cv2.imshow(...) Exercise A and B display pattern.

### Non-obvious Lines
`model = YOLO(MODEL_PATH)` is called once before the loop. Loading the model takes a few seconds, and doing it inside the loop would make the robot unusable. `stream = open_stream(STREAM_URL)` also connects once. If the stream drops, the loop exits because `read_frame()` will return `None` repeatedly. `pid = PID(0.7, 0.1, 0.05, output_limit=1)` creates a single PID for the turn axis. The initial gains are a reasonable starting point; use the tuning guide in the PID section to adjust them. `if best is not None` : when no detection meets the confidence threshold, the loop does nothing to the motors. The robot holds its last motor state. If you want the robot to stop when no target is visible, add `send_stop()` in the `else` branch. `results[0].plot()` draws YOLO's own bounding boxes and class labels on the frame. FPS is recalculated every second and drawn with `cv2.putText()`. `stream.close()` on exit tears down the HTTP connection cleanly. The UDP socket `cmd_sock` is module-level and closed automatically when the process ends.

### Frame-by-frame Walkthrough
Step 1: Read a frame. `read_frame(stream)` blocks until a complete JPEG arrives from the phone. The loop calls this at the speed of the phone camera. Step 2: Run detection. `model(frame, imgsz=416, conf=CONFIDENCE, verbose=False)` runs YOLO on the frame and returns detection results. Step 3: Find the best box. `findbest(results)` returns the largest bounding box or None. Step 4: Compute and send motor command. If a box was found, the horizontal center is normalized to -1...+1, the PID produces a turn correction, and `send_command()` sends the motor values over UDP. Step 5: Draw and display. YOLO's annotated frame is shown with FPS overlay. Step 6: Check for quit. `cv2.waitKey(1)` keeps the window responsive and exits when Q is pressed.

---

## Running and Testing


---

### Pre-run Hardware Checklist
Arduino is running the `robot_udp` sketch from Exercise D. Arduino Serial Monitor shows its IP address and Ready. Battery is connected and the shield jumper is set to BATT PWR . Phone stream is active and verified in a browser. Robot has at least 2 meters of clear floor space in all directions. Target object is nearby and visible to the phone camera.

### First Run Procedure
Stage 1: Detection only. Temporarily set SPEED = 0 . Run python `obj_track_advpid.py`. Hold the ball in front of the phone camera. Verify that YOLO draws a box around the ball and the FPS counter appears. Stage 2: Turn command check. Keep SPEED = 0 and watch the robot. Move the ball left and right. The robot should rotate toward whichever side the ball is on. If it rotates the wrong way, invert the sign in send_command() . Stage 3: First live run. Set SPEED = 80 for a slow first test. Place the ball about 60 cm in front of the phone. The robot should slowly orient toward and approach it. Stage 4: Tune and increase speed. Once basic tracking works, raise SPEED to 100 or 120. Use the PID tuning guide if the robot oscillates left and right.

### Common Failures and Fixes
Robot spins in circles constantly Likely cause: motor sign wrong Run `send_command(100, 100)` from Exercise D's keyboard test. If the robot spins instead of moving forward, adjust the sign in `send_command(-power - SPEED, power - SPEED)`. Robot does not move even when ball is visible Likely cause: wrong ARDUINO_IP or UDP path Ping the Arduino IP from the laptop. Rerun the Exercise D keyboard test to confirm UDP works. Robot does not detect the ball Likely cause: CONFIDENCE too high or wrong MODEL_PATH Lower CONFIDENCE to 0.1. Print `model.names` at startup to confirm the model loaded correctly. Robot oscillates left and right Likely cause: kp too high Reduce kp from 0.7 toward 0.4, then add kd to dampen overshoot. Robot tracks then drives past the ball Likely cause: SPEED too high, or no stop when ball is lost Reduce SPEED. Add `send_stop()` in the `else` branch when `best is None`.

### What Success Looks Like
Place the ball on the floor while the robot faces a different direction. Run the script. Within about two seconds the robot turns toward the ball and moves toward it. Move the ball a meter to the side and the robot pivots and approaches again. Remove the ball from view and the robot holds its last motor state until the stream ends or you press Q.
!!! tip "Closed-loop vision robot"
    You have combined a neural network you trained, streaming video from your phone, a PID controller, and UDP commands into one working physical system.

