# Home Assistant Local Setup & Development

This repository contains the local setup for [Home Assistant](https://www.home-assistant.io/) with the [home-assistant/core](https://github.com/home-assistant/core) source code mounted directly for local execution and development.

## Architecture

- **Web Dashboard:** [http://localhost:8123](http://localhost:8123)
- **Source Code:** [`./core/homeassistant`](file:///D:/Antigravity%20Projects/IOT_Dashboard/core/homeassistant) (mounted live into the container at `/usr/src/homeassistant/homeassistant`)
- **Version Running:** `2026.12.0.dev0` (from cloned `dev` branch)
- **Configuration Directory:** [`./config`](file:///D:/Antigravity%20Projects/IOT_Dashboard/config) (persists database, yaml configs, logs)

---

## Useful Commands

### Start / Stop the Service
- **Start / Reload:**
  ```powershell
  docker compose up -d
  ```
- **Stop:**
  ```powershell
  docker compose down
  ```
- **Restart (to reload source code edits in `core/`):**
  ```powershell
  docker compose restart
  ```

### Monitoring & Logs
- **View live Home Assistant logs:**
  ```powershell
  docker compose logs -f
  ```
- **Inspect configuration log file:**
  ```powershell
  Get-Content config/home-assistant.log -Tail 50 -Wait
  ```

### Development Workflow
1. Edit any component, platform, or core logic in [`core/homeassistant/`](file:///D:/Antigravity%20Projects/IOT_Dashboard/core/homeassistant).
2. Run `docker compose restart`.
3. Open [http://localhost:8123](http://localhost:8123) to see your changes running immediately.
