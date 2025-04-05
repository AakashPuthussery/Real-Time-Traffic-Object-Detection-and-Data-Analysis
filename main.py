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

# Allowed class IDs for detection
ALLOWED_CLASSES = {0, 2, 3, 5, 7, 15, 16, 17, 18, 19, 20, 21, 22}

# Function to parse command-line arguments
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

    # Parse arguments
    args = parse_arguments()
    frame_width, frame_height = args.webcam_resolution

    # Open webcam (using index 1 instead of 0)
    print("Initializing webcam on index 1...")
    cap = cv2.VideoCapture(1)  # Changed to index 1
    if not cap.isOpened():
        print("Error: Could not open webcam at index 1")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    print(f"Webcam initialized with resolution: {frame_width}x{frame_height}")

    # Load YOLOv8 model
    print("Loading YOLOv8 model...")
    model = YOLO("yolov8l.pt")
    print("YOLO model loaded successfully!")

    # Set up annotation tools
    box_annotator = sv.BoxAnnotator(thickness=2)

    # Convert ZONE_POLYGON to actual pixel coordinates
    zone_polygon = (ZONE_POLYGON * np.array([frame_width, frame_height])).astype(int)

    # Create a PolygonZone
    zone = sv.PolygonZone(polygon=zone_polygon)

    # Create a PolygonZoneAnnotator
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone, 
        color=sv.Color.RED,  # Fixed: Using 'RED' instead of 'red()'
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

        # Filter detections to only include allowed classes
        filtered_detections = detections[np.isin(detections.class_id, list(ALLOWED_CLASSES))]

        # Annotate the frame without using 'labels'
        frame = box_annotator.annotate(scene=frame, detections=filtered_detections)

        # Manually draw labels using OpenCV
        for (x1, y1, x2, y2), confidence, class_id in zip(
            filtered_detections.xyxy, 
            filtered_detections.confidence, 
            filtered_detections.class_id
        ):
            label = f"{model.model.names[int(class_id)]} {confidence:.2f}"
            cv2.putText(
                frame, label, (int(x1), int(y1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
            )


        zone.trigger(detections=filtered_detections)
        frame = zone_annotator.annotate(scene=frame)

        # Show the output
        cv2.imshow("YOLOv8 Object Detection", frame)

        # Press 'Esc' to exit
        if cv2.waitKey(30) == 27:
            print("Exit command received, closing...")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Script finished.")

if __name__ == "__main__":
    main()
