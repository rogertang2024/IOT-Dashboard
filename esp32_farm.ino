#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>

// ==============================================================================
// NETWORK CONFIGURATION
// ==============================================================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

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

// ACTUATORS & LEDS
// NOTE: GPIO 35 is input-only on ESP32, so Red LED is assigned to GPIO 27
int red   = 27;    // Error / Alert LED (changed from 35)
int green = 32;    // Status OK LED
int blue1 = 25;    // Indicator LED 1
int blue2 = 26;    // Indicator LED 2
int pump  = 15;    // Relay / Water Pump Control

DHT dht(dhtPin, DHT11);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsgTime = 0;
const unsigned long publishInterval = 5000; // Publish sensors every 5 seconds

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

  // Send current pump status
  client.publish("farm/pump/state", digitalRead(pump) == HIGH ? "ON" : "OFF", true);
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

  if (strcmp(topic, "farm/pump") == 0) {
    if (message == "ON") {
      digitalWrite(pump, HIGH);
      client.publish("farm/pump/state", "ON", true);
      Serial.println(">> Water pump switched ON via Home Assistant");
    } 
    else if (message == "OFF") {
      digitalWrite(pump, LOW);
      client.publish("farm/pump/state", "OFF", true);
      Serial.println(">> Water pump switched OFF via Home Assistant");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT Broker (");
    Serial.print(mqtt_server);
    Serial.print(")... ");

    String clientId = "ESP32Farm-" + String((uint32_t)ESP.getEfuseMac(), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("CONNECTED!");
      client.subscribe("farm/pump");
      publish_homeassistant_discovery();
    } else {
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
  // Serial must be started first to view boot messages
  Serial.begin(115200);
  delay(200);

  // Initialize Pin Modes
  pinMode(green, OUTPUT);
  pinMode(red, OUTPUT);
  pinMode(blue1, OUTPUT);
  pinMode(blue2, OUTPUT);
  pinMode(pump, OUTPUT);
  digitalWrite(pump, LOW); // Ensure pump starts in OFF state

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
  client.loop(); // Keeps MQTT connection alive and handles pump commands instantly

  // Non-blocking timer: read and publish sensors every 5 seconds
  unsigned long now = millis();
  if (now - lastMsgTime >= publishInterval) {
    lastMsgTime = now;

    int pirVal   = digitalRead(pir);
    float temp   = dht.readTemperature();
    int ldrVal   = digitalRead(ldr);
    int waterVal = digitalRead(water);
    int rawSoil  = analogRead(soil);

    // Check sensor reading validity
    if (isnan(temp)) {
      digitalWrite(red, HIGH);
      digitalWrite(green, LOW);
      Serial.println("Warning: DHT sensor read failure!");
    } else {
      digitalWrite(green, HIGH);
      digitalWrite(red, LOW);
    }

    // Map 12-bit ADC (0 - 4095) to percentage (0 - 100%)
    int soilPercentage = map(rawSoil, 4095, 0, 0, 100);
    soilPercentage = constrain(soilPercentage, 0, 100);

    // Indicator LEDs for LDR
    if (ldrVal == 1) {
      digitalWrite(blue1, HIGH);
      digitalWrite(blue2, HIGH);
    } else {
      digitalWrite(blue1, LOW);
      digitalWrite(blue2, LOW);
    }

    // Auto-irrigation check (optional local safety)
    if (soilPercentage < 20 && waterVal == 1) {
      Serial.println("Soil dry and water available: Auto pump ON");
      digitalWrite(pump, HIGH);
      client.publish("farm/pump/state", "ON", true);
    }

    if (pirVal == 1) {
      Serial.println("Motion detected (Animal / Human)");
    }

    // Print Telemetry to Serial Monitor
    Serial.println("-------------------------------------");
    Serial.printf("Temp: %.1f °C | Soil: %d %% | PIR: %d | Water: %d | LDR: %d\n",
                  temp, soilPercentage, pirVal, waterVal, ldrVal);

    // Publish to MQTT for Home Assistant
    if (!isnan(temp)) {
      client.publish("farm/temp", String(temp, 1).c_str());
    }
    client.publish("farm/soil", String(soilPercentage).c_str());
    client.publish("farm/pir", String(pirVal).c_str());
    client.publish("farm/water", String(waterVal).c_str());
    client.publish("farm/ldr", String(ldrVal).c_str());
  }
}

