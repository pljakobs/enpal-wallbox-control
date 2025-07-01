# Wallbox Control Script

A Python-based automation tool for controlling wallbox (electric vehicle charger) interfaces via web browser automation. This script provides command-line access to start/stop charging, change charging modes, and monitor wallbox status.

## Features

- **Headless Operation**: Runs without GUI by default, perfect for servers and automation
- **Smart Status Checking**: Reads current status and mode before taking actions
- **Safe Operation**: Prevents conflicting actions (e.g., stopping while finishing)
- **Multiple Actions**: Start/stop charging, set charging modes (eco/full/solar), get status/mode
- **Configurable**: Easy configuration via config file
- **Verbose Mode**: Optional detailed output for debugging
- **Clean Output**: Minimal output by default, perfect for scripts and automation
- **Grafana Integration**: Webhook server for automated responses to InfluxDB metrics (see [GRAFANA_INTEGRATION.md](GRAFANA_INTEGRATION.md))

## Installation

### Prerequisites

- Python 3.7 or higher
- Firefox browser installed on the system
- Network access to the wallbox interface

### Step 1: Clone or Download

```bash
# Clone the repository or download the files
cd /path/to/your/projects
# Copy wallbox.py to your desired location
```

### Step 2: Create Virtual Environment

```bash
# Create a virtual environment
python3 -m venv wallbox_env

# Activate the virtual environment
source wallbox_env/bin/activate  # On Linux/Mac
# or
wallbox_env\Scripts\activate     # On Windows
```

### Step 3: Install Dependencies

```bash
# Install required packages
pip install selenium geckodriver-autoinstaller
```

Alternatively, use the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Step 4: Configuration

On first run, the script will create a default configuration file `wallbox.conf`. Edit this file to match your setup:

```ini
[DEFAULT]
wallbox_url = http://your-wallbox-address/wallbox
page_load_timeout = 5
```

**Configuration Options:**
- `wallbox_url`: The URL of your wallbox web interface
- `page_load_timeout`: Time in seconds to wait for pages to load (default: 5)

## Usage

### Basic Commands

#### Get Current Status
```bash
python wallbox.py --get-status
```
Output: `Finishing`, `Ready`, `Charging`, etc.

#### Get Current Mode
```bash
python wallbox.py --get-mode
```
Output: `Eco`, `Full`, `Solar`

#### Set Charging Mode
```bash
python wallbox.py --set-mode eco
python wallbox.py --set-mode full
python wallbox.py --set-mode solar
```

#### Start/Stop Charging
```bash
python wallbox.py start
python wallbox.py stop
```

### Advanced Options

#### Verbose Mode
Enable detailed output for debugging:
```bash
python wallbox.py --get-status --verbose
```

#### GUI Mode
Force browser to show (for debugging):
```bash
python wallbox.py --get-status --no-headless
```

### Examples

```bash
# Quick status check
python wallbox.py --get-status
# Output: Ready

# Set to eco mode if not already set
python wallbox.py --set-mode eco
# Output: Mode updated: Full -> Eco

# Start charging with verbose output
python wallbox.py start --verbose
# Output: Detailed logging of the process

# Check mode with no extra output (perfect for scripts)
MODE=$(python wallbox.py --get-mode)
echo "Current mode: $MODE"
```

## Safety Features

The script includes several safety mechanisms:

1. **Status Awareness**: Checks current status before taking actions
2. **Mode Detection**: Won't change mode if already set correctly
3. **Finishing Protection**: Prevents stopping while charging cycle is finishing
4. **Error Handling**: Graceful error handling with optional verbose output

## Automation Examples

### Cron Job Examples

```bash
# Check status every hour
0 * * * * /path/to/wallbox_env/bin/python /path/to/wallbox.py --get-status >> /var/log/wallbox.log

# Set to solar mode every morning at 8 AM
0 8 * * * /path/to/wallbox_env/bin/python /path/to/wallbox.py --set-mode solar

# Set to eco mode every evening at 10 PM
0 22 * * * /path/to/wallbox_env/bin/python /path/to/wallbox.py --set-mode eco
```

### Shell Script Example

```bash
#!/bin/bash
# wallbox-auto.sh - Intelligent charging control

# Get current status
STATUS=$(python wallbox.py --get-status)
MODE=$(python wallbox.py --get-mode)

echo "Current status: $STATUS, Mode: $MODE"

# Set to solar mode during day hours
HOUR=$(date +%H)
if [ $HOUR -ge 8 ] && [ $HOUR -le 18 ]; then
    if [ "$MODE" != "Solar" ]; then
        echo "Setting to solar mode for daytime charging"
        python wallbox.py --set-mode solar
    fi
else
    if [ "$MODE" != "Eco" ]; then
        echo "Setting to eco mode for nighttime"
        python wallbox.py --set-mode eco
    fi
fi
```

## Troubleshooting

### Common Issues

1. **"Could not find button" errors**
   - Check that the wallbox URL is correct in `wallbox.conf`
   - Verify the wallbox web interface is accessible
   - Try running with `--verbose` and `--no-headless` to see what's happening

2. **Firefox/Driver issues**
   - Ensure Firefox is installed
   - The script automatically downloads the correct geckodriver
   - Try running with `--verbose` for detailed error messages

3. **Network connectivity**
   - Verify you can access the wallbox URL in a browser
   - Check firewall settings
   - Ensure the wallbox is on the same network or accessible

4. **Permission issues**
   - Ensure the script has permission to create config files
   - Check that the virtual environment is activated

### Debug Mode

For troubleshooting, run with maximum verbosity:

```bash
python wallbox.py --get-status --verbose --no-headless
```

This will:
- Show detailed step-by-step output
- Display the browser window so you can see what's happening
- Print all button texts found on the page

## Command Line Reference

```
usage: wallbox.py [-h] [--get-status] [--get-mode] [--set-mode {eco,full,solar}] 
                  [--no-headless] [-v] [{start,stop}]

Control wallbox charging

positional arguments:
  {start,stop}          Action to perform: start/stop charging

options:
  -h, --help            show this help message and exit
  --get-status          Get current wallbox status
  --get-mode            Get current charging mode
  --set-mode {eco,full,solar}
                        Set charging mode (eco/full/solar)
  --no-headless         Run browser with GUI (headless is default)
  -v, --verbose         Enable verbose output for debugging
```

## Webhook Server

Start a webhook server for remote control via HTTP API:

```bash
python wallbox.py --webhook-server
```

The webhook server provides REST API endpoints for remote wallbox control and integrates with Grafana alerting, MQTT, and other automation systems.

#### Webhook Server Endpoints

**Status and Control:**
- `GET /health` - Health check endpoint
- `GET /wallbox/status` - Get current wallbox status  
- `GET /wallbox/mode` - Get current charging mode
- `POST /wallbox/mode` - Set charging mode (eco/full/solar)
- `POST /wallbox/start` - Start charging
- `POST /wallbox/stop` - Stop charging

**Automation Webhooks:**
- `POST /webhook/grafana` - Grafana alerting webhook for automated responses
- `POST /webhook/mqtt` - MQTT-style webhook for IoT integration

#### Detailed API Reference

**GET /health**
```bash
curl http://localhost:8080/health
# Response: {"status": "healthy", "timestamp": "2025-07-01T12:00:00", "version": "1.0.0"}
```

**GET /wallbox/status**
```bash
curl http://localhost:8080/wallbox/status
# Response: {"status": "Ready", "timestamp": "2025-07-01T12:00:00"}
```

**GET /wallbox/mode**
```bash
curl http://localhost:8080/wallbox/mode
# Response: {"mode": "Eco", "timestamp": "2025-07-01T12:00:00"}
```

**POST /wallbox/mode**
```bash
# Set to solar mode
curl -X POST http://localhost:8080/wallbox/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "solar"}'
# Response: {"success": true, "mode": "solar", "timestamp": "2025-07-01T12:00:00"}

# Valid modes: "eco", "full", "solar"
```

**POST /wallbox/start**
```bash
curl -X POST http://localhost:8080/wallbox/start
# Response: {"success": true, "action": "start", "timestamp": "2025-07-01T12:00:00"}
```

**POST /wallbox/stop**
```bash
curl -X POST http://localhost:8080/wallbox/stop
# Response: {"success": true, "action": "stop", "timestamp": "2025-07-01T12:00:00"}
```

**POST /webhook/grafana** (Grafana Alerting Integration)
```bash
# High solar production alert (auto-switch to solar mode)
curl -X POST http://localhost:8080/webhook/grafana \
  -H "Content-Type: application/json" \
  -d '{
    "state": "alerting",
    "ruleName": "High Solar Production",
    "message": "Solar production > 5kW"
  }'
# Response: {"action": "set_mode_solar", "success": true, "reason": "high_solar_production"}

# Recovery alert (auto-switch back to eco mode)
curl -X POST http://localhost:8080/webhook/grafana \
  -H "Content-Type: application/json" \
  -d '{
    "state": "ok",
    "ruleName": "High Solar Production"
  }'
# Response: {"action": "set_mode_eco", "success": true, "reason": "solar_production_normalized"}
```

**POST /webhook/mqtt** (MQTT-style Commands)
```bash
# MQTT command to start charging
curl -X POST http://localhost:8080/webhook/mqtt \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "wallbox/command",
    "message": "{\"command\": \"start\"}"
  }'
# Response: {"action": "start", "success": true}

# MQTT command to set mode
curl -X POST http://localhost:8080/webhook/mqtt \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "wallbox/command", 
    "message": "{\"command\": \"set_mode\", \"mode\": \"solar\"}"
  }'
# Response: {"action": "set_mode", "mode": "solar", "success": true}

# Solar production data (auto-switch if > 3kW)
curl -X POST http://localhost:8080/webhook/mqtt \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "solar/production",
    "message": "{\"production\": 3500}"
  }'
# Response: {"action": "auto_switch_to_solar", "success": true, "production": 3500}
```

#### Authentication

Enable authentication by setting an auth token in `webhook.conf`:

```ini
[webhook]
auth_token = your-secret-token-here
```

Then include the token in requests:

```bash
curl -H "Authorization: Bearer your-secret-token-here" \
  http://localhost:8080/wallbox/status
```

#### Webhook Configuration

Configure the webhook server in `webhook.conf`:

```ini
[webhook]
host = 0.0.0.0
port = 8080
debug = false

# Optional authentication
auth_token = your-secret-token-here

# InfluxDB integration
influxdb_url = http://localhost:8086
influxdb_token = your-token
influxdb_org = your-org
influxdb_bucket = wallbox

# Logging
log_level = INFO
wallbox_config = wallbox.conf
```

#### Running as System Service

Install as a systemd service for automatic startup:

```bash
# Copy unit file
sudo cp wallbox_webhook.unit /etc/systemd/system/wallbox-webhook.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable wallbox-webhook.service
sudo systemctl start wallbox-webhook.service

# Check status
sudo systemctl status wallbox-webhook.service
```

See [GRAFANA_INTEGRATION.md](GRAFANA_INTEGRATION.md) for detailed automation examples.

## Dependencies

- **selenium**: Web browser automation
- **geckodriver-autoinstaller**: Automatic Firefox driver management
- **configparser**: Configuration file handling (built-in)
- **argparse**: Command line argument parsing (built-in)

## License

This project is provided as-is for educational and automation purposes. Use at your own risk and ensure compatibility with your wallbox system.

## Contributing

Feel free to submit issues, feature requests, or improvements. When reporting issues, please include:

- Python version
- Operating system
- Wallbox model/interface type
- Error messages with `--verbose` output
- Configuration file contents (without sensitive information)
