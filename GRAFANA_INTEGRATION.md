# Grafana Integration Guide

This guide shows how to integrate your wallbox control script with Grafana alerts based on InfluxDB data.

## Overview

The integration works by:
1. **InfluxDB** stores your metrics (solar production, electricity prices, battery status, etc.)
2. **Grafana** monitors these metrics and triggers alerts when conditions are met
3. **Webhook Server** receives Grafana alerts and triggers wallbox actions
4. **Wallbox Script** executes the requested actions

## Setup Instructions

### 1. Install Webhook Server Dependencies

```bash
# Activate your virtual environment
source wallbox_env/bin/activate

# Install additional dependencies
pip install flask

# Or use requirements.txt
pip install -r requirements.txt
```

### 2. Configure the Webhook Server

Edit `webhook.conf` to match your setup:

```ini
[server]
port = 5000
secret_token = your-secure-random-token-here

[alerts]
high_solar_production.firing = set-mode,solar
low_electricity_price.firing = set-mode,full
high_electricity_price.firing = set-mode,eco
```

### 3. Start the Webhook Server

```bash
# Start the webhook server
python webhook_server.py

# Or run in background
nohup python webhook_server.py &
```

### 4. Configure Grafana Alerts

#### Example Alert: High Solar Production

1. **Create Alert Rule:**
   - Query: `SELECT mean("solar_power") FROM "energy" WHERE time >= now() - 5m GROUP BY time(1m)`
   - Condition: `IS ABOVE 5000` (5kW threshold)
   - Evaluation: Every `1m` for `2m`

2. **Add Webhook Notification Channel:**
   - Type: `Webhook`
   - URL: `http://your-server:5000/webhook/grafana`
   - HTTP Method: `POST`
   - Headers: `Authorization: Bearer your-secure-random-token-here`

#### Example Alert: Low Electricity Price

```json
{
  "alert": {
    "name": "LowElectricityPrice",
    "message": "Electricity price is low - switch to full charging mode",
    "frequency": "5m",
    "conditions": [
      {
        "query": {
          "queryType": "",
          "refId": "A",
          "model": {
            "expr": "electricity_price_per_kwh < 0.10"
          }
        },
        "reducer": {
          "type": "last",
          "params": []
        },
        "evaluator": {
          "params": [0.10],
          "type": "lt"
        }
      }
    ]
  }
}
```

## Example InfluxDB Queries for Alerts

### Solar Production Monitoring
```sql
-- High solar production (switch to solar mode)
SELECT mean("solar_power_kw") 
FROM "energy_production" 
WHERE time >= now() - 5m 
GROUP BY time(1m)

-- Alert condition: > 3.0 kW
```

### Electricity Price Monitoring
```sql
-- Current electricity price
SELECT last("price_per_kwh") 
FROM "electricity_prices" 
WHERE time >= now() - 1h

-- Low price alert: < 0.10 EUR/kWh (switch to full mode)
-- High price alert: > 0.25 EUR/kWh (switch to eco mode)
```

### Battery Status Monitoring
```sql
-- Battery charge level
SELECT last("charge_percentage") 
FROM "battery_status" 
WHERE time >= now() - 5m

-- Battery full: >= 95% (start charging car)
-- Battery low: <= 20% (stop car charging)
```

### Grid Load Monitoring
```sql
-- Grid power consumption
SELECT mean("grid_power_kw") 
FROM "energy_consumption" 
WHERE time >= now() - 5m 
GROUP BY time(1m)

-- High consumption: > 10kW (switch to eco mode)
```

## Alert Rule Examples

### 1. Smart Solar Charging
```yaml
Alert Name: SmartSolarCharging
Condition: solar_power > 3000 AND battery_charge > 50
Action: Start charging in solar mode
Frequency: Check every 2m, trigger after 2 consecutive matches
```

### 2. Price-Based Optimization
```yaml
Alert Name: CheapElectricity  
Condition: electricity_price < 0.10
Action: Switch to full charging mode
Frequency: Check every 5m
```

### 3. Emergency Grid Protection
```yaml
Alert Name: HighGridLoad
Condition: grid_consumption > 15000
Action: Stop charging immediately
Frequency: Check every 30s, trigger immediately
```

## Advanced Integration Examples

### Time-Based Automation with Grafana Variables

Create dashboard variables for:
- `$time_of_day`: Current hour of day
- `$solar_forecast`: Solar production forecast
- `$electricity_price`: Current electricity price

### Multi-Condition Smart Charging

```sql
-- Complex condition combining multiple factors
SELECT 
  mean("solar_power") as solar,
  last("electricity_price") as price,
  last("battery_charge") as battery
FROM "energy_data" 
WHERE time >= now() - 5m

-- Alert logic:
-- IF solar > 4kW AND price < 0.15 AND battery > 30% 
-- THEN start_charging_solar_mode
```

## Webhook API Reference

### Endpoint: `/webhook/grafana`
Receives Grafana alert webhooks.

**Headers:**
```
Authorization: Bearer your-secret-token
Content-Type: application/json
```

**Payload Example:**
```json
{
  "status": "firing",
  "alerts": [{
    "labels": {
      "alertname": "HighSolarProduction"
    },
    "annotations": {
      "description": "Solar production is above 5kW"
    }
  }]
}
```

### Endpoint: `/webhook/test`
Test endpoint for manual testing.

**Example:**
```bash
curl -X POST http://localhost:5000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

## Security Considerations

1. **Use HTTPS** in production
2. **Strong secret token** for webhook authentication
3. **Firewall rules** to restrict webhook access
4. **Rate limiting** to prevent abuse
5. **Log monitoring** for suspicious activity

## Monitoring and Logging

The webhook server logs all activities to:
- Console output
- `webhook.log` file

Monitor logs for:
- Failed webhook authentications
- Wallbox command failures
- Alert processing errors

## Troubleshooting

### Common Issues

1. **Webhook not receiving alerts**
   - Check Grafana notification channel configuration
   - Verify webhook server is running and accessible
   - Check firewall/network connectivity

2. **Authentication failures**
   - Verify secret token matches in both systems
   - Check Authorization header format

3. **Wallbox commands failing**
   - Test wallbox script manually
   - Check wallbox.conf configuration
   - Verify network access to wallbox

### Debug Mode

Run webhook server in debug mode:
```bash
DEBUG=true python webhook_server.py
```

Test with verbose wallbox output:
```bash
# Edit webhook_server.py to add --verbose flag to wallbox commands
```

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/wallbox-webhook.service`:

```ini
[Unit]
Description=Wallbox Webhook Server
After=network.target

[Service]
Type=simple
User=wallbox
WorkingDirectory=/path/to/wallbox
Environment=PATH=/path/to/wallbox_env/bin
ExecStart=/path/to/wallbox_env/bin/python webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable wallbox-webhook
sudo systemctl start wallbox-webhook
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "webhook_server.py"]
```

Build and run:
```bash
docker build -t wallbox-webhook .
docker run -d -p 5000:5000 --name wallbox-webhook wallbox-webhook
```
