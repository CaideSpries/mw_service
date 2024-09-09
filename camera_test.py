import cv2

# Attempt to open the default camera (0 for /dev/video0)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
else:
    print("Camera opened successfully.")

    for i in range(10):
        ret, frame = cap.read()
        if ret:
            print(f"Frame {i} captured, resolution: {frame.shape}")
        else:
            print("Failed to capture frame")

    cap.release()
