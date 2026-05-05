# project_A_design.md
### Instruction document for coding agent
### Build Project A: "Train Your First Object Detector"
### This is the prerequisite project that must be completed before Project 1

---

## OVERVIEW

Create a new set of lessons accessible via `?lesson=projA-*` in the SPA.
Add it to the sidebar BEFORE Project 1, labeled clearly as a prerequisite.

This project teaches the student to:
1. Understand what YOLO is and how object detection works
2. Collect their own image data using Roboflow
3. Label that data with bounding boxes
4. Train a YOLO26n model in Google Colab
5. Read and understand the training metrics
6. Run inference on their own webcam locally using VS Code

By the end they have a working `best.pt` file they trained themselves
from data they collected themselves. This is the file used in Project 1.

**Model choice throughout this project: YOLO26n (nano)**
YOLO26 is the latest Ultralytics model, purpose-built for edge and
low-power devices. The nano variant is the smallest and fastest.
It runs well on CPU-only laptops and still achieves strong accuracy
on simple single-class detection tasks like tracking a ball or mug.
Reference: https://docs.ultralytics.com/models/yolo26/

---

## SIDEBAR ENTRY

Add this group to the sidebar ABOVE the existing Project 1 group:

```
★ Project A: Train Your First Detector    ← prerequisite badge style
   PA.0  What is Object Detection?
   PA.1  Introducing YOLO26
   PA.2  Setting Up VS Code & Dependencies
   PA.3  Collecting Your Data with Roboflow
   PA.4  Labeling Your Images
   PA.5  Exporting the Dataset
   PA.6  Training in Google Colab
   PA.7  Reading the Training Results
   PA.8  Running Inference Locally
   PA.9  Understanding the Model Output
   PA.10 Preparing for Project 1
```

Chapter accent color: #10b981 (emerald green — distinct from Project 1's orange).

Add a banner at the top of the Project 1 sidebar group that says:
"Complete Project A first — it produces the best.pt file used here."
Style it as a small amber warning chip, not a full callout box.

---

## LESSON PA.0 — WHAT IS OBJECT DETECTION?

**Purpose:** Establish the concept clearly before any tools are introduced.
A student who doesn't understand what a model is trying to do will
not understand why any of the steps matter.

### Content:

**Opening — three kinds of "seeing":**

Write this as three definition cards side by side (or stacked on mobile),
using the existing definition-card component:

Card 1 — Image Classification:
"Given an image, output one label. Is this a cat or a dog?
The model looks at the whole image and gives one answer."

Card 2 — Object Detection:
"Given an image, find every instance of target objects and draw a
box around each one. Output: a list of boxes, each with a class name
and a confidence score. This is what YOLO does."

Card 3 — Instance Segmentation:
"Like detection but instead of a box, draw the exact pixel outline
of each object. More precise, much slower."

Then a ROBOTICS callout:
"For robot tracking, detection is the right choice. You need to know
WHERE the object is (bounding box center) and how big it appears
(box area = proxy for distance). Classification alone can't give you
position. Segmentation is overkill and too slow for real-time control."

**What a bounding box actually is:**

Explain that every detection is a rectangle defined by four numbers.
Show two coordinate formats because students will see both:

Format 1 — xyxy (corner format):
[x_top_left, y_top_left, x_bottom_right, y_bottom_right]
Example: [120, 45, 380, 290]

Format 2 — xywh (center format, used in YOLO training labels):
[x_center, y_center, width, height] — all normalized 0 to 1
Example: [0.5, 0.3, 0.18, 0.24]

Draw a simple HTML/CSS diagram of a frame with a box inside it,
labeled with both formats on the same image so students see the
relationship visually.

**What a confidence score is:**

Explain that every detection also comes with a number from 0 to 1.
YOLO produces many candidate boxes and the confidence score is how
sure the model is that this box contains the target object.
Boxes below the threshold (default 0.5) are discarded.

Show this visually as a slider diagram: 0.0 → lots of false positives,
1.0 → only the most obvious detections pass, 0.5-0.6 is the sweet spot.

---

## LESSON PA.1 — INTRODUCING YOLO26

**Purpose:** Explain YOLO conceptually and specifically why YOLO26n is
the right choice for this course. Students should understand what they
are using, not just copy-paste model names.

### Content:

**What is YOLO?**

YOLO stands for You Only Look Once. Before YOLO, object detection
systems looked at a frame multiple times using a sliding window —
slow and computationally expensive. YOLO processes the whole image
in a single forward pass through the network and produces all
detections at once. That is why it is fast enough for real-time use.

**The YOLO family — brief history (keep this short, 1 paragraph):**
YOLO has been through many versions — v1 through v8, then v9, v10,
v11, and now YOLO26. Each generation improved speed and accuracy.
YOLO26 is the latest as of 2026 and is specifically designed for
edge devices — meaning low-power hardware like a laptop CPU or a
small microcontroller.

**Why YOLO26 nano specifically:**

Show this as a comparison table (display only, not interactive):

| Model | Size | Speed (CPU) | Good for |
|-------|------|-------------|----------|
| yolo26n | 3.5 MB | Very fast | This course ✓ |
| yolo26s | 11 MB | Fast | When nano isn't accurate enough |
| yolo26m | 30 MB | Medium | Good GPU available |
| yolo26l | 59 MB | Slow on CPU | Server/cloud deployment |

Add a TIP callout:
"For a simple task like detecting one object type against a clear
background — a ball, a mug, a cone — nano is genuinely enough.
The limitation of a small model is not usually accuracy on simple
tasks. It is accuracy on crowded, complex scenes. Your use case
is neither of those."

**What end-to-end means (YOLO26 specific):**

Older YOLO versions needed a post-processing step called Non-Maximum
Suppression (NMS) to remove duplicate boxes. YOLO26 eliminates this
step — it produces one clean prediction per object directly.
In practice this means: slightly faster inference, slightly simpler
code, and easier deployment on hardware with no post-processing support.

**ROBOTICS callout:**
"YOLO26 was specifically designed for edge deployment — the same
category as microcontrollers and embedded systems that power real
robots. Learning it now means the skills transfer directly to
deploying ML on physical hardware later."

---

## LESSON PA.2 — SETTING UP VS CODE & DEPENDENCIES

**Purpose:** Same setup as Project 1's P1.1 and P1.2 but condensed,
since Project A comes first and Project 1 will reference back to this.

### Content:

If the student already completed P1.1 and P1.2, add a callout at the
top: "Already set up VS Code from Project 1? Skip to PA.3."

Otherwise, include the full setup:

**VS Code install** — same as P1.1 steps 1-6.

**Create a new project folder** called `my-detector` (separate from
the object tracker folder).

**Create and activate a virtual environment** — same as P1.2 steps 1-2.

**Install dependencies for Project A:**

```
pip install ultralytics roboflow opencv-python
```

Explain each:

| Package | Role in this project |
|---------|---------------------|
| ultralytics | Loads YOLO26, runs training, runs inference |
| roboflow | Downloads your labeled dataset from Roboflow in the right format |
| opencv-python | Opens your webcam and displays the detection results |

**Verify installation:**

Tell the student to create `test_setup.py` and type:
```python
from ultralytics import YOLO
import cv2
import roboflow
print("All good!")
```
Run it. If "All good!" prints, setup is complete.

**Download YOLO26n weights:**

Create `download_model.py`:
```python
from ultralytics import YOLO
model = YOLO("yolo26n.pt")  # downloads automatically on first run
print(f"Model loaded. Parameters: {sum(p.numel() for p in model.model.parameters()):,}")
```
Run it. Ultralytics will download `yolo26n.pt` (~3.5 MB) automatically.
The parameter count will print — explain what a parameter is:
each number the model learned during its original training on COCO dataset.

**INFO callout — what is COCO?**
"YOLO26n comes pre-trained on COCO — a dataset of 118,000 images
covering 80 common object categories (people, cars, chairs, animals etc.).
We will fine-tune this pre-trained model on your custom data.
Fine-tuning means: keep most of what it already learned, adapt the
last layers to recognize your specific object. This is why you only
need 100-150 images instead of 100,000."

---

## LESSON PA.3 — COLLECTING YOUR DATA WITH ROBOFLOW

**Purpose:** Teach the student how to gather good training images.
Data quality is more important than model architecture — emphasize this.

### Content:

**Step 1 — Create a free Roboflow account**
Go to roboflow.com. Sign up. Free tier is sufficient for this project.

**Step 2 — Create a new project**
- Click "Create New Project"
- Project type: Object Detection
- Give it a name matching your target object (e.g. "tennis-ball-detector")
- Annotation group: your class name, lowercase, no spaces (e.g. "ball")

**Step 3 — Decide what to detect**

Before collecting images, decide on one object. Guidelines:

GOOD choices for this project:
- A brightly colored ball (tennis ball, orange ball, colored ping-pong ball)
- A specific mug or water bottle you own
- A toy or object with a distinctive shape/color
- A colored cone or marker

AVOID for first project:
- Human faces (too complex, ethical considerations)
- Multiple similar-looking objects
- Anything that changes shape significantly (cloth, paper)

ROBOTICS callout:
"The ball is the classic choice for a reason. It is roughly spherical
so every angle looks similar — the model doesn't need to learn many
different poses. It often has a distinctive color that separates it
from backgrounds. These properties mean you need fewer images."

**Step 4 — How to capture images**

Target: 150 images minimum, 300 is better.

Capture from multiple:
- Distances (close, medium, far)
- Angles (straight on, from left, from right, from above)
- Backgrounds (different rooms, floors, surfaces)
- Lighting conditions (bright room, dim room, window light)
- Partial occlusion (half the object behind something)

WARNING callout:
"The single biggest mistake beginners make is collecting all images
in one location with one background. The model will learn the
background as part of the object and fail completely in a new room.
Vary your backgrounds deliberately."

**Step 5 — Upload images to Roboflow**
Drag and drop images into your Roboflow project, or use the
Roboflow mobile app to capture directly to the project.

---

## LESSON PA.4 — LABELING YOUR IMAGES

**Purpose:** Teach bounding box annotation. This is the most time-consuming
part. Set expectations and teach good labeling habits.

### Content:

**What labeling means:**
For every image, you draw a rectangle tightly around every instance
of your object. Roboflow's web annotation tool is a simple drag-to-draw
interface.

**Step-by-step in Roboflow:**
1. Open your project → click "Annotate"
2. Click the first image
3. Press B (or click the box tool)
4. Click and drag to draw a rectangle around your object
5. Type the class name (it will autocomplete after the first time)
6. Press Enter to confirm
7. Press the right arrow key to go to the next image

**Good labeling rules — explain each with a why:**

Rule 1: Draw the box tightly around the object.
Why: loose boxes include background pixels that confuse the model.

Rule 2: Label every instance in the image, not just the prominent one.
Why: if you miss an instance, the model is punished during training
for detecting something you left unlabeled. This is called a false
negative in the loss function.

Rule 3: If the object is less than 20% visible, skip it.
Why: a heavily occluded object provides little useful signal and
the inconsistency hurts more than the extra data helps.

Rule 4: Be consistent with box tightness throughout your dataset.
Why: inconsistent labels create noise that reduces final accuracy.

**Time estimate callout (INFO):**
"Labeling 150 images takes roughly 30-45 minutes if your object
appears once per image. Put on a podcast. It is repetitive but
there is no shortcut — label quality is the ceiling on model quality."

**Roboflow auto-label feature (mention but don't rely on):**
Roboflow has an AI auto-labeling feature. It works well once you
have a few dozen manually labeled images to seed it. For the first
50 images, label manually. Then try auto-label and correct its
mistakes for the rest. This hybrid approach is what professionals use.

---

## LESSON PA.5 — EXPORTING THE DATASET

**Purpose:** Explain train/val/test splits, augmentation, and how to
get the dataset into the format YOLO26 expects.

### Content:

**Train / validation / test split:**

Explain with a clear analogy:
- Training set: the practice problems you study from
- Validation set: the practice exam you check yourself with during studying
- Test set: the final exam, only looked at once at the very end

Standard split for small datasets: 80% train / 15% validation / 5% test.
Roboflow handles this automatically.

Show a simple visual: 150 images → 120 train / 22 val / 8 test.

**Augmentation:**

Explain what augmentation is: artificially increasing your dataset
size by applying random transformations to existing images.
Each transformation teaches the model to be robust to that variation.

In Roboflow, enable these augmentations (and explain each):
- Flip horizontal: the model learns the object looks the same mirrored
- Rotation ±15°: handles camera tilt
- Brightness ±25%: handles different lighting
- Blur up to 1.5px: handles slight focus issues

WARNING callout:
"Do not enable too many augmentations on a small dataset. Each
augmentation multiplies your dataset size, which sounds good,
but if the augmentations are too extreme (e.g. 90° rotation of a
ball on a floor) the model learns impossible scenarios."

**Exporting in YOLOv8 format:**

In Roboflow:
1. Click "Generate" to create a dataset version with your augmentations
2. Click "Export Dataset"
3. Format: YOLOv8 (this format also works for YOLO26)
4. Choose "Get download code" — Roboflow gives you a Python snippet

The snippet looks like:
```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_KEY_HERE")
project = rf.workspace("YOUR_WORKSPACE").project("YOUR_PROJECT")
version = project.version(1)
dataset = version.download("yolov8")
```

Tell the student to save this snippet — they will paste it into
the Colab notebook in the next lesson.

**INFO callout — why YOLOv8 format for YOLO26:**
"YOLO26 uses the same dataset format as YOLOv8. The format is just
a folder structure with images and matching .txt label files.
Ultralytics kept this consistent across model generations."

---

## LESSON PA.6 — TRAINING IN GOOGLE COLAB

**Purpose:** Run the actual training. Use Colab for GPU access.
Walk through every cell of the training notebook.

### Content:

**Why Colab for training:**
Training on a CPU for 50 epochs on 150 images would take 2-4 hours.
Colab's free T4 GPU does it in 8-12 minutes. Use the right tool
for the right job — inference runs locally, training runs in the cloud.

**How to get GPU in Colab:**
Runtime menu → Change runtime type → T4 GPU → Save.
Tell the student to check: Runtime → View resources — should show GPU memory.

WARNING callout:
"Colab free tier gives you GPU access for roughly 2-4 hours per day.
Training this project takes about 10 minutes so free tier is more
than enough. Do not leave the notebook idle — Colab disconnects after
90 minutes of inactivity and you lose your session."

**Full training notebook — cell by cell:**

Tell the agent to build this as the training Colab notebook
(`notebooks/projA-training.ipynb`) and link it from the lesson.
Show every cell on the site page with explanation, same as Project 1.

---

Cell 1 — Install dependencies:
```python
!pip install ultralytics roboflow -q
```
Explanation: `-q` means quiet — suppresses the long install log.

---

Cell 2 — Check GPU:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None — check runtime type'}")
```
Explanation: If this prints "None", the student forgot to switch to GPU runtime.

---

Cell 3 — Download dataset from Roboflow:
Show the Roboflow snippet from PA.5 here. Tell the student to paste
their own snippet (api_key, workspace, project will differ per student).

---

Cell 4 — Inspect the dataset structure:
```python
import os
dataset_path = "YOUR-PROJECT-NAME-1"  # folder Roboflow created
for split in ["train", "valid", "test"]:
    images = len(os.listdir(f"{dataset_path}/{split}/images"))
    labels = len(os.listdir(f"{dataset_path}/{split}/labels"))
    print(f"{split}: {images} images, {labels} labels")
```
Explanation: teaches students to verify their data before training.
A mismatch between images and labels means something went wrong in export.

---

Cell 5 — Look at one label file:
```python
import random
label_files = os.listdir(f"{dataset_path}/train/labels")
sample = random.choice(label_files)
with open(f"{dataset_path}/train/labels/{sample}") as f:
    content = f.read()
print(f"File: {sample}")
print(f"Contents:\n{content}")
print("\nFormat: class_id  x_center  y_center  width  height (all normalized 0-1)")
```
Explanation: demystifies the label format. Students see the raw numbers
they created during labeling. Connect back to the xywh explanation from PA.0.

---

Cell 6 — Visualize a training image with its label:
```python
import cv2
import matplotlib.pyplot as plt
import numpy as np

img_dir = f"{dataset_path}/train/images"
lbl_dir = f"{dataset_path}/train/labels"

img_file = random.choice(os.listdir(img_dir))
lbl_file = img_file.replace(".jpg", ".txt").replace(".png", ".txt")

img = cv2.imread(f"{img_dir}/{img_file}")
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
h, w = img.shape[:2]

with open(f"{lbl_dir}/{lbl_file}") as f:
    for line in f:
        parts = list(map(float, line.strip().split()))
        cx, cy, bw, bh = parts[1]*w, parts[2]*h, parts[3]*w, parts[4]*h
        x1, y1 = int(cx - bw/2), int(cy - bh/2)
        x2, y2 = int(cx + bw/2), int(cy + bh/2)
        cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), 2)

plt.imshow(img)
plt.title(f"Sample: {img_file}")
plt.axis("off")
plt.show()
```
Explanation: before training, always visualize your data to confirm
labels look correct. If the box is in the wrong place, the label
is wrong, not the model.

---

Cell 7 — Train YOLO26n:
```python
from ultralytics import YOLO

model = YOLO("yolo26n.pt")   # start from pretrained nano weights

results = model.train(
    data=f"{dataset_path}/data.yaml",
    epochs=50,
    imgsz=416,
    batch=16,
    name="my_detector",
    patience=15,          # stop early if val loss stops improving
    save=True,
    device=0              # GPU device 0 — auto-falls back to CPU
)
```

Explain every argument in an anatomy table:

| Argument | Value | What it means |
|----------|-------|---------------|
| data | data.yaml | The config file Roboflow generated — lists your class names and folder paths |
| epochs | 50 | How many times to loop through the full training set. 50 is enough for small datasets |
| imgsz | 416 | Resize all images to 416×416 during training. Larger = more accurate but slower |
| batch | 16 | Process 16 images at once. Reduce to 8 if Colab runs out of GPU memory |
| patience | 15 | If validation accuracy doesn't improve for 15 epochs, stop early |
| device | 0 | Use GPU 0. Falls back to CPU automatically |

---

Cell 8 — Find the trained weights:
```python
import glob
weights = glob.glob("runs/detect/my_detector/weights/best.pt")
print(f"Best weights saved at: {weights[0]}")
```
Explanation: best.pt is saved at the epoch where validation accuracy
was highest — NOT necessarily the last epoch. This is why patience
and early stopping matter.

---

## LESSON PA.7 — READING THE TRAINING RESULTS

**Purpose:** Teach the student to interpret training metrics.
This is where many tutorials skip crucial understanding.

### Content:

**The training output folder:**
After training, Ultralytics saves everything to `runs/detect/my_detector/`.
Show the folder structure with an explanation of each file:

```
runs/detect/my_detector/
├── weights/
│   ├── best.pt      ← USE THIS — best validation accuracy
│   └── last.pt      ← last epoch weights, not necessarily best
├── results.csv      ← all metrics per epoch as numbers
├── results.png      ← charts of all metrics over time
├── confusion_matrix.png
├── PR_curve.png
└── val_batch0_pred.jpg  ← sample predictions on validation images
```

**Key metrics — explain each one clearly:**

mAP50 (most important):
Mean Average Precision at 50% IoU threshold. This is the headline
accuracy number. For a single-class detector on simple backgrounds,
expect 0.85-0.97. Below 0.7 means your data or labels need work.
Explain IoU briefly: how much the predicted box overlaps with the
true box, as a fraction. 50% overlap = IoU of 0.5.

Precision:
Of all the boxes the model predicted, what fraction were correct?
High precision = few false positives (model doesn't hallucinate objects).

Recall:
Of all the real objects in the images, what fraction did the model find?
High recall = few missed objects.

The precision-recall tradeoff callout (TIP):
"Lowering the confidence threshold increases recall but decreases
precision — you catch more real objects but also accept more false
positives. Raising it does the opposite. The confidence setting in
your inference code (default 0.5) is where you set this tradeoff
for your application."

Box loss and class loss:
These should decrease steadily over epochs. If they plateau early,
the model has converged. If they decrease then suddenly spike,
the learning rate may be too high or your labels have errors.

**Show training curve diagram:**
Describe what a healthy training curve looks like vs. an overfit one:
- Healthy: train loss and val loss both decrease together
- Overfit: train loss keeps decreasing but val loss stops or increases
- Underfit: both losses are high and barely decreasing (need more epochs or data)

---

## LESSON PA.8 — RUNNING INFERENCE LOCALLY

**Purpose:** Download best.pt and run it on a live webcam in VS Code.

### Content:

**Download best.pt from Colab:**
In Colab, Files panel (left sidebar folder icon) → navigate to
`runs/detect/my_detector/weights/` → right-click `best.pt` → Download.
Move it to your `my-detector` VS Code project folder.

**Create `detect_webcam.py`:**

Show this full script on the page (display only, not browser-runnable):

```python
import cv2
from ultralytics import YOLO

# Load your trained model
model = YOLO("best.pt")

# Open webcam (0 = default webcam)
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

print("Press Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run detection
    results = model(frame, imgsz=416, conf=0.5, verbose=False)

    # Draw results on the frame
    annotated = results[0].plot()

    # Show FPS
    fps = cap.get(cv2.CAP_PROP_FPS)
    cv2.putText(annotated, f"Model: yolo26n (your data)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.imshow("My Detector", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

Anatomy table for key lines:
- `results[0].plot()` — Ultralytics built-in method that draws all
  boxes, class names, and confidence scores onto the frame
- `conf=0.5` — minimum confidence to show a detection
- `verbose=False` — suppresses per-frame terminal output (otherwise floods terminal)
- `cv2.VideoCapture(0)` — 0 means the default camera. Try 1 if you
  have multiple cameras and the wrong one opens

**Run it:**
```
python detect_webcam.py
```

**Tuning on the fly callout (TIP):**
"If you see too many false positives (wrong detections), increase
conf to 0.65 or 0.7. If the model misses the real object often,
decrease conf to 0.4. You can also try imgsz=320 if the laptop
feels slow — smaller image = faster but slightly less accurate."

---

## LESSON PA.9 — UNDERSTANDING THE MODEL OUTPUT

**Purpose:** Look at the raw YOLO output before `.plot()` hides it.
This is critical because Project 1 uses the raw output directly.

### Content:

**Why this lesson:**
The tracker in Project 1 does not use `.plot()`. It reads
`box.xyxy`, `box.conf`, and `box.cls` directly to compute motor
commands. A student who only ever called `.plot()` will be lost
when they see those attribute names. This lesson bridges the gap.

**Show this script (display only):**

```python
import cv2
from ultralytics import YOLO

model = YOLO("best.pt")
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, imgsz=416, conf=0.5, verbose=False)

    # Look at the raw output — don't use .plot() yet
    for r in results:
        print(f"\nFrame detections: {len(r.boxes)}")

        for i, box in enumerate(r.boxes):
            # Bounding box in pixel coordinates (x1,y1,x2,y2)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            # Center of the box
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            # Area of the box (proxy for distance)
            area = (x2 - x1) * (y2 - y1)

            # Confidence score
            confidence = float(box.conf[0])

            # Class index and name
            class_id   = int(box.cls[0])
            class_name = model.names[class_id]

            print(f"  Detection {i}: {class_name} ({confidence:.0%} confident)")
            print(f"    Box:    ({x1:.0f}, {y1:.0f}) to ({x2:.0f}, {y2:.0f})")
            print(f"    Center: ({cx:.0f}, {cy:.0f})")
            print(f"    Area:   {area:.0f} px²")

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

**Anatomy table for every new attribute:**

| Attribute | Type | What it contains |
|-----------|------|-----------------|
| `r.boxes` | list | All detections in this frame. Empty list = nothing detected |
| `box.xyxy[0]` | tensor | [x1, y1, x2, y2] in pixel coordinates. [0] because there's one box per entry |
| `.cpu().numpy()` | conversion | Moves the tensor from GPU memory to CPU and converts to a NumPy array so you can do math with it |
| `box.conf[0]` | float tensor | Confidence score 0-1. float() converts it to a plain Python number |
| `box.cls[0]` | int tensor | Index of the detected class. Use model.names[index] to get the string name |
| `model.names` | dict | Maps class index → class name. e.g. {0: "ball"} for your single-class model |

**Connect to Project 1 callout (ROBOTICS box):**
"Look at the `_detect()` method in `obj_track_adv.py`. It does
exactly this — loops through `r.boxes`, checks the class name,
computes the area, and returns the bounding box coordinates.
Now that you understand what each line reads, that method
should make complete sense."

---

## LESSON PA.10 — PREPARING FOR PROJECT 1

**Purpose:** Checklist and bridge. Confirm readiness for the tracker project.

### Content:

**What you now have:**
- A trained `best.pt` file specific to your target object
- Understanding of what the model outputs and how to read it
- A working local Python environment with all packages installed
- Intuition for confidence thresholds and bounding box coordinates

**Rename your weights for clarity:**
Rename `best.pt` to something descriptive like `ball_detector.pt`
or `mug_detector.pt`. In Project 1, update the Tracker initialization:
```python
tracker = Tracker("ball_detector.pt", "ball")
```
The second argument must match the class name you used in Roboflow exactly.

**Verify your model is ready (checklist — interactive, localStorage):**
□ best.pt is in the my-detector folder and webcam detection works
□ The model correctly detects your target object from at least 1 meter away
□ The model runs at acceptable speed (even 5 fps is enough for Project 1)
□ You understand what box.xyxy, box.conf, and box.cls contain
□ mAP50 on the validation set was above 0.75

**If mAP50 is below 0.75 callout (WARNING):**
"Don't move to Project 1 with a weak model — the tracker will
behave erratically and it will be impossible to tell if the problem
is the model or the control code. Add 50-100 more images with
more varied backgrounds and retrain. This almost always fixes it."

**What's next:**
Link to Project 1 with a framing sentence:
"You have the model. Project 1 connects it to real motors."

---

## TECHNICAL NOTES FOR THE AGENT

- All code blocks in this project are DISPLAY ONLY except the Colab
  notebook cells, which are in the .ipynb file and not on the page.
  Use the VS Code badge (purple #007acc) for local scripts.
  Use the Colab badge for training cells.

- The Colab notebook must be created at:
  `notebooks/projA-training.ipynb`
  with all cells from PA.6 in order, pre-run output cleared,
  and a markdown header linking back to the course site.

- Every code block that shows a local Python script must include the
  suggested filename as the code block's data-filename attribute
  (e.g., data-filename="detect_webcam.py").

- Lesson completion tracking, prev/next navigation, and mark-as-complete
  all work exactly the same as existing lessons.

- The sidebar group for Project A must appear ABOVE Project 1 and carry
  an "(A)" prefix or "Prerequisite" chip so students understand ordering.

---

*End of project_A_design.md*