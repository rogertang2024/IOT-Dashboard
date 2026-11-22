import paho.mqtt.publish as publish
publish.single("farm/security/scan_request", "1", hostname="localhost", port=1883)
print("Scan request sent!")
