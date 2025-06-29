#!/usr/bin/python3
import sys
import argparse
import configparser
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
import geckodriver_autoinstaller
import time

# Default configuration
DEFAULT_CONFIG = {
    'wallbox_url': 'http://enpal.fritz.box/wallbox',
    'page_load_timeout': '5'
}

def load_config():
    """Load configuration from config file or use defaults"""
    config = configparser.ConfigParser()
    config_file = 'wallbox.conf'
    
    # Create default config file if it doesn't exist
    if not os.path.exists(config_file):
        config['DEFAULT'] = DEFAULT_CONFIG
        with open(config_file, 'w') as f:
            config.write(f)
        print(f"Created default configuration file: {config_file}")
    
    # Load existing config
    config.read(config_file)
    return config['DEFAULT']

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Control wallbox charging')
    
    # Create mutually exclusive group for main actions
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('action', nargs='?', choices=['start', 'stop'], 
                       help='Action to perform: start/stop charging')
    group.add_argument('--get-status', action='store_true',
                       help='Get current wallbox status')
    group.add_argument('--get-mode', action='store_true',
                       help='Get current charging mode')
    group.add_argument('--set-mode', choices=['eco', 'full', 'solar'],
                       help='Set charging mode (eco/full/solar)')
    
    # Browser options
    parser.add_argument('--no-headless', action='store_true', 
                       help='Run browser with GUI (headless is default)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output for debugging')
    
    return parser.parse_args()

# Map actions to button texts
ACTION_BUTTON_MAP = {
    'start': 'START CHARGING',
    'stop': 'STOP CHARGING', 
    'eco': 'SET ECO',
    'full': 'SET FULL',
    'solar': 'SET SOLAR'
}

def get_current_status_and_mode(driver):
    """Read the current status and mode from the wallbox interface"""
    try:
        # Get all text content from the page
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Look for status and mode information
        status = None
        mode = None
        
        # Split into lines and look for relevant information
        lines = body_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Status'):
                # Extract status (e.g., "Status: Finishing" -> "Finishing")
                if ':' in line:
                    status = line.split(':', 1)[1].strip()
                else:
                    status = line.replace('Status', '').strip()
            elif line.startswith('Mode'):
                # Extract mode (e.g., "Mode Eco" -> "Eco")
                mode = line.replace('Mode', '').strip()
        
        return status, mode
    except Exception as e:
        print(f"Error reading status/mode: {e}")
        return None, None

def should_proceed_with_action(action, current_status, current_mode):
    """Determine if the action should proceed based on current status and mode"""
    vprint(f"Current Status: {current_status}")
    vprint(f"Current Mode: {current_mode}")
    
    # If we can't read status/mode, proceed with caution
    if current_status is None or current_mode is None:
        vprint("Warning: Could not read current status/mode, proceeding anyway...")
        return True
    
    # Check if charging is still finishing - only block stop action
    if current_status and "finishing" in current_status.lower() and action == 'stop':
        always_print(f"Charging cycle is still finishing (Status: {current_status})")
        always_print("Waiting for current cycle to complete before stopping...")
        return False
    
    # Check if mode is already set correctly
    mode_map = {
        'eco': 'Eco',
        'full': 'Full', 
        'solar': 'Solar'
    }
    
    if action in mode_map:
        expected_mode = mode_map[action]
        if current_mode and expected_mode.lower() in current_mode.lower():
            vprint(f"Mode is already set to {expected_mode}, no action needed")
            return False
    
    # For start/stop actions, always proceed (user knows what they want)
    if action in ['start', 'stop']:
        return True
    
    vprint(f"Proceeding with {action} action")
    return True

def find_and_click_button(driver, action):
    """Find and click the button for the specified action"""
    target_button_text = ACTION_BUTTON_MAP[action]
    vprint(f"Looking for '{target_button_text}' button...")
    
    # Find all buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    vprint(f"Found {len(buttons)} buttons on the page")
    
    target_button = None
    for i, button in enumerate(buttons):
        button_text = button.text or button.get_attribute("value") or ""
        vprint(f"Button {i+1}: '{button_text}'")
        if target_button_text in button_text:
            target_button = button
            vprint(f"Found {target_button_text} button (Button {i+1})")
            break
    
    if target_button:
        vprint(f"Clicking the {target_button_text} button...")
        target_button.click()
        vprint(f"Successfully clicked the {action} button!")
        return True
    else:
        always_print(f"Could not find {target_button_text} button!")
        return False

# Parse command line arguments
args = parse_arguments()

# Load configuration
config = load_config()

def vprint(*args_to_print, **kwargs):
    """Print only if verbose mode is enabled"""
    if args.verbose:
        print(*args_to_print, **kwargs)

def always_print(*args_to_print, **kwargs):
    """Always print (for important messages)"""
    print(*args_to_print, **kwargs)

# Determine what action to take
if args.get_status:
    action_type = 'get_status'
    vprint("Requested action: Get status")
elif args.get_mode:
    action_type = 'get_mode'
    vprint("Requested action: Get mode")
elif args.set_mode:
    action_type = 'set_mode'
    action_value = args.set_mode
    vprint(f"Requested action: Set mode to {action_value}")
else:
    action_type = 'action'
    action_value = args.action
    vprint(f"Requested action: {action_value}")

# Install and set up Firefox driver
geckodriver_autoinstaller.install()

# Check if we should run in headless mode
def should_run_headless():
    # If --no-headless is specified, force GUI mode
    if args.no_headless:
        return False
    # Otherwise, default to headless mode
    return True

# Set up Firefox options
from selenium.webdriver.firefox.options import Options
firefox_options = Options()

if should_run_headless():
    vprint("Running in headless mode (no GUI)")
    firefox_options.add_argument("--headless")
else:
    vprint("Running with GUI")

# Set up Firefox driver
driver = webdriver.Firefox(options=firefox_options)

try:
    # Navigate to the wallbox interface
    wallbox_url = config.get('wallbox_url', DEFAULT_CONFIG['wallbox_url'])
    vprint(f"Navigating to wallbox interface: {wallbox_url}")
    driver.get(wallbox_url)
    
    # Wait for page to load
    timeout = int(config.get('page_load_timeout', DEFAULT_CONFIG['page_load_timeout']))
    vprint(f"Waiting {timeout} seconds for page to load...")
    time.sleep(timeout)
    
    # Get page title and print it
    vprint(f"Page title: {driver.title}")
    
    # Read current status and mode
    vprint("Reading current wallbox status and mode...")
    current_status, current_mode = get_current_status_and_mode(driver)
    
    # Handle different action types
    if action_type == 'get_status':
        always_print(current_status or 'Unknown')
        
    elif action_type == 'get_mode':
        always_print(current_mode or 'Unknown')
        
    elif action_type == 'set_mode':
        # Check if mode is already set correctly
        mode_map = {'eco': 'Eco', 'full': 'Full', 'solar': 'Solar'}
        expected_mode = mode_map[action_value]
        
        if current_mode and expected_mode.lower() in current_mode.lower():
            vprint(f"Mode is already set to {expected_mode}, no action needed")
            always_print(f"Mode: {current_mode} (no change needed)")
        else:
            vprint(f"Setting mode from {current_mode} to {expected_mode}")
            success = find_and_click_button(driver, action_value)
            if success:
                time.sleep(3)
                new_status, new_mode = get_current_status_and_mode(driver)
                always_print(f"Mode updated: {current_mode} -> {new_mode}")
            else:
                always_print(f"Failed to set mode to {action_value}")
                
    elif action_type == 'action':
        # Check if we should proceed with the action
        if not should_proceed_with_action(action_value, current_status, current_mode):
            always_print("Action cancelled based on current status/mode")
        else:
            # Find and click the requested button
            success = find_and_click_button(driver, action_value)
            
            if success:
                # Wait a moment to see the result
                time.sleep(3)
                
                # Read status/mode again to see if anything changed
                vprint("Reading updated status and mode...")
                new_status, new_mode = get_current_status_and_mode(driver)
                if new_status != current_status or new_mode != current_mode:
                    always_print(f"Status: {current_status} -> {new_status}")
                    if new_mode != current_mode:
                        always_print(f"Mode: {current_mode} -> {new_mode}")
                else:
                    vprint("No changes detected in status/mode")
                    always_print(f"Action '{action_value}' completed")
                    
            else:
                always_print(f"Failed to execute action: {action_value}")
    
except Exception as e:
    always_print(f"An error occurred: {e}")
    if args.verbose:
        import traceback
        traceback.print_exc()
    
finally:
    vprint("Closing browser...")
    driver.quit()
