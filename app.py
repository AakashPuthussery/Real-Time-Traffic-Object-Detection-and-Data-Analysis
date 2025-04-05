import cv2
import argparse
from ultralytics import YOLO
import supervision as sv
import numpy as np

# Define a polygon region for object detection
ZONE_POLYGON = np.array([
    [0, 0],
    [0.5, 0],
    [0.5, 1],
    [0, 1]
])

# Define relevant class IDs
CLASS_NAMES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    16: "bird", 17: "cat", 18: "dog", 19: "horse",
    20: "sheep", 21: "cow", 22: "elephant"
}

ANIMAL_CLASSES = {16, 17, 18, 19, 20, 21, 22}  # Grouped animal classes
ALLOWED_CLASSES = {0, 1, 2, 3, 5} | ANIMAL_CLASSES  # Combined set

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv8 live")
    parser.add_argument(
        "--webcam-resolution", 
        default=[1280, 720], 
        nargs=2, 
        type=int
    )
    args = parser.parse_args()
    return args

def main():
    print("Starting script...")

    args = parse_arguments()
    frame_width, frame_height = args.webcam_resolution

    print("Initializing webcam on index 1...")
    cap = cv2.VideoCapture(1)  # Change to 0 if needed
    if not cap.isOpened():
        print("Error: Could not open webcam at index 1")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    print(f"Webcam initialized with resolution: {frame_width}x{frame_height}")

    print("Loading YOLOv8 model...")
    model = YOLO("yolov8l.pt")
    print("YOLO model loaded successfully!")

    box_annotator = sv.BoxAnnotator(thickness=2)
    zone_polygon = (ZONE_POLYGON * np.array([frame_width, frame_height])).astype(int)
    zone = sv.PolygonZone(polygon=zone_polygon)

    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone, 
        color=sv.Color.RED,
        thickness=2
    )

    print("Starting detection loop... Press 'Esc' to exit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Frame not captured, exiting...")
            break

        print("Frame captured, running YOLO detection...")
        result = model(frame, agnostic_nms=True)[0]

        # Convert YOLO results to Supervision detections
        detections = sv.Detections.from_ultralytics(result)

        # Filter detections to include only allowed classes
        filtered_detections = detections[np.isin(detections.class_id, list(ALLOWED_CLASSES))]

        # Initialize count dictionary
        object_counts = {
            "car": 0,
            "bike": 0,
            "bus": 0,
            "pedestrian": 0,
            "animals": 0
        }

        # Process each detected object
        for (x1, y1, x2, y2), confidence, class_id in zip(
            filtered_detections.xyxy, 
            filtered_detections.confidence, 
            filtered_detections.class_id
        ):
            class_id = int(class_id)
            label = f"{CLASS_NAMES.get(class_id, 'Unknown')} {confidence:.2f}"
            
            # Update object counts
            if class_id == 2:
                object_counts["car"] += 1
            elif class_id in {1, 3}:
                object_counts["bike"] += 1
            elif class_id == 5:
                object_counts["bus"] += 1
            elif class_id == 0:
                object_counts["pedestrian"] += 1
            elif class_id in ANIMAL_CLASSES:
                object_counts["animals"] += 1

            # Display label on frame
            cv2.putText(
                frame, label, (int(x1), int(y1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
            )

        # Print the detected object counts
        print(f"Detected Objects: {object_counts}")

        # Display count on frame
        count_text = f"Cars: {object_counts['car']} | Bikes: {object_counts['bike']} | Buses: {object_counts['bus']} | Pedestrians: {object_counts['pedestrian']} | Animals: {object_counts['animals']}"
        cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        zone.trigger(detections=filtered_detections)
        frame = zone_annotator.annotate(scene=frame)

        cv2.imshow("YOLOv8 Object Detection", frame)

        # Press 'Esc' to exit
        if cv2.waitKey(30) == 27:
            print("Exit command received, closing...")
            break
        return object_counts

    cap.release()
    cv2.destroyAllWindows()
    print("Script finished.")

if __name__ == "__main__":
    main()
