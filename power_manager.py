"""Datalogs the current readings."""
import serial

ser = serial.Serial('/dev/ttyAMA0', baudrate=38400, timeout=10)

while True:
    print(ser.readline())
