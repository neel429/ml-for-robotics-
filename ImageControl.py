import socket
import cv2 as cv
from teachable_machine import TeachableMachine


# -----------------------------
# Network / robot settings
# -----------------------------

ARDUINO_IP = "192.168.7.7"
ARDUINO_PORT = 5005

# Left motor pins
LEFT_IN1 = 4
LEFT_IN2 = 5
LEFT_PWM = 6

# Right motor pins
RIGHT_IN1 = 12
RIGHT_IN2 = 13
RIGHT_PWM = 11

MOTOR_SPEED = 180

# Only act on a prediction if the model is at least this confident (0.0 - 1.0)
CONFIDENCE_THRESHOLD = 0.8

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(command):
    print("Sending:", command)
    sock.sendto(command.encode(), (ARDUINO_IP, ARDUINO_PORT))


# -----------------------------
# Motor control (same protocol as DCMotorControl.py)
# -----------------------------

def left_motor(speed):
    send(f"M {LEFT_IN1} {LEFT_IN2} {LEFT_PWM} {speed}")


def right_motor(speed):
    send(f"M {RIGHT_IN1} {RIGHT_IN2} {RIGHT_PWM} {speed}")


def forward():
    left_motor(MOTOR_SPEED)
    right_motor(MOTOR_SPEED)


def backward():
    left_motor(-MOTOR_SPEED)
    right_motor(-MOTOR_SPEED)


def turn_left():
    left_motor(MOTOR_SPEED)
    right_motor(-MOTOR_SPEED)


def turn_right():
    left_motor(-MOTOR_SPEED)
    right_motor(+MOTOR_SPEED)


def stop_motors():
    left_motor(0)
    right_motor(0)


# Map each trained class name to the action it should trigger
ACTIONS = {
    "forward": forward,
    "backward": backward,
    "left": turn_left,
    "right": turn_right,
    "stop": stop_motors,
}


# -----------------------------
# Load Teachable Machine model
# -----------------------------

model = TeachableMachine(model_path="keras_modelv2.h5",
                         labels_file_path="labels.txt")

image_path = "screenshot.jpg"


def clean_name(raw):
    # labels can come back like "0 Forward" or "Forward" -> "forward"
    parts = str(raw).strip().split(" ", 1)
    name = parts[1] if len(parts) > 1 and parts[0].isdigit() else raw
    return name.strip().lower()


def to_fraction(confidence):
    # The library may report confidence as 0.0-1.0 or 0-100; normalize to 0.0-1.0
    value = float(confidence)
    return value / 100 if value > 1 else value


# -----------------------------
# Main loop
# -----------------------------

cap = cv.VideoCapture(0, cv.CAP_DSHOW)
last_action = None

print("Press ESC in the camera window to quit.")

while True:
    ok, img = cap.read()
    if not ok:
        continue

    # Webcams mirror the image; flip it back so left/right look correct.
    img = cv.flip(img, 1)

    # The library classifies a saved image file, so write the frame out first
    cv.imwrite(image_path, img)
    result = model.classify_image(image_path)

    name = clean_name(result["class_name"])
    confidence = to_fraction(result["class_confidence"])

    print("class_name:", name, "confidence:", round(confidence, 2))

    # Draw the prediction onto the frame ourselves (the library's built-in
    # drawing needs a font file that isn't present on Windows).
    label = f"{name} {confidence * 100:.0f}%"
    cv.putText(img, label, (10, 30),
               cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv.imshow("Robot Vision", img)

    # Only send a new command when the class changes and we're confident.
    # This avoids flooding the robot with the same command every frame.
    if confidence >= CONFIDENCE_THRESHOLD and name != last_action:
        if name in ACTIONS:
            ACTIONS[name]()
            last_action = name

    if cv.waitKey(1) == 27:  # ESC to quit
        break

# Clean up: stop the robot and close the window
stop_motors()
cap.release()
cv.destroyAllWindows()
