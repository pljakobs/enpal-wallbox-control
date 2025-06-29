#!/usr/bin/env python3
"""
Webhook server for receiving Grafana alerts and triggering wallbox actions
"""

from flask import Flask, request, jsonify
import subprocess
import json
import logging
from datetime import datetime
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),
        logging.StreamHandler()
    ]
)

# Configuration
WALLBOX_SCRIPT = './wallbox.py'
SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET', 'your-secret-token-here')

def run_wallbox_command(action, mode=None):
    """Execute wallbox script with given parameters"""
    try:
        if mode:
            cmd = ['python', WALLBOX_SCRIPT, '--set-mode', mode]
        else:
            cmd = ['python', WALLBOX_SCRIPT, action]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Command timed out'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/webhook/grafana', methods=['POST'])
def grafana_webhook():
    """Handle Grafana webhook alerts"""
    
    # Verify secret token (basic security)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer ') or auth_header[7:] != SECRET_TOKEN:
        logging.warning(f"Unauthorized webhook attempt from {request.remote_addr}")
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        logging.info(f"Received Grafana alert: {json.dumps(data, indent=2)}")
        
        # Extract alert information
        alerts = data.get('alerts', [])
        if not alerts:
            return jsonify({'error': 'No alerts in payload'}), 400
        
        alert = alerts[0]  # Process first alert
        alert_name = alert.get('labels', {}).get('alertname', 'Unknown')
        status = data.get('status', 'unknown')
        
        # Determine action based on alert
        action_result = process_alert(alert_name, status, alert)
        
        return jsonify({
            'message': 'Alert processed successfully',
            'alert': alert_name,
            'status': status,
            'action_result': action_result
        })
        
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500

def process_alert(alert_name, status, alert_data):
    """Process specific alert and determine wallbox action"""
    
    # Example alert processing logic
    actions = {
        'HighSolarProduction': {
            'firing': ('set-mode', 'solar'),
            'resolved': None
        },
        'LowElectricityPrice': {
            'firing': ('set-mode', 'full'),
            'resolved': None
        },
        'HighElectricityPrice': {
            'firing': ('set-mode', 'eco'),
            'resolved': None
        },
        'SolarProductionHigh': {
            'firing': ('start', None),
            'resolved': None
        },
        'BatteryFull': {
            'firing': ('start', None),
            'resolved': ('stop', None)
        },
        'EmergencyStop': {
            'firing': ('stop', None),
            'resolved': None
        }
    }
    
    if alert_name in actions:
        action_config = actions[alert_name].get(status)
        if action_config:
            action, mode = action_config
            logging.info(f"Executing action: {action} {mode or ''}")
            return run_wallbox_command(action, mode)
        else:
            logging.info(f"No action configured for alert {alert_name} with status {status}")
            return {'success': True, 'message': 'No action required'}
    else:
        logging.warning(f"Unknown alert: {alert_name}")
        return {'success': False, 'error': f'Unknown alert: {alert_name}'}

@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Test endpoint for webhook functionality"""
    data = request.get_json() or {}
    action = data.get('action', 'start')
    mode = data.get('mode')
    
    logging.info(f"Test webhook called with action: {action}, mode: {mode}")
    result = run_wallbox_command(action, mode)
    
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'wallbox-webhook'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logging.info(f"Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
