#!/usr/bin/env python3
"""
Wallbox Webhook Server

A Flask-based webhook server for controlling wallbox operations remotely.
Supports Grafana alerting, MQTT integration, and general HTTP webhooks.
"""

import os
import sys
import json
import logging
import argparse
import configparser
from datetime import datetime
from typing import Dict, Any, Optional

import flask
from flask import Flask, request, jsonify
import requests

# Add the current directory to the path so we can import wallbox
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from wallbox import WallboxController
except ImportError:
    print("Error: Could not import WallboxController from wallbox.py")
    print("Make sure wallbox.py is in the same directory as this webhook server.")
    sys.exit(1)


class WebhookServer:
    """Webhook server for wallbox control"""
    
    def __init__(self, config_file: str = "webhook.conf"):
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
        self.app = Flask(__name__)
        self.wallbox = None
        self.setup_routes()
    
    def load_config(self) -> Dict[str, Any]:
        """Load webhook server configuration"""
        config = {
            'host': '0.0.0.0',
            'port': 8080,
            'debug': False,
            'auth_token': None,
            'influxdb_url': None,
            'influxdb_token': None,
            'influxdb_org': None,
            'influxdb_bucket': None,
            'mqtt_broker': None,
            'mqtt_port': 1883,
            'mqtt_topic': 'wallbox/status',
            'log_level': 'INFO',
            'wallbox_config': 'wallbox.conf'
        }
        
        if os.path.exists(self.config_file):
            parser = configparser.ConfigParser()
            parser.read(self.config_file)
            
            if 'webhook' in parser:
                for key, value in parser['webhook'].items():
                    if key in ['port', 'mqtt_port']:
                        config[key] = int(value)
                    elif key in ['debug']:
                        config[key] = value.lower() in ['true', '1', 'yes']
                    else:
                        config[key] = value
        
        return config
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['log_level'].upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.before_request
        def authenticate():
            """Simple token-based authentication"""
            if self.config.get('auth_token'):
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({'error': 'Missing or invalid authorization header'}), 401
                
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                if token != self.config['auth_token']:
                    return jsonify({'error': 'Invalid token'}), 401
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        @self.app.route('/wallbox/status', methods=['GET'])
        def get_status():
            """Get wallbox status"""
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                status = self.wallbox.get_status()
                self.logger.info(f"Status requested: {status}")
                
                response = {
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to InfluxDB if configured
                self.send_to_influxdb('wallbox_status', {'status': status})
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallbox/mode', methods=['GET'])
        def get_mode():
            """Get wallbox charging mode"""
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                mode = self.wallbox.get_mode()
                self.logger.info(f"Mode requested: {mode}")
                
                response = {
                    'mode': mode,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to InfluxDB if configured
                self.send_to_influxdb('wallbox_mode', {'mode': mode})
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error getting mode: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallbox/mode', methods=['POST'])
        def set_mode():
            """Set wallbox charging mode"""
            try:
                data = request.get_json()
                if not data or 'mode' not in data:
                    return jsonify({'error': 'Missing mode parameter'}), 400
                
                mode = data['mode']
                if mode not in ['eco', 'full', 'solar']:
                    return jsonify({'error': 'Invalid mode. Must be eco, full, or solar'}), 400
                
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                success = self.wallbox.set_mode(mode)
                self.logger.info(f"Mode set to {mode}: {'success' if success else 'failed'}")
                
                response = {
                    'success': success,
                    'mode': mode,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to InfluxDB if configured
                self.send_to_influxdb('wallbox_mode_change', {
                    'mode': mode,
                    'success': success
                })
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error setting mode: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallbox/start', methods=['POST'])
        def start_charging():
            """Start charging"""
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                success = self.wallbox.start_charging()
                self.logger.info(f"Start charging: {'success' if success else 'failed'}")
                
                response = {
                    'success': success,
                    'action': 'start',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to InfluxDB if configured
                self.send_to_influxdb('wallbox_action', {
                    'action': 'start',
                    'success': success
                })
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error starting charging: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallbox/stop', methods=['POST'])
        def stop_charging():
            """Stop charging"""
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                success = self.wallbox.stop_charging()
                self.logger.info(f"Stop charging: {'success' if success else 'failed'}")
                
                response = {
                    'success': success,
                    'action': 'stop',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to InfluxDB if configured
                self.send_to_influxdb('wallbox_action', {
                    'action': 'stop',
                    'success': success
                })
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error stopping charging: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/webhook/grafana', methods=['POST'])
        def grafana_webhook():
            """Handle Grafana alerting webhooks"""
            try:
                data = request.get_json()
                self.logger.info(f"Grafana webhook received: {json.dumps(data, indent=2)}")
                
                # Extract alert information
                state = data.get('state', 'unknown')
                rule_name = data.get('ruleName', 'unknown')
                
                # Handle different alert states
                if state == 'alerting':
                    # Handle alerting state (e.g., high solar production)
                    response = self.handle_alert(data)
                elif state == 'ok':
                    # Handle recovery state
                    response = self.handle_recovery(data)
                else:
                    # Handle other states (no_data, etc.)
                    response = {'message': f'Alert state {state} acknowledged'}
                
                # Send acknowledgment to InfluxDB
                self.send_to_influxdb('grafana_alert', {
                    'state': state,
                    'rule_name': rule_name,
                    'handled': True
                })
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error handling Grafana webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/webhook/mqtt', methods=['POST'])
        def mqtt_webhook():
            """Handle MQTT-style webhooks"""
            try:
                data = request.get_json()
                topic = data.get('topic', '')
                message = data.get('message', '')
                
                self.logger.info(f"MQTT webhook - Topic: {topic}, Message: {message}")
                
                # Handle different topics
                if 'wallbox/command' in topic:
                    response = self.handle_mqtt_command(message)
                elif 'solar/production' in topic:
                    response = self.handle_solar_data(message)
                else:
                    response = {'message': 'MQTT webhook acknowledged'}
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error handling MQTT webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Endpoint not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def handle_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle alerting state"""
        rule_name = alert_data.get('ruleName', '')
        
        if 'solar' in rule_name.lower() and 'high' in rule_name.lower():
            # High solar production - switch to solar mode
            self.logger.info("High solar production detected, switching to solar mode")
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                success = self.wallbox.set_mode('solar')
                return {
                    'action': 'set_mode_solar',
                    'success': success,
                    'reason': 'high_solar_production'
                }
            except Exception as e:
                self.logger.error(f"Error setting solar mode: {e}")
                return {'error': str(e)}
        
        return {'message': 'Alert acknowledged but no action taken'}
    
    def handle_recovery(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recovery state"""
        rule_name = alert_data.get('ruleName', '')
        
        if 'solar' in rule_name.lower():
            # Solar production back to normal - switch to eco mode
            self.logger.info("Solar production normalized, switching to eco mode")
            try:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                success = self.wallbox.set_mode('eco')
                return {
                    'action': 'set_mode_eco',
                    'success': success,
                    'reason': 'solar_production_normalized'
                }
            except Exception as e:
                self.logger.error(f"Error setting eco mode: {e}")
                return {'error': str(e)}
        
        return {'message': 'Recovery acknowledged but no action taken'}
    
    def handle_mqtt_command(self, message: str) -> Dict[str, Any]:
        """Handle MQTT command messages"""
        try:
            command_data = json.loads(message)
            command = command_data.get('command', '')
            
            if not self.wallbox:
                self.wallbox = WallboxController(self.config['wallbox_config'])
            
            if command == 'start':
                success = self.wallbox.start_charging()
                return {'action': 'start', 'success': success}
            elif command == 'stop':
                success = self.wallbox.stop_charging()
                return {'action': 'stop', 'success': success}
            elif command == 'set_mode':
                mode = command_data.get('mode', 'eco')
                success = self.wallbox.set_mode(mode)
                return {'action': 'set_mode', 'mode': mode, 'success': success}
            else:
                return {'error': f'Unknown command: {command}'}
                
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON in MQTT message'}
        except Exception as e:
            self.logger.error(f"Error handling MQTT command: {e}")
            return {'error': str(e)}
    
    def handle_solar_data(self, message: str) -> Dict[str, Any]:
        """Handle solar production data"""
        try:
            solar_data = json.loads(message)
            production = solar_data.get('production', 0)
            
            # Example logic: switch to solar mode if production > 3kW
            if production > 3000:
                if not self.wallbox:
                    self.wallbox = WallboxController(self.config['wallbox_config'])
                
                current_mode = self.wallbox.get_mode()
                if current_mode != 'solar':
                    success = self.wallbox.set_mode('solar')
                    return {
                        'action': 'auto_switch_to_solar',
                        'success': success,
                        'production': production
                    }
            
            return {'message': 'Solar data processed', 'production': production}
            
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON in solar data'}
        except Exception as e:
            self.logger.error(f"Error handling solar data: {e}")
            return {'error': str(e)}
    
    def send_to_influxdb(self, measurement: str, fields: Dict[str, Any]):
        """Send data to InfluxDB if configured"""
        if not all([
            self.config.get('influxdb_url'),
            self.config.get('influxdb_token'),
            self.config.get('influxdb_org'),
            self.config.get('influxdb_bucket')
        ]):
            return
        
        try:
            # Simple InfluxDB line protocol
            timestamp = int(datetime.now().timestamp() * 1000000000)  # nanoseconds
            
            field_strings = []
            for key, value in fields.items():
                if isinstance(value, str):
                    field_strings.append(f'{key}="{value}"')
                elif isinstance(value, bool):
                    field_strings.append(f'{key}={str(value).lower()}')
                else:
                    field_strings.append(f'{key}={value}')
            
            line = f"{measurement} {','.join(field_strings)} {timestamp}"
            
            headers = {
                'Authorization': f'Token {self.config["influxdb_token"]}',
                'Content-Type': 'text/plain'
            }
            
            url = f"{self.config['influxdb_url']}/api/v2/write"
            params = {
                'org': self.config['influxdb_org'],
                'bucket': self.config['influxdb_bucket']
            }
            
            response = requests.post(url, headers=headers, params=params, data=line, timeout=5)
            
            if response.status_code != 204:
                self.logger.warning(f"InfluxDB write failed: {response.status_code}")
            
        except Exception as e:
            self.logger.warning(f"Failed to send data to InfluxDB: {e}")
    
    def run(self):
        """Run the webhook server"""
        self.logger.info(f"Starting webhook server on {self.config['host']}:{self.config['port']}")
        self.logger.info(f"Authentication: {'enabled' if self.config.get('auth_token') else 'disabled'}")
        
        self.app.run(
            host=self.config['host'],
            port=self.config['port'],
            debug=self.config['debug']
        )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Wallbox Webhook Server')
    parser.add_argument('--config', '-c', default='webhook.conf',
                        help='Configuration file path (default: webhook.conf)')
    parser.add_argument('--port', '-p', type=int,
                        help='Port to run server on (overrides config)')
    parser.add_argument('--host', default=None,
                        help='Host to bind to (overrides config)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    
    args = parser.parse_args()
    
    server = WebhookServer(args.config)
    
    # Override config with command line args
    if args.port:
        server.config['port'] = args.port
    if args.host:
        server.config['host'] = args.host
    if args.debug:
        server.config['debug'] = True
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down webhook server...")
    except Exception as e:
        print(f"Error starting webhook server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
