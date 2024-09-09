# mw_service
# Microwave Pyrolysis Monitoring System Code

This repository contains the code for a Raspberry Pi-based temperature monitoring and data logging system for microwave pyrolysis experiments. The system collects temperature data from thermistors and a thermocouple (MAX6675), converts the voltage readings to temperature values, and logs them in a CSV file. Additionally, a Flask-based web server is hosted on the Raspberry Pi, allowing for real-time access to the sensor data and the ability to download the log file directly from a browser.

Features:
- Sensor Data Collection: Reads voltage values from up to 4 thermistors using an MCP3008 ADC and converts them into temperature using the Steinhart-Hart equation.
- Thermocouple Integration: Reads temperature from a MAX6675 thermocouple amplifier module.
- Data Logging: Continuously logs timestamped temperature readings from the sensors into a CSV file.
- Flask Web Server: Provides real-time access to sensor data through a web interface. Allows downloading of the CSV log.

# Clone the Repository

Open a terminal and run the following command to clone the repository to your local machine:

git clone https://github.com/CaideSpries/mw_service.git
Navigate into the project directory:

cd mw_service

## Step 1:
Make sure Python3 is installed on your machine and install Dependencies

## Step 2:
Install the required Python packages listed in requirements.txt:

pip install -r requirements.txt
Run the Application

## Step 3:
After setting everything up, you can run the logging script:

python log_sensors.py
