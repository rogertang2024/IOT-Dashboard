# Smart Farm UI/UX Overhaul & Real-Time Weather/AQI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the Home Assistant dashboard into a modern, agricultural Smart Farm UI/UX with live Internet-fed AQI, PM2.5, barometric pressure, weather forecasts, and dynamic real-time telemetry graphs.

**Architecture:** Use Home Assistant REST sensors to fetch real-time air quality (US AQI, PM2.5) and surface barometric air pressure (hPa) from Open-Meteo APIs for farm coordinates (39.9719, -86.2106). Reorganize dashboard layouts into 4 dedicated agricultural zones: Field Mapping, Microclimate & AQI, Soil & Irrigation, and Security Camera.

**Tech Stack:** Home Assistant Core (YAML / Lovelace), Open-Meteo REST APIs, Leaflet.js, Docker.

**Spec:** [docs/superpowers/specs/2026-11-15-smart-farm-uiux-weather-aqi-design.md](file:///d:/Antigravity%20Projects/IOT_Dashboard/docs/superpowers/specs/2026-11-15-smart-farm-uiux-weather-aqi-design.md)

## Global Constraints
- Sensor fetching must use free Open-Meteo endpoints without API keys.
- Coordinates fixed to farm location (`latitude: 39.9719`, `longitude: -86.2106`).
- Fullscreen map card must remain at the top of the dashboard.
- Must preserve all existing ESP32 farm entities (`switch.farm_water_pump`, `sensor.farm_temperature`, `sensor.farm_soil_moisture`, etc.) and camera (`camera.camera`).

## Review Focus
- Valid JSON parsing in REST sensor value templates.
- Correct unit of measurements (`hPa` for pressure, `AQI` for air quality, `µg/m³` for PM2.5).
- Error-free Lovelace configuration rendering without broken card banners.

---

### Task 1: Add REST Sensors for AQI, PM2.5, and Barometric Air Pressure

**Files:**
- Modify: `config/configuration.yaml:50`

**Interfaces:**
- Consumes: Open-Meteo REST APIs (`api.open-meteo.com` and `air-quality-api.open-meteo.com`)
- Produces: `sensor.farm_barometric_pressure`, `sensor.farm_air_quality_index`, `sensor.farm_pm2_5`

- [ ] **Step 1: Add REST sensor definitions to `config/configuration.yaml`**
- [ ] **Step 2: Validate YAML syntax via Python `yaml.safe_load`**

---

### Task 2: Reload Home Assistant and Verify Sensor States

**Files:**
- Verify: Home Assistant SQLite database & runtime state

- [ ] **Step 1: Restart Home Assistant container**
- [ ] **Step 2: Query Home Assistant states to verify numerical readings for `sensor.farm_air_quality_index`, `sensor.farm_pm2_5`, and `sensor.farm_barometric_pressure`**

---

### Task 3: Redesign Dashboards into Smart Farm Agricultural Zones

**Files:**
- Modify: `config/.storage/lovelace.lovelace`
- Modify: `config/.storage/lovelace`
- Modify: `config/farm_dashboard.yaml`

**Interfaces:**
- Consumes: All farm telemetry entities, live camera, satellite map, weather forecast, AQI and pressure sensors.
- Produces: 4-Zone Smart Farm Lovelace layout.

- [ ] **Step 1: Configure Zone 1 (🌾 Soil Fertility & Field Mapping - Top with Fullscreen)**
- [ ] **Step 2: Configure Zone 2 (🌦️ Microclimate, AQI & Barometric Pressure Gauges)**
- [ ] **Step 3: Configure Zone 3 (💧 Soil & Irrigation Station with Real-time Graphs)**
- [ ] **Step 4: Configure Zone 4 (📹 Security Camera & Wildlife Motion)**
- [ ] **Step 5: Apply layout to all dashboard storage files**

---

### Task 4: Final Verification and UI Validation

**Files:**
- Verify: `http://localhost:8123/` and `/local/fertility_map.html`

- [ ] **Step 1: Restart Home Assistant and verify dashboard loads cleanly**
- [ ] **Step 2: Confirm all gauges, graphs, weather, AQI, and map render without errors**
