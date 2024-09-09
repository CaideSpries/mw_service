import time
import csv
from datetime import datetime
import spidev
import math
import RPi.GPIO as GPIO

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)

# --- MAX6675 Class ---
class MAX6675:
    def __init__(self, cs_pin):
        self.cs_pin = cs_pin
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def read_temp(self):
        GPIO.output(self.cs_pin, GPIO.LOW)
        time.sleep(0.01)

        # Open the SPI bus for MAX6675
        spi = spidev.SpiDev()
        spi.open(0, 1)  # Use SPI0.1 for MAX6675
        spi.max_speed_hz = 500000

        # Read two bytes of data from MAX6675
        value = spi.xfer2([0x00, 0x00])
        GPIO.output(self.cs_pin, GPIO.HIGH)
        spi.close()  # Close SPI after use

        # Process raw temperature value
        raw_value = ((value[0] << 8) | value[1]) >> 3
        temp_c = raw_value * 0.25
        return round(temp_c, 2)  # Return temperature with 2 decimal places

# Setup SPI for MCP3008 (SPI0.0)
spi = spidev.SpiDev()
spi.open(0, 0)  # Use SPI0.0 for MCP3008
spi.max_speed_hz = 1000000

# Number of thermistors to read
no_of_thermistors = 4  # Adjust this value based on how many thermistors you want to log

# Function to read MCP3008 (single channel)
def read_adc(adcnum):
    if (adcnum > 7) or (adcnum < 0):
        return -1
    r = spi.xfer2([1, (8 + adcnum) << 4, 0])
    adcout = ((r[1] & 3) << 8) + r[2]
    voltage = (adcout * 3.3) / 1024.0  # Convert raw ADC value to voltage (assuming 3.3V reference)
    return voltage

# Function to convert voltage to temperature for thermistors
def voltage_to_temperature(voltage):
    if voltage <= 0:  # Check if voltage is valid
        return float('NaN')  # Return NaN to avoid division by zero

    R_fixed = 10000  # 10k fixed resistor
    V_ref = 3.3  # Reference voltage for the ADC

    try:
        # Calculate the resistance of the thermistor
        R_thermistor = R_fixed * (V_ref / voltage - 1)
        lnohm = math.log(R_thermistor)
    except ValueError:
        return float('NaN')  # Return NaN if log fails (negative ohms)

    # Steinhart-Hart coefficients for 10k thermistor
    a = 1.285210645e-3
    b = 2.124174560e-4
    c = 1.438197044e-7

    t1 = b * lnohm
    t2 = c * lnohm**3
    temp_k = 1 / (a + t1 + t2)  # Temperature in Kelvin
    temp_c = temp_k - 273.15  # Convert Kelvin to Celsius

    return round(temp_c, 2)  # Return temperature with 2 decimal places

# Initialize MAX6675 on GPIO 7 (CS pin)
max6675 = MAX6675(cs_pin=7)

logging_active = False  # A flag to control the logging loop

# Log data function
def log_data(log_file):
    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)

        if file.tell() == 0:  # Write header if file is empty
            header = ['Timestamp'] + [f'Thermistor{i+1}' for i in range(no_of_thermistors)] + ['Thermocouple', 'Comment']
            writer.writerow(header)

        while logging_active:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Read and convert thermistor voltages
            thermistor_readings = [voltage_to_temperature(read_adc(i)) for i in range(no_of_thermistors)]

            # Reading temperature from MAX6675
            thermocouple_temp = max6675.read_temp()

            # Log the data
            writer.writerow([timestamp] + thermistor_readings + [thermocouple_temp, ''])  # Empty comment field

            # Print debug information
            thermistor_info = " | ".join([f"Thermistor{i+1}: {thermistor_readings[i]:.2f} °C" for i in range(no_of_thermistors)])
            print(f"{timestamp} | {thermistor_info} | Thermocouple: {thermocouple_temp:.2f} °C")

            file.flush()
            time.sleep(10)

# Start logging
def start_logging(log_file):
    global logging_active
    logging_active = True
    log_data(log_file)

# Stop logging
def stop_logging():
    global logging_active
    logging_active = False
    print("Logging stopped.")

if __name__ == "__main__":
    try:
        start_logging("temperature_log.csv")
    except KeyboardInterrupt:
        stop_logging()
        spi.close()  # Close SPI before exiting
        GPIO.cleanup()  # Clean up GPIO pins properly