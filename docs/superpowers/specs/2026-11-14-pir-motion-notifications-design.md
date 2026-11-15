# Design: Farm PIR Motion Notification Automation

## Intent & Why
Notify the user directly inside the Home Assistant dashboard whenever the ESP32 Farm PIR sensor detects human or animal movement in the farm area.

## Goals
- Detect state change of `binary_sensor.farm_motion_detection` from `off` to `on`.
- Send an in-dashboard persistent notification (`persistent_notification.create`) with title, description, and timestamp.
- Include a debounce/cooldown (e.g. 30 seconds) so continuous movement does not spam notifications.

## Non-Goals
- Computer vision AI on the camera stream (user chose PIR sensor trigger).
- External push notifications or third-party webhooks (e.g. Telegram/Discord).

## Approaches Considered
- **Approach 1 (Chosen):** In-Dashboard Persistent Notification using Home Assistant's native notification system. Instant setup, zero external dependencies or account requirements.
- **Approach 2:** Mobile Push Notifications via Home Assistant Companion App. Rejected by user preference for simple in-dashboard alert.

## Implementation Details
1. Add automation to `config/automations.yaml`:
   - **Trigger:** `binary_sensor.farm_motion_detection` changes to `'on'`.
   - **Mode:** `single` with a `delay` (30s cooldown) or throttle to prevent duplicate triggers.
   - **Action:** Call service `persistent_notification.create` with:
     - Title: `"Farm Alert: Motion Detected"`
     - Message: `"PIR motion sensor detected movement (human or animal) at {{ now().strftime('%H:%M:%S') }}. Check the Farm Camera stream."`
     - Notification ID: `"farm_motion_alert"` (or timestamped for history).
2. Reload Home Assistant automations.
3. Test by simulating or publishing MQTT `"1"` to `farm/pir` and verifying the notification pops up in Home Assistant.

