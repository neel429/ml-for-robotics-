# * Exercise C: Precise Movement with Encoders

---

## What You Are Building


---

Most beginner robot tutorials control motors with a simple on/off command: turn the motor on, wait two seconds, turn it off. The robot moves roughly forward for roughly two seconds. How far it actually traveled depends on the battery level, floor surface, motor temperature, wheel slip, and many other small effects. You never really know.
Encoder motors solve this problem. An encoder is a sensor built into the motor assembly that counts how many times the motor shaft has rotated. Every rotation is divided into a fixed number of pulses. By counting these pulses, it can be estimated how far each wheel has traveled and send speed corrections to motors.
This is called **closed-loop control**. The motor does not just receive a command and run blindly. It receives a command, then the controller continuously checks whether the motor has done what was requested. Open-loop is guessing. Closed-loop is measuring.

### Hardware List
Students need every item below before starting. Keep the motor battery separate from USB power, and do not connect the battery until the wiring lesson tells you to.
Item Quantity Notes Arduino UNO R4 WiFi 1 The microcontroller brain that runs the sketch and reads encoder pulses. SnappyXO motor shield 1 Plugs directly onto Arduino and has a motor driver TB6612FNG integrated. DC encoder motors with gearbox 2 Must provide A and B channel output. Robot chassis with wheels 1 Use a 2WD differential-drive chassis. WS2812B RGB LED or similar 1 Status indicator. Data wire connects to A3. 7.4V LiPo or 6V Alkaline battery pack 1 Powers motors through the shield. USB-C cable 1 Programming and Serial Monitor connection. Jumper wires, male to male 15+ Encoder and LED signal wires. Small screwdriver 1 Used for the motor screw terminals.

### System Diagram
Three separate things move through this system. Follow each one on its own row below.
**1. Command path** : your code travels from the laptop down to the wheels:
Laptop USB: upload sketch + serial monitor → Arduino UNO R4 WiFi runs control, counts ticks → Motor Shield TB6612FNG driver + regulator → Left + Right Motors wheels turn
**2. Feedback path** : the encoders report wheel motion back to the Arduino:
Encoders on each motor generate pulses as wheels turn → Arduino UNO R4 WiFi interrupts count the pulses
**3. Power path** : kept separate from the logic; the battery only feeds the motors:
Battery 6V motor power only → Motor Shield powers the motors

### What You Will Learn
**Encoder feedback**
What a quadrature encoder is, why it produces pulses, and how those pulses become a wheel-distance measurement.
**Interrupts**
How hardware interrupts count fast encoder pulses without relying on the main loop to poll pins.
**Distance math**
How to convert wheel diameter and ticks per revolution into centimeters per tick.
**Reusable motion functions**
How to write `driveDistance()` and `turnDegrees()` so the robot can run a repeatable path.
!!! tip "Why this comes before Project 1"
    The telemetry the Uno R4 WiFi sends back in Project 1 is encoder data. Understanding encoders here means you understand what the robot is measuring later, even when Project 1 moves the control loop into firmware and sends data back over UDP.

---

## Understanding the Hardware


---

### The Arduino UNO R4 WiFi
The Arduino UNO R4 WiFi is a microcontroller board. A microcontroller is a small computer designed to run one program repeatedly and interact directly with hardware. It reads sensors, controls pins, prints serial data, and drives external electronics. Unlike your laptop, it does not run a general operating system. It runs one sketch from power-on until power-off.
**Digital pins**
Pins 0 to 13 can be set `HIGH` or `LOW`, or read as inputs. In this exercise, pins 2 and 3 are used for encoder interrupts.
**Analog pins**
A0 to A5 read voltages between 0V and 5V as numbers. They are not the focus here, but they are useful for later sensors.
**USB port**
USB programs the board and opens the Serial Monitor. Serial output is how you inspect encoder counts and debug motion.
The R4 WiFi version also includes a WiFi module and LED matrix. WiFi is not used in Exercise C, but it matters in Project 1 when the robot receives commands and streams telemetry.

### The SnappyXO Motor Shield V3 Is an All-In-One Board
The motor shield you are using is a custom board designed specifically for this course. Rather than the older L298N driver found on many cheap shields, it integrates the modern TB6612FNG motor driver, plus an onboard voltage regulator and power selection, all on one board. You do not need a separate motor driver module, and the shield plugs directly onto the Arduino UNO R4 WiFi.
Shield feature What it gives you DC Motors #1 and #2 Two green screw-terminal outputs on the right side of the board for the left and right DC motors. Servo connectors Two connectors labeled Servos, A0 and A1, for future servo experiments. Battery terminal A green screw terminal labeled Battery for the motor battery input. Onboard voltage regulator Regulates battery power for DC and servo motors to 6V.

### TB6612FNG vs L298N
The TB6612FNG uses MOSFETs internally rather than bipolar transistors. It handles up to 1.2A continuous per channel, runs cool, and has very low voltage drop across the driver so your motors receive close to the full battery voltage.
!!! info "Why this chip is better"
    The L298N found on many cheap shields can lose up to 2V across the driver, which noticeably reduces motor torque. The TB6612FNG wastes less voltage as heat, so the same battery gives stronger motor output.

### The Encoder Motors
An encoder motor is a DC geared motor with a sensor board attached to the back. The motor itself still has two power wires. The encoder adds power and signal wires so the Arduino can measure rotation.
Wire group Typical wires Purpose Motor power Motor + and motor - Connect directly to the shield's DC motor output terminals. Reversing these two wires reverses motor direction. Encoder power VCC and GND Power the Hall sensor or optical encoder board, usually from Arduino 5V and GND. Encoder signals Channel A and channel B Pulse outputs used to count motion and detect direction.
!!! info "Encoder resolution"
    The encoder is usually on the high-speed motor shaft before the gearbox. If the encoder produces 11 pulses per motor revolution and the gearbox ratio is 30:1, one full wheel rotation produces about `11 x 30 = 330` pulses. This is the encoder resolution for one wheel revolution.

---

## How Encoder Motors Work


---

### Quadrature Encoding
The two encoder channels do not only count motion. They also encode direction. Channel A produces a pulse wave. Channel B produces the same kind of wave, but shifted one quarter cycle out of phase. When the motor spins forward, channel A changes before channel B. When the motor spins backward, channel B changes before channel A.
Forward rotation Channel A Channel B B lags A by one quarter cycle, so A leads. Backward rotation Channel A Channel B B leads A by one quarter cycle, so direction is reversed.
For a full quadrature decoder, the Arduino checks the relationship between A and B on each transition. For this exercise, you will use a simpler reliable approach: attach an interrupt to channel A, and count up or down based on the direction command you sent to the motor.

### Hardware Interrupts
A common beginner mistake is reading encoder pulses inside `loop()` using `digitalRead()`. That can work slowly by hand, but motors produce pulses quickly. The main loop might be busy printing to Serial, checking a target distance, or updating motor power. If the loop is busy when a pulse arrives, that pulse is missed.
Hardware interrupts solve this. When a pin interrupt fires, the Arduino pauses the current code, runs a tiny function called an Interrupt Service Routine (ISR), and then resumes. The ISR should be extremely short because it can interrupt anything else the sketch is doing.
**Good ISR behavior**
**Bad ISR behavior**
!!! warning "Keep ISRs short"
    The ISR should only update the tick counter. Everything else belongs in the main loop, where delays, printing, and calculations are safe.

### Tick Counters
A tick counter is just a number. Every time the left encoder pulse arrives, `ticksLeft` changes. Every time the right encoder pulse arrives, `ticksRight` changes. Later, those numbers are converted into centimeters.
Minimal encoder counter shape
```cpp
volatile long ticksLeft = 0;
volatile long ticksRight = 0;

void leftEncoderISR() {
  ticksLeft++;
}

void rightEncoderISR() {
  ticksRight++;
}
```

---

## Wiring the System


---

The SnappyXO motor shield plugs directly onto the Arduino UNO R4 WiFi. There is no external motor driver module to wire. The TB6612FNG chip is already on the shield. Your only wiring tasks are connecting the motors to the shield screw terminals, connecting encoder signal wires to specific Arduino pins, connecting the RGB LED, and connecting the battery.
Work through each group one at a time. After each group, do a visual check before moving to the next one.

### Connection Group 1: Motor Shield
Align the shield carefully over the Arduino so every pin lines up with its socket. Press down firmly and evenly until the shield seats fully. No wires are needed here: this connection is made by the pins.
!!! warning "Pins reserved by the shield"
    The shield uses Arduino pins `4`, `5`, and `6` for Motor #1, and pins `11`, `12`, and `13` for Motor #2. Do not connect anything else to those pins.

### Connection Group 2: Motors to Shield Screw Terminals
Connect the motor power wires to the green screw terminals labeled DC Motors.
Motor wire Terminal on shield Left motor + DC Motor #1 + Left motor - DC Motor #1 - Right motor + DC Motor #2 + Right motor - DC Motor #2 -
!!! tip "Fixing motor direction"
    If a motor spins in the wrong direction after uploading the first motion sketch, swap the two wires at that motor's terminal block. That is the only correction needed; no code change is required for direction.

### Connection Group 3: Encoders to Arduino Pins
Each encoder motor has four signal wires plus power. Connect them as follows.
Encoder wire Arduino pin Note Left encoder A 2 Hardware interrupt. Left encoder B A0 Direction read inside the left encoder ISR. Right encoder A 3 Hardware interrupt. Right encoder B 8 Direction read inside the right encoder ISR. Left encoder VCC 5V Encoder power. Left encoder GND GND Encoder ground. Right encoder VCC 5V Encoder power. Right encoder GND GND Encoder ground.
!!! info "Why A0 and 8 for channel B?"
    Pins 2 and 3 are reserved for channel A because they support hardware interrupts. Channel B does not need an interrupt; it is only read inside the channel A ISR at the moment the interrupt fires. A0 and 8 are used because pins 4, 5, 6, 11, 12, and 13 are occupied by the motor shield, and pins 7, 9, and 10 are kept free for future use.
!!! warning "A0 works as a digital input"
    A0 is an analog pin, but it also works as a digital input. In code, refer to it as `A0`; the Arduino framework handles the mapping automatically. Do not use the number 14 in these sketches.

### Connection Group 4: RGB LED
This LED will be used as a visual status indicator in later sketches: green for tracking, orange for searching, and red for stopped. It uses a single data wire and a communication protocol called one-wire serial.
LED wire Arduino pin Data A3 VCC 5V GND GND
!!! info "RGB LED library note"
    A WS2812B or similar addressable LED requires the FastLED or NeoPixel library. Installation is covered in the first sketch that uses it. You do not need that library for the encoder test or drive sketches in PC.6 through PC.10.

### Connection Group 5: Battery Power
Wire Where to connect 6V battery positive (+) Shield Battery + screw terminal. 6V battery negative (-) Shield Battery - screw terminal.
!!! warning "Connect battery last"
    Connect the battery last, after all other wiring is complete and double-checked. Disconnect the battery first before making any wiring changes. A wiring error with the battery connected can damage the motor driver chip instantly.

### Pins Available for Future Use
These pins are completely free and are not used by the shield, encoders, or LED: `7`, `9`, `10`, `A1`, `A2`, `A4`, and `A5`. They are available for additional sensors, a buzzer, or other peripherals in later projects.

---

## Arduino Programming Basics


---

You already learned variables, functions, loops, and conditionals in Python. Arduino sketches use C++, which looks different, but the logic is the same. This lesson teaches the syntax changes before the first real sketch.
By the end, `setup()`, `loop()`, semicolons, typed variables, `pinMode()`, `digitalWrite()`, `analogWrite()`, `digitalRead()`, `Serial.print()`, and `volatile` will all have a clear job.

### Python vs Arduino C++
Both languages can express the same control logic. The main difference is that Arduino C++ requires more explicit syntax.
Concept Python Arduino C++ Declare a variable speed = 150 int speed = 150; End a statement newline semicolon ; Define a block indentation curly braces { } Define a function def my_func(): void myFunc() { } Print something print("hello") Serial.println("hello"); Comment one line # this is a comment // this is a comment Comment many lines not common /* this is a comment */ Infinite loop while True: void loop() { }
!!! warning "Two beginner mistakes to avoid"
    Every C++ statement ends with a semicolon. Forgetting one is the most common beginner compile error. Blocks use curly braces, not indentation. Indentation still matters for humans, but the compiler ignores it.

### The Two Mandatory Functions
Every Arduino sketch must have `setup()` and `loop()`. `setup()` runs once when the board powers on or resets. `loop()` runs forever after `setup()` finishes.
Python equivalent
```python
def setup():
    print("Starting up")
    # one-time initialization here

def loop():
    # repeating code here
    pass

setup()
while True:
    loop()
```

Arduino C++
```cpp
void setup() {
  Serial.println("Starting up");
  // one-time initialization here
}

void loop() {
  // repeating code here
}
```
!!! info "What void means"
    The word `void` before a function name means the function returns nothing. If a function returns an integer, you write `int myFunction()`. If it returns a decimal number, you write `float myFunction()`. `setup()` and `loop()` always return `void` because Arduino calls them automatically.

### Declaring Variables: Types Are Required
Python figures out a variable's type from its value. Arduino C++ requires you to state the type explicitly.
Python
```python
speed = 150
name = "ARIA"
ready = True
```

Arduino C++
```cpp
int speed = 150;
float distance = 2.45;
bool ready = true;
char letter = 'A';
```
Type What it stores Example int Whole numbers from about -32768 to 32767 int count = 0; long Larger whole numbers long ticks = 0; float Decimal numbers float distance = 1.5; bool True or false bool ready = true; char A single character char key = 'w'; void Nothing, used for functions void setup() { }
!!! tip "Choosing types in this exercise"
    Use `int` for most counters and pin numbers. Use `long` for encoder tick counts because ticks can grow very large after extended operation. Use `float` for real-world measurements like distance in centimeters.
!!! warning "C++ booleans are lowercase"
    In Python, `True` and `False` are capitalized. In Arduino C++, they are lowercase: `true` and `false`. Writing `True` in a C++ sketch causes a compile error.

### Constants: #define and const
In Python, constants are usually written in all caps by convention. In Arduino C++, you will see two common styles.
define
```cpp
#define MAX_SPEED 255
#define LED_PIN   13
```

const
```cpp
const int MAX_SPEED = 255;
const int LED_PIN = 13;
```
`const` is preferred when the value has a clear type because the compiler can catch more mistakes. `#define` is a preprocessor text substitution. In Exercises C and D, `#define` is used for pin numbers and `const` is used for measured values such as wheel diameter.

### volatile: Variables Shared With Interrupts
`volatile` is specific to embedded programming. It tells the compiler that a variable can change unexpectedly, such as when an interrupt service routine updates encoder counts while the main loop is running.
Encoder counters
```cpp
volatile long ticksLeft = 0;
volatile long ticksRight = 0;
```
Without `volatile`, the compiler may cache a tick count and the main loop can read a stale value. At high speed, that makes encoder counts appear frozen or jump unpredictably.
!!! info "Use volatile for ISR-shared variables"
    `volatile` does not make code slower in any way you would notice. Use it for any variable that an ISR writes and the main loop reads. Forgetting it is much riskier than including it.

### The Four Hardware Functions
These four functions are the vocabulary of hardware control on Arduino. Nearly every sketch in Exercises C and D uses them.
pinMode(pin, mode) Configures a pin as either input or output. Call it in setup() before using the pin. Use INPUT_PULLUP for encoder signal pins so the input does not float randomly. pinMode(13, OUTPUT);
pinMode(2, INPUT_PULLUP); digitalWrite(pin, value) Sets an output pin to HIGH or LOW . It controls LEDs and motor direction pins such as TB6612FNG IN1 and IN2 . digitalWrite(13, HIGH);
digitalWrite(13, LOW); analogWrite(pin, value) Outputs a PWM signal from 0 to 255 . Despite the name, it does not produce a true analog voltage. It creates a fast digital pulse that motors and LEDs respond to like proportional power. analogWrite(6, 0);
analogWrite(6, 128);
analogWrite(6, 255); digitalRead(pin) Reads an input pin and returns HIGH or LOW . Encoder code uses it inside the ISR to read channel B and determine direction. int state = digitalRead(2);
if (state == HIGH) {
  // pin is at 5V
}

### Serial Communication: Arduino's Print Statement
The Arduino has no screen. The Serial Monitor in the Arduino IDE is how you see debug output over USB.
Serial basics
```cpp
Serial.begin(115200);       // in setup()
Serial.println("hello");    // print with newline
Serial.print("hello");      // print without newline
Serial.println(myVariable); // print a variable
```
Python Arduino C++ print("Speed:", speed) Serial.print("Speed: "); Serial.println(speed); print(f"L={l} R={r}") Serial.print("L="); Serial.print(l); Serial.print(" R="); Serial.println(r);
!!! tip "Serial.println is your first debugging tool"
    When something is not working, print variable values and confirm the code reaches the line you think it reaches. Remove extra debug prints once the sketch is stable so the output stays readable.

### Loops and Conditionals
The logic of `if`, `for`, and `while` is identical to Python. The syntax changes.
Python if
```python
if battery < 10:
    print("low")
elif battery < 25:
    print("ok")
else:
    print("full")
```

Arduino C++ if
```cpp
if (battery < 10) {
  Serial.println("low");
} else if (battery < 25) {
  Serial.println("ok");
} else {
  Serial.println("full");
}
```
Python loop
```python
for i in range(5):
    print(i)

while battery > 20:
    battery -= 1
```

Arduino C++ loop
```cpp
for (int i = 0; i < 5; i++) {
  Serial.println(i);
}

while (battery > 20) {
  battery--;
}
```
The Arduino `for` loop has three parts separated by semicolons: the initial value, the condition to keep looping, and the update after each iteration. `i++` means `i = i + 1`. `i--` means `i = i - 1`.

### A Complete Minimal Sketch
This sketch uses constants, variables, `setup()`, `loop()`, pin control, delay timing, an `if` statement, and Serial output.
basics_demo.ino
```cpp
#define LED_PIN 13
const int BLINK_SPEED = 500;  // milliseconds

int loopCount = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("Setup complete.");
}

void loop() {
  loopCount++;

  digitalWrite(LED_PIN, HIGH);
  delay(BLINK_SPEED);

  digitalWrite(LED_PIN, LOW);
  delay(BLINK_SPEED);

  if (loopCount % 5 == 0) {
    Serial.print("Loop count: ");
    Serial.println(loopCount);
  }
}
```

### Anatomy Table
`#define LED_PIN 13` Creates a named constant by text substitution. No type and no semicolon. const int BLINK_SPEED = 500; Creates a typed named constant. Prefer this for values that have a clear type. int loopCount = 0; A global variable declared outside any function. It is accessible from both setup() and loop() . delay(BLINK_SPEED) Pauses execution for 500 ms. During delay() , the Arduino does nothing else. Later sketches use millis() when they need to respond to sensors continuously. loopCount % 5 == 0 The % operator is modulo, the remainder after division. This condition is true when loopCount is exactly divisible by 5.
Upload this sketch, open Serial Monitor at `115200`, and verify that the LED blinks and the loop count prints every five blinks. When this works, you are ready for the hardware sketches.

---

## Your First Arduino Sketch: Blink and Serial


---

Before writing motor or encoder code, verify that the Arduino IDE can detect your board, compile a sketch, upload it, and open the Serial Monitor. If this step fails, encoder debugging will be confusing later.

### Step 1: Install the Arduino IDE
Go to arduino.cc/en/software and download Arduino IDE 2. Install it normally for your operating system. Open the IDE once so it can finish its first-run setup.

### Step 2: Install the UNO R4 Board Package
Open File , then Preferences . In Additional boards manager URLs , paste https://downloads.arduino.cc/packages/package_index.json . Open Tools , then Board , then Boards Manager . Search for Arduino UNO R4 and install Arduino UNO R4 Boards by Arduino.

### Step 3: Select the Board and Port
Connect the Arduino to your laptop with the USB cable. In the board selector dropdown, choose **Arduino UNO R4 WiFi**, then select the port that appeared when you plugged in the board. On Windows it looks like `COM3` or `COM7`. On macOS it often looks like `/dev/cu.usbmodem...`. On Linux it often looks like `/dev/ttyACM0`.

### Step 4: Upload Blink
Open **File**, then **Examples**, then **01.Basics**, then **Blink**. Click the upload button. The onboard LED should blink once per second after upload.
!!! tip "If upload fails"
    Check the selected port, try a different USB cable, and close any program that might have the serial port open. Many charging cables do not carry data.

### Step 5: Open the Serial Monitor
Replace Blink with the sketch below. Upload it, open the Serial Monitor, and set the baud rate dropdown to `115200`.
serial_test.ino
```cpp
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Arduino UNO R4 WiFi is ready.");
  Serial.println("Serial communication working.");
}

void loop() {
  Serial.print("Uptime (ms): ");
  Serial.println(millis());
  delay(1000);
}
```
You should see the uptime printing once per second. Serial communication is how you will watch encoder counts, confirm target ticks, and debug motor behavior in every remaining sketch.

---

## Reading Encoder Pulses


---

This sketch does not move the motors. It only reads and prints encoder counts while you rotate the wheels by hand. That isolates encoder wiring before motor control adds more variables.
encoder_test.ino
```cpp
// Encoder pin definitions
// Encoder pin definitions
#define ENC_LEFT_A   2
#define ENC_LEFT_B   A0
#define ENC_RIGHT_A  3
#define ENC_RIGHT_B  8

volatile long ticksLeft  = 0;
volatile long ticksRight = 0;

// Change these if encoder direction is reversed
const int LEFT_ENCODER_SIGN  = -1;
const int RIGHT_ENCODER_SIGN = 1;

void leftEncoderISR() {
  if (digitalRead(ENC_LEFT_B) == HIGH) {
    ticksLeft += LEFT_ENCODER_SIGN;
  } else {
    ticksLeft -= LEFT_ENCODER_SIGN;
  }
}

void rightEncoderISR() {
  if (digitalRead(ENC_RIGHT_B) == HIGH) {
    ticksRight += RIGHT_ENCODER_SIGN;
  } else {
    ticksRight -= RIGHT_ENCODER_SIGN;
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(ENC_LEFT_A,  INPUT_PULLUP);
  pinMode(ENC_LEFT_B,  INPUT_PULLUP);
  pinMode(ENC_RIGHT_A, INPUT_PULLUP);
  pinMode(ENC_RIGHT_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC_LEFT_A), leftEncoderISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_RIGHT_A), rightEncoderISR, RISING);

  Serial.println("Encoder test ready. Rotate wheels by hand.");
}

void loop() {
  long leftCopy;
  long rightCopy;

  noInterrupts();
  leftCopy = ticksLeft;
  rightCopy = ticksRight;
  interrupts();

  Serial.print("Left: ");
  Serial.print(leftCopy);
  Serial.print(leftCopy > 0 ? "  (forward)" : leftCopy < 0 ? "  (backward)" : "  (zero)");

  Serial.print("    Right: ");
  Serial.print(rightCopy);
  Serial.println(rightCopy > 0 ? "  (forward)" : rightCopy < 0 ? "  (backward)" : "  (zero)");

  delay(200);
}
```
!!! info "How the ISR detects direction"
    Channel A fires a pulse on every tick regardless of direction. Channel B fires the same pulses but shifted 90 degrees in phase. When the motor spins forward, B is already HIGH by the time A rises. When the motor spins backward, B is still LOW when A rises. Reading B inside the channel A interrupt gives direction with the same two encoder signal wires.

### What To Do
Upload the sketch. Open the Serial Monitor at 115200 baud. Rotate the left wheel forward by hand. The count should increase. Rotate it backward. The count should decrease back toward zero. Repeat the same test on the right wheel. If forward rotation decreases the count, swap the channel A and B wire connections for that encoder. The labels A and B on the motor are arbitrary; what matters is which channel leads the other.
Write your measured value here: `______`
Write your measured value here: `______`
These numbers go into the next sketches. Measure them from your actual motors. Do not assume the datasheet value is exact until you verify it.
!!! tip "If the count does not change"
    The encoder signal wire is disconnected, connected to the wrong pin, or the encoder is not powered. Check VCC, GND, and the channel A wire for that motor.
!!! info "If the count jumps randomly"
    You may be seeing electrical noise. Add a 100 ohm resistor in series with the signal wire and a 100 nF capacitor from signal to GND near the Arduino input pin.

---

## Converting Ticks to Distance


---

Once you know ticks per wheel revolution, distance becomes a geometry problem. One wheel revolution moves the robot forward by one wheel circumference. The encoder divides that circumference into ticks.
Distance per tick cm per tick = (wheel diameter x π) / ticks per revolution Use centimeters for wheel diameter so the result is centimeters per tick.

### Example
Value Example Wheel diameter 65 mm = 6.5 cm Ticks per revolution 1080 Distance per tick (6.5 x 3.14159) / 1080 = 0.0192 cm per tick Ticks for 30 cm 30 / 0.0192 = 1562 ticks

### Measure Your Wheel
Use a ruler or calipers to measure the outer diameter of one wheel in millimeters. Convert millimeters to centimeters by dividing by 10. Use the encoder tick count you measured in PC.6. Calculate CM_PER_TICK and copy it into the next sketch.
`______ cm`
`______ ticks`
`(______ x 3.14159) / ______ = ______`
!!! info "Why measure instead of trusting a datasheet?"
    Budget gearbox ratios are often approximate. A nominal 30:1 gearbox might be 29.8:1. On one movement the error is small; over many movements it accumulates. Measuring your actual wheel diameter and encoder count reduces that error.

---

## Driving Forward a Precise Distance


---

This is the first sketch that moves the robot. Before uploading, prop the robot on a book or box so the wheels spin freely. Verify direction before letting the robot drive on the floor.
You must fill in the values measured earlier: `TICKS_PER_REV` and `WHEEL_DIAM_CM`. The motor pins below match the SnappyXO shield used in this course.
drive_distance.ino
```cpp
#include <Arduino.h>
#include <math.h>

// Measured values - replace with your own.
const float WHEEL_DIAM_CM = 6.5;
const long TICKS_PER_REV = 1080;

const float CM_PER_TICK = (WHEEL_DIAM_CM * 3.14159) / TICKS_PER_REV;

// Motor pins - matches the custom shield layout.
// Motor #1 = Left motor.
#define LEFT_IN1_PIN    4
#define LEFT_IN2_PIN    5
#define LEFT_EN_PIN     6

// Motor #2 = Right motor.
#define RIGHT_IN1_PIN   12
#define RIGHT_IN2_PIN   13
#define RIGHT_EN_PIN    11

// Encoder pins.
#define ENC_LEFT_A   2
#define ENC_LEFT_B   A0
#define ENC_RIGHT_A  3
#define ENC_RIGHT_B  8

volatile long ticksLeft = 0;
volatile long ticksRight = 0;

void leftEncoderISR() {
  ticksLeft++;
}

void rightEncoderISR() {
  ticksRight++;
}

void setMotors(int leftSpeed, int rightSpeed) {
  // TB6612FNG direction control:
  // IN1 HIGH + IN2 LOW = forward
  // IN1 LOW + IN2 HIGH = backward

  // Left motor
  if (leftSpeed >= 0) {
    digitalWrite(LEFT_IN1_PIN, HIGH);
    digitalWrite(LEFT_IN2_PIN, LOW);
  } else {
    digitalWrite(LEFT_IN1_PIN, LOW);
    digitalWrite(LEFT_IN2_PIN, HIGH);
  }
  analogWrite(LEFT_EN_PIN, abs(leftSpeed));

  // Right motor
  if (rightSpeed >= 0) {
    digitalWrite(RIGHT_IN1_PIN, HIGH);
    digitalWrite(RIGHT_IN2_PIN, LOW);
  } else {
    digitalWrite(RIGHT_IN1_PIN, LOW);
    digitalWrite(RIGHT_IN2_PIN, HIGH);
  }
  analogWrite(RIGHT_EN_PIN, abs(rightSpeed));
}

void stopMotors() {
  analogWrite(LEFT_EN_PIN,  0);
  analogWrite(RIGHT_EN_PIN, 0);

  digitalWrite(LEFT_IN1_PIN,  LOW);
  digitalWrite(LEFT_IN2_PIN,  LOW);
  digitalWrite(RIGHT_IN1_PIN, LOW);
  digitalWrite(RIGHT_IN2_PIN, LOW);
}

void resetEncoders() {
  noInterrupts();
  ticksLeft = 0;
  ticksRight = 0;
  interrupts();
}

long readLeftTicks() {
  noInterrupts();
  long value = ticksLeft;
  interrupts();
  return value;
}

long readRightTicks() {
  noInterrupts();
  long value = ticksRight;
  interrupts();
  return value;
}

void driveDistance(float targetCm, int speed) {
  long targetTicks = (long)(fabs(targetCm) / CM_PER_TICK + 0.5);
  int direction = (targetCm >= 0) ? 1 : -1;
  unsigned long startedAt = millis();

  resetEncoders();

  Serial.print("Driving ");
  Serial.print(targetCm);
  Serial.print(" cm - target ticks: ");
  Serial.println(targetTicks);

  while (true) {
    long left = readLeftTicks();
    long right = readRightTicks();

    bool leftDone = left >= targetTicks;
    bool rightDone = right >= targetTicks;
    if (leftDone && rightDone) {
      break;
    }

    long remaining = targetTicks - max(left, right);
    int commandSpeed = speed;
    if (remaining < 50) {
      commandSpeed = max(80, speed / 3);
    }

    setMotors(leftDone ? 0 : direction * commandSpeed,
              rightDone ? 0 : direction * commandSpeed);

    if (millis() - startedAt > 10000) {
      Serial.println("TIMEOUT - check encoder wiring");
      break;
    }
  }

  stopMotors();

  Serial.print("Done. Left ticks: ");
  Serial.print(readLeftTicks());
  Serial.print("  Right ticks: ");
  Serial.println(readRightTicks());
}

void setup() {
  Serial.begin(115200);

  pinMode(LEFT_IN1_PIN,  OUTPUT);
  pinMode(LEFT_IN2_PIN,  OUTPUT);
  pinMode(LEFT_EN_PIN,   OUTPUT);
  pinMode(RIGHT_IN1_PIN, OUTPUT);
  pinMode(RIGHT_IN2_PIN, OUTPUT);
  pinMode(RIGHT_EN_PIN,  OUTPUT);

  pinMode(ENC_LEFT_A, INPUT_PULLUP);
  pinMode(ENC_LEFT_B, INPUT_PULLUP);
  pinMode(ENC_RIGHT_A, INPUT_PULLUP);
  pinMode(ENC_RIGHT_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC_LEFT_A), leftEncoderISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_RIGHT_A), rightEncoderISR, RISING);

  stopMotors();
  delay(2000);
  Serial.println("Starting movement sequence...");
}

void loop() {
  driveDistance(30.0, 180);
  delay(1000);
  driveDistance(-30.0, 180);
  delay(1000);

  while (true) {}
}
```
!!! info "Pin note for this shield"
    The shield uses pins `4`, `5`, and `6` for the left motor and `11`, `12`, and `13` for the right motor. Encoder channel A uses interrupt pins `2` and `3`; encoder channel B uses `A0` and `8`. On the UNO R4, all digital pins support `analogWrite()`, so pin 6 works for left motor speed.

### Before Uploading
Lift the robot so the wheels do not touch the floor. Upload the sketch and watch both wheels during the forward movement. Both wheels should spin in the same forward direction. If one spins backward, swap that motor's two power wires. Only after direction is correct, place the robot on the floor and test the 30 cm movement.

### Anatomy of `driveDistance()`
Code idea Why it matters targetTicks = (long)(fabs(targetCm) / CM_PER_TICK + 0.5) Converts centimeters into encoder ticks and rounds to the nearest whole tick. The absolute value means reverse motion still uses a positive target count. IN1 , IN2 , and EN pins The TB6612FNG uses two direction pins per motor and one PWM enable pin for speed. This is different from generic DIR plus PWM examples. noInterrupts() and interrupts() Protect shared tick variables while reading or resetting them so the ISR cannot change a value halfway through the operation. leftDone && rightDone The motion stops only after both wheel counters have reached the target tick count. Slow-down zone Reducing power during the final 50 ticks helps prevent overshoot from mechanical momentum. Elapsed-time timeout The robot stops if encoder counts never reach the target, which protects you from an infinite loop caused by bad wiring.

---

## Turning Exactly 90 Degrees


---

A differential-drive robot turns in place by spinning one wheel forward and the other backward. The robot rotates around its center point, and each wheel travels along a circular arc.
Turn arc distance arc cm = (wheelbase x π x turn angle) / 360 For a 90-degree turn, this simplifies to (wheelbase x 3.14159) / 4 .

### Measure Your Wheelbase
Measure the distance between the center of the left wheel contact patch and the center of the right wheel contact patch. This is the wheelbase or track width.
`______ cm`
`(______ x 3.14159) / 4 = ______ cm`

### Add the Turn Function
Add this constant and function to your `drive_distance.ino` sketch. The function uses the same encoder counters and motor helpers you already wrote.
turn_degrees_addition.ino
```cpp
const float WHEELBASE_CM = 10.0;  // measure your chassis

void turnDegrees(float degrees, int speed) {
  float arcCm = (WHEELBASE_CM * 3.14159 * fabs(degrees)) / 360.0;
  long targetTicks = (long)(arcCm / CM_PER_TICK + 0.5);
  unsigned long startedAt = millis();

  resetEncoders();

  int leftDirection = (degrees > 0) ? 1 : -1;
  int rightDirection = -leftDirection;

  Serial.print("Turning ");
  Serial.print(degrees);
  Serial.print(" degrees - arc: ");
  Serial.print(arcCm);
  Serial.print(" cm - target ticks: ");
  Serial.println(targetTicks);

  while (true) {
    long left = readLeftTicks();
    long right = readRightTicks();

    bool leftDone = left >= targetTicks;
    bool rightDone = right >= targetTicks;
    if (leftDone && rightDone) {
      break;
    }

    setMotors(leftDone ? 0 : leftDirection * speed,
              rightDone ? 0 : rightDirection * speed);

    if (millis() - startedAt > 5000) {
      Serial.println("TIMEOUT - turn did not complete");
      break;
    }
  }

  stopMotors();

  Serial.print("Turn done. Left: ");
  Serial.print(readLeftTicks());
  Serial.print("  Right: ");
  Serial.println(readRightTicks());
}
```

### Test a Single Turn
Replace your current `loop()` with a single turn test. Start with lower speed so the robot is easier to observe.
turn_test_loop.ino
```cpp
void loop() {
  delay(1000);
  turnDegrees(90.0, 150);
  delay(1000);
  turnDegrees(-90.0, 150);

  while (true) {}
}
```
!!! info "Calibrating the wheelbase value"
    The 90-degree turn is usually the hardest movement to make exact. Floor surface, battery voltage, wheel slip, and chassis weight all affect the turn. If the robot consistently turns too far, adjust `WHEELBASE_CM` down in 0.5 cm increments. If it consistently turns too little, adjust `WHEELBASE_CM` up.
**Calibrated wheelbase value** — After testing, write your final value here: `______ cm`

---

## Putting It Together: Running a Path


---

Now combine `driveDistance()` and `turnDegrees()` into a programmed path. The robot will draw a square: drive 30 cm, turn 90 degrees, repeat four times, and return near the start position.
drive_square_loop.ino
```cpp
void loop() {
  Serial.println("Drawing a square...");

  for (int i = 0; i < 4; i++) {
    Serial.print("Side ");
    Serial.println(i + 1);

    driveDistance(30.0, 180);
    delay(500);
    turnDegrees(90.0, 150);
    delay(500);
  }

  Serial.println("Square complete. Stopped.");
  while (true) {}
}
```

### What To Observe
Place tape on the floor to mark the start position and starting heading. Run the square once and let the robot stop by itself. Measure how far the final position is from the start position. Measure the final heading error. The robot should face the same direction it started.
A robot that returns within about 2 cm and 5 degrees of the start position is well calibrated for the purposes of Project 1.
Start 30 cm 90 deg 30 cm 90 deg
!!! tip "Dead reckoning"
    This exercise is called dead reckoning: navigating by tracking motion from a known starting point without an external position reference. Real autonomous vehicles combine wheel encoders with GPS, IMUs, cameras, and SLAM because dead-reckoning errors accumulate over time.

### How To Tune the Square
Observation Likely adjustment Each side is too long or too short. Recheck wheel diameter, ticks per revolution, and CM_PER_TICK . Turns are always too wide or too narrow. Adjust WHEELBASE_CM in small increments. Robot curves during straight segments. Reduce the PWM command on the faster side or add a drift correction coefficient. First square is good but repeated squares drift. This is normal dead-reckoning error. The robot needs external sensing to correct long-term drift.

---

## Troubleshooting and Tuning


---

Hardware bugs usually look mysterious until you separate them into power, wiring, signal, and calibration problems. Use this section as a checklist before changing code.

### Expandable Troubleshooting Table
Motors do not spin at all Likely cause: no battery power Verify the battery is connected to the shield Battery terminal with correct polarity. One motor spins, the other does not Likely cause: wrong pin mapping Check that your direction and PWM pin definitions match the custom shield layout. Then swap only one variable at a time while testing. Robot drifts left or right during straight drive Likely cause: motors have different speeds Reduce PWM on the faster motor or add a drift correction coefficient. Mechanical differences between cheap gearmotors are normal. Encoder counts do not change Likely cause: wrong interrupt pin or no encoder power Check that encoder channel A is on the pin used in the sketch, then verify encoder VCC and GND. Test with PC.6 before running motor code. Direction detection always shows forward Likely cause: channel B wired to wrong pin Check that left encoder B is connected to A0 and right encoder B is connected to pin 8 . Channel B is what lets the ISR decide forward versus backward. Counts jump erratically Likely cause: electrical noise Add a 100 ohm series resistor on the encoder signal wire and a 100 nF capacitor from signal to GND near the Arduino pin. Keep motor power wires away from encoder signal wires. Robot overshoots the target distance Likely cause: slow-down zone too late Increase the slow-down threshold from 50 ticks to 80 or 100 ticks, or lower the main drive speed. Heavier robots need more braking distance. Turn angle is always off by the same amount Likely cause: wheelbase value wrong Adjust WHEELBASE_CM in 0.5 cm increments until a commanded 90-degree turn produces an actual 90-degree turn. Turn direction is reversed Likely cause: one side motor polarity reversed Swap that motor's two power wires at the shield terminal block, then rerun the lifted-wheel direction test before driving on the floor. Serial Monitor shows unreadable text Likely cause: wrong baud rate Set the Serial Monitor dropdown to 115200 , matching Serial.begin(115200) in the sketch.

### Connecting This To Project 1
When you reach Project 1, the encoder data you learned to read here is the same kind of data the telemetry class receives from the robot controller. The tick counts produced by the ISR in this exercise become streaming telemetry in the full tracker.
**Exercise C**
The Arduino reads ticks and controls motors locally. You print encoder counts to Serial and stop motion when counts reach a target.
**Project 1**
Motor control happens inside firmware, and tick counts are sent back to Python so the tracker can display telemetry and later support closed-loop speed control.
The `driveDistance()` function is a simplified form of closed-loop control. Project 1's PID controllers are the professional version of the same idea: measure the error, compute a correction, apply the correction, and repeat.

### Final Checklist
Arduino IDE is installed and UNO R4 WiFi is detected on the correct port. Blink sketch uploaded successfully and the onboard LED blinks. encoder_test.ino runs, counts increase forward, and counts decrease backward. TICKS_PER_REV is measured and written down for both motors. WHEEL_DIAM_CM is measured with a ruler or calipers. CM_PER_TICK is calculated and filled into the drive sketch. Robot drives forward 30 cm with less than 2 cm error. Robot turns 90 degrees with less than 10 degrees error. WHEELBASE_CM is calibrated so the square path closes within 2 cm. You can explain what a hardware interrupt is and why it is needed.
When all boxes are checked, you are ready for Project 1.
