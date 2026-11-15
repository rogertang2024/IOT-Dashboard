# Design: Smart Farm UI/UX Overhaul with Real-Time Weather, AQI, and Barometric Pressure

## Intent & Why
Provide a complete, modern agricultural dashboard for the smart farm by integrating missing live environmental telemetry (local Weather, Air Quality Index, and Barometric Air Pressure) pulled automatically from meteorological APIs, paired with an organized, mobile-first farm UI/UX layout.

## Goals
1. **Live Internet Environmental Data:**
   - Real-time Air Quality Index (`sensor.farm_air_quality_index`) and PM2.5 (`sensor.farm_pm2_5`).
   - Real-time Barometric Air Pressure (`sensor.farm_barometric_pressure` in hPa).
   - Local hyper-local weather forecast card (`weather.smart_farm` or Met.no/Open-Meteo) based on farm coordinates (`39.9719, -86.2106`).
2. **Smart Farm UI/UX Redesign:**
   - Clean, agricultural layout organized into 4 logical zones:
     - 🌾 **Soil Fertility & Field Mapping** (Satellite map with live phone GPS at the top).
     - 🌦️ **Microclimate, AQI & Atmospheric Pressure** (Weather forecast, AQI color-coded gauge, barometric pressure gauge).
     - 💧 **Irrigation & Soil Telemetry Station** (Live soil moisture, soil temperature, water pump control, reservoir level, LDR light level).
     - 📹 **Wildlife & Security Monitor** (Live camera stream and PIR motion detection indicator).
3. **Dynamic Real-Time Graphs:**
   - Enhanced history graphs for soil moisture, temperature, and barometric pressure trends with proper agricultural ranges and update frequencies.

## Non-Goals
- Requiring the user to purchase additional hardware sensors for AQI/pressure (pulled directly from free live APIs).
- Requiring paid third-party API accounts or tokens.

## Approaches Considered
- **Approach 1 (Chosen):** Native REST and Meteorological API feeds (Open-Meteo) configured directly in Home Assistant. 100% free, zero API keys or user sign-ups, accurate to farm GPS coordinates.
- **Approach 2:** Third-party station accounts (OpenWeatherMap + WAQI). Rejected due to requiring account registration and private API key management.

## Implementation Details
1. **Configuration (`config/configuration.yaml`):**
   - Add `rest` sensor platform fetching live AQI, PM2.5, and barometric pressure every 10 minutes from Open-Meteo.
2. **Dashboard Configuration (`config/.storage/lovelace.lovelace` and `config/farm_dashboard.yaml`):**
   - Reconstruct dashboard into themed card stacks with headers, icons, gauges, weather forecast card, and history graphs.
3. **Verification:**
   - Verify sensor values are successfully populated in Home Assistant states database.
   - Verify all cards render cleanly on both mobile and desktop viewports.
