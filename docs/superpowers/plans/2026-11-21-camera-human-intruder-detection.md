# Camera Human Intruder Detection & Photograph Alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local computer-vision intruder detection service that uses the camera to verify human presence on motion, draws a bounding box on the photograph, saves it to the dashboard, and triggers the GPIO 23 siren and alarm.

**Architecture:** An event-driven architecture where Home Assistant takes a camera frame snapshot upon sustained PIR motion while armed and publishes an MQTT scan request. A local Python service running OpenCV analyzes the frame for human presence, annotates the intruder photograph, and publishes detection status to MQTT. Home Assistant then escalates the alarm, sounds the buzzer, and displays the intruder photo on the dashboard.

**Tech Stack:** Python 3.11, OpenCV 4.x (`cv2`), Home Assistant, Mosquitto MQTT, Docker, Lovelace UI.

**Spec:** [`docs/superpowers/specs/2026-11-21-camera-human-intruder-detection-design.md`](file:///d:/Antigravity%20Projects/IOT_Dashboard/docs/superpowers/specs/2026-11-21-camera-human-intruder-detection-design.md)

## Global Constraints
- Host: Windows 10/11 with Python 3.11 and Docker.
- 100% local processing; zero external cloud services, API keys, or paid tokens.
- Mosquitto MQTT broker on `localhost:1883` (container `mqtt:1883`).
- Static web assets stored in `config/www/` and served at `/local/`.
- Siren switch entity: `switch.farm_alarm_siren` (GPIO 23 buzzer).
- Alarm PIN: `1234`.

## Review Focus
1. **Empty / Corrupt Snapshot File:** If the snapshot file does not exist or is corrupted during camera write, `person_detector.py` must catch the exception gracefully and publish an error/no-detection rather than crashing.
2. **False Alarm Suppression:** A motion trigger with an animal/leaves snapshot must produce `state: OFF` and NOT activate the siren or trip the alarm.
3. **Double Trigger / Race Condition:** Rapid repeated motion events while a scan is in flight must not corrupt the output image or drop events.
4. **Clean Disarm Recovery:** Disarming the alarm with PIN `1234` must immediately silence the siren and reset the detection alert state.
5. **Dashboard Cache Busting:** The Lovelace UI image component must refresh properly when `intruder_alert.jpg` is updated.

---

### Task 1: Vision Detection Engine (`services/person_detector.py`)

**Files:**
- Create: `services/person_detector.py`
- Test: `tests/test_person_detector_unit.py`

**Steps:**
- [ ] Write unit test `tests/test_person_detector_unit.py` that generates:
  - A mock image containing a human silhouette/figure (or known test image).
  - A mock blank/nature image without humans.
  - Verifies that `detect_person(image_path)` returns `(True, confidence, bbox)` for human and `(False, 0.0, None)` for non-human.
- [ ] Run `python tests/test_person_detector_unit.py` and confirm it fails (module not found).
- [ ] Implement `services/person_detector.py`:
  - Initialize OpenCV HOG People Detector (`cv2.HOGDescriptor_getDefaultPeopleDetector()`).
  - Implement `detect_person(image_path, confidence_threshold=0.50)` with sigmoid score normalization $\sigma(w) = \frac{1}{1 + e^{-w}}$.
  - If detected, draw a red bounding box (`cv2.rectangle`) with timestamp and `"INTRUDER DETECTED [XX%]"` header, and write to `config/www/intruder_alert.jpg`.
  - Provide both a callable function `process_snapshot(input_path, output_path)` and a standalone MQTT subscriber daemon mode that listens on `farm/security/scan_request` and publishes results to `farm/security/human_detected`.
- [ ] Run `python tests/test_person_detector_unit.py` and confirm tests pass.
- [ ] Commit changes.

---

### Task 2: Home Assistant Configuration & MQTT Sensor

**Files:**
- Modify: `config/configuration.yaml:70-95`
- Test: `tests/test_ha_sensor_config.py`

**Steps:**
- [ ] Write test `tests/test_ha_sensor_config.py` that publishes a mock JSON payload `{"state": "ON", "confidence": 0.85, "timestamp": "2026-11-21 21:00:00"}` to `farm/security/human_detected` and checks SQLite `states` table for `binary_sensor.farm_human_detected == 'on'`.
- [ ] Update `config/configuration.yaml`:
  - Add `binary_sensor.farm_human_detected` under `mqtt.binary_sensor`:
    - `state_topic: "farm/security/human_detected"`
    - `value_template: "{{ value_json.state }}"`
    - `json_attributes_topic: "farm/security/human_detected"`
    - `payload_on: "ON"`
    - `payload_off: "OFF"`
    - `off_delay: 60`
    - `device_class: "safety"`
    - `icon: "mdi:account-alert"`
- [ ] Restart Home Assistant container: `docker restart homeassistant`.
- [ ] Run `python tests/test_ha_sensor_config.py` and verify `binary_sensor.farm_human_detected` is registered and functional.
- [ ] Commit changes.

---

### Task 3: Visual Intrusion Escalation Automations

**Files:**
- Modify: `config/automations.yaml`
- Test: `tests/test_intrusion_automations.py`

**Steps:**
- [ ] Write integration test `tests/test_intrusion_automations.py`:
  - Tests that motion sustained $\ge 3$s while armed requests camera snapshot and publishes `farm/security/scan_request`.
  - Tests that `binary_sensor.farm_human_detected: 'on'` trips the alarm panel to `'triggered'` and turns on `switch.farm_alarm_siren`.
  - Tests that disarming with PIN `1234` silences the siren and dismisses alert notifications.
- [ ] Update `config/automations.yaml`:
  - Update `farm_intrusion_confirmed_alert`:
    - Triggers on `binary_sensor.farm_motion_detection` sustained $\ge 3$s in `armed_away` or `armed_home`.
    - Action: `camera.snapshot` $\rightarrow$ `/config/www/security_snapshot.jpg` and MQTT publish `farm/security/scan_request`.
  - Add `farm_human_intruder_confirmed_alert`:
    - Triggers on `binary_sensor.farm_human_detected` state `to: 'on'` while armed.
    - Action: `alarm_control_panel.alarm_trigger`, `switch.turn_on` for `switch.farm_alarm_siren`, and `persistent_notification.create` with link to `/local/intruder_alert.jpg`.
  - Update `farm_alarm_disarmed_silence`:
    - Ensures intruder notification is dismissed upon entering PIN `1234`.
- [ ] Reload automations in Home Assistant.
- [ ] Run `python tests/test_intrusion_automations.py` and confirm all scenarios pass.
- [ ] Commit changes.

---

### Task 4: Lovelace UI Intruder Photograph Card

**Files:**
- Modify: `config/farm_dashboard.yaml`
- Modify: `config/.storage/lovelace.lovelace`

**Steps:**
- [ ] In `config/farm_dashboard.yaml`, add the **Intruder Alert & Photograph** card right under the Camera card:
  - Picture Entity / Markdown card showing `/local/intruder_alert.jpg`.
  - Status chip showing `binary_sensor.farm_human_detected` (Normal vs Intruder Confirmed).
  - Timestamp indicator.
- [ ] Update `config/.storage/lovelace.lovelace` to synchronize storage mode.
- [ ] Verify dashboard YAML syntax and load status via curl/Python.
- [ ] Commit changes.

---

### Task 5: End-to-End Resilience & Safety Verification

**Files:**
- Create: `tests/test_human_detector_e2e.py`
- Modify: `services/person_detector.py` (background daemon execution)

**Steps:**
- [ ] Launch `services/person_detector.py` daemon in the background or wire it into the automated runner.
- [ ] Execute `tests/test_human_detector_e2e.py`:
  - **Scenario A (False Alarm Suppression):** Inject non-human image $\rightarrow$ trigger motion $\rightarrow$ verify siren remains OFF, alarm remains armed.
  - **Scenario B (Confirmed Intrusion):** Inject human test image $\rightarrow$ trigger motion $\rightarrow$ verify bounding box rendered to `config/www/intruder_alert.jpg`, siren turns ON, alarm enters `triggered`.
  - **Scenario C (Disarm & Recovery):** Enter PIN `1234` $\rightarrow$ verify siren shuts off and system disarms cleanly.
- [ ] Confirm all tests exit with code 0.
- [ ] Commit and summarize to the user.
