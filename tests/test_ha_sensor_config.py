#!/usr/bin/env python3
"""
Test Home Assistant MQTT Sensor Configuration for Visual Human Detection
"""

import time
import json
import sqlite3
import subprocess

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def mqtt_pub(topic, payload, retain=False):
    cmd = ['docker', 'exec', 'mqtt', 'mosquitto_pub', '-t', topic, '-m', payload]
    if retain:
        cmd.append('-r')
    subprocess.run(cmd, check=True)

def get_entity_state(entity_id):
    try:
        conn = sqlite3.connect('file:config/home-assistant_v2.db?mode=ro', uri=True)
        c = conn.cursor()
        c.execute('''
            SELECT s.state 
            FROM states s 
            JOIN states_meta m ON s.metadata_id=m.metadata_id 
            WHERE m.entity_id = ? 
            ORDER BY s.last_updated_ts DESC LIMIT 1
        ''', (entity_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def wait_for_state(entity_id, expected_state, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        state = get_entity_state(entity_id)
        if state == expected_state:
            return state
        time.sleep(0.5)
    return get_entity_state(entity_id)

def test_sensor():
    print("Testing binary_sensor.farm_human_detected configuration...")
    payload = json.dumps({"state": "ON", "confidence": 0.88, "timestamp": "2026-11-21 21:00:00"})
    mqtt_pub("farm/security/human_detected", payload, retain=True)
    state = wait_for_state("binary_sensor.farm_human_detected", "on")
    print(f"State in HA: {state}")
    assert state == "on", f"Expected 'on', got '{state}'"

    # Reset
    reset_payload = json.dumps({"state": "OFF", "confidence": 0.0, "timestamp": "2026-11-21 21:01:00"})
    mqtt_pub("farm/security/human_detected", reset_payload, retain=True)
    state = wait_for_state("binary_sensor.farm_human_detected", "off")
    print(f"State after reset: {state}")
    assert state == "off", f"Expected 'off', got '{state}'"
    print("✅ PASS: binary_sensor.farm_human_detected working properly.")

if __name__ == "__main__":
    test_sensor()
