import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
else:
    print("Webcam is working")
cap.release()
print("Initializing YOLO model...")
model = YOLO("yolov8l.pt")
print("YOLO model loaded!")

print("Starting webcam...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
    return

print("Webcam started successfully!")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Frame not captured")
        break

    print("Frame captured, running YOLO detection...")
    result = model(frame, agnostic_nms=True)[0]
    print("YOLO detection complete!")

    cv2.imshow("yolov8", frame)

    if cv2.waitKey(30) == 27:
        break
