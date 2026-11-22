# Design Document: Camera Human Intruder Detection & Photograph Alert System

## 1. Intent & Problem Statement
The Smart Farm Security System currently triggers alerts based on PIR motion. However, non-human events (wind-blown vegetation, wildlife, shadows) can still create false alarms. 
This system adds visual AI verification: when motion occurs while armed, the camera takes a photo, a local computer-vision service verifies whether a human/person is present, crops/bounds the intruder, saves the photograph to the Home Assistant dashboard, sounds the physical GPIO 23 buzzer, and alerts the user.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Local AI Verification:** 100% local computer vision detection with zero cloud dependencies or external API keys.
- **Intruder Photograph Capture:** Save an annotated snapshot with a bounding box, timestamp, and confidence label to `/config/www/intruder_alert.jpg` (accessible via `/local/intruder_alert.jpg` in Home Assistant).
- **False Positive Elimination:** Suppress alarm escalation and siren if motion occurs without a confirmed human in the frame.
- **Escalation & Notification:** On confirmed human presence:
  - Turn ON `switch.farm_alarm_siren` (ESP32 GPIO 23 buzzer).
  - Trigger `alarm_control_panel.farm_security_system`.
  - Create persistent alert notification containing the intruder photo.
  - Display the intruder photograph in the Lovelace dashboard.

### Non-Goals
- Facial recognition or identification of specific known individuals.
- 24/7 continuous video recording (NVR/DVR functionality).
- Cloud push notifications (e.g. Twilio/Pushover) requiring paid external accounts.

### Anti-Goals
- High-CPU background loops that saturate the CPU decoding video streams 24/7.
- Delaying alerts by more than 1.5 seconds after camera capture.

---

## 3. Constraints
- **Host OS:** Windows 10/11 with Python 3.11 and Docker Desktop.
- **Installed Libraries:** `cv2` (OpenCV 4.x), `numpy`, and `PIL` already installed in local Python environment.
- **Network / Containers:**
  - Mosquitto MQTT broker on `localhost:1883` (container `mqtt:1883`).
  - Home Assistant on `localhost:8123` (container `homeassistant:8123`).
  - Raspberry Pi MJPEG camera stream on `http://192.168.1.169:8000/stream.mjpg` (integrated as `camera.camera`).
- **Storage:** Home Assistant `www/` directory is mapped at `config/www/` for static web assets.

---

## 4. Approaches Considered
1. **Approach 1: Event-Driven Verification (Selected):** 
   - Camera takes snapshot on motion $\rightarrow$ Local Python service processes snapshot $\rightarrow$ publishes detection to MQTT.
   - *Why chosen:* Near-zero idle CPU, sub-second latency, directly integrates with existing Home Assistant PIR trigger.
2. **Approach 2: Continuous Real-Time Video Stream Analyzer:**
   - 24/7 MJPEG decode loop at 10 FPS.
   - *Rejected:* Heavy CPU overhead on Windows host; redundant when farm is peaceful.
3. **Approach 3: Dedicated Docker Container:**
   - Standalone custom Docker container with PyTorch/YOLO.
   - *Rejected:* Heavy container image footprint; local Python already has OpenCV DNN ready.

---

## 5. Architectural Specification

```
[ ESP32 PIR Motion ]
        │
        ▼ (MQTT "farm/pir": 1)
[ Home Assistant Automation ]
        │
        ├──> action: camera.snapshot -> config/www/security_snapshot.jpg
        │
        ▼ (MQTT "farm/security/scan_request": 1)
[ Local Vision Detector Service (services/person_detector.py) ]
        │
        ├──> OpenCV DNN / HOG People Detector Model
        │
   ┌────┴─────────────────────────────┐
   ▼ (Human Found)                    ▼ (No Human / Animal)
Annotate Bounding Box             Publish farm/security/human_detected = "OFF"
Save config/www/intruder_alert.jpg  Log non-human motion (False alarm suppressed)
Publish farm/security/human_detected = "ON"
   │
   ▼
[ Home Assistant Escalation ]
   ├──> alarm_control_panel.trigger
   ├──> switch.turn_on: switch.farm_alarm_siren (GPIO 23 Buzzer)
   ├──> persistent_notification with intruder photo
   └──> Lovelace UI card update
```

### Components

#### A. Vision Detection Service (`services/person_detector.py`)
- Subscribes to MQTT topic `farm/security/scan_request`.
- Also monitors `config/www/security_snapshot.jpg` for modifications.
- Uses OpenCV Built-in Person Detector (`cv2.HOGDescriptor_getDefaultPeopleDetector()`) with SVM weight normalization:
  - Input: `config/www/security_snapshot.jpg`.
  - Normalizes detection weights to 0.0–1.0 confidence via sigmoid transformation $\sigma(w) = \frac{1}{1 + e^{-w}}$.
  - Detects person (confidence threshold $\ge 0.50$).
  - If detected: draws bounding box (red, 2px), labels `"INTRUDER DETECTED [XX%]"`, writes timestamp.
  - Saves output to `config/www/intruder_alert.jpg`.
  - Publishes JSON payload to `farm/security/human_detected`:
    ```json
    {
      "state": "ON",
      "confidence": 0.88,
      "timestamp": "2026-11-21 21:20:00"
    }
    ```
  - If no person detected:
    - Publishes `{"state": "OFF", "confidence": 0.0, "timestamp": "..."}` to `farm/security/human_detected`.

#### B. Home Assistant MQTT Entity (`config/configuration.yaml`)
- Add `binary_sensor.farm_human_detected`:
  - `state_topic: "farm/security/human_detected"`
  - `value_template: "{{ value_json.state }}"`
  - `json_attributes_topic: "farm/security/human_detected"`
  - `payload_on: "ON"`
  - `payload_off: "OFF"`
  - `off_delay: 60` (auto-resets after 60 seconds if no further detection)
  - `device_class: "safety"`
  - `icon: "mdi:account-alert"`

#### C. Automations (`config/automations.yaml`)
1. **Trigger Snapshot & Vision Scan:**
   - Trigger: `binary_sensor.farm_motion_detection` state to `'on'` for $\ge 3$ seconds while `alarm_control_panel.farm_security_system` is armed (`armed_away` or `armed_home`).
   - Action: 
     - `camera.snapshot` target `camera.camera` $\rightarrow$ `filename: '/config/www/security_snapshot.jpg'`.
     - MQTT publish `farm/security/scan_request` with payload `"1"`.
2. **Intruder Confirmed Escalation:**
   - Trigger: `binary_sensor.farm_human_detected` state to `'on'` while armed.
   - Action:
     - `alarm_control_panel.alarm_trigger` for `alarm_control_panel.farm_security_system`.
     - `switch.turn_on` for `switch.farm_alarm_siren` (GPIO 23 buzzer).
     - `persistent_notification.create` with title `"🚨 INTRUDER CONFIRMED"` and message displaying link to `/local/intruder_alert.jpg` and confidence score.
3. **Reset on Disarm:**
   - Disarming with PIN `1234` immediately silences siren, dismisses notifications, and resets detection state.

#### D. Lovelace Dashboard Card (`config/farm_dashboard.yaml`)
- Add an "Intruder Alert & Photograph" card directly under the Camera stream view in `farm_dashboard.yaml`:
  - Shows `/local/intruder_alert.jpg` with conditional border styling or badge when `binary_sensor.farm_human_detected` is `'on'`.
  - Shows last detection timestamp and status.

#### E. Test Suite Verification (`tests/test_human_detector.py`)
- Validates:
  1. Positive human image generates `ON` + bounding box in `intruder_alert.jpg`.
  2. Negative image (nature / empty field / non-human) outputs `OFF` without triggering alarm.
  3. End-to-end MQTT trigger and Home Assistant notification delivery.
