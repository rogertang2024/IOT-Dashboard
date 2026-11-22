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
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.upper_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')

    def _sigmoid(self, x):
        """Normalize raw SVM distance to 0.0 - 1.0 probability."""
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 1.0 if x > 0 else 0.0

    def detect(self, image_input, confidence_threshold=0.50):
        """
        Detect people/faces in an image file or numpy array.
        Tests both standard orientation and 180-degree rotation (for inverted cameras).
        Returns: (detected: bool, max_confidence: float, boxes: list of (x, y, w, h), best_image: np.ndarray)
        """
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return False, 0.0, [], None
            img = cv2.imread(image_input)
            if img is None:
                return False, 0.0, [], None
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            return False, 0.0, [], None

        # Test both normal orientation and 180-degree rotated orientation
        orientations = [
            ("normal", img),
            ("rotated_180", cv2.rotate(img, cv2.ROTATE_180))
        ]

        best_detected = False
        best_conf = 0.0
        best_boxes = []
        best_img = img

        for orient_name, current_img in orientations:
            gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            current_boxes = []
            current_conf = 0.0

            # 1. Face Detection (Haar Cascade)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(35, 35))
            for (fx, fy, fw, fh) in faces:
                current_boxes.append((int(fx), int(fy), int(fw), int(fh)))
                if 0.95 > current_conf:
                    current_conf = 0.95

            # 2. Upper Body Detection (Haar Cascade)
            uppers = self.upper_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50))
            for (ux, uy, uw, uh) in uppers:
                current_boxes.append((int(ux), int(uy), int(uw), int(uh)))
                if 0.85 > current_conf:
                    current_conf = 0.85

            # 3. Full Body HOG Detection
            h, w = current_img.shape[:2]
            scale = 1.0
            if w > 800:
                scale = 800.0 / w
                img_resized = cv2.resize(current_img, (800, int(h * scale)))
            else:
                img_resized = current_img

            try:
                hog_boxes, weights = self.hog.detectMultiScale(
                    img_resized,
                    winStride=(8, 8),
                    padding=(16, 16),
                    scale=1.05,
                    hitThreshold=0.0
                )
                for i, box in enumerate(hog_boxes):
                    weight = weights[i] if i < len(weights) else 0.0
                    weight_val = float(weight[0]) if isinstance(weight, (list, np.ndarray)) else float(weight)
                    conf = self._sigmoid(weight_val)
                    if conf >= confidence_threshold:
                        orig_box = (
                            int(box[0] / scale),
                            int(box[1] / scale),
                            int(box[2] / scale),
                            int(box[3] / scale)
                        )
                        current_boxes.append(orig_box)
                        if conf > current_conf:
                            current_conf = conf
            except Exception as e:
                print(f"[PersonDetector] HOG detection error: {e}", flush=True)

            if len(current_boxes) > 0 and current_conf > best_conf:
                best_detected = True
                best_conf = current_conf
                best_boxes = current_boxes
                best_img = current_img

        return best_detected, round(best_conf, 2), best_boxes, best_img

    def annotate_and_save(self, image_to_save, dest_path, boxes, confidence):
        """Draw bounding boxes and timestamp header on image and save to dest_path."""
        if isinstance(image_to_save, str):
            img = cv2.imread(image_to_save)
        else:
            img = image_to_save.copy()

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
            cv2.rectangle(img, (x, max(0, y - th - 6)), (x + tw + 6, max(th + 6, y)), (0, 0, 255), -1)
            cv2.putText(img, label, (x + 3, max(th + 2, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        return cv2.imwrite(dest_path, img)

    def process_snapshot(self, snapshot_path, alert_output_path, confidence_threshold=0.50):
        """Analyze snapshot and output annotated alert image if intruder detected."""
        detected, conf, boxes, best_img = self.detect(snapshot_path, confidence_threshold)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if detected and best_img is not None:
            self.annotate_and_save(best_img, alert_output_path, boxes, conf)
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

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SNAPSHOT_FILE = os.path.join(BASE_DIR, "config", "www", "security_snapshot.jpg")
    ALERT_FILE = os.path.join(BASE_DIR, "config", "www", "intruder_alert.jpg")
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    TOPIC_REQUEST = "farm/security/scan_request"
    TOPIC_RESULT = "farm/security/human_detected"

    detector = PersonDetector()
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="person_detector_daemon")
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id="person_detector_daemon")

    last_processed_mtime = os.path.getmtime(SNAPSHOT_FILE) if os.path.exists(SNAPSHOT_FILE) else 0

    def process_and_publish():
        nonlocal last_processed_mtime
        if not os.path.exists(SNAPSHOT_FILE):
            return
        mtime = os.path.getmtime(SNAPSHOT_FILE)
        time.sleep(0.3)
        res = detector.process_snapshot(SNAPSHOT_FILE, ALERT_FILE)
        payload = json.dumps(res)
        client.publish(TOPIC_RESULT, payload, retain=True)
        last_processed_mtime = mtime
        print(f"[PersonDetector Daemon] Published result: {payload}", flush=True)

    def on_connect(c, userdata, flags, rc, *args):
        print(f"[PersonDetector Daemon] Connected to MQTT broker (rc: {rc})", flush=True)
        c.subscribe(TOPIC_REQUEST)
        print(f"[PersonDetector Daemon] Subscribed to {TOPIC_REQUEST}", flush=True)

    def on_message(c, userdata, msg):
        print(f"[PersonDetector Daemon] Scan request received on {msg.topic}", flush=True)
        process_and_publish()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[PersonDetector Daemon] Connecting to {MQTT_BROKER}:{MQTT_PORT}...", flush=True)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    # Main loop: checks MQTT and also watches file changes as a backup
    try:
        while True:
            if os.path.exists(SNAPSHOT_FILE):
                mtime = os.path.getmtime(SNAPSHOT_FILE)
                if mtime > last_processed_mtime:
                    process_and_publish()
            time.sleep(0.5)
    except KeyboardInterrupt:
        client.loop_stop()

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
