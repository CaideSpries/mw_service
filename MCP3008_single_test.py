#!/usr/bin/python
import spidev
import RPi.GPIO as GPIO
import time

# Create an SPI object and open SPI port 0, device (CS) 0
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

# Function to read SPI data from MCP3008 (single channel)
def readadc(adcnum):
    if (adcnum > 7) or (adcnum < 0):
        return -1
    r = spi.xfer2([1, (8 + adcnum) << 4, 0])
    adcout = ((r[1] & 3) << 8) + r[2]
    return adcout

# Continuously read and convert value to voltage
while True:
    v = readadc(0) * (3.3 / 1023.0)  # Convert to voltage
    print("Channel 0 Voltage: {:.3f} V".format(v))
    time.sleep(1)
