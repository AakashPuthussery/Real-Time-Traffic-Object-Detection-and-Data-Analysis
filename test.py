import streamlit as st
import cv2
import torch
from ultralytics import YOLO
import supervision as sv
import numpy as np
from database_operations import insert_data  # Import database function
from datetime import datetime

# Define class mapping and allowed classes
CLASS_MAPPING = {
    0: "pedestrian", 
    2: "car", 
    3: "bike",  
    5: "bus", 
    7: "truck", 
    15: "animals"
}
ALLOWED_CLASSES = set(CLASS_MAPPING.keys())

# Load YOLO model
model = YOLO("yolov8l.pt")

# Streamlit UI
st.title("🔍 YOLOv8 Object Detection Dashboard")
st.sidebar.header("Controls")

# Start/Stop Buttons
start_detection = st.sidebar.button("▶ Start Detection")
stop_detection = st.sidebar.button("⏹ Stop Detection")

# Webcam settings
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow backend on Windows for better support

# Placeholder for video stream
frame_placeholder = st.empty()

# Initialize annotators
box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

# Detection Loop
if start_detection:
    if not cap.isOpened():
        st.error("Error: Could not open webcam.")
    else:
        with st.spinner("Running object detection..."):
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    st.warning("⚠ Could not capture frame. Check the camera.")
                    break

                # Run YOLO detection
                result = model(frame, agnostic_nms=True)[0]
                detections = sv.Detections.from_ultralytics(result)

                # Filter only allowed classes
                mask = np.isin(detections.class_id, list(ALLOWED_CLASSES))
                filtered_detections = detections[mask]

                # Initialize object counts
                counts = { "car": 0, "bus": 0, "bike": 0, "truck": 0, "pedestrian": 0, "animals": 0 }
                for class_id in filtered_detections.class_id:
                    class_name = CLASS_MAPPING.get(class_id, None)
                    if class_name:
                        counts[class_name] += 1

                # Insert detected object counts into database
                current_time = datetime.now().strftime('%H:%M:%S')
                current_date = datetime.now().strftime('%Y-%m-%d')
                insert_data(counts["car"], counts["bus"], counts["bike"], counts["truck"], counts["pedestrian"], counts["animals"], current_date, current_time)

                # Draw bounding boxes
                frame = box_annotator.annotate(scene=frame, detections=filtered_detections)

                # Add labels separately
                labels = [CLASS_MAPPING[class_id] for class_id in filtered_detections.class_id]
                frame = label_annotator.annotate(scene=frame, detections=filtered_detections, labels=labels)

                # Convert BGR to RGB and display in Streamlit
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_placeholder.image(frame, channels="RGB", use_column_width=True)

                # Stop if button is clicked
                if stop_detection:
                    break

# Release webcam resources
cap.release()
