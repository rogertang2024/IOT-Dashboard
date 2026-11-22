# Smart Security and Safety System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified security and equipment safety system for the farm with PIN authentication, multi-sensor correlation, false-positive filtering, local autonomous fallback, connectivity watchdog, and automated resilience testing.

**Architecture:** Home Assistant native `manual` Alarm Control Panel (`alarm_control_panel.farm_security`, PIN: `1234`) coordinated with MQTT sensors and ESP32 firmware on GPIO 23 (buzzer). Multi-tier escalation from local buzzer/LEDs to dashboard banners and mobile snapshots. Autonomous local cutoff on ESP32 for pump dry-run protection.

**Tech Stack:** Home Assistant Core (YAML / Alarm Control Panel), Eclipse Mosquitto MQTT, Arduino C++ (ESP32), Python 3 (automated test suite).

**Spec:** [docs/superpowers/specs/2026-11-21-smart-security-safety-system-design.md](file:///d:/Antigravity%20Projects/IOT_Dashboard/docs/superpowers/specs/2026-11-21-smart-security-safety-system-design.md)

## Global Constraints
- Buzzer assigned to GPIO 23 on ESP32.
- PIN code fixed to `1234`.
- LWT topic: `farm/status` with `online` / `offline`.
- False alarm temporal debounce threshold: 3 seconds.
- Snapshot path: `/config/www/security_snapshot.jpg`.

## Review Focus
- Momentary PIR triggers (< 3s) while Armed Away must not trip alarm.
- Water reservoir at 0 must immediately disengage pump relay and lock out pump command.
- MQTT broker disconnect must flip `binary_sensor.farm_node_connectivity` to off.
- `alarm_control_panel` PIN keypad must disarm only with `1234`.
- ESP32 firmware must compile cleanly and handle edge-triggered publishing.

---

### Task 1: Update ESP32 Firmware with Siren Buzzer, Edge Triggers & Local Safety Interlock

**Files:**
- Modify: `esp32_farm.ino`

**Interfaces:**
- Consumes: GPIO 23 (buzzer), GPIO 15 (pump), GPIO 12 (water), GPIO 13 (pir)
- Produces: MQTT LWT `farm/status`, edge-triggered MQTT updates, topic `farm/alarm/siren` handler

- [ ] **Step 1: Add GPIO 23 Buzzer definition and pin configuration**
- [ ] **Step 2: Add MQTT Last Will & Testament (LWT) configuration to `reconnect()`**
  Publish `farm/status` = `online` on connect with LWT set to `offline` (retain=true).
- [ ] **Step 3: Implement immediate edge-triggered publishing for PIR and Water sensors**
- [ ] **Step 4: Implement autonomous hardware pump dry-run interlock in `loop()`**
  If `waterVal == 0` and pump is HIGH, immediately force pump LOW and publish `farm/pump/state` OFF.
- [ ] **Step 5: Add subscription and callback handler for `farm/alarm/siren`** (`ON` = digitalWrite(23, HIGH), `OFF` = digitalWrite(23, LOW)).

---

### Task 2: Configure Home Assistant Alarm Panel, Siren Switch & Safety Sensors

**Files:**
- Modify: `config/configuration.yaml`

**Interfaces:**
- Consumes: MQTT topics `farm/status`, `farm/pir`, `farm/water`, `farm/temp`, `farm/alarm/siren`
- Produces: `alarm_control_panel.farm_security`, `switch.farm_alarm_siren`, `binary_sensor.farm_node_connectivity`, `binary_sensor.farm_pump_dry_run_risk`, `sensor.farm_security_health_summary`

- [ ] **Step 1: Add `alarm_control_panel` manual integration with PIN `1234`, 30s delays**
- [ ] **Step 2: Add MQTT switch for `switch.farm_alarm_siren` (command_topic: `farm/alarm/siren`)**
- [ ] **Step 3: Add safety template binary sensors in `configuration.yaml`**
  - `binary_sensor.farm_node_connectivity` (tracks `farm/status` == 'online')
  - `binary_sensor.farm_pump_dry_run_risk` (pump == 'on' and water == 'off')
  - `binary_sensor.farm_sensor_health` (flags NaN/missing readings)
  - `sensor.farm_security_health_summary` (human-readable status overview)
- [ ] **Step 4: Validate YAML syntax using Python**

---

### Task 3: Build Security & Safety Automations

**Files:**
- Modify: `config/automations.yaml`

**Interfaces:**
- Consumes: `alarm_control_panel.farm_security`, `binary_sensor.farm_motion_detection`, `switch.farm_water_pump`, `binary_sensor.farm_water_level`
- Produces: Alarm triggers, siren activation, snapshot capture, notifications

- [ ] **Step 1: Implement 3-second sustained motion intrusion automation**
  Trigger: `binary_sensor.farm_motion_detection` to `'on'` for 3 seconds.
  Condition: Alarm is in `armed_away`.
  Action: Call `alarm_control_panel.alarm_trigger`, turn on `switch.farm_alarm_siren`, capture `camera.snapshot`.
- [ ] **Step 2: Implement Dry-Run Emergency Interlock automation**
  Trigger: `binary_sensor.farm_water_level` to `'off'` while `switch.farm_water_pump` is `'on'`.
  Action: Force `switch.farm_water_pump` to `'off'`, create persistent hazard notification.
- [ ] **Step 3: Implement Alarm Siren & Notification Escalation automation**
  Trigger: `alarm_control_panel.farm_security` state changes to `triggered`.
  Action: Dispatch persistent notification + camera snapshot attachment, turn on physical buzzer (`switch.farm_alarm_siren`).
- [ ] **Step 4: Implement Alarm Disarm Siren Silence automation**
  Trigger: `alarm_control_panel.farm_security` state changes to `disarmed`.
  Action: Turn off `switch.farm_alarm_siren`.
- [ ] **Step 5: Implement Connectivity Loss Watchdog automation**
  Trigger: `binary_sensor.farm_node_connectivity` changes to `'off'`.
  Action: Create urgent system notification: "Alert: Farm node connectivity lost!".

---

### Task 4: Integrate Alarm Keypad & Security Health Matrix into Dashboards

**Files:**
- Modify: `config/.storage/lovelace.lovelace`
- Modify: `config/.storage/lovelace`
- Modify: `config/farm_dashboard.yaml`

**Interfaces:**
- Consumes: `alarm_control_panel.farm_security`, safety sensors, siren switch
- Produces: Visual keypad and security overview card on main dashboard

- [ ] **Step 1: Add `alarm-panel` card with numeric PIN keypad right beneath the Satellite Map**
- [ ] **Step 2: Add Security & Safety Health Matrix status badge card**
- [ ] **Step 3: Synchronize across `lovelace.lovelace`, `lovelace`, and `farm_dashboard.yaml`**

---

### Task 5: Build and Run Automated Resilience & Safety Test Suite

**Files:**
- Create: `tests/test_safety_system.py`

**Interfaces:**
- Consumes: Mosquitto MQTT (`localhost:1883`), Home Assistant SQLite DB (`config/home-assistant_v2.db`)
- Produces: Pass/Fail verification report across 5 scenarios

- [ ] **Step 1: Write test script covering:**
  - Test A: 1-second PIR motion spike $\rightarrow$ Assert alarm remains Armed (false alarm suppressed)
  - Test B: 3.5-second continuous PIR motion $\rightarrow$ Assert alarm transitions to `triggered` & siren activated
  - Test C: Pump ON + Water 0 $\rightarrow$ Assert pump immediately forced OFF
  - Test D: Disarm with PIN `1234` $\rightarrow$ Assert alarm returns to `disarmed` & siren silenced
  - Test E: Connectivity LWT offline $\rightarrow$ Assert node connectivity flags offline
- [ ] **Step 2: Run test suite against live Home Assistant and verify all tests pass**
- [ ] **Step 3: Clean up and document test outcomes**
