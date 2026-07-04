#include <Servo.h>
#include <WiFiS3.h>
#include <WiFiUDP.h>

// Fill in your WiFi network before uploading.
const char* SSID = "YOUR_WIFI_NAME";
const char* PASSWORD = "YOUR_WIFI_PASSWORD";

const int UDP_PORT = 5001;
const int TELEM_PORT = 5002;

#define PAN_PIN  A1
#define TILT_PIN 9

const int PAN_MIN = 10;
const int PAN_MAX = 170;
const int TILT_MIN = 30;
const int TILT_MAX = 150;
const int PAN_HOME = 90;
const int TILT_HOME = 40;

const int SMOOTH_STEP = 2;
const unsigned long SMOOTH_INTERVAL_MS = 20;

Servo panServo;
Servo tiltServo;

int currentPan = PAN_HOME;
int currentTilt = TILT_HOME;
int targetPan = PAN_HOME;
int targetTilt = TILT_HOME;

WiFiUDP udp;
char buf[64];

IPAddress laptopIP;
bool laptopKnown = false;
unsigned long lastSmoothMs = 0;

int clampAngle(int angle, int minAngle, int maxAngle) {
  if (angle < minAngle) return minAngle;
  if (angle > maxAngle) return maxAngle;
  return angle;
}

int stepToward(int current, int target, int step) {
  if (current == target) return current;

  int delta = (target > current) ? step : -step;
  int next = current + delta;

  if ((delta > 0 && next > target) || (delta < 0 && next < target)) {
    next = target;
  }

  return next;
}

void sendAck() {
  if (!laptopKnown) return;

  char ack[32];
  snprintf(ack, sizeof(ack), "SERVO_ACK,%d,%d", currentPan, currentTilt);
  udp.beginPacket(laptopIP, TELEM_PORT);
  udp.write((const uint8_t*)ack, strlen(ack));
  udp.endPacket();
}

void parseCommand(char* message) {
  if (strncmp(message, "SERVO,", 6) == 0) {
    int pan = 0;
    int tilt = 0;
    if (sscanf(message + 6, "%d,%d", &pan, &tilt) == 2) {
      targetPan = clampAngle(pan, PAN_MIN, PAN_MAX);
      targetTilt = clampAngle(tilt, TILT_MIN, TILT_MAX);
    }
  }
  else if (strcmp(message, "HOME") == 0 || strcmp(message, "STOP") == 0) {
    targetPan = PAN_HOME;
    targetTilt = TILT_HOME;
  }
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(SSID);

  while (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(SSID, PASSWORD);

    for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) {
      delay(500);
      Serial.print(".");
    }
  }

  Serial.println();
  Serial.print("Connected! IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);
  panServo.write(PAN_HOME);
  tiltServo.write(TILT_HOME);

  connectWiFi();

  udp.begin(UDP_PORT);
  Serial.print("Listening for servo commands on UDP port ");
  Serial.println(UDP_PORT);
  Serial.println("Commands: SERVO,pan,tilt   HOME   STOP");
}

void loop() {
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    int len = udp.read(buf, sizeof(buf) - 1);
    if (len > 0) {
      buf[len] = '\0';
      laptopIP = udp.remoteIP();
      laptopKnown = true;
      parseCommand(buf);
    }
  }

  unsigned long now = millis();
  if (now - lastSmoothMs >= SMOOTH_INTERVAL_MS) {
    lastSmoothMs = now;

    int nextPan = stepToward(currentPan, targetPan, SMOOTH_STEP);
    int nextTilt = stepToward(currentTilt, targetTilt, SMOOTH_STEP);
    bool moved = (nextPan != currentPan) || (nextTilt != currentTilt);

    currentPan = nextPan;
    currentTilt = nextTilt;

    if (moved) {
      panServo.write(currentPan);
      tiltServo.write(currentTilt);
      sendAck();
    }
  }
}
