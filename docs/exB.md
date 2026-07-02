# * Exercise B: Your Phone as a Robot Camera

---

## Why a Phone and Not a Webcam


---

In Exercise A you ran detection on a webcam plugged into your laptop. That works for a desktop demo but it is useless for a robot. A robot moves. It cannot drag a USB cable behind it unless you mount the whole computer on the robot, which sometimes may be impractical. The camera must be wireless.
A phone is the perfect solution for learning. It already has a high quality camera, a battery, WiFi, and a screen. Both apps we use turn the phone into a network camera that streams live video over your local WiFi. Your laptop connects to that stream over the network exactly the way a browser loads a video: no cable, no Bluetooth, no special hardware.
This is also exactly how Project 1's robot works. The `MobileVideoStream` class in `shared.py` connects to a phone stream using the same URL format you will set up in this exercise. By the end of Exercise B you will understand every line of that class.
!!! tip "Same architecture, smaller scale"
    Professional mobile robots use the same concept at a higher level. A drone streams its camera feed over WiFi or 4G to a ground station running detection algorithms. An autonomous vehicle streams from multiple cameras to an onboard computer. The architecture is identical to what you are building here: the difference is bandwidth and latency.

### What You Need
The best.pt file from Exercise A. Your phone and laptop on the same WiFi network. Android phone: IP Webcam app, free from the Play Store. iOS: Simple IP Camera app, free from the App Store. The my-detector VS Code folder from Exercise A with the virtual environment active.

---

## phonesense (No App Required)

---

[phonesense](https://github.com/snappyxo/phonesense) is a third option that requires nothing on your phone at all. Instead of installing an app, you run a small server on your laptop and open its URL in your phone's browser. The laptop serves the streaming page; the phone's browser sends the camera feed back over your local WiFi.

This is the fastest way to get started if you do not have IP Webcam or Simple IP Camera installed, or if you want to skip the manual URL-finding step entirely.

### Install phonesense

Install it into your virtual environment the same way you installed other packages in Exercise A:
```bash
pip install phonesense
```
If you prefer to keep it isolated from your project, `uvx` and `pipx` also work:
```bash
uvx phonesense
# or
pipx run phonesense
```

### Start the Standalone Server

<!-- TODO: add screenshot here -->

Open a **second terminal** alongside your normal VS Code terminal and run:
```bash
phonesense
```
If you used `uvx` or `pipx` instead of `pip install`, run `uvx phonesense` or `pipx run phonesense` instead.

phonesense starts a server and prints one or more stream URLs, for example:
```
Phone page	https://192.168.1.10:8080/phone
```
Open the first URL in your phone's browser. Leave this terminal running the whole time you are working on the exercise.

The URL you just opened on your phone but with `camera/stream` (e.g. `https://192.168.1.10:8080/camera/stream`) is your stream URL. You will paste it into `STREAM_URL` in `detect_stream.py` exactly the same way you would paste an IP Webcam or Simple IP Camera URL.
<!-- TODO: change this language -->
!!! tip "phonesense uses HTTPS"
    phonesense generates a self-signed certificate and serves over HTTPS. Your phone browser will show a security warning the first time you open the URL. This is expected and safe on a local network. Tap past it with your browser:

    | Browser | Steps |
    |---|---|
    | Chrome (Android / Windows / Linux) | Tap **Advanced** → **Proceed to ... (unsafe)** |
    | Safari (iOS / macOS) | Tap **Show Details** → **visit this website** |
    | Edge (Windows) | Tap **Advanced** → **Continue to ... (unsafe)** |
    | Firefox (any platform) | Tap **Advanced** → **Accept the Risk and Continue** |


### What phonesense Gives You

| | IP Webcam / Simple IP Camera | phonesense |
|---|---|---|
| Phone-side setup | Install an app | Open a URL in the phone browser |
| Stream URL | Copy from the app screen | Printed in the terminal |

If you are using phonesense, skip to "Running Detection on the Stream" and follow the same steps as other users, using your phonesense URL.


---

## Android Setup: IP Webcam


---

Install IP Webcam. Open the Play Store on your Android phone. Search for IP Webcam by Thyoni Tech (used to be by Pavel Khlebovich before). Install it. It is free with no required account, but shows ads in the beginning. There is a paid, ad-free version available as well. Open the app. Open IP Webcam. You will see a long list of settings. Leave everything at the default for now. Scroll all the way to the bottom of the settings list. Start the server. Tap Start server at the very bottom of the screen. The phone screen turns into a live camera preview.
At the bottom of the preview screen you will see two URLs printed in white text. They look like this:
Example Android URLs
```bash
http://192.168.1.47:8080
http://10.0.0.3:8080
```
These are the addresses your laptop uses to connect to the stream. Write down both of them. You will test which one works in PB.4.
!!! info "Why two URLs?"
    Your phone may have two network interfaces active at once: your home WiFi and a mobile hotspot or VPN. Each interface gets a different IP address. Only one of those addresses is on the same network as your laptop. You will test both to find the right one in PB.4.

### Keep The App Open
Do not close IP Webcam or let the phone screen turn off while testing. The stream only works while the app is running in the foreground. Go to your phone settings and set screen timeout to **Never** or the longest available option while you are working on this exercise.
!!! tip "Keep the phone charging"
    Keep your phone plugged into a charger while running IP Webcam. Streaming video over WiFi drains the battery significantly faster than normal use.

### Stream URL Format For Android
Android / IP Webcam stream URL
```bash
http://PHONE_IP:8080/video
```
The `/video` path returns a continuous MJPEG stream: a sequence of JPEG images sent one after another over a single HTTP connection.

---

## iOS Setup: SimpleIPCamera


---

Install SimpleIPCamera Open the App Store on your iPhone. Search for SimpleIPCamera by CIT.CZ (formerly, Rune Funch). Install it. It is free. Open the app and start streaming. Open SimpleIPCamera. Tap the large Start button on the main screen. Write down the stream URL. The app begins streaming immediately and shows you the stream URL at the top of the screen. It looks like http://192.168.1.52:8080/live .
This is what you paste into Python.

### Keep The App Open
Same requirement as Android: keep the app running in the foreground and plug your phone in to prevent the screen from locking.
!!! info "Simple IP Camera vs IP Webcam"
    Simple IP Camera uses the same MJPEG format as IP Webcam on Android. The stream URL path is slightly different, `/live` instead of `/video`, but the Python code handles it identically. The only change between Android and iOS is the URL you paste into the script.

### Stream URL Format For iOS
iOS / Simple IP Camera stream URL
```bash
http://PHONE_IP:8080/live
```


---

## Finding Your Phone's IP Address


---

On your iPhone go to Settings, tap WiFi, and check that you are connected to the same network name as your laptop.
If your laptop is on ethernet and your phone is on WiFi they are usually on the same network. This is fine.
!!! warning "Mobile data will not work"
    If your phone is on mobile data, 4G, or 5G and not on WiFi, the stream will not work. Connect your phone to the same WiFi as your laptop before continuing.

Both apps display the IP address on screen when the stream is running. If you need to find it manually, use the steps below.
**Android**
Go to Settings, tap Connections or Network, tap WiFi. Tap the network name you are connected to. Scroll down to find **IP address**. It looks like `192.168.x.x` or `10.x.x.x`.
**iPhone**
Go to Settings, tap WiFi. Tap the small **i** icon next to the network name you are connected to. The IP address is shown under the IPv4 Address section.

### What The IP Address Means
An IP address is a unique number assigned to your phone on the local network. It tells your laptop exactly where to send requests when it wants to fetch the video stream. It looks like four numbers separated by dots: `192.168.1.47`.
The first two or three groups of numbers will match between your phone and laptop if they are on the same network.
Device IP address Meaning Laptop 192.168.1.10 Same 192.168.1 prefix. Phone 192.168.1.47 Same network: should work. Phone 172.20.10.3 Different prefix: usually a different network, will not work.
!!! warning "IP addresses can change"
    IP addresses on a home or university WiFi network are not permanent. Your phone gets a new address each time it reconnects to WiFi. If your Python script suddenly cannot connect, check that the IP address in your script still matches the one shown in the app.

---

## Testing the Stream in a Browser


---

Before writing any Python code, confirm the stream works using your browser. This takes 30 seconds and immediately tells you if the network connection is working.
Open your laptop browser. Open Chrome, Firefox, or Safari on your laptop. Type the stream URL in the address bar. For Android use http://PHONE_IP:8080/video . For iOS use http://PHONE_IP:8080/live . Replace PHONE_IP with the address shown in your app. Press Enter. If the connection works, your browser will show a live video feed from your phone camera with a small delay of roughly half a second.
Browser test examples
```bash
http://192.168.1.47:8080/video
http://192.168.1.52:8080/live
```
If you see a live video, your stream is working. Move to PB.5. If the page does not load or times out, work through the troubleshooting table.
What you see What to try Page times out immediately Phone and laptop are on different networks. Connect the phone to the same WiFi as the laptop. Connection refused Wrong port. Confirm the URL matches exactly what the app shows on screen. Page loads but no video Try the other URL if Android showed two. Force-close and reopen the app. Video loads very slowly Move phone and laptop closer to the WiFi router. Streaming needs a decent connection. Works in browser, fails in Python Firewall on laptop may be blocking the connection. Temporarily disable the laptop firewall for testing.
!!! tip "Browser test first"
    The browser test is the most important debugging step in this entire exercise. If the stream does not work in a browser it will not work in Python. Fix the network connection before touching any code.

---

## Running Detection on the Stream


---

The stream works in your browser. Now open VS Code, activate your virtual environment from Exercise A, and create a new file called `detect_stream.py` in your `my-detector` folder.
Paste the following code:
detect_stream.py
```python
import cv2
import numpy as np
import requests
import time
from ultralytics import YOLO

# -- CONFIGURATION----------------------------------------------------
# Paste your phone stream URL here
# Android (IP Webcam):      "http://192.168.x.x:8080/video"
# iOS (Simple IP Camera): "http://192.168.x.x:8080/live"
STREAM_URL = "http://YOUR_PHONE_IP:8080/video"
# TODO: add phonesense url

# Path to your trained model from Exercise A
MODEL_PATH = "best.pt"

# Only show detections above this confidence level (0.0 to 1.0)
CONFIDENCE = 0.5
# --------------------------------------------------------------------

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

        jpg = buf[start:end + 2]
        buf = buf[end + 2:]

        if len(jpg) <= 2:
            continue

        frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            return frame
    return None

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

    while True:
        frame = read_frame(stream)
        if frame is None:
            continue

        # Run detection on the frame
        results = model(frame, imgsz=416, conf=CONFIDENCE, verbose=False)

        # Draw boxes on the frame
        annotated = results[0].plot()

        # Calculate and display FPS
        frame_count += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            frame_count = 0
            fps_timer = time.time()
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Phone Stream - YOLO26n Detection", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.close()
    cv2.destroyAllWindows()
    print("Stopped.")

if __name__ == "__main__":
    main()
```

### Step 1 : Edit The STREAM_URL Line
Change `YOUR_PHONE_IP` to the IP address shown in your phone app. If you are using phonesense, paste the URL that phonesense printed in your terminal.
STREAM_URL examples
```bash
Android (IP Webcam):        STREAM_URL = "http://192.168.1.47:8080/video"
iOS (Simple IP Camera):     STREAM_URL = "http://192.168.1.52:8080/live"
phonesense:                 STREAM_URL = "https://192.168.1.10:8765/video"
```
<!-- TODO: fix phonesense line -->

### Step 2 : Make Sure best.pt Is In The Same Folder
Your trained model file from Exercise A must be in the `my-detector` folder alongside `detect_stream.py`. If you named it something else like `ball_detector.pt`, update the `MODEL_PATH` line accordingly.

### Step 3 : Run The Script
In the VS Code terminal with the virtual environment active:
Run detect_stream.py
```bash
python detect_stream.py
```

### What You Should See
A window opens showing your phone camera feed live. When you hold your trained object in front of the phone camera, a bounding box appears around it with the class name and confidence score. The FPS counter in the top left shows how fast the detection is running.
4 to 12 fps depending on your laptop. This is usable for object tracking.
20 to 40 fps. This feels much smoother, but is not required.


---

## Understanding the Stream Code


---

This lesson explains every meaningful section of `detect_stream.py` so there are no black boxes. This understanding is required for Project 1 where the same concepts appear in a more complex form.

### The Configuration Block
`STREAM_URL`, `MODEL_PATH`, and `CONFIDENCE` are defined at the top of the file as constants rather than buried inside functions. This is deliberate. Any value you might want to change when testing or deploying belongs at the top of the file where it is easy to find. This pattern appears throughout Project 1's code.

### The open_stream Function
requests.get with streaming
```python
requests.get(url, stream=True, timeout=10)
```
`requests.get` is the same function used to load a webpage, but with `stream=True` it does not download the full response at once. Instead it keeps the HTTP connection open and lets you read data piece by piece. This is how MJPEG streaming works: the server never closes the connection, it just keeps sending JPEG frames one after another.
`timeout=10` means: if the phone does not respond within 10 seconds, raise an error instead of hanging forever. Without a timeout, a failed connection would freeze your script with no feedback.

### The read_frame Function
MJPEG is not a video format. It is a stream of individual JPEG images sent back to back over a single HTTP connection. To extract frames from this stream you need to find where each JPEG starts and ends.
Every JPEG file starts with `0xFF 0xD8`.
Every JPEG file ends with `0xFF 0xD9`.
Read a chunk of bytes from the stream into a buffer. Search the buffer for the start marker 0xFF 0xD8 . Search the buffer for the end marker 0xFF 0xD9 , but only after the start marker. When both are found, everything between them is one complete JPEG. Decode that JPEG into an image array using OpenCV. Return the image and clear the processed bytes from the buffer.
JPEG marker extraction
```python
start = buf.find(b"\\xff\\xd8")          # find the JPEG start marker
end = buf.find(b"\\xff\\xd9", start + 2) # find the next end marker
jpg = buf[start:end + 2]              # slice out the complete JPEG
frame = cv2.imdecode(...)             # decode bytes into an image array
```
!!! warning "Do not decode an empty JPEG"
    The end marker must be searched *after* the start marker. If the code finds an old end marker first, the slice can be empty and OpenCV raises `(-215:Assertion failed) !buf.empty()` inside `cv2.imdecode`.
This exact pattern is used in the `MobileVideoStream` class in `shared.py`. Now you know exactly why it is there.

### Why cv2.imdecode Instead Of cv2.VideoCapture
In Exercise A you used `cv2.VideoCapture(0)` to open a webcam. `VideoCapture` handles USB and some network cameras using built-in drivers. However it does not reliably handle MJPEG streams from phone apps. `imdecode` works on raw bytes directly, which gives us full control over how frames are read and handles connection drops and reconnects cleanly.

### The Detection Line
YOLO inference line
```python
results = model(frame, imgsz=416, conf=CONFIDENCE, verbose=False)
```
This is identical to what you wrote in Exercise A's `detect_webcam.py`. The only difference is the source of the frame: instead of coming from `VideoCapture`, it comes from the phone stream via `read_frame`. The model does not know or care where the frame came from. It receives a NumPy array of pixels and returns detections.
!!! tip "Separate model from data source"
    Keep your model separate from your data source. The same model file runs on a webcam, a phone stream, a saved video file, or a single image with no changes.

---

## Connecting the Dots to Project 1


---

Project 1's robot uses a class called `MobileVideoStream` (in a file named `shared.py`) to pull frames from the phone. You have not started Project 1 yet, so here is that exact class printed below. Read through it now : you will recognize every concept from this exercise. When you reach Project 1, this file will already be familiar instead of new.
MobileVideoStream (from Project 1's shared.py)
```python
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
```
Here is what each part does, mapped to what you already built:
The __init__ method: creates the stream URL and starts a background thread. You now know why a background thread exists: to keep frames flowing without blocking the main detection loop. The _run method: contains the MJPEG parsing loop. The buf.find() calls for 0xff 0xd8 and 0xff 0xd9 are exactly the same as read_frame in your detect_stream.py . The difference is that MobileVideoStream runs this loop in a background thread and stores the latest frame in self.frame , while your simple script reads frames one at a time in the main loop. The read method: returns the latest frame and a frame ID number. The main loop checks whether the frame ID has changed since the last iteration. If it has not, the loop skips processing because there is no point running the model on a frame it has already analyzed. The backoff reconnect logic: if the stream drops, the thread waits 1 second, then 2, then 4, up to 8 seconds before retrying. Your simple script has no reconnect logic, which is fine for testing, but a robot that must run for hours needs this.

### What Is Different In Project 1?
Exercise B phone stream → detect → draw boxes → show on screen → Project 1 phone stream → detect → PID → state machine → motors + HUD
The phone stream handling is identical. The detection call is identical. Project 1 just adds what happens after the detection: instead of drawing a box and stopping, it computes a control response and sends it to a motor controller.
You are not learning something new in Project 1. You are adding to something you already understand.

### Final Checklist Before Moving To Exercise C
Phone stream opens in the browser without timing out. detect_stream.py runs without errors. The detection window shows your phone camera feed live. Your trained object is detected with a bounding box when held in front of the camera. You understand what 0xff 0xd8 and 0xff 0xd9 are and why the code searches for them. You can explain the difference between read_frame in this exercise and the MobileVideoStream class shown above.
When all boxes are checked you are ready for Exercise C, where the robot hardware starts moving with encoder feedback.
