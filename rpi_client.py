#!/usr/bin/env python3
"""
Raspberry Pi to Home Assistant MQTT Bridge with Auto-Discovery
Publishes system metrics and sensor telemetry, and listens for control commands.
"""

import json
import os
import shutil
import time
import paho.mqtt.client as mqtt

# GPIO Hardware Setup (Pin 26 for relay)
RELAY_PIN = 26
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
    HAS_GPIO = True
    print(f"[GPIO] Initialized GPIO {RELAY_PIN} as OUTPUT (Relay)")
except (ImportError, RuntimeError) as e:
    HAS_GPIO = False
    print(f"[GPIO] RPi.GPIO not available ({e}). Running in simulation mode.")

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# The IP address of the PC running your Home Assistant and MQTT Docker containers
BROKER_IP = "192.168.1.251"
BROKER_PORT = 1883
DEVICE_NAME = "Raspberry Pi Node"
DEVICE_ID = "rpi_node"

DISCOVERY_PREFIX = "homeassistant"
STATE_TOPIC = f"{DEVICE_ID}/telemetry"
RELAY_COMMAND_TOPIC = f"{DEVICE_ID}/relay1/set"
RELAY_STATE_TOPIC = f"{DEVICE_ID}/relay1/state"

current_relay_state = "OFF"


# ==============================================================================
# TELEMETRY READERS
# ==============================================================================
def get_cpu_temp():
    """Reads Raspberry Pi CPU temperature in Celsius."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(float(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 45.0  # Fallback simulation if running on non-Pi test


def get_system_stats():
    """Reads CPU, RAM, and Disk metrics."""
    try:
        # Load average (approx 1-min CPU load %)
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        cpu_usage = round((load1 / cpu_count) * 100, 1)
    except Exception:
        cpu_usage = 12.0

    # Disk usage %
    total, used, free = shutil.disk_usage("/")
    disk_usage = round((used / total) * 100, 1)

    return cpu_usage, disk_usage


# ==============================================================================
# MQTT CALLBACKS
# ==============================================================================
def on_connect(client, userdata, flags, rc):
    global current_relay_state
    if rc == 0:
        print("[MQTT] Successfully connected to Mosquitto Broker!")
        # Publish discovery configs so Home Assistant auto-detects all sensors
        publish_discovery(client)
        # Subscribe to control commands (e.g., relay toggle)
        client.subscribe(RELAY_COMMAND_TOPIC)
        # Publish initial relay state
        client.publish(RELAY_STATE_TOPIC, current_relay_state, retain=True)
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    global current_relay_state
    payload = msg.payload.decode("utf-8")
    print(f"[COMMAND] Received {msg.topic}: {payload}")

    if msg.topic == RELAY_COMMAND_TOPIC:
        if payload in ["ON", "OFF"]:
            current_relay_state = payload
            if HAS_GPIO:
                GPIO.output(RELAY_PIN, GPIO.HIGH if payload == "ON" else GPIO.LOW)
            client.publish(RELAY_STATE_TOPIC, current_relay_state, retain=True)
            print(f"[RELAY] Switched to {current_relay_state} on GPIO {RELAY_PIN}")


# ==============================================================================
# HOME ASSISTANT AUTO-DISCOVERY
# ==============================================================================
def publish_discovery(client):
    device_info = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "model": "Raspberry Pi",
        "manufacturer": "Raspberry Pi Foundation",
    }

    sensors = [
        {
            "name": "CPU Temperature",
            "stat_t": STATE_TOPIC,
            "val_tpl": "{{ value_json.cpu_temp }}",
            "unit_of_meas": "°C",
            "dev_cla": "temperature",
            "stat_cla": "measurement",
            "uniq_id": f"{DEVICE_ID}_cpu_temp",
        },
        {
            "name": "CPU Usage",
            "stat_t": STATE_TOPIC,
            "val_tpl": "{{ value_json.cpu_usage }}",
            "unit_of_meas": "%",
            "stat_cla": "measurement",
            "uniq_id": f"{DEVICE_ID}_cpu_usage",
        },
        {
            "name": "Disk Usage",
            "stat_t": STATE_TOPIC,
            "val_tpl": "{{ value_json.disk_usage }}",
            "unit_of_meas": "%",
            "stat_cla": "measurement",
            "uniq_id": f"{DEVICE_ID}_disk_usage",
        },
    ]

    for s in sensors:
        topic = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/{s['uniq_id']}/config"
        config = {
            "name": s["name"],
            "state_topic": s["stat_t"],
            "value_template": s["val_tpl"],
            "unit_of_measurement": s["unit_of_meas"],
            "state_class": s.get("stat_cla"),
            "unique_id": s["uniq_id"],
            "device": device_info,
        }
        if "dev_cla" in s:
            config["device_class"] = s["dev_cla"]
        client.publish(topic, json.dumps(config), retain=True)

    # Auto-discover a Switch for 2-way control
    switch_topic = f"{DISCOVERY_PREFIX}/switch/{DEVICE_ID}/relay1/config"
    switch_config = {
        "name": "Pi Relay Switch",
        "command_topic": RELAY_COMMAND_TOPIC,
        "state_topic": RELAY_STATE_TOPIC,
        "unique_id": f"{DEVICE_ID}_relay1",
        "device": device_info,
    }
    client.publish(switch_topic, json.dumps(switch_config), retain=True)
    print("[DISCOVERY] Published Home Assistant auto-discovery configs.")


# ==============================================================================
# MAIN LOOP
# ==============================================================================
if __name__ == "__main__":
    client = mqtt.Client(client_id=DEVICE_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to MQTT Broker at {BROKER_IP}:{BROKER_PORT}...")
    client.connect(BROKER_IP, BROKER_PORT, 60)
    client.loop_start()

    try:
        while True:
            cpu_t = get_cpu_temp()
            cpu_u, disk_u = get_system_stats()

            telemetry = {
                "cpu_temp": cpu_t,
                "cpu_usage": cpu_u,
                "disk_usage": disk_u,
            }

            client.publish(STATE_TOPIC, json.dumps(telemetry))
            print(f"[TELEMETRY] Sent: {telemetry}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping client...")
        if HAS_GPIO:
            GPIO.cleanup()
        client.loop_stop()
        client.disconnect()

