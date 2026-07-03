"""
test_servos.py

Quick UDP test for the Exercise E pan-tilt Arduino sketch.
Run this before pan_and_tilt.py to verify the servos respond.
"""

import socket
import time


ESP_IP = "192.168.x.x"  # Arduino IP from Serial Monitor
CMD_PORT = 5001


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(message):
    sock.sendto(message.encode("utf-8"), (ESP_IP, CMD_PORT))
    print(f"Sent: {message}")
    time.sleep(1.0)


try:
    send("HOME")
    send("SERVO,45,40")
    send("SERVO,135,40")
    send("SERVO,90,80")
    send("SERVO,90,40")
    send("HOME")
finally:
    sock.close()
