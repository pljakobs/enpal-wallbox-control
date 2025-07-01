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
from selenium.webdriver.firefox.options import Options
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


class WallboxController:
    """Class to control wallbox operations"""
    
    def __init__(self, config_file='wallbox.conf', headless=True, verbose=False):
        """Initialize the wallbox controller"""
        if isinstance(config_file, str):
            # Load config from file
            config = configparser.ConfigParser()
            if os.path.exists(config_file):
                config.read(config_file)
                self.config = config['DEFAULT'] if 'DEFAULT' in config else DEFAULT_CONFIG
            else:
                self.config = DEFAULT_CONFIG
        else:
            # Use provided config dict
            self.config = config_file
            
        self.headless = headless
        self.verbose = verbose
        self.driver = None
        
        # Map actions to button texts
        self.action_button_map = {
            'start': 'START CHARGING',
            'stop': 'STOP CHARGING', 
            'eco': 'SET ECO',
            'full': 'SET FULL',
            'solar': 'SET SOLAR'
        }
    
    def vprint(self, *args_to_print, **kwargs):
        """Print only if verbose mode is enabled"""
        if self.verbose:
            print(*args_to_print, **kwargs)
    
    def _setup_driver(self):
        """Setup the Selenium driver"""
        if self.driver:
            return  # Already set up
            
        geckodriver_autoinstaller.install()
        
        firefox_options = Options()
        if self.headless:
            self.vprint("Running in headless mode (no GUI)")
            firefox_options.add_argument("--headless")
        else:
            self.vprint("Running with GUI")
        
        self.driver = webdriver.Firefox(options=firefox_options)
    
    def _navigate_to_wallbox(self):
        """Navigate to the wallbox interface"""
        wallbox_url = self.config.get('wallbox_url', DEFAULT_CONFIG['wallbox_url'])
        self.vprint(f"Navigating to wallbox interface: {wallbox_url}")
        self.driver.get(wallbox_url)
        
        # Wait for page to load
        timeout = int(self.config.get('page_load_timeout', DEFAULT_CONFIG['page_load_timeout']))
        self.vprint(f"Waiting {timeout} seconds for page to load...")
        time.sleep(timeout)
        
        self.vprint(f"Page title: {self.driver.title}")
    
    def _get_current_status_and_mode(self):
        """Read the current status and mode from the wallbox interface"""
        try:
            # Get all text content from the page
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            
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
            self.vprint(f"Error reading status/mode: {e}")
            return None, None
    
    def _should_proceed_with_action(self, action, current_status, current_mode):
        """Determine if the action should proceed based on current status and mode"""
        self.vprint(f"Current Status: {current_status}")
        self.vprint(f"Current Mode: {current_mode}")
        
        # Smart logic for when to proceed with actions
        if action == 'start':
            if current_status and 'charging' in current_status.lower():
                self.vprint("Already charging, skipping start action")
                return False
            if current_status and 'finishing' in current_status.lower():
                self.vprint("Currently finishing, will proceed with start")
                return True
                
        elif action == 'stop':
            if current_status and ('standby' in current_status.lower() or 'stopped' in current_status.lower()):
                self.vprint("Already stopped/standby, skipping stop action")
                return False
                
        self.vprint(f"Proceeding with {action} action")
        return True
    
    def _find_and_click_button(self, action):
        """Find and click the button for the specified action"""
        target_button_text = self.action_button_map[action]
        self.vprint(f"Looking for '{target_button_text}' button...")
        
        # Find all buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        self.vprint(f"Found {len(buttons)} buttons on the page")
        
        target_button = None
        for i, button in enumerate(buttons):
            button_text = button.text or button.get_attribute("value") or ""
            self.vprint(f"Button {i+1}: '{button_text}'")
            if target_button_text in button_text:
                target_button = button
                self.vprint(f"Found {target_button_text} button (Button {i+1})")
                break
        
        if target_button:
            target_button.click()
            self.vprint(f"Successfully clicked the {action} button!")
            return True
        else:
            self.vprint(f"Could not find {target_button_text} button!")
            return False
    
    def _ensure_driver_ready(self):
        """Ensure driver is set up and navigated to wallbox"""
        if not self.driver:
            self._setup_driver()
            self._navigate_to_wallbox()
    
    def get_status(self):
        """Get current wallbox status"""
        try:
            self._ensure_driver_ready()
            status, _ = self._get_current_status_and_mode()
            return status or 'Unknown'
        except Exception as e:
            self.vprint(f"Error getting status: {e}")
            return 'Error'
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def get_mode(self):
        """Get current wallbox charging mode"""
        try:
            self._ensure_driver_ready()
            _, mode = self._get_current_status_and_mode()
            return mode or 'Unknown'
        except Exception as e:
            self.vprint(f"Error getting mode: {e}")
            return 'Error'
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def set_mode(self, mode):
        """Set wallbox charging mode"""
        valid_modes = ['eco', 'full', 'solar']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {valid_modes}")
        
        try:
            self._ensure_driver_ready()
            current_status, current_mode = self._get_current_status_and_mode()
            
            # Check if mode is already set correctly
            mode_map = {'eco': 'Eco', 'full': 'Full', 'solar': 'Solar'}
            expected_mode = mode_map[mode]
            
            if current_mode and expected_mode.lower() in current_mode.lower():
                self.vprint(f"Mode is already set to {expected_mode}, no action needed")
                return True
            else:
                self.vprint(f"Setting mode from {current_mode} to {expected_mode}")
                success = self._find_and_click_button(mode)
                if success:
                    time.sleep(3)
                    new_status, new_mode = self._get_current_status_and_mode()
                    self.vprint(f"Mode updated: {current_mode} -> {new_mode}")
                return success
                
        except Exception as e:
            self.vprint(f"Error setting mode: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def start_charging(self):
        """Start charging"""
        try:
            self._ensure_driver_ready()
            current_status, current_mode = self._get_current_status_and_mode()
            
            if not self._should_proceed_with_action('start', current_status, current_mode):
                return True  # Already in desired state
            
            success = self._find_and_click_button('start')
            if success:
                time.sleep(3)
                new_status, new_mode = self._get_current_status_and_mode()
                self.vprint(f"Status: {current_status} -> {new_status}")
            
            return success
            
        except Exception as e:
            self.vprint(f"Error starting charging: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def stop_charging(self):
        """Stop charging"""
        try:
            self._ensure_driver_ready()
            current_status, current_mode = self._get_current_status_and_mode()
            
            if not self._should_proceed_with_action('stop', current_status, current_mode):
                return True  # Already in desired state
            
            success = self._find_and_click_button('stop')
            if success:
                time.sleep(3)
                new_status, new_mode = self._get_current_status_and_mode()
                self.vprint(f"Status: {current_status} -> {new_status}")
            
            return success
            
        except Exception as e:
            self.vprint(f"Error stopping charging: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None


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
    group.add_argument('--webhook-server', action='store_true',
                       help='Start webhook server for remote control')
    
    # Browser options
    parser.add_argument('--no-headless', action='store_true', 
                       help='Run browser with GUI (headless is default)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output for debugging')
    
    return parser.parse_args()

# Parse command line arguments
args = parse_arguments()

# Handle webhook server mode
if args.webhook_server:
    print("Starting webhook server...")
    try:
        from webhook_server import WebhookServer
        server = WebhookServer()
        server.run()
    except ImportError:
        print("Error: webhook_server.py not found or has import errors.")
        print("Make sure Flask is installed: pip install flask")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nWebhook server stopped.")
        sys.exit(0)

# Load configuration
config = load_config()

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
