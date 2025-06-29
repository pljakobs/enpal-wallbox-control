# Wallbox Control Script

A Python-based automation tool for controlling yoru enpall wallbox (electric vehicle charger) interfaces via web browser automation. This script provides command-line access to start/stop charging, change charging modes, and monitor wallbox status.

## Features

- **Headless Operation**: Runs without GUI by default, perfect for servers and automation
- **Smart Status Check/activate  # On Linux/Mac
# or
wallbox_env\Scripts\acing**: Reads current status and mode before taking actions
- **Multiple Actions**: Start/stop charging, set charging modes (eco/full/solar), get status/mode
- **Configurable**: Easy configuration via config file
- **Verbose Mode**: Optional detailed output for debugging
- **Clean Output**: Minimal output by default, perfect for scripts and automation

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

Alternatively, use the provided `requirements.txt` 

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
python wallbox.py --get-mode)
echo "Current mode: $MODE"
```
t-mode
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
STATUS=$(python wallbo x.py --get-status)
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
