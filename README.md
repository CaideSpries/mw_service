# mw_service
## Microwave Pyrolysis Monitoring System Code

This repository contains the code for a Raspberry Pi-based temperature monitoring and data logging system designed for microwave pyrolysis experiments. The system collects temperature data from thermistors and a thermocouple (MAX6675), logs the data, and provides a real-time view via a Flask-based web server with live camera streaming and recording.

### Features
- **Sensor Data Collection**: Reads voltage values from up to 8 thermistors using an MCP3008 ADC and converts them into temperature using the Steinhart-Hart equation.
- **Thermocouple Integration**: Reads temperature from a MAX6675 thermocouple amplifier module for high-temperature monitoring.
- **Camera Integration**: Streams a live camera feed inside the microwave cavity to the web server for remote monitoring and records video to an MP4 file for later review.
- **Data Logging**: Continuously logs timestamped temperature readings from all sensors into a CSV file.
- **Flask Web Server**: Provides real-time access to sensor data and camera feed through a web interface. The web server also allows for downloading the CSV log file and recorded video directly from a browser.

### Hardware Used
- **Raspberry Pi 3B+**
- **Thermistors**: DHT0B103J3953SY DO-35 Axial Glass Case NTC Thermistor for Temperature Sensing/Compensation with R25°C= 10kΩ, ±5% Tolerance.
- **Thermocouple**: MAX6675 Thermocouple Amplifier with K Type Thermocouple and Stud Probe.
- **Camera**: DF Robot dsj-3808-308 USB Camera for Raspberry Pi.
- **ADC**: MCP3008 Analog-to-Digital Converter for interfacing thermistors.

---

## Setup Instructions

### Prerequisites
1. **Hardware Requirements**:
   - A Raspberry Pi 3B+ with internet access.
   - SSH or direct access to the Raspberry Pi for setup.
   - DHT0B103J3953SY thermistors (up to 8) and an MCP3008 ADC for temperature sensing.
   - MAX6675 Thermocouple Amplifier with K Type Thermocouple and Stud Probe for high-temperature monitoring.
   - DF Robot dsj-3808-308 USB camera for live video streaming and recording.
   - Ensure the Raspberry Pi is set up as an **Access Point** for local network access to the web server.

2. **Software Requirements**:
   - Python 3 installed on the Raspberry Pi.

### Clone the Repository
Open a terminal and run the following command to clone the repository to the Raspberry Pi:
```bash
git clone https://github.com/CaideSpries/mw_service.git
```

### Navigate to project directory
```bash
cd mw_service
```

### Install Dependencies
Ensure the Raspberry Pi has internet access, then install the required Python packages:
```bash
pip install -r requirements.txt
```

### Set up Raspberry Pi as an Access Point
1. Configure the Raspberry Pi as a wireless access point if it’s not already set up.
2. Once configured, identify the IP address of the Raspberry Pi using ifconfig. For example, the IP might be something like 192.168.4.1.
3. This IP address will be used to access the web server interface in a browser.

## Running the Application
### Step 1: Start the Web Server
To launch the monitoring system, use the following command:
```bash
make run
```

### Step 2: Access the Web Server
In a browser on a device connected to the Raspberry Pi's network, navigate to:
```bash
http://<Raspberry Pi IP>:5000/
```

For example:
```bash
http://192.168.4.1:5000/
```

This will open the web interface, where you can:

- View real-time temperature data.
- Access the live camera feed inside the microwave cavity.
- Download the temperature log file (CSV): Allows for easy data analysis and record-keeping.
- Download recorded video (MP4): Provides a record of the experiment's visual progress for further review.

### Step 3: Shutdown the server when finished
You can shutdown and exit the server by pressing ```bash
control + C
```

## Some other commands
Some other important commands such as:
```bash
make rm_logs
```
Will remove the CSV and MP4 files to create more space if needed.

```bash
make clean
```

Will remove the virtual environment for cleanup.

## Additional Notes
- IP Address Check: Verify the IP address assigned to the Raspberry Pi's access point using ifconfig to ensure the correct IP is used to access the web server.
- Camera Module: Make sure the DF Robot dsj-3808-308 USB camera is properly configured and enabled in the Raspberry Pi’s settings before running the server.
