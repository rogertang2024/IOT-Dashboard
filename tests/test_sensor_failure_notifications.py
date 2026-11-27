#!/usr/bin/env python3
"""
Sensor Failure & Notification Verification Test
Tests:
1. Individual Sensor Failure Alert (sensor.farm_temperature -> unavailable)
2. Connectivity Loss Watchdog Alert (binary_sensor.farm_node_connectivity -> off for 15s)
3. Equipment / Water Sensor Dry-Run Hazard Alert (pump on + water off)
"""

import json
import time
import urllib.request
from pathlib import Path
import paho.mqtt.publish as publish
import websocket

HA_URL = "http://localhost:8123"
HA_WS_URL = "ws://localhost:8123/api/websocket"
MQTT_HOST = "localhost"
MQTT_PORT = 1883


def load_ha_token() -> str:
    secrets_path = Path(__file__).resolve().parent.parent / "config" / "secrets.yaml"
    for line in secrets_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("ha_token:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("ha_token not found in config/secrets.yaml")


def ha_request(method: str, path: str, token: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{HA_URL}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else None


def mqtt_pub(topic: str, payload: str, retain: bool = False):
    publish.single(topic, payload, hostname=MQTT_HOST, port=MQTT_PORT, retain=retain)


def get_notifications(token: str) -> dict[str, dict]:
    """Fetch active persistent notifications via HA WebSocket API."""
    ws = websocket.create_connection(HA_WS_URL, timeout=10)
    try:
        auth_req = json.loads(ws.recv())
        assert auth_req.get("type") == "auth_required"
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_res = json.loads(ws.recv())
        assert auth_res.get("type") == "auth_ok", f"WS auth failed: {auth_res}"
        ws.send(json.dumps({"id": 1, "type": "persistent_notification/get"}))
        res = json.loads(ws.recv())
        assert res.get("success"), f"persistent_notification/get failed: {res}"
        raw = res.get("result", {})
        if isinstance(raw, list):
            return {item["notification_id"]: item for item in raw if "notification_id" in item}
        return raw
    finally:
        ws.close()


def wait_for_notification(token: str, notification_id: str, timeout: int = 25) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        notifs = get_notifications(token)
        if notification_id in notifs:
            return notifs[notification_id]
        time.sleep(1)
    raise AssertionError(
        f"Timed out waiting for {notification_id}. Active notifications: {list(get_notifications(token).keys())}"
    )


def main():
    token = load_ha_token()
    print("=" * 70)
    print("SENSOR FAILURE & NOTIFICATION TEST SUITE")
    print("=" * 70)

    # 1. Reload automations
    print("\n[1/4] Reloading Home Assistant automations...")
    ha_request("POST", "/api/services/automation/reload", token, {})
    time.sleep(2)

    # Verify new automations are loaded
    states = ha_request("GET", "/api/states", token)
    auto_states = {s["entity_id"]: s["state"] for s in states if s["entity_id"].startswith("automation.")}
    assert auto_states.get("automation.safety_sensor_failure_alert") == "on", (
        f"automation.safety_sensor_failure_alert not on: {auto_states.get('automation.safety_sensor_failure_alert')}"
    )
    print("  PASS: safety_sensor_failure_alert is ON")

    # 2. Test Individual Sensor Failure (sensor.farm_temperature -> unavailable)
    print("\n[2/4] Testing individual sensor failure (sensor.farm_temperature -> unavailable)...")
    mqtt_pub("farm/temp", "24.0")
    time.sleep(1.5)
    ha_request(
        "POST",
        "/api/states/sensor.farm_temperature",
        token,
        {"state": "unavailable", "attributes": {"friendly_name": "Farm Temperature", "unit_of_measurement": "°C"}},
    )
    notif_sensor = wait_for_notification(
        token, "farm_sensor_failure_sensor_farm_temperature", timeout=12
    )
    print(f"  PASS: Notification created -> {notif_sensor.get('title')}")
    print(f"        Message: {notif_sensor.get('message', '').strip()}")

    # 3. Test Connectivity Watchdog (Node Offline for 15s)
    print("\n[3/4] Testing connectivity loss watchdog (farm/status -> offline for 15s)...")
    mqtt_pub("farm/status", "online", retain=True)
    time.sleep(1.5)
    mqtt_pub("farm/status", "offline", retain=True)
    notif_offline = wait_for_notification(token, "farm_offline_alert", timeout=22)
    print(f"  PASS: Notification created -> {notif_offline.get('title')}")
    print(f"        Message: {notif_offline.get('message', '').strip()}")

    # 4. Test Dry-Run / Water Sensor Hazard Notification
    print("\n[4/4] Testing water-level / pump dry-run hazard notification...")
    mqtt_pub("farm/water", "1")
    mqtt_pub("farm/pump/state", "ON")
    time.sleep(1.5)
    mqtt_pub("farm/water", "0")
    notif_pump = wait_for_notification(token, "farm_hazard_pump", timeout=10)
    print(f"  PASS: Notification created -> {notif_pump.get('title')}")
    print(f"        Message: {notif_pump.get('message', '').strip()}")

    print("\n" + "=" * 70)
    print("ALL 3 SENSOR FAILURE NOTIFICATION TESTS PASSED!")
    print("Notifications are currently active in Home Assistant UI.")
    print("=" * 70)


if __name__ == "__main__":
    main()
