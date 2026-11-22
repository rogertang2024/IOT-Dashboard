#!/usr/bin/env python3
"""
Local Computer-Vision Person Detector Service
Uses OpenCV HOG People Detector to verify human presence on camera snapshots.
Supports direct import and MQTT daemon mode.
"""

import os
import sys
import time
import json
import math
from datetime import datetime
import cv2
import numpy as np

# Ensure stdout is unbuffered
sys.stdout.reconfigure(line_buffering=True)

class PersonDetector:
    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def _sigmoid(self, x):
        """Normalize raw SVM distance to 0.0 - 1.0 probability."""
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 1.0 if x > 0 else 0.0

    def detect(self, image_input, confidence_threshold=0.50):
        """
        Detect people in an image file or numpy array.
        Returns: (detected: bool, max_confidence: float, boxes: list of (x, y, w, h))
        """
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return False, 0.0, []
            img = cv2.imread(image_input)
            if img is None:
                return False, 0.0, []
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            return False, 0.0, []

        # Resize for faster, consistent HOG detection if very large
        h, w = img.shape[:2]
        scale = 1.0
        if w > 800:
            scale = 800.0 / w
            img_resized = cv2.resize(img, (800, int(h * scale)))
        else:
            img_resized = img

        try:
            # detectMultiScale returns bounding boxes and SVM weights
            boxes, weights = self.hog.detectMultiScale(
                img_resized,
                winStride=(8, 8),
                padding=(16, 16),
                scale=1.05,
                hitThreshold=0.0
            )
        except Exception as e:
            print(f"[PersonDetector] HOG detection error: {e}", flush=True)
            return False, 0.0, []

        valid_boxes = []
        max_conf = 0.0

        for i, box in enumerate(boxes):
            weight = weights[i] if i < len(weights) else 0.0
            # Weight is a numpy array or float
            if isinstance(weight, (list, np.ndarray)):
                weight_val = float(weight[0])
            else:
                weight_val = float(weight)

            conf = self._sigmoid(weight_val)
            if conf >= confidence_threshold:
                # Scale box back to original coordinates
                orig_box = (
                    int(box[0] / scale),
                    int(box[1] / scale),
                    int(box[2] / scale),
                    int(box[3] / scale)
                )
                valid_boxes.append(orig_box)
                if conf > max_conf:
                    max_conf = conf

        detected = len(valid_boxes) > 0
        return detected, round(max_conf, 2), valid_boxes

    def annotate_and_save(self, src_path_or_img, dest_path, boxes, confidence):
        """Draw bounding boxes and timestamp header on image and save to dest_path."""
        if isinstance(src_path_or_img, str):
            img = cv2.imread(src_path_or_img)
        else:
            img = src_path_or_img.copy()

        if img is None:
            return False

        h, w = img.shape[:2]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Top alert banner
        banner_h = 40
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 160), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        header_text = f"INTRUDER CONFIRMED [{int(confidence * 100)}%] - {now_str}"
        cv2.putText(img, header_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        # Draw red bounding boxes
        for (x, y, bw, bh) in boxes:
            cv2.rectangle(img, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
            label = f"Person: {int(confidence * 100)}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x, y - th - 6), (x + tw + 6, y), (0, 0, 255), -1)
            cv2.putText(img, label, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        return cv2.imwrite(dest_path, img)

    def process_snapshot(self, snapshot_path, alert_output_path, confidence_threshold=0.50):
        """Analyze snapshot and output annotated alert image if intruder detected."""
        detected, conf, boxes = self.detect(snapshot_path, confidence_threshold)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if detected:
            self.annotate_and_save(snapshot_path, alert_output_path, boxes, conf)
            return {
                "state": "ON",
                "confidence": conf,
                "timestamp": now_str,
                "alert_image": alert_output_path
            }
        else:
            return {
                "state": "OFF",
                "confidence": 0.0,
                "timestamp": now_str,
                "alert_image": None
            }

def run_mqtt_daemon():
    """Run as a standalone background MQTT daemon."""
    import paho.mqtt.client as mqtt

    SNAPSHOT_FILE = os.path.abspath("config/www/security_snapshot.jpg")
    ALERT_FILE = os.path.abspath("config/www/intruder_alert.jpg")
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    TOPIC_REQUEST = "farm/security/scan_request"
    TOPIC_RESULT = "farm/security/human_detected"

    detector = PersonDetector()
    client = mqtt.Client(client_id="person_detector_daemon")

    def on_connect(c, userdata, flags, rc):
        print(f"[PersonDetector Daemon] Connected to MQTT broker with result code {rc}")
        c.subscribe(TOPIC_REQUEST)
        print(f"[PersonDetector Daemon] Subscribed to {TOPIC_REQUEST}")

    def on_message(c, userdata, msg):
        print(f"[PersonDetector Daemon] Received scan request on {msg.topic}")
        # Brief sleep to ensure file write buffer completed
        time.sleep(0.3)
        res = detector.process_snapshot(SNAPSHOT_FILE, ALERT_FILE)
        payload = json.dumps(res)
        c.publish(TOPIC_RESULT, payload)
        print(f"[PersonDetector Daemon] Published result to {TOPIC_RESULT}: {payload}")

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[PersonDetector Daemon] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_mqtt_daemon()
    elif len(sys.argv) > 1:
        img_path = sys.argv[1]
        out_path = sys.argv[2] if len(sys.argv) > 2 else "annotated.jpg"
        d = PersonDetector()
        res = d.process_snapshot(img_path, out_path)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python person_detector.py [--daemon | <image_path> [output_path]]")
