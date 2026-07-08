import cv2 as cv

# A simple tour of common OpenCV functions.
# Run it, then press a number key to switch effects. Press ESC to quit.
#
#   1 = Normal (no effect)
#   2 = Grayscale
#   3 = Blur
#   4 = Edge detection (Canny)
#   5 = Black & white (threshold)
#   6 = HSV color space
#   7 = Flip (mirror)
#   8 = Draw shapes + text
#   9 = Color tracking (use the sliders in the "Controls" window)

cap = cv.VideoCapture(0)   # open the default webcam
mode = 1                   # which effect is currently selected


# --- Sliders for color tracking (mode 9) -------------------------------
# Trackbars let you change values while the program runs. They live in
# their own window. We create six: a low and high bound for H, S, and V.
def nothing(x):
    pass

cv.namedWindow("Controls")
cv.createTrackbar("H low", "Controls", 100, 179, nothing)
cv.createTrackbar("H high", "Controls", 130, 179, nothing)
cv.createTrackbar("S low", "Controls", 150, 255, nothing)
cv.createTrackbar("S high", "Controls", 255, 255, nothing)
cv.createTrackbar("V low", "Controls", 50, 255, nothing)
cv.createTrackbar("V high", "Controls", 255, 255, nothing)
# The defaults above are a starting point for tracking a BLUE object.

print("Press keys 1-9 to change the effect. Press ESC to quit.")

while True:
    ok, frame = cap.read()         # grab one frame from the camera
    if not ok:
        continue

    # --- Apply the selected effect -------------------------------------
    if mode == 1:
        # Show the original frame, unchanged.
        output = frame

    elif mode == 2:
        # cvtColor converts between color spaces. Here: color -> gray.
        output = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    elif mode == 3:
        # GaussianBlur smooths the image. Bigger numbers = more blur.
        # The (15, 15) is the kernel size and must be odd numbers.
        output = cv.GaussianBlur(frame, (15, 15), 0)

    elif mode == 4:
        # Canny finds edges. The two numbers are the detection thresholds.
        output = cv.Canny(frame, 100, 200)

    elif mode == 5:
        # threshold makes a pure black & white image.
        # First convert to gray, then anything brighter than 127 -> white.
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        _, output = cv.threshold(gray, 127, 255, cv.THRESH_BINARY)

    elif mode == 6:
        # HSV is another color space (Hue, Saturation, Value).
        # It's often easier than BGR for detecting specific colors.
        output = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

    elif mode == 7:
        # flip mirrors the image. 1 = horizontal, 0 = vertical.
        output = cv.flip(frame, 1)

    elif mode == 8:
        # Draw on top of the frame: a rectangle, a circle, and some text.
        output = frame.copy()
        cv.rectangle(output, (50, 50), (250, 200), (0, 255, 0), 3)
        cv.circle(output, (400, 150), 60, (255, 0, 0), -1)   # -1 = filled
        cv.putText(output, "Hello OpenCV", (50, 300),
                   cv.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

    elif mode == 9:
        # Color tracking: find an object by its color and box it.
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

        # Read the current slider positions to build the color range.
        low = (cv.getTrackbarPos("H low", "Controls"),
               cv.getTrackbarPos("S low", "Controls"),
               cv.getTrackbarPos("V low", "Controls"))
        high = (cv.getTrackbarPos("H high", "Controls"),
                cv.getTrackbarPos("S high", "Controls"),
                cv.getTrackbarPos("V high", "Controls"))

        # inRange makes a mask: white where the color matches, black elsewhere.
        mask = cv.inRange(hsv, low, high)

        # findContours finds the outlines of the white blobs in the mask.
        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL,
                                      cv.CHAIN_APPROX_SIMPLE)

        output = frame.copy()
        if contours:
            # Pick the biggest blob -- that's most likely our object.
            biggest = max(contours, key=cv.contourArea)
            if cv.contourArea(biggest) > 500:   # ignore tiny specks of noise
                x, y, w, h = cv.boundingRect(biggest)
                cv.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 3)

        # Show the mask in its own window so you can see what's matching.
        cv.imshow("Mask", mask)

    # --- Show the result -----------------------------------------------
    # Put a small label in the corner so you know which effect is active.
    label = f"Mode {mode}  (press 1-8, ESC to quit)"
    if len(output.shape) == 2:
        # Grayscale/edge images have no color channel, so we can't draw
        # colored text on them -- convert back to color first.
        output = cv.cvtColor(output, cv.COLOR_GRAY2BGR)
    cv.putText(output, label, (10, 30),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv.imshow("OpenCV Demo", output)

    # --- Handle key presses --------------------------------------------
    key = cv.waitKey(1) & 0xFF
    if key == 27:              # ESC
        break
    elif ord("1") <= key <= ord("9"):
        mode = key - ord("0")  # convert the key '1'-'9' into the number

cap.release()
cv.destroyAllWindows()
