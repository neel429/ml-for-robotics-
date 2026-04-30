# project_1_design.md
### Instruction document for coding agent
### Build the Project 1 lesson page for the ML for Robotics site

---

## OVERVIEW

Create a new file `project-1.html` (or a set of lessons accessible via 
`?lesson=proj1-*` in the SPA) that teaches the object tracking project 
contained in `obj_track_adv.py`.

The reference file `obj_track_adv.py` is already in the repository. 
The agent must read it and pull exact code snippets from it into the 
lesson pages — do not rewrite or paraphrase the code, show it verbatim.

This project does NOT use Google Colab. Everything runs locally on the 
student's machine using VS Code. Teach setup before any code.

The page must match the existing site design exactly — same sidebar 
navigation structure, same callout boxes, same code block style, same 
anatomy table pattern, same font and colors. Treat this as a new chapter 
in the existing SPA, added after the existing chapters in the sidebar.

---

## SIDEBAR ENTRY

Add a new collapsible chapter group to the sidebar:

```
★ Project 1: Object Tracker
   P1.0  What We Are Building
   P1.1  Setting Up VS Code
   P1.2  Installing Dependencies
   P1.3  Configuration: Tuning Your Robot
   P1.4  The PID Controller
   P1.5  Reading the Camera Stream
   P1.6  Sending Commands (UDP)
   P1.7  Receiving Telemetry
   P1.8  State Machine: How the Robot Thinks
   P1.9  The Tracker: Putting It Together
   P1.10 Visualisation and the HUD
   P1.11 The Main Loop
   P1.12 Running and Testing
```

Use the existing star (★) prefix style used for checkpoint exercises.
Chapter accent color for Project 1: #f97316 (orange).

---

## LESSON P1.0 — WHAT WE ARE BUILDING

**Purpose:** Orient the student. No code here. Just context, a diagram, 
and a system overview so they know what all the pieces are before 
touching anything.

### Content to include:

**Opening paragraph:**
This project is a real robot object tracker. A camera mounted on a 
phone streams live video over WiFi. A YOLO neural network runs on your 
laptop and detects a ball in each frame. Two PID controllers compute 
how fast each motor should spin to center the ball in frame and close 
the distance to it. Those motor commands are sent over UDP to an ESP 
microcontroller, which drives the wheels. Encoder feedback comes back 
the other way so you can see what the robot is actually doing.

**System diagram:**
Draw this as a styled HTML flow diagram (no images), matching the 
existing site's diagram style:

```
[Phone Camera]
     │  MJPEG over WiFi (HTTP)
     ▼
[Your Laptop — Python]
  ├─ YOLO detection
  ├─ PID turn controller
  ├─ PID distance controller
  └─ State machine
     │  Motor commands (UDP)
     ▼
[ESP Microcontroller]
  ├─ Left motor driver
  └─ Right motor driver
     │  Encoder ticks (UDP)
     └──────────────────────► back to laptop (Telemetry)
```

**What you will learn in this project:**
List these as a plain unordered list (no bullets, styled as the 
existing skill-pill or step list):
- How to stream and decode live video in Python using OpenCV
- How a PID controller works and how to tune its three parameters
- How UDP sockets send and receive data between devices on a network
- How a finite state machine makes a robot behave predictably
- How YOLO detects objects in real time and what the output looks like
- How to structure a real robotics codebase across multiple classes

**Hardware note callout (INFO box):**
"This lesson covers the software only. The ESP microcontroller, motor 
drivers, and physical robot are introduced in a separate hardware chapter. 
You can follow P1.0 through P1.12 and run the code in simulation mode 
without any hardware connected."

---

## LESSON P1.1 — SETTING UP VS CODE

**Purpose:** Get the student from zero to a working Python environment 
in VS Code. Assume they have never used VS Code before.

### Content to include:

**Step 1 — Download and install VS Code**
Direct them to code.visualstudio.com. 
Mention: available for Windows, macOS, and Linux. Free.

**Step 2 — Install the Python extension**
Once VS Code opens:
- Click the Extensions icon in the left sidebar (looks like four squares)
- Search for "Python"
- Install the one published by Microsoft (first result, millions of downloads)

**Step 3 — Install Python itself**
Direct them to python.org/downloads.
Tell them to download Python 3.10 or 3.11 (not 3.12+ — some packages 
lag behind).
On Windows: tick "Add Python to PATH" during installation — 
this is the single most common mistake.

Add a WARNING callout:
"If you skip 'Add Python to PATH' on Windows, every command in the 
terminal will say 'python is not recognized'. If this happens, 
re-run the installer and tick that box."

**Step 4 — Open a terminal in VS Code**
Menu → Terminal → New Terminal.
A panel opens at the bottom. This is where all commands are typed.

**Step 5 — Verify Python works**
Tell the student to type in the terminal:
```
python --version
```
They should see something like `Python 3.11.x`.
On macOS/Linux they may need `python3 --version`.

Add a TIP callout:
"VS Code shows the selected Python interpreter in the bottom status bar. 
Click it to switch between versions if you have more than one installed."

**Step 6 — Create a project folder**
Tell them to create a folder called `object-tracker` anywhere on their 
machine, then open it in VS Code: File → Open Folder.

**Step 7 — Copy the project file**
Tell them to place `obj_track_adv.py` and `best.pt` (the YOLO weights 
file) into that folder. Both files will be provided separately.

---

## LESSON P1.2 — INSTALLING DEPENDENCIES

**Purpose:** Teach pip, virtual environments, and get all packages installed.

### Content to include:

**What is pip?**
Short prose explanation: pip is Python's package manager. It downloads 
and installs libraries from the internet. You run it in the terminal.

**What is a virtual environment?**
Short prose explanation: a virtual environment is an isolated copy of 
Python just for this project. Packages you install here don't affect 
other projects on your machine. It is best practice to always use one.

**Step 1 — Create a virtual environment**
In the VS Code terminal, with the project folder open:
```
python -m venv venv
```
This creates a folder called `venv` inside your project folder.

**Step 2 — Activate it**

Show all three OS variants:

Windows:
```
venv\Scripts\activate
```

macOS / Linux:
```
source venv/bin/activate
```

After activation the terminal prompt starts with `(venv)`.

**Step 3 — Install all packages**
Tell the student to run:
```
pip install opencv-python numpy requests ultralytics
```

Then explain what each package does — use a simple table:

| Package | What it does in this project |
|---------|------------------------------|
| opencv-python | Reads the camera stream, draws the HUD overlay, shows the video window |
| numpy | Fast math arrays — used inside the PID controller and YOLO output processing |
| requests | Makes the HTTP connection to the phone camera stream |
| ultralytics | The YOLO library — loads best.pt and runs object detection |

**Installation time callout (INFO):**
"ultralytics will download PyTorch as a dependency. This is a large 
download (~800 MB). Let it finish — it only happens once."

**Step 4 — Verify imports**
Tell the student to create a new file `test_imports.py` and paste:

Pull this exact block from obj_track_adv.py lines 1-7 (the import block 
at the top of the file). Show it verbatim in a non-runnable code block.

Then run:
```
python test_imports.py
```
If no errors appear, everything is installed correctly.

---

## LESSON P1.3 — CONFIGURATION: TUNING YOUR ROBOT

**Purpose:** Teach the configuration constants block before any class 
or logic. Students need to understand what these numbers mean and that 
they will need to change them for their specific hardware.

### Content to include:

**Opening:**
Before any code runs, the file declares a set of constants at the top. 
These are the numbers you will adjust most often when tuning the robot. 
Understanding each one now saves a lot of confusion later.

**Show the full CONFIGURATION block from obj_track_adv.py verbatim.**
Reference: everything under the `# CONFIGURATION` comment heading down 
to the `# CONTROLLERS` heading. Show it in a display-only code block 
(not runnable).

**Then explain each group with an anatomy table:**

Group 1 — Network:
| Constant | What it means |
|----------|---------------|
| ESP_IP | The IP address of your ESP microcontroller on your WiFi network. You will find this in the ESP's serial output when it boots. |
| UDP_CMD_PORT | The port number the ESP listens on for motor commands. Must match what is programmed in the ESP firmware. |
| UDP_TELEM_PORT | The port the laptop listens on for encoder data coming back from the ESP. |

Group 2 — Vision:
| Constant | What it means |
|----------|---------------|
| TARGET_OBJECT | The class name YOLO looks for. Must exactly match a label in your YOLO model. "ball" works with the provided best.pt. |
| TARGET_AREA | The pixel area the bounding box should be when the robot is at the correct distance. Larger = robot gets closer. Tune this for your arena. |

Group 3 — PID gains:
Explain what Kp, Ki, Kd mean in plain language before showing the table:
"These three numbers control how aggressively the robot reacts. Kp is 
the main response — higher means faster reaction but more oscillation. 
Ki corrects steady-state error that Kp alone can't fix. Kd dampens 
overshooting. Both PIDs in this project start with Ki=0 — tune Kp and 
Kd first."

Group 4 — Motion limits:
Explain MAX_SPEED, MIN_SPEED, MAX_TURN, MAX_ACCEL with the anatomy table.
Highlight MAX_ACCEL specifically — explain that without it the motors 
would jump from 0 to full speed instantly which can tip the robot.

Group 5 — Dead zones:
Explain ANGLE_DEAD_ZONE and AREA_DEAD_ZONE. Use a robotics callout:
"Dead zones prevent the robot from twitching when the ball is nearly 
centered. If the error is smaller than the dead zone, the controller 
treats it as zero. Without this, small camera wobbles cause constant 
micro-corrections."

---

## LESSON P1.4 — THE PID CONTROLLER

**Purpose:** Teach PID as a concept first, then show the implementation.

### Content to include:

**Concept section — what is a PID controller?**
Write this as a genuinely clear explanation for an ME freshman. Use the 
classic thermostat analogy but then bring it to robotics:

A PID controller has one job: reduce error to zero. Error is the 
difference between where you are and where you want to be. In this 
project there are two errors: how far the ball is from the center of 
the frame (angle error) and how far the robot is from the ball (distance 
error).

The three terms:
- P (Proportional): output is proportional to current error. Big error = 
  big correction. Responds immediately but overshoots.
- I (Integral): output is proportional to accumulated error over time. 
  Fixes the case where P alone leaves a small permanent offset.
- D (Derivative): output is proportional to how fast the error is 
  changing. Dampens overshooting — it "sees" that the error is shrinking 
  fast and backs off.

Show a simple diagram (HTML/CSS, no image) of the PID loop:
```
setpoint ──► [Σ error] ──► [P + I + D] ──► output ──► system ──► measurement
                 ▲                                                      │
                 └──────────────────────────────────────────────────────┘
```

**Then show the PID class from obj_track_adv.py verbatim.**
Reference: the entire `class PID` block including `__init__`, `update`, 
and `reset`. Show in a display-only code block.

**Anatomy table for the `update` method — explain every line:**
Key lines to annotate:
- `dt = 0.02 if self._prev_time is None` — why 0.02 as the default dt
- `self._integral = np.clip(...)` — why the integral is clamped 
  (integral windup explanation)
- `derivative = (error - self._prev_error) / dt` — this is just the 
  slope of the error signal
- `output = self.kp * error + self.ki * self._integral + self.kd * derivative`
  — this is the full PID equation, annotate each term

**Add the PID equation displayed clearly:**
```
output = Kp × error  +  Ki × ∫error dt  +  Kd × d(error)/dt
```
Label each term underneath: Proportional / Integral / Derivative

**Tuning guide callout (ROBOTICS box):**
"Start with Ki=0 and Kd=0. Increase Kp until the robot oscillates, 
then back off by 30%. Then add Kd to dampen the oscillation. 
Only add Ki if there is a consistent offset the robot can't correct."

---

## LESSON P1.5 — READING THE CAMERA STREAM

**Purpose:** Teach networking (HTTP MJPEG streaming), threading, and 
OpenCV image decoding.

### Content to include:

**Concept: What is MJPEG streaming?**
The phone camera app (e.g. IP Webcam on Android) serves a continuous 
stream of JPEG images over HTTP — like a video made of individual 
photos sent one after another. The laptop connects as an HTTP client 
and reads the stream byte by byte, finding JPEG markers to extract 
each frame.

**Concept: Why a background thread?**
If we waited for each frame in the main loop, the robot would pause 
every time the network was slow. The background thread runs independently 
and always has the latest frame ready. The main loop just grabs whatever 
is there.

**Show the full `MobileVideoStream` class from obj_track_adv.py verbatim.**
Reference: entire `class MobileVideoStream` block.

**Anatomy table — key lines to explain:**
- `threading.Thread(target=self._run, daemon=True).start()` — daemon 
  thread means it dies automatically when the main program exits
- `response.iter_content(1024)` — reads 1024 bytes at a time from the stream
- `buf.find(b"\xff\xd8")` and `buf.find(b"\xff\xd9")` — these are the 
  JPEG start and end markers. Every JPEG file on earth starts with 
  FF D8 and ends with FF D9.
- `cv2.imdecode(np.frombuffer(...))` — converts raw bytes into a NumPy 
  array that OpenCV can work with
- `with self._lock:` — a lock prevents the main thread and the stream 
  thread from reading/writing the frame at the same time (race condition)
- `backoff = min(backoff * 2, 8.0)` — exponential backoff: wait 1s, 
  then 2s, then 4s, then cap at 8s between reconnect attempts

**INFO callout:**
"You can test the stream independently. Open a browser and go to 
http://[phone-ip]:8080/video — if you see live video, the stream works 
and Python will be able to read it."

---

## LESSON P1.6 — SENDING COMMANDS (UDP)

**Purpose:** Teach UDP sockets and the motor command protocol.

### Content to include:

**Concept: TCP vs UDP — why UDP for motor commands?**
TCP guarantees delivery and order — good for files, bad for real-time 
control. If a motor command packet is lost, you don't want Python to 
pause and wait for a retry. You just send the next command. UDP fires 
and forgets, which is exactly what real-time robot control needs. 
A slightly stale command is better than a delayed one.

**Show the full `Commander` class from obj_track_adv.py verbatim.**

**Anatomy table:**
- `socket.AF_INET, socket.SOCK_DGRAM` — AF_INET means IPv4, SOCK_DGRAM 
  means UDP (as opposed to SOCK_STREAM which would be TCP)
- `f"MOTOR,{int(left)},{int(right)},{light.upper()}"` — this is the 
  protocol. The ESP firmware expects exactly this comma-separated format.
- `self._sock.sendto(msg.encode(), (self.ip, self.port))` — encodes 
  the string to bytes and sends it to the ESP's IP and port

**Protocol callout (INFO):**
"The ESP firmware listens for packets starting with 'MOTOR,' followed 
by three comma-separated values: left speed, right speed, and light 
state. Sending anything else will be ignored by the firmware. 
The 'STOP,OFF' packet is a special command that cuts all motor power."

---

## LESSON P1.7 — RECEIVING TELEMETRY

**Purpose:** Teach the other direction — reading data FROM the robot.

### Content to include:

**Concept: Why telemetry?**
Sending commands is only half the picture. The encoder ticks coming 
back from the ESP tell you what the wheels are actually doing — not 
just what you asked them to do. This is how you would eventually detect 
wheel slip, stalls, or asymmetry between left and right motors.

**Show the full `Telemetry` class from obj_track_adv.py verbatim.**

**Anatomy table — key lines:**
- `self._sock.bind(("", port))` — bind to all interfaces on this port. 
  The empty string means "any IP on this machine". The ESP sends packets 
  to this port.
- `self._sock.settimeout(1.0)` — if no packet arrives within 1 second, 
  the recv call gives up instead of hanging forever
- `parts[0] == "ENC" and len(parts) == 5` — validates the packet 
  format before reading values. Always validate before parsing.
- The `read()` method returns a copy of the data under the lock — same 
  thread-safety pattern as MobileVideoStream

**Compare to Commander (callout):**
"Commander sends TO the ESP. Telemetry receives FROM the ESP. 
Commander uses sendto() — no binding needed. Telemetry uses bind() 
then recvfrom() — it declares 'I am listening on this port'."

---

## LESSON P1.8 — STATE MACHINE: HOW THE ROBOT THINKS

**Purpose:** Teach finite state machines as a concept and show how 
this one works.

### Content to include:

**Concept: What is a finite state machine?**
A state machine is a way of organizing behavior into distinct modes. 
At any moment the robot is in exactly one state, and events cause 
transitions between states. Without a state machine, behavior becomes 
a mess of if-statements that interact in unpredictable ways.

**Show the `RobotState` class (4 lines) verbatim, then draw the 
state diagram as HTML/CSS:**

```
         ball found              ball found (5 frames)
STOPPED ──────────► ACQUIRING ─────────────────────► TRACKING
   ▲                    │                                │
   │    timeout         │ ball lost                      │ ball lost
   │    exceeded        ▼                                ▼
   └──────────────── SEARCHING ◄───────────────────────── 
```

**For each state, write a short paragraph explaining:**

STOPPED: No ball has been seen recently. Motors are off. The robot 
does nothing until the vision system finds a target.

SEARCHING: The ball was visible but just disappeared. The robot 
spins slowly in the last known direction for up to LOST_TIMEOUT 
seconds hoping to reacquire it. If it succeeds, it goes to ACQUIRING. 
If time runs out, it goes to STOPPED.

ACQUIRING: The ball was just found. The robot moves at reduced speed 
(40%) for ACQUIRE_FRAMES frames to confirm this is a real detection 
and not a false positive before committing to full tracking.

TRACKING: The ball has been confirmed. Both PID controllers run at 
full authority. Speed limit is 100%.

**Show the `_update_state` method from the Tracker class verbatim.**

**Anatomy table for `_update_state`:**
Annotate the speed_limit ramp during ACQUIRING, the LOST_TIMEOUT check, 
and why reset() is called on both PIDs when entering STOPPED 
(to clear accumulated integral).

---

## LESSON P1.9 — THE TRACKER: PUTTING IT TOGETHER

**Purpose:** Show how detection, state machine, and PID combine.

### Content to include:

**Overview:**
The Tracker class is the brain. It owns the YOLO model, both PIDs, 
the state machine, and the control logic. Its `control()` method is 
called once per frame and returns two numbers: left motor speed and 
right motor speed.

**Sub-section: Detection (`_detect` method)**
Show the `_detect` method verbatim.
Explain:
- `imgsz=320` — runs YOLO at 320×320 resolution for speed. Higher 
  resolution is more accurate but slower.
- `conf=0.60` — only accept detections where YOLO is at least 60% 
  confident. Lower = more detections but more false positives.
- Why the method returns only the LARGEST bounding box — if two balls 
  are in frame, track the bigger (closer) one.

**Sub-section: Motor output (`_motor_outputs_for_ball` method)**
Show the method verbatim.
Annotate:
- `raw_angle_error = (cx - frame_width / 2) / frame_width` — 
  normalises the horizontal position to the range [-0.5, +0.5]. 
  Zero means ball is centered. Positive means ball is right of center.
- Why the scale step exists (`if max_raw > MAX_SPEED`) — this preserves 
  the turn ratio. Without it, clipping one side would straighten the 
  robot's path unintentionally.
- `base_speed = 10` — the robot always has a small forward speed when 
  tracking. It never just spins in place during tracking.

**Sub-section: The `control()` method**
Show verbatim. 
Annotate:
- `ramp(self.cur_left, tgt_left, MAX_ACCEL)` — acceleration limiting. 
  Without this, speed changes are instantaneous which can flip the robot.
- The three branches (bbox found / searching / stopped) and what motor 
  values each produces.

---

## LESSON P1.10 — VISUALISATION AND THE HUD

**Purpose:** Teach OpenCV drawing functions and explain the overlay.

### Content to include:

**Show the full `draw_overlay` function verbatim.**

**Explain each visual element with its corresponding code line:**

Use a two-part structure: screenshot description of what appears on 
screen, then the exact code line that draws it.

Elements to explain:
- `cv2.line(...w//2...)` — the green vertical centerline. Shows where 
  the ball needs to be.
- The cyan smoothed-angle line — shows the current angle error after 
  smoothing, not the raw value.
- The bounding box color coding: green = correct distance, red = too 
  close, blue = too far. Show the three conditions from the code.
- `cv2.rectangle` and `cv2.circle` — basic OpenCV drawing functions. 
  Explain the coordinate system (origin top-left, x right, y down).
- The HUD text lines — show the `lines` list and explain each metric.
- `cv2.putText` parameters — font, position, scale, color, thickness.

**INFO callout:**
"Everything drawn by draw_overlay is rendered on a copy of the frame 
in memory and never sent to the robot. It is purely for the developer 
watching the laptop screen."

---

## LESSON P1.11 — THE MAIN LOOP

**Purpose:** Show how all components connect in `main()`.

### Content to include:

**Show the full `main()` function verbatim.**

**Walk through it in numbered steps matching the code structure:**

Step 1 — Initialization: MobileVideoStream, Commander, Telemetry 
are all created here. Explain why Telemetry starts before the camera 
(so no encoder packets are missed).

Step 2 — Camera wait loop: the `for _ in range(30)` loop polls 
`video.connected` every 0.5 seconds for up to 15 seconds. 
Explain why: the camera app takes a few seconds to start streaming.

Step 3 — CMD_INTERVAL timing: explain why `now - last_cmd_time >= CMD_INTERVAL` 
rather than sending a command every frame. The camera may run at 30 fps 
but the ESP only needs commands at ~33Hz (0.03s interval). Decoupling 
them prevents flooding the ESP.

Step 4 — FPS counter: explain the 30-frame rolling FPS calculation.

Step 5 — Keyboard controls: Q / R / F / S — what each does and why 
SMOOTH_RATE is adjustable at runtime.

Step 6 — Shutdown sequence: commander.stop() sends a final STOP packet, 
then video and telemetry threads are stopped. Explain why order matters — 
stop sending commands before tearing down networking.

---

## LESSON P1.12 — RUNNING AND TESTING

**Purpose:** End-to-end checklist for the first run. No new code.

### Content to include:

**Pre-flight checklist (render as a styled interactive checklist 
where boxes can be ticked — store state in localStorage):**

□ Python 3.10 or 3.11 is installed and `python --version` works
□ Virtual environment is activated (terminal shows `(venv)`)
□ All packages installed without errors
□ `best.pt` is in the same folder as `obj_track_adv.py`
□ Phone camera app is running and the stream URL is reachable in a browser
□ `mobile_ip` at the bottom of `main()` is updated to your phone's IP
□ `ESP_IP` in the configuration block is updated to your ESP's IP
□ (Optional, no hardware) ESP_IP can be left as-is — Commander will 
  fail silently if nothing is listening

**How to run:**
```
python obj_track_adv.py
```

**What to expect on first run (describe the sequence):**
1. "Loading YOLO model..." appears — takes 3-10 seconds
2. "Using CUDA" or "Using CPU" — CUDA means your GPU is available 
   (faster). CPU works fine for testing.
3. "Waiting for camera..." with dots
4. A window opens showing the camera feed with the HUD overlay
5. STATE shows STOPPED until a ball is visible
6. Hold a ball in front of the camera — STATE should change to 
   ACQUIRING then TRACKING

**Common problems table:**

| Error | Likely cause | Fix |
|-------|--------------|-----|
| `ModuleNotFoundError: ultralytics` | packages not installed or wrong venv | activate venv and run pip install again |
| `Could not connect to camera` | wrong IP or camera app not running | check IP, reopen camera app |
| `python is not recognized` (Windows) | PATH not set | reinstall Python with "Add to PATH" ticked |
| Window opens but no detection | wrong TARGET_OBJECT name or low confidence | check model's class names, try lowering conf to 0.40 |
| Robot turns wrong direction | motor wiring reversed | negate left_speed or right_speed in the commander.motors() call |

**ROBOTICS callout at the end:**
"You have just run a real-time closed-loop vision system. The camera, 
the neural network, the two PID controllers, the state machine, and the 
networking are all running simultaneously. This is the same architecture 
used in professional mobile robot platforms — just at a smaller scale."

---

## TECHNICAL NOTES FOR THE AGENT

- All code blocks in this project are DISPLAY ONLY (not runnable in 
  the browser) because this code requires a local Python environment, 
  a camera, and hardware. Do not add data-runnable="true" to any block.
  Instead, add a "Run locally" badge (styled differently from the 
  Colab badge — use a VS Code purple color: #007acc).

- Every code block must reference the exact line range from 
  obj_track_adv.py in a comment above the block, e.g.:
  `<!-- obj_track_adv.py lines 18-45 -->`
  This makes future updates easy — when the .py file changes, 
  the agent knows exactly which HTML block to update.

- The anatomy tables, callout boxes, and step-numbered layouts must 
  use the exact same CSS classes already defined in style.css from 
  the improvements-ch1.md spec. No new component types.

- Lesson completion tracking (Mark as Complete + localStorage) must 
  work the same as all other lessons.

- Prev/Next navigation at the bottom of each lesson must chain through 
  P1.0 → P1.1 → ... → P1.12 in order.
  
INFO callout — "No GPU? No problem":

The code automatically detects whether a GPU is available and falls 
back to CPU if not. Most student laptops will run on CPU.

Expected performance:
- With dedicated GPU (NVIDIA):  25-60 fps
- CPU only (modern laptop):     5-15 fps  ← still works

If tracking feels too slow on CPU, open obj_track_adv.py and find 
the line:
  self.model = YOLO(model_path)
Change it to load the nano model instead:
  self.model = YOLO("yolov8n.pt")
Ultralytics will download it automatically on first run. 
Nano is 6x faster than the default medium model at a small 
accuracy cost — for a bright colored ball in a clean background 
it is more than sufficient.

Apple Silicon Macs (M1/M2/M3): you automatically get GPU acceleration 
through Metal. The code handles this — "Using CPU" will print but 
PyTorch internally uses the GPU cores. Performance will be excellent.
---

*End of project_1_design.md*
