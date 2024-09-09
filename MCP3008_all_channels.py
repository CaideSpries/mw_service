#!/usr/bin/python
import spidev
import time

# Define delay and create SPI object
delay = 0.5
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

# Function to read all channels from MCP3008
def readadc(adcnum):
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, (8 + adcnum) << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

print('Reading MCP3008 values, press Ctrl-C to quit...')
print('| {0:>4} | {1:>4} | {2:>4} | {3:>4} | {4:>4} | {5:>4} | {6:>4} | {7:>4} |'.format(*range(8)))
print('-' * 57)

# Main program loop to read all channels
while True:
    values = [0]*8
    for i in range(8):
        values[i] = readadc(i)
    print('| {0:>4} | {1:>4} | {2:>4} | {3:>4} | {4:>4} | {5:>4} | {6:>4} | {7:>4} |'.format(*values))
    time.sleep(delay)
