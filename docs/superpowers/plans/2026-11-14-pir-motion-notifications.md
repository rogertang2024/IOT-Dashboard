# Farm PIR Motion Notification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically send an in-dashboard notification in Home Assistant whenever the ESP32 PIR motion sensor detects human or animal movement in the farm area.

**Architecture:** A Home Assistant YAML automation listens for state changes of `binary_sensor.farm_motion_detection` from `off` to `on`. It dispatches a persistent notification via `persistent_notification.create` with a 30-second cooldown to prevent alert flooding.

**Tech Stack:** Home Assistant Automations (YAML), Eclipse Mosquitto MQTT, Docker.

**Spec:** [docs/superpowers/specs/2026-11-14-pir-motion-notifications-design.md](file:///d:/Antigravity%20Projects/IOT_Dashboard/docs/superpowers/specs/2026-11-14-pir-motion-notifications-design.md)

## Global Constraints

- Automation must bind to existing entity `binary_sensor.farm_motion_detection`.
- Action must use `persistent_notification.create` with a unique notification ID.
- Rate-limiting cooldown must be at least 30 seconds to prevent alert storms.

## Review Focus

- Repeated motion triggers within 30 seconds: must be throttled and not produce multiple duplicate notifications.
- Valid YAML syntax in `automations.yaml`: must not fail Home Assistant config validation.
- Message content: must include a readable timestamp and reference the Farm Camera.

---

### Task 1: Configure PIR Motion Alert Automation

**Files:**
- Modify: `config/automations.yaml:1`

**Interfaces:**
- Consumes: Entity `binary_sensor.farm_motion_detection` (MQTT binary sensor)
- Produces: Persistent notification service call `persistent_notification.create`

- [ ] **Step 1: Write the automation configuration into `config/automations.yaml`**

Configure the automation with alias `"Farm: Motion Alert"`, trigger on `binary_sensor.farm_motion_detection` to `'on'`, `mode: single`, action `persistent_notification.create`, followed by a 30-second delay cooldown.

```yaml
- id: 'farm_motion_detection_alert'
  alias: 'Farm: Motion Alert'
  description: 'Notify when PIR sensor detects human or animal movement'
  trigger:
    - platform: state
      entity_id: binary_sensor.farm_motion_detection
      to: 'on'
  mode: single
  action:
    - action: persistent_notification.create
      data:
        title: 'Farm Alert: Motion Detected'
        message: 'PIR motion sensor detected movement (human or animal) at {{ now().strftime("%H:%M:%S") }}. Check the Farm Camera stream.'
        notification_id: 'farm_motion_alert'
    - delay: '00:00:30'
```

- [ ] **Step 2: Verify YAML syntax and file formatting**

Run validation check on the file to ensure valid YAML structure without parser errors.

---

### Task 2: Reload Automations and Verify Notification Trigger

**Files:**
- Verify: Home Assistant runtime state via MQTT test

- [ ] **Step 1: Reload automations in Home Assistant container**

Execute `homeassistant.reload_all` or restart/reload config in container:
`docker exec homeassistant python -c "..."` or restart the container to apply `automations.yaml`.

- [ ] **Step 2: Trigger PIR motion detection via MQTT**

Publish payload `"1"` to topic `farm/pir` using docker Mosquitto client:
`docker exec mqtt mosquitto_pub -t "farm/pir" -m "1"`

- [ ] **Step 3: Verify notification is generated**

Check Home Assistant SQLite database or query active persistent notifications to confirm `farm_motion_alert` was created with the formatted message.

- [ ] **Step 4: Reset PIR motion sensor to idle**

Publish payload `"0"` to topic `farm/pir` to reset state:
`docker exec mqtt mosquitto_pub -t "farm/pir" -m "0"`

