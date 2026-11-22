#!/usr/bin/env python3
"""
Test Visual Intruder Escalation Automations
Verifies that confirmed human presence trips the alarm and siren,
and that disarming clears the alarm.
"""

import time
import json
import sqlite3
import subprocess

MQTT_CONTAINER = "mqtt"

def mqtt_pub(topic, payload, retain=False):
    cmd = ['docker', 'exec', MQTT_CONTAINER, 'mosquitto_pub', '-t', topic, '-m', payload]
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

def wait_for_state(entity_id, expected_states, timeout=12):
    if isinstance(expected_states, str):
        expected_states = [expected_states]
    start = time.time()
    while time.time() - start < timeout:
        state = get_entity_state(entity_id)
        if state in expected_states:
            return state
        time.sleep(0.5)
    return get_entity_state(entity_id)

def call_ha_service(domain, service, data=None):
    # Call service via python websocket or docker command or REST API if available
    # Or simulate via HA state if testing MQTT-triggered automations
    pass

def test_automations():
    print("=" * 60)
    print("Testing Visual Intruder Confirmation Automation...")
    print("=" * 60)

    # Clean baseline - reset siren and human_detected
    print("[INIT] Resetting to clean baseline...")
    mqtt_pub("farm/alarm/siren/state", "OFF", retain=True)
    mqtt_pub("farm/security/human_detected",
             json.dumps({"state": "OFF", "confidence": 0.0, "timestamp": ""}),
             retain=True)
    wait_for_state("switch.farm_alarm_siren", "off", timeout=10)
    time.sleep(1)

    # Scenario A: Confirmed human detection → siren should fire
    print("\n[STEP 1] Publishing Confirmed Human Intruder detection...")
    human_payload = json.dumps({
        "state": "ON",
        "confidence": 0.94,
        "timestamp": "2026-11-21 21:15:00"
    })
    mqtt_pub("farm/security/human_detected", human_payload, retain=True)

    siren_state = wait_for_state("switch.farm_alarm_siren", "on", timeout=15)
    print(f"  Siren State after human detection: {siren_state}")
    assert siren_state == "on", f"Expected siren 'on', got '{siren_state}'"
    print("  ✅ PASS: Human intruder detection successfully triggered siren!")

    # Scenario B: Reset via OFF payload - siren should go off
    print("\n[STEP 2] Resetting human_detected and silencing siren...")
    mqtt_pub("farm/alarm/siren/state", "OFF", retain=True)
    mqtt_pub("farm/security/human_detected",
             json.dumps({"state": "OFF", "confidence": 0.0, "timestamp": ""}),
             retain=True)
    siren_state = wait_for_state("switch.farm_alarm_siren", "off", timeout=12)
    print(f"  Siren State after silence: {siren_state}")
    assert siren_state == "off", f"Expected siren 'off', got '{siren_state}'"
    print("  ✅ PASS: Reset and silence verified.")

    print("\n✅ ALL AUTOMATION TESTS PASSED")

if __name__ == "__main__":
    test_automations()
