from flask import Flask, render_template, redirect, url_for, request, Response, jsonify, send_from_directory, has_request_context
import log_sensors
import csv
import os
import cv2
import threading
import queue
import time
import logging

# Define a filter to suppress specific route logs
class NoLoggingFilter(logging.Filter):
    def filter(self, record):
        # Check if the request context is active before trying to access `request.path`
        if has_request_context():
            return request.path != '/get_latest_data'
        return True

# Apply this filter to the werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(NoLoggingFilter())
werkzeug_logger.setLevel(logging.WARNING)  # Adjust the log level as needed
app = Flask(__name__)

class Logger:
    def __init__(self):
        self.log_file_name = None
        self.video_file_name = None
        self.logging_active = False
        self.providing_frames = True  # Always provide frames for live feed
        self.video_writer = None
        self.cap = cv2.VideoCapture(0)  # Start capturing as soon as Logger is created
        self.frame_thread = None
        self.frame_queue = queue.Queue()
        self.comments = {}
        self.frame_times = []
        self.comment_queue = queue.Queue()  # Queue to hold comments to be added
        self.comment_batch = {}  # Use a dictionary to collect comments for each timestamp
        self.has_setup_writer = False

        # Start the frame generation thread immediately
        if self.cap.isOpened():
            self.frame_thread = threading.Thread(target=self.gen_frames, daemon=True)  # Daemonize the thread
            self.frame_thread.start()
            #self.gen_frames()  # Run gen_frames directly without threading
            print("Live stream thread started.")
        else:
            print("Failed to open camera on initialization.")

        # Start a separate thread to process queued comments every few seconds
        self.comment_processing_thread = threading.Thread(target=self.process_comment_queue, daemon=True)
        self.comment_processing_thread.start()

    def start_logging(self, power_setting, catalyst, microwave_duration):
        self.log_file_name = f"{power_setting}_{catalyst}_{microwave_duration}_sensor_log.csv"
        self.video_file_name = f"{power_setting}_{catalyst}_{microwave_duration}_video.mp4"
        self.comments.clear()
        self.logging_active = True
        self.has_setup_writer = False  # Reset the writer setup flag
        log_sensors.start_logging(self.log_file_name)

    def stop_logging(self):
        log_sensors.stop_logging()
        self.logging_active = False

        # Release video writer
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            self.has_setup_writer = False
            print("Video writer released in stop_logging.")

        # Clear frame times to avoid inconsistent frame rates
        self.frame_times.clear()

        # Add a small delay to ensure resources are flushed correctly
        time.sleep(2)

        if self.video_file_name:
            print(f"Video saved in file: {self.video_file_name}")

        print("Logging stopped and resources cleaned up.")

    def calculate_frame_rate(self):
        if len(self.frame_times) < 2:
            return 30.0
        total_time = self.frame_times[-1] - self.frame_times[0]
        average_frame_rate = len(self.frame_times) / total_time if total_time > 0 else 30.0
        return max(min(average_frame_rate, 30.0), 1.0)  # Ensure frame rate is at least 1.0

    def log_comment(self, timestamp, comment):
        self.comment_queue.put((timestamp, comment))
        print(f"Comment queued for timestamp {timestamp}")

    def process_comment_queue(self):
        while True:
            try:
                # Collect all available comments from the queue into a list
                comments_to_process = []
                while not self.comment_queue.empty():
                    comments_to_process.append(self.comment_queue.get())
                    self.comment_queue.task_done()  # Mark this comment as processed

                if comments_to_process:
                    self.batch_update_comments_in_file(comments_to_process)

                time.sleep(2)  # Process every 2 seconds

            except Exception as e:
                print(f"Error while processing comments: {e}")

    def batch_update_comments_in_file(self, comments):
        try:
            if self.log_file_name:
                # Read all rows from the CSV file
                with open(self.log_file_name, mode='r+', newline='') as file:
                    reader = csv.reader(file)
                    rows = list(reader)

                    # Create a dictionary for quick lookup of new comments
                    comment_dict = {timestamp: comment for timestamp, comment in comments}

                    # Update rows with comments
                    for row in rows:
                        if len(row) > 0 and row[0] in comment_dict:
                            if len(row) < 11:
                                row.extend([''] * (11 - len(row)))
                            row[10] = comment_dict[row[0]]  # Add/replace the comment

                    # Write back the updated rows to the CSV file
                    file.seek(0)
                    writer = csv.writer(file)
                    writer.writerows(rows)
                    file.truncate()

                print(f"Batch of {len(comments)} comments processed.")

        except Exception as e:
            print(f"Error updating comments in batch: {e}")

    def gen_frames(self):
        if not self.cap.isOpened():
            print("Camera is not opened in gen_frames.")
            return

        frame_count = 0
        try:
            while self.providing_frames:
                success, frame = self.cap.read()
                if not success:
                    print("Failed to capture frame.")
                    break

                current_time = time.time()
                self.frame_times.append(current_time)
                if len(self.frame_times) > 30:
                    self.frame_times.pop(0)

                # Setup video writer if logging has started
                if self.logging_active and not self.has_setup_writer:
                    try:
                        dynamic_frame_rate = self.calculate_frame_rate()
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        self.video_writer = cv2.VideoWriter(self.video_file_name, fourcc, dynamic_frame_rate,
                                                            (640, 480))
                        self.has_setup_writer = True
                        print(f"Video writer initialized for recording at {dynamic_frame_rate} fps")
                    except Exception as e:
                        print(f"Error initializing video writer: {e}")
                        break

                # Write frame if logging
                if self.logging_active and self.video_writer is not None:
                    try:
                        self.video_writer.write(frame)
                        frame_count += 1
                        time.sleep(0.01)  # Small delay to help sync
                    except Exception as e:
                        print(f"Error writing frame: {e}")
                        break

                # Convert frame to JPEG and queue it for the live feed
                try:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if not ret:
                        print("Failed to encode frame to JPEG.")
                        continue
                    frame = buffer.tobytes()
                    self.frame_queue.put(frame)
                except Exception as e:
                    print(f"Error encoding or queuing frame: {e}")
                    break

            print(f"Finished capturing {frame_count} frames during logging.")

        except Exception as e:
            print(f"Error in gen_frames: {e}")

        finally:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                print("Video writer released in gen_frames cleanup.")
            self.has_setup_writer = False
            print("Exiting gen_frames.")

    def get_frame(self):
        while True:
            frame = self.frame_queue.get()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def cleanup(self):
        # Stop providing frames and ensure the frame generation thread stops
        self.providing_frames = False

        # Join the frame thread with a longer timeout to ensure it completes
        if self.frame_thread is not None:
            self.frame_thread.join(timeout=5)  # Increase timeout
            print("Frame thread joined successfully.")

        # Release the video writer, ensuring it is flushed
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None  # Explicitly set to None
            print("Video writer released in cleanup.")

        # Release the camera resource
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.cap = None  # Explicitly set to None
            print("Camera released in cleanup.")

        # Clear the frame queue
        with self.frame_queue.mutex:
            self.frame_queue.queue.clear()
            print("Frame queue cleared in cleanup.")

        print("Cleanup completed.")


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
        if len(row) > 1:  # Ensure row has enough elements
            rounded_row = [row[0]] + [f"{float(x):.2f}" if x.replace('.', '', 1).isdigit() else x for x in row[1:-1]]
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
        if os.path.isfile(file_path) and (filename.endswith('.csv') or filename.endswith('.mp4')):
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
    finally:
        logger.cleanup()
        print("Application terminated gracefully.")

