from flask import Flask, render_template, redirect, url_for, request, Response, jsonify, send_from_directory
import log_sensors
import csv
import os
import cv2
import threading
import queue
import time

app = Flask(__name__)

class Logger:
    def __init__(self):
        self.log_file_name = None
        self.video_file_name = None
        self.logging_active = False
        self.providing_frames = True
        self.video_writer = None
        self.cap = cv2.VideoCapture(0)
        self.frame_thread = None
        self.frame_queue = queue.Queue()
        self.comments = {}

        # Start the frame generation in a separate thread
        self.frame_thread = threading.Thread(target=self.gen_frames)
        self.frame_thread.start()

    def start_logging(self, power_setting, catalyst, microwave_duration):
        self.log_file_name = f"{power_setting}_{catalyst}_{microwave_duration}_sensor_log.csv"
        self.video_file_name = f"{power_setting}_{catalyst}_{microwave_duration}_video.avi"
        self.comments.clear()

        self.logging_active = True
        log_sensors.start_logging(self.log_file_name)

    def stop_logging(self):
        log_sensors.stop_logging()
        self.logging_active = False

    def log_comment(self, timestamp, comment):
        self.comments[timestamp] = comment  # Save the comment in the dictionary
        if self.log_file_name:
            with open(self.log_file_name, mode='r+', newline='') as file:
                reader = csv.reader(file)
                rows = list(reader)
                file.seek(0)
                writer = csv.writer(file)

                for row in rows:
                    if row[0] == timestamp:  # Match the timestamp
                        if len(row) == 6:  # If comment column is missing, add it
                            row.append(comment)
                        else:
                            row[6] = comment  # Update the existing comment
                    writer.writerow(row)

    def gen_frames(self):
        if not self.cap.isOpened():
            print("Failed to open camera.")
            return

        print("Camera opened successfully.")
        has_setup_writer = False
        try:
            while self.providing_frames:
                # Set up video writer if it hasn't been done yet
                if not has_setup_writer and self.logging_active:
                    start_time = time.time()
                    frame_count = 0
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    self.video_writer = cv2.VideoWriter(self.video_file_name, fourcc, 10.2024, (640, 480))
                    has_setup_writer = True
                    print(f"Video writer set up with file name: {self.video_file_name}")
                elif not self.logging_active and has_setup_writer:
                    end_time = time.time()
                    print(f"Captured {frame_count} frames in {end_time - start_time} seconds.")
                    print(f"Frames per second: {frame_count / (end_time - start_time)}")
                    has_setup_writer = False
                    self.video_writer = None

                success, frame = self.cap.read()
                if not success:
                    print("Failed to capture frame.")
                    break

                # Write frame to video if recording is active
                if self.logging_active and self.video_writer is not None:
                    frame_count += 1
                    self.video_writer.write(frame)

                # Send frame as JPEG to the client
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                self.frame_queue.put(frame)
        except Exception as e:
            print(f"Error while reading camera stream: {e}")
        finally:
            if self.video_writer is not None:
                self.video_writer.release()

    def get_frame(self):
        while True:
            frame = self.frame_queue.get()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    data = []
    try:
        if logger.log_file_name is not None:
            with open(logger.log_file_name, newline='') as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)
    except FileNotFoundError:
        data = []

    return render_template('index.html', data=data)


@app.route('/start', methods=['POST'])
def start_logging():
    power_setting = request.form['power']
    catalyst = request.form['catalyst']
    microwave_duration_minutes = request.form['microwave_duration_minutes']
    microwave_duration_seconds = request.form['microwave_duration_seconds']

    # Combine minutes and seconds into a single duration string
    microwave_duration = f"{microwave_duration_minutes}m_{microwave_duration_seconds}s"

    logger.start_logging(power_setting, catalyst, microwave_duration)
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_logging():
    logger.stop_logging()
    return redirect(url_for('index'))

@app.route('/video_feed')
def video_feed():
    return Response(logger.get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_latest_data')
def get_latest_data():
    data = []
    try:
        if logger.log_file_name is not None:
            with open(logger.log_file_name, newline='') as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)
    except FileNotFoundError:
        data = []

    if len(data) > 1:
        data_without_headers = data[1:]
    else:
        data_without_headers = []

    rounded_data = []
    for row in data_without_headers:
        rounded_row = [row[0]] + [f"{float(x):.2f}" for x in row[1:-1]]
        rounded_data.append(rounded_row)

    return jsonify(rounded_data[-10:])

@app.route('/add_comment', methods=['POST'])
def add_comment():
    timestamp = request.form['timestamp']
    comment = request.form['comment']
    logger.log_comment(timestamp, comment)
    return jsonify(success=True)

@app.route('/download_log')
def download_log():
    if logger.log_file_name and os.path.exists(logger.log_file_name):
        directory = os.path.dirname(os.path.abspath(logger.log_file_name))
        return send_from_directory(directory=directory, path=os.path.basename(logger.log_file_name), as_attachment=True)
    return "Log file not found", 404

@app.route('/download_video')
def download_video():
    if logger.video_file_name and os.path.exists(logger.video_file_name):
        directory = os.path.dirname(os.path.abspath(logger.video_file_name))
        filename = os.path.basename(logger.video_file_name)
        return send_from_directory(directory=directory, path=filename, as_attachment=True, mimetype='video/x-msvideo')
    return "Video file not found", 404

def start_cleanup_thread(directory, interval_minutes=1):
    """
    Start a background thread that removes old files every `interval_minutes`.
    """
    def cleanup_task():
        while True:
            remove_old_files(directory)
            time.sleep(interval_minutes * 60)

    cleanup_thread = threading.Thread(target=cleanup_task)
    cleanup_thread.daemon = True  # Daemonize thread to exit when the main program does
    cleanup_thread.start()

def remove_old_files(directory, max_age_minutes=10):
    """
    Remove files older than `max_age_minutes` from the specified directory.
    """
    current_time = time.time()
    max_age_seconds = max_age_minutes * 60

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and (filename.endswith('.csv') or filename.endswith('.avi')):
            file_creation_time = os.path.getctime(file_path)
            if current_time - file_creation_time > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"Removed old file: {file_path}")
                except Exception as e:
                    print(f"Error while deleting file {file_path}: {e}")

if __name__ == '__main__':
    log_directory = os.path.dirname(os.path.abspath(__file__))  # Assuming logs are in the same directory as app.py
    start_cleanup_thread(log_directory)

    logger = Logger()

    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
        logger.stop_logging()
        logger.providing_frames = False
        if logger.cap.isOpened():
            logger.cap.release()
            print("Camera released.")

        # Ensure the frame thread is properly stopped
        if logger.frame_thread is not None:
            logger.frame_thread.join()
