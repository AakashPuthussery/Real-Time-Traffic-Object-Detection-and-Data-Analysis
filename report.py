import cv2
import argparse
import matplotlib.pyplot as plt
from ultralytics import YOLO
import supervision as sv
import numpy as np
from database_operations import insert_data
from datetime import datetime

# Define a polygon region for object detection
ZONE_POLYGON = np.array([
    [0, 0],
    [0.5, 0],
    [0.5, 1],
    [0, 1]
])

# Allowed class IDs for detection
CLASS_MAPPING = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "animals"
}
ALLOWED_CLASSES = set(CLASS_MAPPING.keys())

# Function to parse command-line arguments
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv8 Object Detection on Video")
    parser.add_argument("--video", type=str, required=True, help="red.mp4")
    args = parser.parse_args()
    return args

def update_visualization(counts):
    """Update the real-time bar chart."""
    plt.clf()
    plt.bar(counts.keys(), counts.values(), color=['blue', 'green', 'red', 'purple', 'orange', 'brown'])
    plt.xlabel("Object Type")
    plt.ylabel("Count")
    plt.title("Live Object Detection Count")
    plt.pause(0.1)  # Update every 0.1 sec

def main():
    print("Starting script...")

    # Parse arguments
    args = parse_arguments()
    video_path = args.video

    # Open video file instead of webcam
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video loaded with resolution: {frame_width}x{frame_height}")

    # Load YOLOv8 model
    model = YOLO("yolov8l.pt")
    print("YOLO model loaded successfully!")

    # Set up annotation tools
    box_annotator = sv.BoxAnnotator(thickness=2)

    # Convert ZONE_POLYGON to pixel coordinates
    zone_polygon = (ZONE_POLYGON * np.array([frame_width, frame_height])).astype(int)
    zone = sv.PolygonZone(polygon=zone_polygon)
    zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.RED, thickness=2)

    print("Starting detection loop... Press 'Esc' to exit.")

    # Initialize Matplotlib for real-time visualization
    plt.ion()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video reached, exiting...")
            break

        print("Frame captured, running YOLO detection...")
        result = model(frame, agnostic_nms=True)[0]

        # Convert YOLO results to Supervision detections
        detections = sv.Detections.from_ultralytics(result)
        filtered_detections = detections[np.isin(detections.class_id, list(ALLOWED_CLASSES))]

        # Count detected objects
        counts = { "car": 0, "bus": 0,"motorcycle":0, "truck": 0, "person": 0, "animals": 0 }
        for class_id in filtered_detections.class_id:
            class_name = CLASS_MAPPING.get(class_id, None)
            if class_name:
                counts[class_name] = counts.get(class_name, 0) + 1

        # Get current date and time
        current_time = datetime.now().strftime('%H:%M:%S')
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Insert data into database
        #insert_data(counts["car"], counts["bus"], counts["bike"], counts["truck"], counts["pedestrian"], counts["animals"], current_date, current_time)

        # Annotate the frame
        frame = box_annotator.annotate(scene=frame, detections=filtered_detections)

        # Manually draw labels using OpenCV
        for (x1, y1, x2, y2), confidence, class_id in zip(
            filtered_detections.xyxy, 
            filtered_detections.confidence, 
            filtered_detections.class_id
        ):
            label = f"{model.model.names[int(class_id)]} {confidence:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        zone.trigger(detections=filtered_detections)
        frame = zone_annotator.annotate(scene=frame)

        # Show the detection output
        cv2.imshow("YOLOv8 Object Detection", frame)

        # **Update the real-time visualization**
        update_visualization(counts)

        # Press 'Esc' to exit
        if cv2.waitKey(30) == 27:
            print("Exit command received, closing...")
            break

    cap.release()
    cv2.destroyAllWindows()
    plt.ioff()
    plt.show()  # Show final visualization
    print("Script finished.")

if __name__ == "__main__":
    main()
