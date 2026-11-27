#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ==============================================================================
// NETWORK CONFIGURATION
// ==============================================================================
const char* ssid     = "YOUR_WIFI_SSID";       // Replace with your WiFi SSID
const char* password = "YOUR_WIFI_PASSWORD";   // Replace with your WiFi password

// The IP of the PC running the Mosquitto MQTT broker
const char* mqtt_server = "192.168.1.251";
const int mqtt_port = 1883;

// ==============================================================================
// PIN DEFINITIONS
// ==============================================================================
// SENSORS
int ldr   = 33;    // LDR Light Sensor (Digital/Analog)
int dhtPin = 4;    // DHT11 Data Pin
int soil  = 34;    // Soil Moisture (ADC1 - Input only)
int pir   = 13;    // PIR Motion Sensor
int water = 12;    // Water Level Sensor

// ACTUATORS, BUZZER & LEDS
int red    = 27;   // Error / Alert LED
int green  = 32;   // Status OK LED
int blue1  = 25;   // Indicator LED 1
int blue2  = 26;   // Indicator LED 2
int pump   = 15;   // Relay / Water Pump Control
int buzzer = 23;   // Siren / Alarm Buzzer (GPIO 23)

DHT dht(dhtPin, DHT11);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsgTime = 0;
const unsigned long publishInterval = 5000; // Periodic sensor heartbeat (5 seconds)

// Edge Detection State Tracking
int lastPirState = -1;
int lastWaterState = -1;

// ==============================================================================
// HOME ASSISTANT AUTO-DISCOVERY
// ==============================================================================
void publish_homeassistant_discovery() {
  Serial.println("Publishing Home Assistant MQTT discovery configs...");

  String device = ",\"dev\":{\"ids\":[\"esp32_farm\"],\"name\":\"Smart Farm ESP32\",\"mf\":\"DIY\",\"mdl\":\"ESP32-WROOM\"}}";

  // 1. Temperature Sensor
  client.publish("homeassistant/sensor/esp32_farm/temp/config",
    ("{\"name\":\"Farm Temperature\",\"stat_t\":\"farm/temp\",\"unit_of_meas\":\"°C\",\"dev_cla\":\"temperature\",\"stat_cla\":\"measurement\",\"uniq_id\":\"farm_temp\"" + device).c_str(), true);

  // 2. Soil Moisture Sensor
  client.publish("homeassistant/sensor/esp32_farm/soil/config",
    ("{\"name\":\"Farm Soil Moisture\",\"stat_t\":\"farm/soil\",\"unit_of_meas\":\"%\",\"stat_cla\":\"measurement\",\"icon\":\"mdi:watering-can\",\"uniq_id\":\"farm_soil\"" + device).c_str(), true);

  // 3. PIR Motion Detector (Binary Sensor)
  client.publish("homeassistant/binary_sensor/esp32_farm/pir/config",
    ("{\"name\":\"Farm Motion Detection\",\"stat_t\":\"farm/pir\",\"payload_on\":\"1\",\"payload_off\":\"0\",\"dev_cla\":\"motion\",\"uniq_id\":\"farm_pir\"" + device).c_str(), true);

  // 4. Water Level Sensor (Binary Sensor)
  client.publish("homeassistant/binary_sensor/esp32_farm/water/config",
    ("{\"name\":\"Farm Water Level\",\"stat_t\":\"farm/water\",\"payload_on\":\"1\",\"payload_off\":\"0\",\"dev_cla\":\"moisture\",\"uniq_id\":\"farm_water\"" + device).c_str(), true);

  // 5. LDR Light Sensor (Binary Sensor)
  client.publish("homeassistant/binary_sensor/esp32_farm/ldr/config",
    ("{\"name\":\"Farm Light Level\",\"stat_t\":\"farm/ldr\",\"payload_on\":\"1\",\"payload_off\":\"0\",\"dev_cla\":\"light\",\"uniq_id\":\"farm_ldr\"" + device).c_str(), true);

  // 6. Water Pump Switch (2-way Control)
  client.publish("homeassistant/switch/esp32_farm/pump/config",
    ("{\"name\":\"Farm Water Pump\",\"cmd_t\":\"farm/pump\",\"stat_t\":\"farm/pump/state\",\"pl_on\":\"ON\",\"pl_off\":\"OFF\",\"icon\":\"mdi:pump\",\"uniq_id\":\"farm_pump\"" + device).c_str(), true);

  // 7. Security Siren Buzzer Switch
  client.publish("homeassistant/switch/esp32_farm/siren/config",
    ("{\"name\":\"Farm Alarm Siren\",\"cmd_t\":\"farm/alarm/siren\",\"stat_t\":\"farm/alarm/siren/state\",\"pl_on\":\"ON\",\"pl_off\":\"OFF\",\"icon\":\"mdi:bullhorn\",\"uniq_id\":\"farm_siren\"" + device).c_str(), true);

  // 8. Node Connectivity Status (Binary Sensor)
  client.publish("homeassistant/binary_sensor/esp32_farm/status/config",
    ("{\"name\":\"Farm Node Connectivity\",\"stat_t\":\"farm/status\",\"payload_on\":\"online\",\"payload_off\":\"offline\",\"dev_cla\":\"connectivity\",\"uniq_id\":\"farm_status\"" + device).c_str(), true);

  // Send current status
  client.publish("farm/pump/state", digitalRead(pump) == HIGH ? "ON" : "OFF", true);
  client.publish("farm/alarm/siren/state", digitalRead(buzzer) == HIGH ? "ON" : "OFF", true);
  client.publish("farm/status", "online", true);
}

// ==============================================================================
// WIFI & MQTT CONNECTION
// ==============================================================================
void setup_wifi() {
  delay(10);
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  message.trim();
  message.toUpperCase();

  Serial.print("Received MQTT [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Pump Command Handling with Safety Check
  if (strcmp(topic, "farm/pump") == 0) {
    if (message == "ON") {
      int currentWater = digitalRead(water);
      if (currentWater == 0) {
        // AUTONOMOUS SAFETY INTERLOCK: Tank empty, refuse to run pump
        digitalWrite(pump, LOW);
        client.publish("farm/pump/state", "OFF", true);
        client.publish("farm/safety/interlock", "DRY_RUN_PREVENTED", true);
        Serial.println(">> REJECTED PUMP ON: Water level is 0! Dry run blocked.");
      } else {
        digitalWrite(pump, HIGH);
        client.publish("farm/pump/state", "ON", true);
        Serial.println(">> Water pump switched ON");
      }
    } 
    else if (message == "OFF") {
      digitalWrite(pump, LOW);
      client.publish("farm/pump/state", "OFF", true);
      Serial.println(">> Water pump switched OFF");
    }
  }

  // Siren / Buzzer Command Handling
  if (strcmp(topic, "farm/alarm/siren") == 0) {
    if (message == "ON") {
      digitalWrite(buzzer, HIGH);
      digitalWrite(red, HIGH);
      client.publish("farm/alarm/siren/state", "ON", true);
      Serial.println(">> SIREN ACTIVATED (GPIO 23) <<");
    } else if (message == "OFF") {
      digitalWrite(buzzer, LOW);
      digitalWrite(red, LOW);
      client.publish("farm/alarm/siren/state", "OFF", true);
      Serial.println(">> Siren Silenced <<");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT Broker (");
    Serial.print(mqtt_server);
    Serial.print(")... ");

    String clientId = "ESP32Farm-" + String((uint32_t)ESP.getEfuseMac(), HEX);

    // Connect with MQTT Last Will and Testament (LWT)
    // If ESP32 abruptly disconnects or loses power, Mosquitto automatically publishes "offline"
    if (client.connect(clientId.c_str(), "farm/status", 1, true, "offline")) {
      Serial.println("CONNECTED!");
      client.publish("farm/status", "online", true);
      client.subscribe("farm/pump");
      client.subscribe("farm/alarm/siren");
      publish_homeassistant_discovery();
    } else {
      digitalWrite(red, HIGH);
      digitalWrite(green, LOW);
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" - Retrying in 3 seconds...");
      delay(3000);
    }
  }
}

// ==============================================================================
// SETUP
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(200);

  // Initialize Pin Modes
  pinMode(green, OUTPUT);
  pinMode(red, OUTPUT);
  pinMode(blue1, OUTPUT);
  pinMode(blue2, OUTPUT);
  pinMode(pump, OUTPUT);
  pinMode(buzzer, OUTPUT);

  digitalWrite(pump, LOW);   // Ensure pump starts in OFF state
  digitalWrite(buzzer, LOW); // Ensure siren starts in OFF state

  pinMode(pir, INPUT);
  pinMode(ldr, INPUT);
  pinMode(water, INPUT);
  pinMode(soil, INPUT);

  // Initialize DHT Sensor
  dht.begin();

  // Connect Network
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

// ==============================================================================
// LOOP
// ==============================================================================
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // 1. HARDWARE FAILSAFE INTERLOCK (Evaluated every loop cycle < 50ms)
  int currentWater = digitalRead(water);
  if (currentWater == 0 && digitalRead(pump) == HIGH) {
    digitalWrite(pump, LOW);
    client.publish("farm/pump/state", "OFF", true);
    client.publish("farm/safety/interlock", "DRY_RUN_EMERGENCY_SHUTDOWN", true);
    Serial.println(">> CRITICAL SAFETY INTERLOCK: Water reservoir depleted! Shutting down pump immediately! <<");
  }

  // 2. IMMEDIATE EDGE-TRIGGERED PUBLISHING (Sub-second event dispatch)
  int currentPir = digitalRead(pir);
  if (currentPir != lastPirState) {
    lastPirState = currentPir;
    client.publish("farm/pir", String(currentPir).c_str());
    Serial.print("Edge Trigger -> PIR Motion: ");
    Serial.println(currentPir);
  }

  if (currentWater != lastWaterState) {
    lastWaterState = currentWater;
    client.publish("farm/water", String(currentWater).c_str(), true);
    Serial.print("Edge Trigger -> Water Level: ");
    Serial.println(currentWater);
  }

  // 3. PERIODIC HEARTBEAT TELEMETRY (Every 5 seconds)
  unsigned long now = millis();
  if (now - lastMsgTime >= publishInterval) {
    lastMsgTime = now;

    float temp  = dht.readTemperature();
    int ldrVal  = digitalRead(ldr);
    int rawSoil = analogRead(soil);
    bool dhtOk  = !isnan(temp);

    // Check sensor & node health (preserve red LED if siren is active)
    if (!dhtOk) {
      digitalWrite(red, HIGH);
      digitalWrite(green, LOW);
      Serial.println("Warning: DHT sensor read failure!");
    } else {
      digitalWrite(green, HIGH);
      if (digitalRead(buzzer) == LOW) {
        digitalWrite(red, LOW);
      }
    }

    // Convert raw analog soil reading to percentage (0 - 100%)
    int soilPercent = map(rawSoil, 4095, 1500, 0, 100);
    soilPercent = constrain(soilPercent, 0, 100);

    // Publish periodic telemetry for ALL sensors every 5s
    client.publish("farm/status", "online", true); // Heartbeat
    client.publish("farm/ldr", String(ldrVal).c_str());
    client.publish("farm/soil", String(soilPercent).c_str());
    client.publish("farm/pir", String(currentPir).c_str());
    client.publish("farm/water", String(currentWater).c_str(), true);
    if (dhtOk) {
      client.publish("farm/temp", String(temp, 1).c_str());
    }

    // Auto night lighting
    if (ldrVal == 1) {
      digitalWrite(blue1, HIGH);
      digitalWrite(blue2, HIGH);
    } else {
      digitalWrite(blue1, LOW);
      digitalWrite(blue2, LOW);
    }
  }
}
